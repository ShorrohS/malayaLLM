"""
Multi-Key Fallback & Rotation Engine for CrewAI & Malayalam Autonomous Pipeline
Supports Google Gemini, OpenRouter, Groq, NVIDIA NIM, Cohere, OpenAI, Anthropic.
Handles automatic round-robin, rate-limit (429 / quota) error detection, cooldowns,
and seamless fallback provider cascades.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any, Callable

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [KeyRotator] %(message)s')
logger = logging.getLogger("KeyRotator")


class ProviderKeyPool:
    """Manages keys and cooldown states for a single LLM provider."""
    def __init__(self, provider: str, keys: List[str]):
        self.provider = provider
        self.keys = [k.strip() for k in keys if k and k.strip()]
        self.current_idx = 0
        self.cooldowns: Dict[str, float] = {}  # key -> timestamp when available again
        self.success_count: Dict[str, int] = {k: 0 for k in self.keys}
        self.fail_count: Dict[str, int] = {k: 0 for k in self.keys}

    def add_keys(self, new_keys: List[str]):
        for k in new_keys:
            cleaned = k.strip()
            if cleaned and cleaned not in self.keys:
                self.keys.append(cleaned)
                self.success_count[cleaned] = 0
                self.fail_count[cleaned] = 0

    def get_active_key(self) -> Optional[str]:
        if not self.keys:
            return None
        
        now = time.time()
        # Scan through keys starting at current_idx
        total = len(self.keys)
        for i in range(total):
            idx = (self.current_idx + i) % total
            candidate = self.keys[idx]
            cooldown_until = self.cooldowns.get(candidate, 0)
            if now >= cooldown_until:
                self.current_idx = (idx + 1) % total
                return candidate
        
        # If all keys are in cooldown, find the one with the shortest remaining cooldown
        shortest_key = min(self.keys, key=lambda k: self.cooldowns.get(k, 0))
        remaining = self.cooldowns.get(shortest_key, 0) - now
        logger.warning(
            f"All {len(self.keys)} keys for {self.provider} are in rate-limit cooldown. "
            f"Shortest cooldown key will unlock in {max(0, int(remaining))}s."
        )
        return shortest_key

    def mark_rate_limited(self, key: str, cooldown_seconds: float = 60.0):
        self.cooldowns[key] = time.time() + cooldown_seconds
        self.fail_count[key] = self.fail_count.get(key, 0) + 1
        logger.warning(
            f"⚠️ Key for [{self.provider}] (prefix: {key[:6]}...) rate-limited (429/Quota). "
            f"Set on cooldown for {cooldown_seconds}s. Total failures: {self.fail_count[key]}"
        )

    def mark_success(self, key: str):
        self.success_count[key] = self.success_count.get(key, 0) + 1
        # Clear cooldown if previously set
        if key in self.cooldowns and time.time() >= self.cooldowns[key]:
            del self.cooldowns[key]

    def get_status(self) -> Dict[str, Any]:
        now = time.time()
        return {
            "provider": self.provider,
            "total_keys": len(self.keys),
            "available_keys": sum(1 for k in self.keys if now >= self.cooldowns.get(k, 0)),
            "in_cooldown": sum(1 for k in self.keys if now < self.cooldowns.get(k, 0)),
            "stats": {
                f"{k[:6]}...{k[-4:] if len(k) > 10 else ''}": {
                    "success": self.success_count.get(k, 0),
                    "fails": self.fail_count.get(k, 0),
                    "cooling_down": now < self.cooldowns.get(k, 0),
                    "cooldown_remaining_sec": max(0, int(self.cooldowns.get(k, 0) - now))
                }
                for k in self.keys
            }
        }


class KeyRotator:
    """
    Intelligent Multi-Key Fallback & Rotation Engine.
    Handles round-robin key management and cross-provider failover.
    """
    # Recommended fallback order for Malayalam NLP pipeline
    DEFAULT_CASCADE = [
        "groq",         # Fast Llama 3.3 70B
        "gemini",       # High quality multi-lingual (Gemini 2.0 Flash)
        "openrouter",   # Free tier router
        "cohere",       # Multi-lingual strength (Command R+)
        "nvidia",       # Llama 3.1 Nemotron
        "openai",       # Standard fallback
        "anthropic"     # Final fallback
    ]

    PROVIDER_ENV_VARS = {
        "gemini": ["GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEYS", "OPENROUTER_API_KEY"],
        "groq": ["GROQ_API_KEYS", "GROQ_API_KEY"],
        "nvidia": ["NVIDIA_API_KEYS", "NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY"],
        "cohere": ["COHERE_API_KEYS", "COHERE_API_KEY"],
        "openai": ["OPENAI_API_KEYS", "OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEYS", "ANTHROPIC_API_KEY"],
        "serper": ["SERPER_API_KEYS", "SERPER_API_KEY"]
    }

    def __init__(self, key_config: Optional[Dict[str, List[str]]] = None):
        self.pools: Dict[str, ProviderKeyPool] = {}
        
        # Load from provided config or environment
        if key_config:
            for prov, keys in key_config.items():
                self.pools[prov.lower()] = ProviderKeyPool(prov.lower(), keys)
        
        # Auto-discover from environment variables
        self.load_from_env()

    def load_from_env(self):
        for provider, var_names in self.PROVIDER_ENV_VARS.items():
            discovered_keys = []
            for var in var_names:
                raw = os.environ.get(var, "")
                if raw:
                    # Supports comma, semicolon, or newline separated keys
                    parts = [p.strip() for p in raw.replace(';', ',').replace('\n', ',').split(',') if p.strip()]
                    discovered_keys.extend(parts)
            
            if discovered_keys:
                if provider not in self.pools:
                    self.pools[provider] = ProviderKeyPool(provider, discovered_keys)
                else:
                    self.pools[provider].add_keys(discovered_keys)

    def register_keys(self, provider: str, keys: List[str]):
        p = provider.lower()
        if p not in self.pools:
            self.pools[p] = ProviderKeyPool(p, keys)
        else:
            self.pools[p].add_keys(keys)
        logger.info(f"Registered {len(keys)} keys for provider [{provider}].")

    def get_key(self, provider: str) -> Optional[str]:
        p = provider.lower()
        if p in self.pools:
            return self.pools[p].get_active_key()
        return None

    def mark_rate_limited(self, provider: str, key: str, cooldown_seconds: float = 60.0):
        p = provider.lower()
        if p in self.pools:
            self.pools[p].mark_rate_limited(key, cooldown_seconds)

    def mark_success(self, provider: str, key: str):
        p = provider.lower()
        if p in self.pools:
            self.pools[p].mark_success(key)

    def is_rate_limit_error(self, err: Exception) -> bool:
        """Detects if an exception corresponds to rate limit, quota exhaustion, or 429."""
        msg = str(err).lower()
        error_indicators = [
            "429", "rate limit", "ratelimit", "quota", "resourceexhausted",
            "too many requests", "tokens per minute", "requests per day",
            "exceeded", "capacity", "insufficient_quota"
        ]
        return any(ind in msg for ind in error_indicators)

    def execute_with_failover(
        self,
        task_fn: Callable[[str, str], Any],
        preferred_provider: str = "groq",
        cascade: Optional[List[str]] = None,
        max_attempts_per_provider: int = 3
    ) -> Any:
        """
        Executes a callable with intelligent key rotation and provider cascade.
        task_fn: func(provider: str, api_key: str) -> result
        """
        order = cascade or ([preferred_provider] + [p for p in self.DEFAULT_CASCADE if p != preferred_provider])
        last_error = None

        for prov in order:
            prov = prov.lower()
            pool = self.pools.get(prov)
            if not pool or not pool.keys:
                continue

            attempts = min(len(pool.keys) * 2, max_attempts_per_provider)
            for attempt in range(attempts):
                key = pool.get_active_key()
                if not key:
                    break

                try:
                    logger.info(f"Dispatching LLM call via [{prov}] (attempt {attempt + 1})")
                    result = task_fn(prov, key)
                    pool.mark_success(key)
                    return result
                except Exception as e:
                    last_error = e
                    if self.is_rate_limit_error(e):
                        logger.warning(f"Rate limit hit on [{prov}] key. Rotating to next key...")
                        pool.mark_rate_limited(key, cooldown_seconds=60.0)
                        # Immediately try next key in pool
                        continue
                    else:
                        logger.error(f"Non-rate-limit error on [{prov}]: {e}")
                        # For general errors, try once more or fall back to next provider
                        break

            logger.warning(f"Provider [{prov}] exhausted all keys. Cascading to next fallback provider...")

        logger.critical("All configured LLM providers and keys failed or exhausted rate limits.")
        raise last_error or RuntimeError("No available LLM keys or providers responded successfully.")

    def get_summary_status(self) -> Dict[str, Any]:
        """Provides an aggregated status report of all registered key pools."""
        return {
            prov: pool.get_status()
            for prov, pool in self.pools.items()
        }


# Global Singleton Instance for shared pipeline usage
key_rotator = KeyRotator()
