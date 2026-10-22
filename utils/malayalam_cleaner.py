"""
Malayalam Morphological Cleaner, Unicode Normalizer, and Quality Critic
Enforces NFKC normalization, atomic Chillu standardization, Malayalam Unicode density checks (>= 60%),
PII redaction, and translationese / fluency quality heuristics.
"""

import re
import html
import unicodedata
from typing import Dict, Any, Tuple, List

# Malayalam Unicode Range: U+0D00 to U+0D7F
MALAYALAM_UNICODE_REGEX = re.compile(r'[\u0D00-\u0D7F]')

# Chillu letter standardization mappings:
# Legacy compositions (Base Consonant + Virama \u0D4D + Zero Width Joiner \u200D) -> Atomic Unicode Chillus
CHILLU_MAP = [
    # ൺ (MALAYALAM LETTER NN: U+0D7A) <- ണ + ് + ZWJ
    (re.compile(r'\u0D23\u0D4D\u200D|\u0D23\u200D\u0D4D'), '\u0D7A'),
    # ൻ (MALAYALAM LETTER N: U+0D7B) <- ന + ് + ZWJ
    (re.compile(r'\u0D28\u0D4D\u200D|\u0D28\u200D\u0D4D'), '\u0D7B'),
    # ർ (MALAYALAM LETTER RR: U+0D7C) <- ര + ് + ZWJ
    (re.compile(r'\u0D30\u0D4D\u200D|\u0D30\u200D\u0D4D'), '\u0D7C'),
    # ൽ (MALAYALAM LETTER L: U+0D7D) <- ല + ് + ZWJ
    (re.compile(r'\u0D32\u0D4D\u200D|\u0D32\u200D\u0D4D'), '\u0D7D'),
    # ൾ (MALAYALAM LETTER LL: U+0D7E) <- ള + ് + ZWJ
    (re.compile(r'\u0D33\u0D4D\u200D|\u0D33\u200D\u0D4D'), '\u0D7E'),
    # ൿ (MALAYALAM LETTER K: U+0D7F) <- ക + ് + ZWJ
    (re.compile(r'\u0D15\u0D4D\u200D|\u0D15\u200D\u0D4D'), '\u0D7F'),
]

# Zero Width Non-Joiner (ZWNJ: \u200C) and Zero Width Joiner (ZWJ: \u200D)
ZW_CHARS_REGEX = re.compile(r'[\u200B\u200C\u200D\uFEFF]')

# PII Patterns for Indian contexts
PII_PATTERNS = [
    # Email
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'), '[EMAIL_REDACTED]'),
    # Indian phone numbers (+91-9876543210, 09876543210, 9876543210)
    (re.compile(r'(?:\+91[\-\s]?)?[6-9]\d{9}\b'), '[PHONE_REDACTED]'),
    # Aadhaar number (12 digits, spaced or continuous)
    (re.compile(r'\b\d{4}[\s\-]\d{4}[\s\-]\d{4}\b'), '[AADHAAR_REDACTED]'),
    # PAN Card (e.g. ABCDE1234F)
    (re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'), '[PAN_REDACTED]')
]

# Common HTML tags & script cleaning
HTML_TAG_REGEX = re.compile(r'<[^>]+>')
URL_REGEX = re.compile(r'https?://\S+|www\.\S+')

# Translationese / low quality syntax markers in Malayalam
# Machine translation frequently produces isolated English grammatical artifacts,
# dangling pronouns, or awkward copula overuse (ആകുന്നു, ആണ് redundantly chained).
TRANSLATIONESE_MARKERS = [
    re.compile(r'\bആയിരിക്കുന്നു\s+ആകുന്നു\b'),
    re.compile(r'\bഇത്\s+ആണ്\s+എന്തെന്നാൽ\b'),
    re.compile(r'\bഓരോന്നും\s+എല്ലാറ്റിനെയും\b'),
    re.compile(r'\bചെയ്യാൻ\s+സാധിക്കും\s+ആണ്\b')
]


class MalayalamCleaner:
    """Production cleaner, normalizer, and validator for Malayalam corpus building."""

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Applies NFKC normalization to compose characters and standardize representations."""
        if not text:
            return ""
        return unicodedata.normalize('NFKC', text)

    @classmethod
    def standardize_chillus(cls, text: str) -> Tuple[str, int]:
        """
        Replaces legacy base+virama+ZWJ sequences with official Unicode 5.1+ atomic chillus.
        Returns (standardized_text, count_of_fixes).
        """
        if not text:
            return "", 0
        
        fixes_count = 0
        cleaned = text
        for pattern, atomic in CHILLU_MAP:
            matches = len(pattern.findall(cleaned))
            if matches > 0:
                fixes_count += matches
                cleaned = pattern.sub(atomic, cleaned)
        return cleaned, fixes_count

    @staticmethod
    def strip_html_and_urls(text: str) -> str:
        """Strips HTML markup and raw URLs while preserving punctuation."""
        if not text:
            return ""
        # Remove script and style contents
        cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove general HTML tags
        cleaned = HTML_TAG_REGEX.sub(' ', cleaned)
        # Clean URLs
        cleaned = URL_REGEX.sub(' ', cleaned)
        # Collapse multi spaces
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        return cleaned.strip()

    @staticmethod
    def redact_pii(text: str) -> Tuple[str, int]:
        """Redacts sensitive PII (emails, Indian phone numbers, Aadhaar, PAN)."""
        if not text:
            return "", 0
        
        redactions = 0
        cleaned = text
        for pattern, replacement in PII_PATTERNS:
            matches = len(pattern.findall(cleaned))
            if matches > 0:
                redactions += matches
                cleaned = pattern.sub(replacement, cleaned)
        return cleaned, redactions

    @staticmethod
    def compute_malayalam_density(text: str) -> float:
        """
        Calculates density of Malayalam Unicode characters relative to total non-whitespace characters.
        Target threshold is >= 0.60 (60%).
        """
        if not text:
            return 0.0
        
        # Remove whitespace
        non_space = re.sub(r'\s+', '', text)
        if not non_space:
            return 0.0
        
        malayalam_chars = len(MALAYALAM_UNICODE_REGEX.findall(non_space))
        return round(malayalam_chars / len(non_space), 4)

    @classmethod
    def evaluate_quality_and_fluency(cls, text: str, density: float) -> Dict[str, Any]:
        """
        Heuristic LLM-as-a-Judge critic simulator evaluating sentence structure,
        agglutination validity, translationese markers, and punctuation.
        """
        if not text or len(text.strip()) < 15:
            return {
                "score": 0.0,
                "rating": "Rejected (Too Short)",
                "passed": False,
                "reasons": ["Text length insufficient"]
            }

        reasons = []
        score = 1.0

        # Density check
        if density < 0.60:
            penalty = (0.60 - density) * 1.5
            score -= penalty
            reasons.append(f"Low Malayalam density ({density*100:.1f}% < 60% threshold)")

        # Translationese check
        flagged_markers = 0
        for marker in TRANSLATIONESE_MARKERS:
            if marker.search(text):
                flagged_markers += 1
        if flagged_markers > 0:
            score -= 0.15 * flagged_markers
            reasons.append(f"Detected {flagged_markers} unnatural translationese grammatical marker(s)")

        # Agglutination formatting check (dangling case markers with leading space)
        # e.g., 'വീട് ൽ' instead of 'വീട്ടിൽ' or 'പുസ്തകം നെ' instead of 'പുസ്തകത്തെ'
        broken_case_markers = re.findall(r'\s+(ിൽ|നെ|ക്ക്|ഓട്|ആൽ|കൾ|ന്റെ)\b', text)
        if broken_case_markers:
            score -= min(0.20, len(broken_case_markers) * 0.05)
            reasons.append(f"Found {len(broken_case_markers)} un-agglutinated dangling case markers")

        # English token ratio
        english_words = re.findall(r'\b[A-Za-z]{3,}\b', text)
        total_words = len(text.split())
        eng_ratio = len(english_words) / max(1, total_words)
        if eng_ratio > 0.25:
            score -= 0.20
            reasons.append(f"High English code-mixing ({eng_ratio*100:.1f}% of tokens)")

        # Repetition / spam loop
        sentences = [s.strip() for s in re.split(r'[.!?\n]', text) if len(s.strip()) > 10]
        if sentences and len(sentences) != len(set(sentences)):
            duplicates = len(sentences) - len(set(sentences))
            score -= min(0.3, duplicates * 0.1)
            reasons.append(f"Contains {duplicates} duplicated repetitive sentence(s)")

        final_score = max(0.0, min(1.0, round(score, 3)))
        passed = final_score >= 0.70 and density >= 0.60

        if final_score >= 0.88:
            rating = "High Quality (Native Fluency)"
        elif final_score >= 0.70:
            rating = "Good (Acceptable for Pretraining)"
        elif final_score >= 0.50:
            rating = "Borderline (Needs Review)"
        else:
            rating = "Low Quality (Translationese / Noisy)"

        return {
            "score": final_score,
            "rating": rating,
            "passed": passed,
            "reasons": reasons if reasons else ["High morphological consistency and valid syntax"]
        }

    @classmethod
    def clean_document(cls, raw_text: str, source_name: str = "web_crawler") -> Dict[str, Any]:
        """
        Executes the end-to-end normalization pipeline:
        HTML stripping -> NFKC -> Chillu standardization -> PII Redaction -> Density & Quality Audit.
        """
        # 1. Strip markup and scripts
        no_html = cls.strip_html_and_urls(raw_text)

        # 1b. Decode HTML entities (e.g. &zwj; -> \u200D)
        unescaped_text = html.unescape(no_html)

        # 2. NFKC Normalization
        nfkc_text = cls.normalize_unicode(unescaped_text)

        # 3. Chillu Letter Standardization
        clean_text, chillu_fixes = cls.standardize_chillus(nfkc_text)

        # 4. PII Redaction
        redacted_text, pii_count = cls.redact_pii(clean_text)

        # 5. Density and Metrics
        density = cls.compute_malayalam_density(redacted_text)
        quality_eval = cls.evaluate_quality_and_fluency(redacted_text, density)

        return {
            "source": source_name,
            "raw_text": raw_text,
            "cleaned_text": redacted_text,
            "malayalam_density": density,
            "density_passed": density >= 0.60,
            "chillu_fixes_count": chillu_fixes,
            "pii_redacted_count": pii_count,
            "fluency_score": quality_eval["score"],
            "quality_rating": quality_eval["rating"],
            "passed_validation": quality_eval["passed"],
            "quality_audit": quality_eval["reasons"]
        }
