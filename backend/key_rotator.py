"""
malayaLLM v2.3.0 - Multi-Key Fallback & Rotation Engine
Accepts multiple API keys across Google Gemini, OpenRouter, Groq, NVIDIA NIM, and local Ollama.
Features automated round-robin rotation, 429 rate-limit backoff, and cross-provider failover.
"""

import os
import sys
import time
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Tuple, Callable

# Setup logging
logger = logging.getLogger("KeyRotator")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [KeyRotator] %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
VAULT_FILE = os.path.join(DATA_DIR, "keys_vault.json")
os.makedirs(DATA_DIR, exist_ok=True)


class KeyPool:
    """Manages rotation, cooldowns, and statistics for a single provider's keys."""
    def __init__(self, provider: str, keys: Optional[List[str]] = None):
        self.provider = provider
        self.keys: List[str] = [k.strip() for k in (keys or []) if k and k.strip()]
        self.current_idx = 0
        self.cooldowns: Dict[str, float] = {}  # key -> timestamp available again
        self.success_count: Dict[str, int] = {k: 0 for k in self.keys}
        self.fail_count: Dict[str, int] = {k: 0 for k in self.keys}

    def set_keys(self, new_keys: List[str]):
        cleaned = [k.strip() for k in new_keys if k and k.strip()]
        self.keys = cleaned
        for k in self.keys:
            if k not in self.success_count:
                self.success_count[k] = 0
            if k not in self.fail_count:
                self.fail_count[k] = 0

    def add_key(self, key: str):
        k = key.strip()
        if k and k not in self.keys:
            self.keys.append(k)
            self.success_count[k] = 0
            self.fail_count[k] = 0

    def get_active_key(self) -> Optional[str]:
        if not self.keys:
            return None
        now = time.time()
        total = len(self.keys)
        for i in range(total):
            idx = (self.current_idx + i) % total
            candidate = self.keys[idx]
            if now >= self.cooldowns.get(candidate, 0):
                self.current_idx = (idx + 1) % total
                return candidate

        # If all keys in cooldown, return shortest cooldown key
        shortest_key = min(self.keys, key=lambda k: self.cooldowns.get(k, 0))
        return shortest_key

    def mark_rate_limited(self, key: str, cooldown_seconds: float = 60.0):
        self.cooldowns[key] = time.time() + cooldown_seconds
        self.fail_count[key] = self.fail_count.get(key, 0) + 1
        masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
        logger.warning(
            f"Provider [{self.provider}] key {masked} rate-limited (429/Quota). "
            f"Cooldown: {cooldown_seconds}s. Failures: {self.fail_count[key]}"
        )

    def mark_success(self, key: str):
        self.success_count[key] = self.success_count.get(key, 0) + 1
        if key in self.cooldowns and time.time() >= self.cooldowns[key]:
            del self.cooldowns[key]

    def get_status(self) -> Dict[str, Any]:
        now = time.time()
        return {
            "provider": self.provider,
            "total_keys": len(self.keys),
            "available_keys": sum(1 for k in self.keys if now >= self.cooldowns.get(k, 0)),
            "in_cooldown": sum(1 for k in self.keys if now < self.cooldowns.get(k, 0)),
            "keys_detail": [
                {
                    "masked": f"{k[:4]}...{k[-4:]}" if len(k) > 8 else "***",
                    "success": self.success_count.get(k, 0),
                    "fails": self.fail_count.get(k, 0),
                    "cooling_down": now < self.cooldowns.get(k, 0),
                    "cooldown_remaining_sec": max(0, int(self.cooldowns.get(k, 0) - now))
                }
                for k in self.keys
            ]
        }


class KeyRotator:
    """
    Multi-Key Fallback & Rotation Engine across Google Gemini, OpenRouter, Groq, NVIDIA NIM, and Ollama.
    """
    SUPPORTED_PROVIDERS = ["groq", "gemini", "openrouter", "nvidia", "ollama"]
    DEFAULT_FALLBACK_CASCADE = ["groq", "gemini", "openrouter", "nvidia", "ollama"]

    def __init__(self):
        self.pools: Dict[str, KeyPool] = {
            p: KeyPool(p) for p in self.SUPPORTED_PROVIDERS
        }
        self.ollama_endpoint = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2")
        self.fallback_cascade = list(self.DEFAULT_FALLBACK_CASCADE)
        self.load_from_vault()
        self.import_env_keys()

    def import_env_keys(self):
        """Scans process environment variables for initial keys if not already loaded."""
        env_mappings = {
            "groq": ["GROQ_API_KEY", "GROQ_KEY"],
            "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            "openrouter": ["OPENROUTER_API_KEY", "OPENROUTER_KEY"],
            "nvidia": ["NVIDIA_API_KEY", "NVIDIA_NIM_KEY"]
        }
        updated = False
        for provider, var_names in env_mappings.items():
            for v in var_names:
                val = os.environ.get(v)
                if val and val.strip() and val.strip() not in self.pools[provider].keys:
                    self.pools[provider].add_key(val.strip())
                    updated = True
        if updated:
            self.save_to_vault()

    def load_from_vault(self):
        """Loads keys from persistent JSON vault file."""
        if not os.path.exists(VAULT_FILE):
            return
        try:
            with open(VAULT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            keys_dict = data.get("keys", {})
            for provider, klist in keys_dict.items():
                if provider in self.pools and isinstance(klist, list):
                    self.pools[provider].set_keys(klist)
            self.ollama_endpoint = data.get("ollama_endpoint", self.ollama_endpoint)
            self.ollama_model = data.get("ollama_model", self.ollama_model)
            if "fallback_cascade" in data:
                self.fallback_cascade = data["fallback_cascade"]
        except Exception as e:
            logger.error(f"Failed to load keys vault: {e}")

    def save_to_vault(self):
        """Saves current keys to persistent JSON vault file with UTF-8 encoding."""
        try:
            data = {
                "keys": {p: self.pools[p].keys for p in self.SUPPORTED_PROVIDERS},
                "ollama_endpoint": self.ollama_endpoint,
                "ollama_model": self.ollama_model,
                "fallback_cascade": self.fallback_cascade,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(VAULT_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save keys vault: {e}")

    def update_provider_keys(self, provider: str, keys: List[str]):
        """Sets new keys for a provider and persists."""
        prov = provider.lower()
        if prov in self.pools:
            self.pools[prov].set_keys(keys)
            self.save_to_vault()

    def add_provider_key(self, provider: str, key: str):
        prov = provider.lower()
        if prov in self.pools:
            self.pools[prov].add_key(key)
            self.save_to_vault()

    def get_candidate(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Walks the fallback cascade to find the first provider with an active key.
        Returns: (provider_name, active_key_or_endpoint)
        """
        for prov in self.fallback_cascade:
            if prov == "ollama":
                # Local Ollama is always a candidate
                return ("ollama", self.ollama_endpoint)
            pool = self.pools.get(prov)
            if pool and pool.keys:
                key = pool.get_active_key()
                if key:
                    return (prov, key)

        # Default fallback
        return ("ollama", self.ollama_endpoint)

    def mark_rate_limited(self, provider: str, key: str, cooldown_seconds: float = 60.0):
        prov = provider.lower()
        if prov in self.pools:
            self.pools[prov].mark_rate_limited(key, cooldown_seconds)

    def mark_success(self, provider: str, key: str):
        prov = provider.lower()
        if prov in self.pools:
            self.pools[prov].mark_success(key)

    def get_status_summary(self) -> Dict[str, Any]:
        """Returns masked status of all pools and Ollama."""
        pools_status = {p: self.pools[p].get_status() for p in self.SUPPORTED_PROVIDERS if p != "ollama"}
        total_cloud_keys = sum(len(p.keys) for prov, p in self.pools.items() if prov != "ollama")
        active_cloud_keys = sum(p.get_status()["available_keys"] for prov, p in self.pools.items() if prov != "ollama")

        return {
            "total_cloud_keys": total_cloud_keys,
            "active_cloud_keys": active_cloud_keys,
            "fallback_cascade": self.fallback_cascade,
            "ollama": {
                "endpoint": self.ollama_endpoint,
                "model": self.ollama_model,
                "is_active": True
            },
            "providers": pools_status
        }

    def test_provider_key(self, provider: str, key: str) -> Tuple[bool, str]:
        """Tests validity of a provider API key or Ollama connection."""
        prov = provider.lower()
        if prov == "ollama":
            url = f"{self.ollama_endpoint.rstrip('/')}/api/tags"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "malayaLLM/2.3.0"})
                with urllib.request.urlopen(req, timeout=4) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        models = [m.get("name", "") for m in data.get("models", [])]
                        return True, f"Ollama Connected. Models available: {', '.join(models[:4]) if models else 'None'}"
                    return False, f"Ollama HTTP {response.status}"
            except Exception as e:
                return False, f"Ollama unreachable: {str(e)}"

        if prov == "groq":
            url = "https://api.groq.com/openai/v1/models"
            try:
                req = urllib.request.Request(url, headers={
                    "Authorization": f"Bearer {key}",
                    "User-Agent": "malayaLLM/2.3.0"
                })
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if resp.status == 200:
                        return True, "Groq Key Validated Successfully!"
            except urllib.error.HTTPError as e:
                return False, f"Groq Error: HTTP {e.code}"
            except Exception as e:
                return False, f"Connection Error: {str(e)}"

        if prov == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "malayaLLM/2.3.0"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if resp.status == 200:
                        return True, "Gemini Key Validated Successfully!"
            except urllib.error.HTTPError as e:
                return False, f"Gemini Error: HTTP {e.code}"
            except Exception as e:
                return False, f"Connection Error: {str(e)}"

        if prov == "openrouter":
            url = "https://openrouter.ai/api/v1/models"
            try:
                req = urllib.request.Request(url, headers={
                    "Authorization": f"Bearer {key}",
                    "User-Agent": "malayaLLM/2.3.0"
                })
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if resp.status == 200:
                        return True, "OpenRouter Key Validated Successfully!"
            except urllib.error.HTTPError as e:
                return False, f"OpenRouter Error: HTTP {e.code}"
            except Exception as e:
                return False, f"Connection Error: {str(e)}"

        if prov == "nvidia":
            url = "https://integrate.api.nvidia.com/v1/models"
            try:
                req = urllib.request.Request(url, headers={
                    "Authorization": f"Bearer {key}",
                    "User-Agent": "malayaLLM/2.3.0"
                })
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if resp.status == 200:
                        return True, "NVIDIA NIM Key Validated Successfully!"
            except urllib.error.HTTPError as e:
                return False, f"NVIDIA Error: HTTP {e.code}"
            except Exception as e:
                return False, f"Connection Error: {str(e)}"

        return True, f"Key saved for {provider}"


# Global Singleton instance
key_rotator = KeyRotator()
