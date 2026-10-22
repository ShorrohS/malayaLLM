"""
malayaLLM v2.3.0 - PDF Ingestion & Malayalam Text Extraction Engine
Handles custom Malayalam PDFs, running header/footer stripping, page number removal,
intra-word line break healing, and semantic chunking for Dravidian NLP pipelines.
"""

import os
import re
import sys
import json
import time
from typing import List, Dict, Any, Optional, Tuple
import pypdf

# Windows console UTF-8 safety
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SOURCES_DIR = os.path.join(DATA_DIR, "sources")
NOVELS_DIR = os.path.join(SOURCES_DIR, "novels")
UPLOADS_DIR = os.path.join(SOURCES_DIR, "uploads")

for d in [SOURCES_DIR, NOVELS_DIR, UPLOADS_DIR]:
    os.makedirs(d, exist_ok=True)

# Common Malayalam & English PDF header/footer and page number patterns
PAGE_NUMBER_PATTERNS = [
    re.compile(r'^\s*(?:പേജ്|Page|Page\s*No\.?|ഭാഗം)?\s*[\d٠-٩\-–—\s/|]+\s*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'^\s*[-–—]\s*\d+\s*[-–—]\s*$', re.MULTILINE),
    re.compile(r'^\s*\[\s*\d+\s*\]\s*$', re.MULTILINE),
    re.compile(r'\b(?:Page\s*\d+\s*of\s*\d+|\d+\s*/\s*\d+)\b', re.IGNORECASE)
]

# Watermark and repetitive publisher boilerplate patterns
BOILERPLATE_PATTERNS = [
    re.compile(r'^\s*Downloaded\s+from\s+.*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'^\s*സൗജന്യ\s+വിതരണത്തിന്\s+മാത്രം.*$', re.MULTILINE),
    re.compile(r'^\s*All\s+Rights\s+Reserved.*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'^\s*Printed\s+and\s+Published\s+by\s+.*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
]

# Malayalam hyphenated line break: e.g. "സാങ്കേ-\nതിക" -> "സാങ്കേതിക"
MALAYALAM_HYPHEN_BREAK = re.compile(r'([\u0D00-\u0D7F]+)[\-–—]\s*\n\s*([\u0D00-\u0D7F]+)')


class MalayalamPDFExtractor:
    """Production PDF text extraction, cleanup, and semantic chunker."""

    @classmethod
    def clean_page_text(cls, text: str) -> str:
        """Strips headers, footers, page numbering, and watermarks."""
        if not text:
            return ""

        cleaned = text

        # 1. Strip page number lines
        for pat in PAGE_NUMBER_PATTERNS:
            cleaned = pat.sub('', cleaned)

        # 2. Strip publisher boilerplates
        for pat in BOILERPLATE_PATTERNS:
            cleaned = pat.sub('', cleaned)

        # 3. Heal hyphenated line breaks in Malayalam
        cleaned = MALAYALAM_HYPHEN_BREAK.sub(r'\1\2', cleaned)

        # 4. Normalize soft hyphens and invisible chars
        cleaned = cleaned.replace('\xad', '').replace('\u200b', '')

        # 5. Fix mid-sentence line breaks while preserving paragraph boundaries
        # Replace single newline not preceded by punctuation with a space
        lines = cleaned.split('\n')
        merged_lines = []
        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                merged_lines.append('')
                continue
            if merged_lines and merged_lines[-1] != '' and not re.search(r'[.!?।:]$', merged_lines[-1]):
                merged_lines[-1] += ' ' + trimmed
            else:
                merged_lines.append(trimmed)

        cleaned = '\n\n'.join([l for l in merged_lines if l])
        return cleaned.strip()

    @classmethod
    def extract_from_pdf(cls, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts raw text page-by-page from a PDF file using pypdf.
        Returns: list of dicts with { page_num, raw_text, cleaned_text }
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF not found: {file_path}")

        pages_data = []
        try:
            reader = pypdf.PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                try:
                    raw_text = page.extract_text() or ""
                    cleaned = cls.clean_page_text(raw_text)
                    if cleaned and len(cleaned.strip()) > 30:
                        pages_data.append({
                            "page_num": idx + 1,
                            "raw_text": raw_text,
                            "cleaned_text": cleaned
                        })
                except Exception as e:
                    print(f"Warning: Failed to extract page {idx + 1} from {file_path}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error opening PDF {file_path}: {e}", file=sys.stderr)

        return pages_data

    @classmethod
    def chunk_into_semantic_units(
        cls,
        pages_data: List[Dict[str, Any]],
        source_name: str,
        target_words: int = 250
    ) -> List[Dict[str, Any]]:
        """
        Chunks page texts into coherent semantic units (150-350 words)
        respecting sentence boundaries (period, Purna Virama ।).
        """
        chunks = []
        full_text = "\n\n".join([p["cleaned_text"] for p in pages_data])
        if not full_text.strip():
            return []

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?।])\s+', full_text)
        current_chunk_sentences = []
        current_word_count = 0
        chunk_idx = 1

        for sentence in sentences:
            s_clean = sentence.strip()
            if not s_clean:
                continue

            words = s_clean.split()
            current_chunk_sentences.append(s_clean)
            current_word_count += len(words)

            if current_word_count >= target_words:
                chunk_text = " ".join(current_chunk_sentences)
                chunks.append({
                    "id": f"pdf_{int(time.time()*1000)}_{chunk_idx}",
                    "source": source_name,
                    "title": f"{os.path.basename(source_name)} - Section {chunk_idx}",
                    "raw_text": chunk_text,
                    "word_count": current_word_count,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                current_chunk_sentences = []
                current_word_count = 0
                chunk_idx += 1

        # Residual chunk
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            if len(chunk_text.split()) > 25:
                chunks.append({
                    "id": f"pdf_{int(time.time()*1000)}_{chunk_idx}",
                    "source": source_name,
                    "title": f"{os.path.basename(source_name)} - Section {chunk_idx}",
                    "raw_text": chunk_text,
                    "word_count": len(chunk_text.split()),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })

        return chunks

    @classmethod
    def process_pdf_file(cls, file_path: str) -> List[Dict[str, Any]]:
        """End-to-end extraction and chunking of a PDF file."""
        pages = cls.extract_from_pdf(file_path)
        return cls.chunk_into_semantic_units(pages, file_path)


pdf_extractor = MalayalamPDFExtractor()
