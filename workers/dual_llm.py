"""
malayaLLM v2.3.0 - Dual-LLM Quality Pipeline Worker
Pass 1: Qwen (Extractor / Worker) - Cleans OCR/web artifacts, normalizes punctuation, extracts coherent prose.
Pass 2: Gemma (Linguistic Reviewer / Proofreader) - Proofreads Dravidian morphology, scores confidence, triggers Auto-Approval (>=85%).
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from typing import Dict, List, Any, Tuple, Optional

# Windows console UTF-8 safety
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from backend.key_rotator import key_rotator
from workers.normalizer import normalizer_worker
from workers.judge import quality_judge


class DualLLMPipeline:
    """Automated Dual-Pass Pipeline with Qwen (Extractor) and Gemma (Proofreader)."""

    def __init__(self):
        self.ollama_endpoint = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.qwen_model = os.environ.get("QWEN_MODEL", "qwen3.5:4b")
        self.gemma_model = os.environ.get("GEMMA_MODEL", "gemma4:e4b")
        self.auto_approve_threshold = 0.85  # 85% confidence required for auto-approval

    def _call_ollama_generate(self, model_name: str, prompt: str, timeout: float = 25.0) -> Optional[str]:
        """Calls local Ollama instance with timeout and returns text response."""
        url = f"{self.ollama_endpoint.rstrip('/')}/api/generate"
        payload = json.dumps({
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9
            }
        }).encode('utf-8')

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    return data.get("response", "").strip()
        except Exception:
            return None
        return None

    # =========================================================================
    # PASS 1: Qwen Extractor & Worker
    # =========================================================================

    def run_qwen_extraction(self, text: str, title: str = "") -> Dict[str, Any]:
        """
        Pass 1: Qwen worker normalizes OCR/PDF breaks, extracts clean Malayalam prose,
        and standardizes sentence structure.
        """
        # First ensure NFKC and base normalizations
        base_norm = normalizer_worker.process(text)
        cleaned_base = base_norm["cleaned_text"]

        prompt = (
            "You are an expert Malayalam corpus text extraction worker.\n"
            "Clean the following text: heal any broken line wraps, remove residual OCR artifacts, "
            "and ensure natural Malayalam sentence flow. Preserve authentic vocabulary.\n\n"
            f"TEXT: \"\"\"{cleaned_base[:1200]}\"\"\"\n\n"
            "Return ONLY the cleaned Malayalam prose with zero explanatory English text."
        )

        ollama_response = self._call_ollama_generate(self.qwen_model, prompt, timeout=20.0)

        if ollama_response and len(ollama_response.strip()) > 30:
            extracted_text = normalizer_worker.strip_html_and_urls(ollama_response)
            extracted_text, _ = normalizer_worker.standardize_chillus(extracted_text)
            extracted_text, _ = normalizer_worker.redact_pii(extracted_text)
            engine = f"Local Ollama ({self.qwen_model})"
        else:
            # Fallback to normalized base text
            extracted_text = cleaned_base
            engine = "Offline Morphological Extractor"

        density = normalizer_worker.calculate_malayalam_density(extracted_text)

        return {
            "extracted_text": extracted_text,
            "engine": engine,
            "density": round(density, 4),
            "density_passed": density >= 0.60,
            "chillu_fixes": base_norm["chillu_fixes"],
            "pii_redacted": base_norm["pii_redacted"]
        }

    # =========================================================================
    # PASS 2: Gemma Linguistic Reviewer & Proofreader
    # =========================================================================

    def run_gemma_proofreading(self, extracted_text: str, title: str = "") -> Dict[str, Any]:
        """
        Pass 2: Gemma evaluates Dravidian morphology, proofreads the syntax,
        computes confidence/quality score (0.0 to 1.0), and determines Auto-Approval.
        """
        prompt = (
            "You are Gemma, an expert Dravidian linguistic reviewer and proofreader for Malayalam training datasets.\n"
            "Evaluate this text for grammatical naturalness, proper Chillu letters (ൺ, ൻ, ർ, ൽ, ൾ, ൿ), "
            "and absence of awkward translationese. Provide a confidence score (0.00 to 1.00).\n\n"
            f"TEXT: \"\"\"{extracted_text[:1200]}\"\"\"\n\n"
            "Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "confidence_score": 0.94,\n'
            '  "fluency_score": 0.95,\n'
            '  "quality_rating": "High Quality (Native Fluency)",\n'
            '  "critique_notes": ["Proper agglutination", "Natural sentence cadence"],\n'
            '  "proofread_text": "<Polished Malayalam text>"\n'
            "}"
        )

        ollama_response = self._call_ollama_generate(self.gemma_model, prompt, timeout=22.0)
        parsed_result = None

        if ollama_response:
            try:
                # Find JSON block in response
                json_match = re.search(r'\{.*\}', ollama_response, re.DOTALL)
                if json_match:
                    parsed_result = json.loads(json_match.group(0))
            except Exception:
                parsed_result = None

        if parsed_result and "confidence_score" in parsed_result:
            confidence = float(parsed_result.get("confidence_score", 0.88))
            fluency = float(parsed_result.get("fluency_score", confidence))
            quality_rating = parsed_result.get("quality_rating", "High Quality")
            critique_notes = parsed_result.get("critique_notes", [])
            proofread_text = parsed_result.get("proofread_text") or extracted_text
            engine = f"Local Ollama ({self.gemma_model})"
        else:
            # Deterministic linguistic critic fallback
            heuristic = quality_judge.evaluate_heuristic(extracted_text)
            fluency = heuristic.get("fluency_score", 0.90)
            # Confidence is derived from density + fluency + lack of translationese
            density = normalizer_worker.calculate_malayalam_density(extracted_text)
            confidence = round((fluency * 0.6) + (density * 0.4), 3)
            quality_rating = heuristic.get("quality_rating", "High Quality")
            critique_notes = heuristic.get("audit_notes", [])
            proofread_text = extracted_text
            engine = "Offline Dravidian Critic"

        # Auto-Approve Gate: >= 85% confidence AND valid Malayalam density
        is_auto_approved = (confidence >= self.auto_approve_threshold)

        return {
            "confidence_score": round(confidence, 3),
            "fluency_score": round(fluency, 3),
            "quality_rating": quality_rating,
            "critique_notes": critique_notes,
            "proofread_text": proofread_text,
            "is_auto_approved": is_auto_approved,
            "engine": engine
        }

    # =========================================================================
    # Full Dual-Pass Execution
    # =========================================================================

    def process_dual_pass(self, raw_text: str, title: str = "") -> Dict[str, Any]:
        """
        Executes end-to-end Dual-Pass Quality Pipeline:
        Pass 1: Qwen Extraction & Cleaning
        Pass 2: Gemma Linguistic Review & Confidence Evaluation
        """
        # Pass 1: Qwen
        qwen_res = self.run_qwen_extraction(raw_text, title)
        extracted = qwen_res["extracted_text"]

        # Pass 2: Gemma
        gemma_res = self.run_gemma_proofreading(extracted, title)

        return {
            "raw_text": raw_text,
            "qwen_extracted_text": extracted,
            "cleaned_text": gemma_res["proofread_text"],
            "malayalam_density": qwen_res["density"],
            "density_passed": qwen_res["density_passed"],
            "chillu_fixes": qwen_res["chillu_fixes"],
            "pii_redacted": qwen_res["pii_redacted"],
            "confidence_score": gemma_res["confidence_score"],
            "fluency_score": gemma_res["fluency_score"],
            "quality_rating": gemma_res["quality_rating"],
            "critique_notes": gemma_res["critique_notes"],
            "is_auto_approved": gemma_res["is_auto_approved"] and qwen_res["density_passed"],
            "qwen_engine": qwen_res["engine"],
            "gemma_engine": gemma_res["engine"]
        }


dual_llm_pipeline = DualLLMPipeline()
