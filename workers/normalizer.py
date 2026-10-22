"""
malayaLLM v2.3.0 - Morphology & Unicode Normalizer Worker
Applies NFKC normalization, fixes Chillu letter encoding bugs (ൺ, ൻ, ർ, ൽ, ൾ, ൿ),
strips HTML tags and URLs, redacts Indian PII, and enforces >= 60% Malayalam Unicode density.
"""

import re
import sys
import html
import unicodedata
from typing import Dict, List, Tuple, Any

# Windows console UTF-8 safety
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Malayalam Unicode Range: U+0D00 to U+0D7F
MALAYALAM_UNICODE_REGEX = re.compile(r'[\u0D00-\u0D7F]')

# Chillu letter standardization mappings:
# Base Consonant + Virama \u0D4D + Zero Width Joiner \u200D -> Official Atomic Unicode Chillus (Unicode 5.1+)
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

# Zero-width joiner variants in HTML/text
ZWJ_ENTITY_REGEX = re.compile(r'&zwj;|&#8205;|&#x200D;', re.IGNORECASE)

# PII Patterns for Indian Contexts
PII_PATTERNS = [
    # Email
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'), '[EMAIL_REDACTED]'),
    # Indian phone numbers (+91-9876543210, 0471-2334455, +91 9847012345)
    (re.compile(r'(?:\+91[\-\s]?)?(?:0\d{2,4}[\-\s]?)?[6-9]\d{9}\b'), '[PHONE_REDACTED]'),
    (re.compile(r'\b0\d{3,4}[\-\s]\d{6,8}\b'), '[PHONE_REDACTED]'),
    # Aadhaar number (12 digits, spaced or continuous: 1234 5678 9012)
    (re.compile(r'\b\d{4}[\s\-]\d{4}[\s\-]\d{4}\b'), '[AADHAAR_REDACTED]'),
    # PAN Card (e.g. ABCDE1234F)
    (re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'), '[PAN_REDACTED]')
]

HTML_TAG_REGEX = re.compile(r'<[^>]+>')
URL_REGEX = re.compile(r'https?://\S+|www\.\S+')


class MalayalamNormalizer:
    """Production Morphology & Unicode Normalizer Worker."""

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Applies NFKC normalization to compose characters and standardize diacritics."""
        if not text:
            return ""
        return unicodedata.normalize('NFKC', text)

    @classmethod
    def standardize_chillus(cls, text: str) -> Tuple[str, int]:
        """
        Replaces legacy base+virama+ZWJ sequences with official Unicode atomic Chillus.
        Returns: (standardized_text, count_of_fixes)
        """
        if not text:
            return "", 0

        # Replace HTML entities of ZWJ first
        cleaned = ZWJ_ENTITY_REGEX.sub('\u200D', text)
        fixes_count = 0

        for pattern, atomic in CHILLU_MAP:
            matches = len(pattern.findall(cleaned))
            if matches > 0:
                fixes_count += matches
                cleaned = pattern.sub(atomic, cleaned)

        return cleaned, fixes_count

    @staticmethod
    def strip_html_and_urls(text: str) -> str:
        """Strips HTML markup and raw URLs while unescaping entities."""
        if not text:
            return ""
        # Remove script and style tags
        cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        # Decode HTML entities
        cleaned = html.unescape(cleaned)
        # Remove HTML tags
        cleaned = HTML_TAG_REGEX.sub(' ', cleaned)
        # Remove web URLs
        cleaned = URL_REGEX.sub(' ', cleaned)
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    @classmethod
    def redact_pii(cls, text: str) -> Tuple[str, int]:
        """Redacts emails, phone numbers, Aadhaar, and PAN cards."""
        if not text:
            return "", 0
        cleaned = text
        redacted_count = 0
        for pattern, replacement in PII_PATTERNS:
            matches = len(pattern.findall(cleaned))
            if matches > 0:
                redacted_count += matches
                cleaned = pattern.sub(replacement, cleaned)
        return cleaned, redacted_count

    @classmethod
    def calculate_malayalam_density(cls, text: str) -> float:
        """
        Calculates ratio of Malayalam Unicode codepoints (U+0D00 - U+0D7F)
        relative to non-whitespace characters.
        """
        if not text:
            return 0.0
        non_space = [ch for ch in text if not ch.isspace()]
        if not non_space:
            return 0.0
        mal_chars = [ch for ch in non_space if '\u0D00' <= ch <= '\u0D7F']
        return len(mal_chars) / len(non_space)

    @classmethod
    def process(cls, raw_text: str) -> Dict[str, Any]:
        """
        Executes complete normalization pipeline on a raw text record:
        1. NFKC Unicode normalization
        2. HTML & URL stripping
        3. Atomic Chillu letter standardization
        4. Indian PII redaction
        5. Malayalam Unicode density calculation (>= 60% gating)
        """
        if not raw_text:
            return {
                "cleaned_text": "",
                "malayalam_density": 0.0,
                "density_passed": False,
                "chillu_fixes": 0,
                "pii_redacted": 0,
                "audit_notes": ["Empty input text"]
            }

        audit_notes: List[str] = []

        # 1. NFKC Normalization
        text = cls.normalize_unicode(raw_text)

        # 2. HTML & URL Stripping
        text = cls.strip_html_and_urls(text)

        # 3. Chillu Letter Standardization
        text, chillu_fixes = cls.standardize_chillus(text)
        if chillu_fixes > 0:
            audit_notes.append(f"Standardized {chillu_fixes} legacy Chillu character sequences to atomic Unicode")

        # 4. PII Redaction
        text, pii_redacted = cls.redact_pii(text)
        if pii_redacted > 0:
            audit_notes.append(f"Redacted {pii_redacted} sensitive PII instances (email/phone/identity numbers)")

        # 5. Density Calculation & Gating
        density = cls.calculate_malayalam_density(text)
        density_passed = (density >= 0.60)

        if density_passed:
            audit_notes.append(f"Malayalam density passed gate ({density*100:.1f}% >= 60.0%)")
        else:
            audit_notes.append(f"Gating Rejected: Malayalam density below threshold ({density*100:.1f}% < 60.0%)")

        return {
            "cleaned_text": text,
            "malayalam_density": round(density, 4),
            "density_passed": density_passed,
            "chillu_fixes": chillu_fixes,
            "pii_redacted": pii_redacted,
            "audit_notes": audit_notes
        }


# Global singleton normalizer
normalizer_worker = MalayalamNormalizer()
