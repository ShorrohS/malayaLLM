"""
malayaLLM v2.3.0 - LLM Quality Judge Worker
Uses rotating LLMs (Groq, Gemini, OpenRouter, NVIDIA NIM, Ollama) or heuristic linguistic critic
to evaluate sentence structure, detect and drop "translationese", and grade Malayalam fluency.
"""

import re
import sys
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, List, Any, Tuple

# Windows console UTF-8 safety
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from backend.key_rotator import key_rotator

logger = logging.getLogger("QualityJudge")

# Common machine translationese markers and clumsy calques in Malayalam
TRANSLATIONESE_PATTERNS = [
    (re.compile(r'\bആയിരിക്കുന്നു\s+ആകുന്നു\b'), "Redundant copula chaining ('has been is')"),
    (re.compile(r'\bഇത്\s+ആണ്\s+എന്തെന്നാൽ\b'), "Literal calque of 'This is because'"),
    (re.compile(r'\bഓരോന്നും\s+എല്ലാറ്റിനെയും\b'), "Redundant quantifiers ('each and every')"),
    (re.compile(r'\bചെയ്യാൻ\s+സാധിക്കും\s+ആണ്\b'), "Clumsy passive modal translation ('is able to do is')"),
    (re.compile(r'\bഅവൻ\s+പറഞ്ഞു\s+എന്ന്\s+പറഞ്ഞു\b'), "Repetitive speech reporting"),
    (re.compile(r'\bഇതിൻ്റെ\s+കാരണം\s+ആകുന്നു\b'), "Unnatural copula phrasing")
]

# Common Dravidian case markers and inflectional suffixes indicating authentic Malayalam
DRAVIDIAN_CASE_MARKERS = [
    re.compile(r'[\u0D00-\u0D7F]+(ത്തിൽ|ത്തിലേക്ക്|ത്തിൻ്റെ|ത്തിന്റെ|ത്തിന്|ത്തോടൊപ്പം|ത്തോടെ)\b'),
    re.compile(r'[\u0D00-\u0D7F]+(കളിൽ|കളിലേക്ക്|കളുടെ|ങ്ങൾക്ക്|ങ്ങളോട്)\b'),
    re.compile(r'[\u0D00-\u0D7F]+(നായ|യായ|യുള്ള|യോട്|യാൽ)\b')
]


class LLMQualityJudge:
    """Production Quality Judge evaluating Malayalam linguistic fluency & translationese."""

    @classmethod
    def evaluate_heuristic(cls, text: str) -> Dict[str, Any]:
        """
        Fast, deterministic linguistic rule critic for 100% offline resilience.
        Evaluates syntax markers, case inflections, copula chaining, and vocabulary distribution.
        """
        if not text or len(text.strip()) < 10:
            return {
                "fluency_score": 0.3,
                "quality_rating": "Low Quality (Insufficient Length)",
                "passed_validation": False,
                "audit_notes": ["Text snippet is too short for reliable morphological analysis"],
                "engine_used": "Offline Linguistic Critic"
            }

        score = 1.0
        audit_notes: List[str] = []

        # 1. Translationese detection
        detected_translationese = []
        for pat, desc in TRANSLATIONESE_PATTERNS:
            if pat.search(text):
                detected_translationese.append(desc)
                score -= 0.25

        if detected_translationese:
            audit_notes.extend([f"Translationese Detected: {d}" for d in detected_translationese])
        else:
            audit_notes.append("No obvious machine translationese or copula chaining artifacts detected")

        # 2. Dravidian case marker richness
        case_marker_matches = sum(len(pat.findall(text)) for pat in DRAVIDIAN_CASE_MARKERS)
        words = text.split()
        if len(words) > 8 and case_marker_matches == 0:
            score -= 0.15
            audit_notes.append("Low agglutinative case inflection density for modern Malayalam prose")
        else:
            audit_notes.append(f"Authentic Dravidian agglutination and case inflections present ({case_marker_matches} markers)")

        # 3. Sentence length and structural rhythm
        sentences = [s.strip() for s in re.split(r'[.!?।]', text) if s.strip()]
        avg_sentence_len = sum(len(s.split()) for s in sentences) / max(1, len(sentences))

        if avg_sentence_len < 3:
            score -= 0.20
            audit_notes.append("Sentence fragments too short and choppy")
        elif avg_sentence_len > 40:
            score -= 0.10
            audit_notes.append("Excessively long run-on compound sentence")

        # Normalize score
        final_score = max(0.1, min(1.0, round(score, 3)))
        passed = (final_score >= 0.70)

        if final_score >= 0.88:
            rating = "High Quality (Native Fluency)"
        elif final_score >= 0.70:
            rating = "Acceptable (Minor Imperfections)"
        elif final_score >= 0.50:
            rating = "Borderline Translationese"
        else:
            rating = "Low Quality (Syntax Distortions)"

        return {
            "fluency_score": final_score,
            "quality_rating": rating,
            "passed_validation": passed,
            "audit_notes": audit_notes,
            "engine_used": "Offline Linguistic Critic"
        }

    @classmethod
    def evaluate_with_llm(cls, text: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Calls rotating LLMs (Groq, Gemini, OpenRouter, NVIDIA, Ollama).
        Catches HTTP 429 rate limits, performs instant hot-swap failover,
        and gracefully falls back to linguistic critic if offline.
        """
        prompt = (
            "You are an expert Malayalam computational linguist evaluating training dataset quality.\n"
            "Evaluate this Malayalam text snippet for grammatical naturalness, fluency, and absence of machine translationese.\n\n"
            f"TEXT: \"\"\"{text[:1000]}\"\"\"\n\n"
            "Return ONLY valid JSON matching this exact schema:\n"
            "{\n"
            '  "fluency_score": 0.95,\n'
            '  "quality_rating": "High Quality (Native Fluency)",\n'
            '  "passed_validation": true,\n'
            '  "audit_notes": ["High morphological consistency", "Natural sentence structure"]\n'
            "}"
        )

        for attempt in range(max_retries):
            provider, key_or_endpoint = key_rotator.get_candidate()

            if not provider or provider == "ollama":
                # Try Ollama if endpoint is reachable
                try:
                    ollama_url = f"{key_rotator.ollama_endpoint.rstrip('/')}/api/generate"
                    payload = json.dumps({
                        "model": key_rotator.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json"
                    }).encode('utf-8')
                    req = urllib.request.Request(ollama_url, data=payload, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=4) as resp:
                        if resp.status == 200:
                            res_json = json.loads(resp.read().decode('utf-8'))
                            response_text = res_json.get("response", "")
                            parsed = json.loads(response_text)
                            parsed["engine_used"] = f"Local Ollama ({key_rotator.ollama_model})"
                            return parsed
                except Exception:
                    # Ollama not running or model not found -> fallback to heuristic
                    return cls.evaluate_heuristic(text)

            # Cloud provider call
            if provider == "groq":
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = json.dumps({
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2
                }).encode('utf-8')
                headers = {
                    "Authorization": f"Bearer {key_or_endpoint}",
                    "Content-Type": "application/json"
                }
                try:
                    req = urllib.request.Request(url, data=payload, headers=headers)
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode('utf-8'))
                            content = data["choices"][0]["message"]["content"]
                            parsed = json.loads(content)
                            key_rotator.mark_success("groq", key_or_endpoint)
                            parsed["engine_used"] = "Groq (Llama-3.3-70B)"
                            return parsed
                except urllib.error.HTTPError as e:
                    if e.code in (429, 403, 401):
                        key_rotator.mark_rate_limited("groq", key_or_endpoint, 60.0)
                        continue
                except Exception as e:
                    logger.warning(f"Groq invocation failed: {e}")
                    continue

            elif provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key_or_endpoint}"
                payload = json.dumps({
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"response_mime_type": "application/json"}
                }).encode('utf-8')
                headers = {"Content-Type": "application/json"}
                try:
                    req = urllib.request.Request(url, data=payload, headers=headers)
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode('utf-8'))
                            content = data["candidates"][0]["content"]["parts"][0]["text"]
                            parsed = json.loads(content)
                            key_rotator.mark_success("gemini", key_or_endpoint)
                            parsed["engine_used"] = "Google Gemini 2.0 Flash"
                            return parsed
                except urllib.error.HTTPError as e:
                    if e.code in (429, 403, 401):
                        key_rotator.mark_rate_limited("gemini", key_or_endpoint, 60.0)
                        continue
                except Exception as e:
                    logger.warning(f"Gemini invocation failed: {e}")
                    continue

        # If all LLM attempts exhausted or in offline environment, use heuristic
        return cls.evaluate_heuristic(text)

    @classmethod
    def judge(cls, text: str) -> Dict[str, Any]:
        """Main judging entry point with automatic fallbacks."""
        return cls.evaluate_with_llm(text)


# Global singleton judge
quality_judge = LLMQualityJudge()
