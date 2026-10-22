"""
malayaLLM v2.3.0 - Decoupled Modular Python Pipeline Engine
Coordinates Ingestor -> Normalizer -> Quality Judge -> Review Queue Staging
Runs autonomously in a non-blocking background thread with Play, Pause, and Step controls.
"""

import os
import sys
import time
import json
import random
import threading
import datetime
from typing import Dict, Any, Optional

# Windows console UTF-8 safety
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from backend.db import (
    get_run_state, update_run_state, increment_run_counters,
    log_event, set_live_item, get_live_item, add_review_item,
    get_recent_logs, get_queue_stats
)
from backend.key_rotator import key_rotator
from workers.ingestor import ingestion_worker
from workers.normalizer import normalizer_worker
from workers.judge import quality_judge
from workers.dual_llm import dual_llm_pipeline
from workers.exporter import staging_exporter


class PipelineEngine:
    """Autonomous Non-Blocking Pipeline Orchestrator."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._paused = True
        self._stop_event = threading.Event()
        self._step_once = False
        self._lock = threading.Lock()
        self.step_delay = 2.0  # Seconds between phases for smooth visual observation
        self.start_time: Optional[float] = None
        self.processed_since_start = 0
        self.last_engine_used = "Offline Linguistic Critic"

        # Granular Per-Phase Play/Pause Controls
        self.phase_enabled = {
            "ingestion": True,
            "normalization": True,
            "judging": True,
            "staging": True
        }

        # Ensure database is synced to initial idle state
        run_state = get_run_state()
        if run_state.get("status") == "running":
            update_run_state(status="paused", current_phase="idle")

    def toggle_phase(self, phase: str, enabled: Optional[bool] = None) -> Dict[str, Any]:
        """Toggles or sets the active/paused state of an individual pipeline phase."""
        with self._lock:
            p = phase.lower().strip()
            if p in self.phase_enabled:
                if enabled is not None:
                    self.phase_enabled[p] = bool(enabled)
                else:
                    self.phase_enabled[p] = not self.phase_enabled[p]
                state_str = "ACTIVE (Running)" if self.phase_enabled[p] else "PAUSED (Bypassed)"
                log_event("default_run", "orchestrator", "WARN" if not self.phase_enabled[p] else "INFO", f"⚙️ Phase '{p.upper()}' updated to: {state_str}")
            return {
                "phase": p,
                "is_enabled": self.phase_enabled.get(p, True),
                "all_phases": dict(self.phase_enabled)
            }

    def start(self) -> Dict[str, Any]:
        """Resumes or starts the continuous autonomous pipeline loop."""
        with self._lock:
            self._paused = False
            self._running = True
            self._step_once = False
            self.start_time = time.time()

            update_run_state(status="running", current_phase="active")
            log_event("default_run", "orchestrator", "INFO", "▶ Pipeline started: Autonomous processing active")

            if self._thread is None or not self._thread.is_alive():
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._loop, daemon=True, name="malayaLLM_Pipeline_Thread")
                self._thread.start()

            return self.get_status()

    def pause(self) -> Dict[str, Any]:
        """Gracefully pauses the autonomous pipeline after current item."""
        with self._lock:
            self._paused = True
            self.start_time = None  # Reset active timing on pause
            update_run_state(status="paused", current_phase="idle")
            log_event("default_run", "orchestrator", "WARN", "❚❚ Pipeline paused: Awaiting operator resume command")
            return self.get_status()

    def step(self) -> Dict[str, Any]:
        """Executes a single item end-to-end and immediately pauses."""
        with self._lock:
            self._step_once = True
            self._paused = False
            self._running = True

            update_run_state(status="running", current_phase="single_step")
            log_event("default_run", "orchestrator", "INFO", "⏭ Single-step execution triggered")

            if self._thread is None or not self._thread.is_alive():
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._loop, daemon=True, name="malayaLLM_Pipeline_Thread")
                self._thread.start()

            return self.get_status()

    def stop(self):
        """Terminates background worker."""
        with self._lock:
            self._running = False
            self._paused = True
            self._stop_event.set()
            update_run_state(status="idle", current_phase="idle")

    def _execute_single_cycle(self) -> bool:
        """Runs one item through all 4 pipeline workers."""
        try:
            # -------------------------------------------------------------
            # PHASE 1: INGESTION
            # -------------------------------------------------------------
            if not self.phase_enabled.get("ingestion", True):
                update_run_state(current_phase="ingestion_paused")
                log_event("default_run", "ingestion", "INFO", "⏸ Phase 1 (Ingestion) PAUSED: waiting to clear downstream backlog")
                time.sleep(1.5)
                return True

            update_run_state(current_phase="ingestion")
            log_event("default_run", "ingestion", "INFO", "📡 Harvesting Malayalam text from data sources...")

            raw_item = ingestion_worker.get_next_item()
            item_id = raw_item["id"]
            source = raw_item["source"]
            title = raw_item["title"]
            raw_text = raw_item["raw_text"]

            set_live_item({
                "item_id": item_id,
                "source": source,
                "title": title,
                "phase": "ingestion",
                "raw_text": raw_text[:400],
                "cleaned_text": "Awaiting Normalizer processing...",
                "malayalam_density": 0.0,
                "fluency_score": 0.0,
                "chillu_fixes": 0,
                "pii_redacted": 0
            })
            increment_run_counters(ingested_count=1, iteration_count=1)
            time.sleep(self.step_delay * 0.4)

            # -------------------------------------------------------------
            # PHASE 2: MORPHOLOGY & UNICODE NORMALIZATION
            # -------------------------------------------------------------
            if not self.phase_enabled.get("normalization", True):
                cleaned_text = raw_text
                density = 1.0
                density_passed = True
                chillu_fixes = 0
                pii_redacted = 0
                norm_notes = ["Phase 2 (Normalization) bypassed by operator"]
                log_event("default_run", "normalizer", "WARN", f"⚡ Phase 2 (Normalizer) PAUSED: Bypassed morphology normalization for '{title[:35]}'")
            else:
                update_run_state(current_phase="normalization")
                log_event("default_run", "normalizer", "INFO", f"🧬 Normalizing morphology and enforcing density on: '{title[:45]}...'")

                norm_result = normalizer_worker.process(raw_text)
                cleaned_text = norm_result["cleaned_text"]
                density = norm_result["malayalam_density"]
                density_passed = norm_result["density_passed"]
                chillu_fixes = norm_result["chillu_fixes"]
                pii_redacted = norm_result["pii_redacted"]
                norm_notes = norm_result["audit_notes"]

                set_live_item({
                    "item_id": item_id,
                    "source": source,
                    "title": title,
                    "phase": "normalization",
                    "raw_text": raw_text[:400],
                    "cleaned_text": cleaned_text[:400],
                    "malayalam_density": density,
                    "fluency_score": 0.0,
                    "chillu_fixes": chillu_fixes,
                    "pii_redacted": pii_redacted
                })
                time.sleep(self.step_delay * 0.4)

                # Enforce >= 60% Malayalam Unicode density gating
                if not density_passed:
                    increment_run_counters(rejected_density_count=1)
                    log_event(
                        "default_run", "normalizer", "WARN",
                        f"⚠️ Gating Dropped: Malayalam density {density*100:.1f}% < 60% threshold for '{title[:35]}'"
                    )
                    time.sleep(self.step_delay * 0.3)
                    return True

                increment_run_counters(normalized_count=1)
                log_event(
                    "default_run", "normalizer", "SUCCESS",
                    f"✓ Normalized: {chillu_fixes} Chillus fixed, {pii_redacted} PII redacted, density: {density*100:.1f}%"
                )

            # -------------------------------------------------------------
            # PHASE 3: DUAL-LLM QUALITY PIPELINE (QWEN + GEMMA)
            # -------------------------------------------------------------
            if not self.phase_enabled.get("judging", True):
                # Bypassed LLM Judge - fast track in <10ms to clear bottleneck!
                update_run_state(current_phase="judging_bypassed")
                log_event("default_run", "dual_llm", "WARN", f"⚡ Phase 3 (LLM Judge) PAUSED: Fast-tracking '{title[:35]}' directly to Staging")
                qwen_text = cleaned_text
                gemma_text = cleaned_text
                fluency_score = 0.95
                confidence_score = 0.90
                quality_rating = "Fast-Track (LLM Bypassed)"
                is_auto_approved = True
                dual_res = {"critique_notes": ["Phase 3 Dual-LLM bypassed by operator to clear bottleneck"]}
                self.last_engine_used = "Fast-Track Bypass"
                increment_run_counters(judged_count=1)
            else:
                update_run_state(current_phase="judging")
                log_event("default_run", "dual_llm", "INFO", f"🤖 Dual-LLM Pass 1: Qwen Extractor processing '{title[:35]}...'")

                dual_res = dual_llm_pipeline.process_dual_pass(cleaned_text, title)
                qwen_text = dual_res.get("qwen_extracted_text", cleaned_text)
                gemma_text = dual_res.get("cleaned_text", qwen_text)
                fluency_score = dual_res.get("fluency_score", 1.0)
                confidence_score = dual_res.get("confidence_score", 0.90)
                quality_rating = dual_res.get("quality_rating", "High Quality")
                is_auto_approved = dual_res.get("is_auto_approved", False)
                qwen_engine = dual_res.get("qwen_engine", "Qwen")
                gemma_engine = dual_res.get("gemma_engine", "Gemma")
                
                self.last_engine_used = f"{qwen_engine} ➔ {gemma_engine}"
                increment_run_counters(judged_count=1)

                set_live_item({
                    "item_id": item_id,
                    "source": source,
                    "title": title,
                    "phase": "judging",
                    "raw_text": raw_text[:400],
                    "cleaned_text": gemma_text[:400],
                    "malayalam_density": density,
                    "fluency_score": fluency_score,
                    "confidence_score": confidence_score,
                    "chillu_fixes": chillu_fixes,
                    "pii_redacted": pii_redacted,
                    "auto_approved": 1 if is_auto_approved else 0
                })
                time.sleep(self.step_delay * 0.4)

                log_event(
                    "default_run", "dual_llm", "SUCCESS",
                    f"✓ Dual-LLM Verified: Confidence {confidence_score*100:.1f}%, Fluency {fluency_score*100:.1f}% [{quality_rating}]"
                )

            # -------------------------------------------------------------
            # PHASE 4: STAGING & AUTOMATED FILTERING (AUTO-APPROVE >= 85%)
            # -------------------------------------------------------------
            if not self.phase_enabled.get("staging", True):
                update_run_state(current_phase="staging_paused")
                log_event("default_run", "staging", "WARN", f"⏸ Phase 4 (Staging) PAUSED: skipping ledger write for '{title[:35]}'")
                time.sleep(self.step_delay * 0.3)
                return True
            update_run_state(current_phase="staging")
            all_notes = norm_notes + dual_res.get("critique_notes", [])
            item_status = "approved" if is_auto_approved else "pending_approval"
            reviewer_notes = f"Auto-approved via Gemma Reviewer (Confidence: {confidence_score*100:.1f}%)" if is_auto_approved else f"Gemma Flagged for HITL Review (Confidence: {confidence_score*100:.1f}% < 85%)"

            add_review_item({
                "item_id": item_id,
                "batch_id": "batch_autonomous",
                "source": source,
                "title": title,
                "raw_text": raw_text,
                "cleaned_text": gemma_text,
                "qwen_extracted_text": qwen_text,
                "gemma_proofread_text": gemma_text,
                "malayalam_density": density,
                "density_passed": density_passed,
                "chillu_fixes": chillu_fixes,
                "pii_redacted": pii_redacted,
                "fluency_score": fluency_score,
                "confidence_score": confidence_score,
                "auto_approved": 1 if is_auto_approved else 0,
                "is_auto_approved": is_auto_approved,
                "quality_rating": quality_rating,
                "audit_notes": all_notes,
                "status": item_status,
                "reviewer_notes": reviewer_notes
            })

            increment_run_counters(total_items_processed=1)
            self.processed_since_start += 1

            set_live_item({
                "item_id": item_id,
                "source": source,
                "title": title,
                "phase": "staging",
                "raw_text": raw_text[:400],
                "cleaned_text": gemma_text[:400],
                "malayalam_density": density,
                "fluency_score": fluency_score,
                "confidence_score": confidence_score,
                "chillu_fixes": chillu_fixes,
                "pii_redacted": pii_redacted,
                "auto_approved": 1 if is_auto_approved else 0
            })

            if is_auto_approved:
                log_event(
                    "default_run", "staging", "SUCCESS",
                    f"⚡ AUTO-APPROVED: '{title[:35]}' (Confidence {confidence_score*100:.1f}% ≥ 85%) -> Staged directly for training"
                )
            else:
                log_event(
                    "default_run", "staging", "WARN",
                    f"📋 HITL QUEUED: '{title[:35]}' (Confidence {confidence_score*100:.1f}% < 85%) -> Routed to Human Review Queue"
                )
            time.sleep(self.step_delay * 0.3)
            return True

        except Exception as e:
            log_event("default_run", "error", "ERROR", f"Pipeline error: {str(e)}")
            update_run_state(error_message=str(e))
            time.sleep(2.0)
            return False

    def _loop(self):
        """Continuous pipeline loop executed in background thread."""
        while not self._stop_event.is_set():
            if self._paused and not self._step_once:
                time.sleep(0.5)
                continue

            self._execute_single_cycle()

            if self._step_once:
                with self._lock:
                    self._step_once = False
                    self._paused = True
                    update_run_state(status="paused", current_phase="idle")
                    log_event("default_run", "orchestrator", "INFO", "Step execution completed. Paused.")

            # Cooldown delay between iterations
            time.sleep(1.0)

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive status, live item, throughput, and metrics."""
        run_state = get_run_state()
        queue_stats = get_queue_stats()
        live_item = get_live_item()
        recent_logs = get_recent_logs(limit=25)
        rotator_summary = key_rotator.get_status_summary()

        is_running = (run_state.get("status") == "running") and not self._paused

        # Compute throughput (items per minute)
        # When paused, current velocity is 0.0 /min
        throughput = 0.0
        if is_running and self.start_time and self.processed_since_start > 0:
            elapsed_min = (time.time() - self.start_time) / 60.0
            if elapsed_min > 0:
                throughput = round(self.processed_since_start / elapsed_min, 1)

        candidate_prov, _ = key_rotator.get_candidate()

        return {
            "is_running": is_running,
            "status": "running" if is_running else "paused",
            "active_engine": self.last_engine_used,
            "candidate_provider": candidate_prov,
            "current_phase": run_state.get("current_phase", "idle"),
            "iteration_count": run_state.get("iteration_count", 0),
            "total_items_processed": run_state.get("total_items_processed", 0),
            "phase_enabled": dict(self.phase_enabled),
            "counters": {
                "ingested": run_state.get("ingested_count", 0),
                "normalized": run_state.get("normalized_count", 0),
                "rejected_density": run_state.get("rejected_density_count", 0),
                "judged": run_state.get("judged_count", 0),
                "approved": run_state.get("approved_count", 0),
                "auto_approved": queue_stats.get("auto_approved_count", 0),
                "hitl_pending": queue_stats.get("pending_count", 0),
                "rejected": run_state.get("rejected_count", 0),
            },
            "dual_llm": {
                "qwen_model": dual_llm_pipeline.qwen_model,
                "gemma_model": dual_llm_pipeline.gemma_model,
                "auto_approve_threshold": dual_llm_pipeline.auto_approve_threshold
            },
            "throughput_per_min": throughput,
            "queue_stats": queue_stats,
            "live_item": live_item,
            "logs": recent_logs,
            "keys_status": rotator_summary,
            "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }


# Global Singleton Pipeline Engine
pipeline_engine = PipelineEngine()
