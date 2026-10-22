"""
malayaLLM v2.3.0 - Autonomous, Lightweight Modular Malayalam Operations Center
FastAPI REST Server exposing pipeline control, live metrics, key rotation, and HITL review queue.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Union

# Enforce UTF-8 on Windows Console
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.db import (
    get_review_queue, get_review_item, update_review_action,
    get_queue_stats, get_recent_logs, init_db, add_review_item,
    auto_proofread_pending_items
)
from backend.key_rotator import key_rotator
from backend.pipeline_engine import pipeline_engine
from workers.exporter import staging_exporter
from workers.ingestor import ingestion_worker, OFFLINE_MALAYALAM_CORPUS
from workers.normalizer import normalizer_worker
from workers.judge import quality_judge
from workers.pdf_extractor import pdf_extractor
from workers.dual_llm import dual_llm_pipeline

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", 8080))

app = FastAPI(
    title="malayaLLM Operations Center",
    version="2.3.0",
    description="Autonomous, Lightweight Modular Malayalam Data Pipeline & Operations Center"
)

# Enable CORS for local testing and multi-device access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Pydantic Request Models
# ==========================================

class KeyUpdatePayload(BaseModel):
    provider: str
    keys: Union[List[str], str]
    test_after_save: Optional[bool] = False


class KeyTestPayload(BaseModel):
    provider: str
    key: str


class QueueActionPayload(BaseModel):
    item_id: Optional[str] = None
    item_ids: Optional[List[str]] = None
    action: str  # 'approve' or 'reject'
    reviewer_notes: Optional[str] = None
    edited_cleaned_text: Optional[str] = None


class OllamaConfigPayload(BaseModel):
    endpoint: Optional[str] = None
    model: Optional[str] = None


# ==========================================
# Pipeline Control Endpoints
# ==========================================

@app.post("/api/pipeline/start")
def start_pipeline():
    """Starts or resumes the autonomous data pipeline loop."""
    status = pipeline_engine.start()
    return JSONResponse(content={"success": True, "message": "Pipeline started", "data": status})


@app.post("/api/pipeline/pause")
def pause_pipeline():
    """Pauses the autonomous data pipeline loop gracefully."""
    status = pipeline_engine.pause()
    return JSONResponse(content={"success": True, "message": "Pipeline paused", "data": status})


@app.post("/api/pipeline/step")
def step_pipeline():
    """Executes a single pipeline iteration through all phases and pauses."""
    status = pipeline_engine.step()
    return JSONResponse(content={"success": True, "message": "Single step executed", "data": status})


@app.get("/api/pipeline/status")
def get_pipeline_status():
    """Returns real-time pipeline status, iteration counters, active item, and recent logs."""
    status = pipeline_engine.get_status()
    return JSONResponse(content=status)


@app.get("/api/pipeline/logs")
def get_pipeline_logs(limit: int = 50):
    """Retrieves recent event logs."""
    logs = get_recent_logs(limit=limit)
    return JSONResponse(content={"logs": logs})


# ==========================================
# Human Review Queue Endpoints
# ==========================================

@app.get("/api/queue/review")
def list_review_queue(
    status: Optional[str] = Query(None, description="pending_approval, approved, rejected, or all"),
    limit: int = 50,
    offset: int = 0
):
    """Fetches items from the Human Review Queue."""
    items = get_review_queue(status=status, limit=limit, offset=offset)
    stats = get_queue_stats()
    return JSONResponse(content={
        "items": items,
        "total_returned": len(items),
        "stats": stats
    })


@app.get("/api/queue/item/{item_id}")
def get_queue_single_item(item_id: str):
    """Retrieves a single review item by ID."""
    item = get_review_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return JSONResponse(content=item)


@app.post("/api/queue/action")
def perform_queue_action(payload: QueueActionPayload):
    """
    Applies 'approve' or 'reject' action to a single item or batch of items.
    Allows optional operator notes and in-place cleaned text corrections.
    """
    action = payload.action.lower()
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    target_ids = []
    if payload.item_ids:
        target_ids.extend(payload.item_ids)
    elif payload.item_id:
        target_ids.append(payload.item_id)
    else:
        raise HTTPException(status_code=400, detail="Must provide item_id or item_ids")

    success_count = 0
    for iid in target_ids:
        # Pass edited text only if applying to single item
        text_override = payload.edited_cleaned_text if len(target_ids) == 1 else None
        if update_review_action(iid, action, payload.reviewer_notes, text_override):
            success_count += 1

    updated_stats = get_queue_stats()
    return JSONResponse(content={
        "success": True,
        "action": action,
        "affected_count": success_count,
        "stats": updated_stats
    })


@app.post("/api/queue/seed_demo")
def seed_demo_items():
    """Generates fresh diverse Malayalam records for the Review Queue."""
    added_count = 0
    for doc in OFFLINE_MALAYALAM_CORPUS[:4]:
        raw_text = doc["raw_text"]
        norm = normalizer_worker.process(raw_text)
        judge = quality_judge.judge(norm["cleaned_text"])

        item_id = f"demo_seed_{int(time.time()*1000)}_{added_count}"
        add_review_item({
            "item_id": item_id,
            "batch_id": "batch_demo_seed",
            "source": doc["source"],
            "title": doc["title"],
            "raw_text": raw_text,
            "cleaned_text": norm["cleaned_text"],
            "malayalam_density": norm["malayalam_density"],
            "density_passed": norm["density_passed"],
            "chillu_fixes": norm["chillu_fixes"],
            "pii_redacted": norm["pii_redacted"],
            "fluency_score": judge["fluency_score"],
            "quality_rating": judge["quality_rating"],
            "audit_notes": norm["audit_notes"] + judge["audit_notes"],
            "status": "pending_approval"
        })
        added_count += 1

    return JSONResponse(content={
        "success": True,
        "added_count": added_count,
        "stats": get_queue_stats()
    })


@app.post("/api/queue/auto_proofread")
def run_auto_proofread_batch():
    """
    Evaluates pending queue records through Gemma Linguistic Proofreader.
    Auto-approves records with confidence >= 85% directly to training staging.
    Routes records with confidence < 85% to Human-in-the-Loop review queue.
    """
    result = auto_proofread_pending_items(dual_llm_pipeline.run_gemma_proofreading)
    return JSONResponse(content={
        "success": True,
        "message": f"Evaluated {result.get('total_scanned', 0)} items with Gemma. Auto-approved: {result.get('auto_approved', 0)}. Retained in HITL: {result.get('remaining_pending', 0)}.",
        "result": result,
        "stats": get_queue_stats()
    })


@app.post("/api/ingest/upload_pdf")
async def upload_custom_pdf(file: UploadFile = File(...)):
    """
    Directly uploads user-provided Malayalam PDF, extracts & cleans contents,
    removes unwanted footers/page numbers/watermarks, and segments into semantic chunks.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    uploads_dir = os.path.join(BASE_DIR, "data", "sources", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename)
    target_path = os.path.join(uploads_dir, safe_name)

    # Save uploaded file safely
    content = await file.read()
    with open(target_path, "wb") as f_out:
        f_out.write(content)

    # Extract, clean, and chunk
    chunks = pdf_extractor.process_pdf_file(target_path)
    if chunks:
        ingestion_worker.enqueue_chunks(chunks)

    return JSONResponse(content={
        "success": True,
        "filename": safe_name,
        "bytes_received": len(content),
        "chunks_extracted": len(chunks),
        "message": f"Successfully extracted and enqueued {len(chunks)} cleaned semantic chunks from {safe_name}."
    })



# ==========================================
# Key Rotator & Credentials Endpoints
# ==========================================

@app.get("/api/keys")
def get_keys_status():
    """Returns active key counts, cooldown states, and masked key info."""
    return JSONResponse(content=key_rotator.get_status_summary())


@app.post("/api/keys")
def save_provider_keys(payload: KeyUpdatePayload):
    """
    Securely saves keys for a provider (Gemini, OpenRouter, Groq, NVIDIA NIM).
    Accepts single key string or list of keys for round-robin rotation.
    """
    prov = payload.provider.lower()
    if prov not in key_rotator.SUPPORTED_PROVIDERS and prov != "ollama":
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {payload.provider}")

    keys_list: List[str] = []
    if isinstance(payload.keys, str):
        # Support newline or comma separated input
        raw_split = re.split(r'[\n,]+', payload.keys)
        keys_list = [k.strip() for k in raw_split if k.strip()]
    elif isinstance(payload.keys, list):
        keys_list = [k.strip() for k in payload.keys if k and k.strip()]

    key_rotator.update_provider_keys(prov, keys_list)

    validation_result = None
    if payload.test_after_save and keys_list:
        valid, msg = key_rotator.test_provider_key(prov, keys_list[0])
        validation_result = {"valid": valid, "message": msg}

    return JSONResponse(content={
        "success": True,
        "provider": prov,
        "total_saved": len(keys_list),
        "validation": validation_result,
        "summary": key_rotator.get_status_summary()
    })


@app.post("/api/keys/test")
def test_single_key(payload: KeyTestPayload):
    """Pings the target provider to test key connectivity."""
    valid, msg = key_rotator.test_provider_key(payload.provider, payload.key)
    return JSONResponse(content={"success": valid, "message": msg})


@app.post("/api/keys/ollama_config")
def update_ollama_config(payload: OllamaConfigPayload):
    """Updates Ollama endpoint and target model for 100% offline usage."""
    if payload.endpoint:
        key_rotator.ollama_endpoint = payload.endpoint.strip()
    if payload.model:
        key_rotator.ollama_model = payload.model.strip()
    key_rotator.save_to_vault()
    return JSONResponse(content={
        "success": True,
        "ollama": {
            "endpoint": key_rotator.ollama_endpoint,
            "model": key_rotator.ollama_model
        }
    })


@app.get("/api/ollama/tags")
def get_ollama_tags():
    """Scans local Ollama daemon for available models."""
    url = f"{key_rotator.ollama_endpoint.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "malayaLLM/2.3.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                return JSONResponse(content={
                    "is_running": True,
                    "endpoint": key_rotator.ollama_endpoint,
                    "models": data.get("models", [])
                })
    except Exception as e:
        return JSONResponse(content={
            "is_running": False,
            "endpoint": key_rotator.ollama_endpoint,
            "error": str(e),
            "models": []
        })


# ==========================================
# Staging & Training Exporter Endpoints
# ==========================================

@app.post("/api/export/trigger")
def trigger_export():
    """Bundles approved dataset records into JSONL, JSON, and Colab QLoRA script."""
    result = staging_exporter.export_approved_dataset()
    return JSONResponse(content=result)


@app.get("/api/training/colab_script")
def get_colab_script():
    """Returns the turnkey Unsloth QLoRA Colab training script."""
    script_text = staging_exporter.get_colab_script_text()
    return PlainTextResponse(content=script_text, media_type="text/plain; charset=utf-8")


@app.get("/api/export/download/unified")
def download_unified_dataset():
    """Serves the single unified training dataset for QLoRA / Unsloth fine-tuning."""
    path = os.path.join(BASE_DIR, "data", "approved_training", "malayalam_dataset_unified.jsonl")
    if not os.path.exists(path):
        staging_exporter.export_approved_dataset()
    if os.path.exists(path):
        return FileResponse(path, filename="malayalam_dataset_unified.jsonl", media_type="application/x-jsonlines")
    raise HTTPException(status_code=404, detail="Unified dataset file not found.")


@app.get("/api/export/download/train")
def download_train_dataset():
    """Serves the 90% training split dataset for Unsloth / QLoRA."""
    path = os.path.join(BASE_DIR, "data", "approved_training", "train.jsonl")
    if not os.path.exists(path):
        staging_exporter.export_approved_dataset()
    if os.path.exists(path):
        return FileResponse(path, filename="train.jsonl", media_type="application/x-jsonlines")
    raise HTTPException(status_code=404, detail="Train dataset file not found.")


@app.get("/api/export/download/val")
def download_val_dataset():
    """Serves the 10% validation split dataset for Unsloth / QLoRA."""
    path = os.path.join(BASE_DIR, "data", "approved_training", "val.jsonl")
    if not os.path.exists(path):
        staging_exporter.export_approved_dataset()
    if os.path.exists(path):
        return FileResponse(path, filename="val.jsonl", media_type="application/x-jsonlines")
    raise HTTPException(status_code=404, detail="Validation dataset file not found.")


@app.get("/api/export/download/manifest")
def download_manifest():
    """Serves dataset manifest metadata and audit report."""
    path = os.path.join(BASE_DIR, "data", "approved_training", "dataset_manifest.json")
    if not os.path.exists(path):
        staging_exporter.export_approved_dataset()
    if os.path.exists(path):
        return FileResponse(path, filename="dataset_manifest.json", media_type="application/json")
    raise HTTPException(status_code=404, detail="Manifest file not found.")


@app.get("/api/pipeline/models")
def get_dual_llm_models():
    """Returns local Ollama dual model configuration and status."""
    return JSONResponse(content={
        "worker_extractor": {
            "role": "Worker / Extractor",
            "model": dual_llm_pipeline.qwen_model,
            "status": "active"
        },
        "reviewer_proofreader": {
            "role": "Linguistic Reviewer / Proofreader",
            "model": dual_llm_pipeline.gemma_model,
            "auto_approve_threshold": ">= 85% Confidence",
            "hitl_threshold": "< 85% Confidence",
            "status": "active"
        }
    })



@app.get("/api/health")
def health_check():
    """System health check endpoint."""
    return JSONResponse(content={
        "status": "healthy",
        "system": "malayaLLM Autonomous Operations Center",
        "version": "2.3.0",
        "pipeline_state": pipeline_engine.get_status().get("status")
    })


# ==========================================
# Static Files & Dashboard UI
# ==========================================

@app.get("/")
def serve_index():
    """Serves the main Operations Center Dashboard UI."""
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html; charset=utf-8")
    return PlainTextResponse("malayaLLM Operations Center UI not found. Check index.html.", status_code=404)


# Mount static assets
for dir_name in ["css", "js", "assets", "data"]:
    dir_path = os.path.join(BASE_DIR, dir_name)
    if os.path.exists(dir_path):
        app.mount(f"/{dir_name}", StaticFiles(directory=dir_path), name=dir_name)


if __name__ == "__main__":
    import uvicorn
    print(f"\n=======================================================")
    print(f" malayaLLM v2.3.0 Operations Center")
    print(f" URL: http://localhost:{PORT}")
    print(f" Offline Capable: Yes (Local Ollama & Heuristic Critic)")
    print(f" UTF-8 Enforced: Yes")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

