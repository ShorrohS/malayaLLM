"""
malayaLLM v2.3.0 - SQLite Job State & Ledger
Manages pipeline state, iteration counters, event logs, and the Human Review Queue.
Database: data/pipeline_state.db
"""

import os
import sys
import json
import sqlite3
import datetime
import threading
from typing import Dict, List, Optional, Any, Tuple

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "pipeline_state.db")
PENDING_DIR = os.path.join(DATA_DIR, "pending_approval")
APPROVED_DIR = os.path.join(DATA_DIR, "approved_training")
REJECTED_DIR = os.path.join(DATA_DIR, "rejected_feedback")

for path in [DATA_DIR, PENDING_DIR, APPROVED_DIR, REJECTED_DIR]:
    os.makedirs(path, exist_ok=True)

_lock = threading.Lock()


def get_db_connection() -> sqlite3.Connection:
    """Creates a thread-safe connection with row factory and busy timeout."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    """Initializes tables for pipeline state, logs, review queue, and active live item."""
    with _lock:
        conn = get_db_connection()
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()

            # 1. Pipeline Runs & State
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'idle',
                current_phase TEXT DEFAULT 'idle',
                iteration_count INTEGER DEFAULT 0,
                total_items_processed INTEGER DEFAULT 0,
                ingested_count INTEGER DEFAULT 0,
                normalized_count INTEGER DEFAULT 0,
                rejected_density_count INTEGER DEFAULT 0,
                judged_count INTEGER DEFAULT 0,
                approved_count INTEGER DEFAULT 0,
                rejected_count INTEGER DEFAULT 0,
                avg_density REAL DEFAULT 0.0,
                avg_fluency REAL DEFAULT 0.0,
                started_at TEXT,
                updated_at TEXT,
                completed_at TEXT,
                error_message TEXT
            )
            """)

            # 2. Pipeline Event Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                phase TEXT,
                level TEXT DEFAULT 'INFO',
                message TEXT,
                timestamp TEXT
            )
            """)

            # 3. Human Review Queue Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_queue (
                item_id TEXT PRIMARY KEY,
                batch_id TEXT,
                source TEXT,
                title TEXT,
                raw_text TEXT,
                cleaned_text TEXT,
                malayalam_density REAL DEFAULT 0.0,
                density_passed INTEGER DEFAULT 1,
                chillu_fixes INTEGER DEFAULT 0,
                pii_redacted INTEGER DEFAULT 0,
                fluency_score REAL DEFAULT 1.0,
                confidence_score REAL DEFAULT 0.0,
                auto_approved INTEGER DEFAULT 0,
                qwen_extracted_text TEXT,
                gemma_proofread_text TEXT,
                quality_rating TEXT DEFAULT 'High Quality',
                audit_notes TEXT DEFAULT '[]',
                status TEXT DEFAULT 'pending_approval',
                created_at TEXT,
                reviewed_at TEXT,
                reviewer_notes TEXT
            )
            """)

            # Safe column migrations for existing databases
            cursor.execute("PRAGMA table_info(review_queue)")
            existing_cols = [r[1] for r in cursor.fetchall()]
            if "confidence_score" not in existing_cols:
                cursor.execute("ALTER TABLE review_queue ADD COLUMN confidence_score REAL DEFAULT 0.0")
            if "auto_approved" not in existing_cols:
                cursor.execute("ALTER TABLE review_queue ADD COLUMN auto_approved INTEGER DEFAULT 0")
            if "qwen_extracted_text" not in existing_cols:
                cursor.execute("ALTER TABLE review_queue ADD COLUMN qwen_extracted_text TEXT")
            if "gemma_proofread_text" not in existing_cols:
                cursor.execute("ALTER TABLE review_queue ADD COLUMN gemma_proofread_text TEXT")

            cursor.execute("PRAGMA table_info(pipeline_runs)")
            run_cols = [r[1] for r in cursor.fetchall()]
            if "auto_approved_count" not in run_cols:
                cursor.execute("ALTER TABLE pipeline_runs ADD COLUMN auto_approved_count INTEGER DEFAULT 0")
            if "hitl_pending_count" not in run_cols:
                cursor.execute("ALTER TABLE pipeline_runs ADD COLUMN hitl_pending_count INTEGER DEFAULT 0")

            # 4. Live Pipeline Item (for real-time frontend visualization)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS live_item (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                item_id TEXT,
                source TEXT,
                title TEXT,
                phase TEXT,
                raw_text TEXT,
                cleaned_text TEXT,
                malayalam_density REAL DEFAULT 0.0,
                fluency_score REAL DEFAULT 0.0,
                confidence_score REAL DEFAULT 0.0,
                chillu_fixes INTEGER DEFAULT 0,
                pii_redacted INTEGER DEFAULT 0,
                auto_approved INTEGER DEFAULT 0,
                updated_at TEXT
            )
            """)

            cursor.execute("PRAGMA table_info(live_item)")
            live_cols = [r[1] for r in cursor.fetchall()]
            if "confidence_score" not in live_cols:
                cursor.execute("ALTER TABLE live_item ADD COLUMN confidence_score REAL DEFAULT 0.0")
            if "auto_approved" not in live_cols:
                cursor.execute("ALTER TABLE live_item ADD COLUMN auto_approved INTEGER DEFAULT 0")

            # Seed default active run if none exists
            cursor.execute("SELECT run_id FROM pipeline_runs WHERE run_id = 'default_run'")
            if not cursor.fetchone():
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                cursor.execute("""
                INSERT INTO pipeline_runs (
                    run_id, status, current_phase, started_at, updated_at
                ) VALUES ('default_run', 'idle', 'idle', ?, ?)
                """, (now, now))

            # Initialize live item slot
            cursor.execute("SELECT id FROM live_item WHERE id = 1")
            if not cursor.fetchone():
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                cursor.execute("""
                INSERT INTO live_item (id, item_id, source, title, phase, raw_text, cleaned_text, updated_at)
                VALUES (1, '', 'Offline Engine Ready', 'malayaLLM Autonomous Pipeline v2.3.0', 'idle', '', '', ?)
                """, (now,))

            conn.commit()

            # Seed review queue from existing pending files if empty
            cursor.execute("SELECT COUNT(*) as cnt FROM review_queue")
            row = cursor.fetchone()
            if row and row['cnt'] == 0:
                _seed_initial_batches(cursor)
                conn.commit()

        finally:
            conn.close()


def _seed_initial_batches(cursor):
    """Imports pending JSON batches into review_queue if table is currently empty."""
    if not os.path.exists(PENDING_DIR):
        return

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for fname in os.listdir(PENDING_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(PENDING_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            batch_id = data.get("id", os.path.splitext(fname)[0])
            source = data.get("source", "Scraped Corpus")
            items = data.get("items", [])
            for item in items:
                item_id = item.get("id", f"{batch_id}_{datetime.datetime.now().timestamp()}")
                notes = json.dumps(item.get("audit_notes", []), ensure_ascii=False)
                cursor.execute("""
                INSERT OR REPLACE INTO review_queue (
                    item_id, batch_id, source, title, raw_text, cleaned_text,
                    malayalam_density, density_passed, chillu_fixes, pii_redacted,
                    fluency_score, quality_rating, audit_notes, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_approval', ?)
                """, (
                    item_id,
                    batch_id,
                    source,
                    item.get("title", "Malayalam Corpus Record"),
                    item.get("raw_text", ""),
                    item.get("cleaned_text", ""),
                    float(item.get("malayalam_density", 0.0)),
                    1 if item.get("density_passed", True) else 0,
                    int(item.get("chillu_fixes", 0)),
                    int(item.get("pii_redacted", 0)),
                    float(item.get("fluency_score", 1.0)),
                    item.get("quality_rating", "High Quality"),
                    notes,
                    now
                ))
        except Exception as e:
            print(f"Error seeding batch file {fname}: {e}", file=sys.stderr)


# ==========================================
# Run State Management
# ==========================================

def get_run_state(run_id: str = "default_run") -> Dict[str, Any]:
    """Fetches the state dictionary for the given run_id."""
    with _lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {"run_id": run_id, "status": "idle", "current_phase": "idle"}
        finally:
            conn.close()


def update_run_state(run_id: str = "default_run", **kwargs) -> Dict[str, Any]:
    """Updates fields on the active pipeline run."""
    with _lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            kwargs["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            set_clauses = [f"{k} = ?" for k in kwargs.keys()]
            values = list(kwargs.values())
            values.append(run_id)

            cursor.execute(
                f"UPDATE pipeline_runs SET {', '.join(set_clauses)} WHERE run_id = ?",
                values
            )
            conn.commit()

            cursor.execute("SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()


def increment_run_counters(run_id: str = "default_run", **increments):
    """Safely increments run counters (e.g. ingested_count=1, iteration_count=1)."""
    with _lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            clauses = [f"{col} = {col} + ?" for col in increments.keys()]
            values = list(increments.values())
            values.append(datetime.datetime.now(datetime.timezone.utc).isoformat())
            values.append(run_id)

            cursor.execute(
                f"UPDATE pipeline_runs SET {', '.join(clauses)}, updated_at = ? WHERE run_id = ?",
                values
            )
            conn.commit()
        finally:
            conn.close()


# ==========================================
# Event Logging
# ==========================================

def log_event(run_id: str, phase: str, level: str, message: str):
    """Appends an event log entry with timestamp."""
    with _lock:
        conn = get_db_connection()
        try:
            now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
            INSERT INTO pipeline_logs (run_id, phase, level, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, (run_id, phase, level, message, now))
            conn.commit()
        finally:
            conn.close()


def get_recent_logs(limit: int = 60, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves the most recent event logs ordered by timestamp descending."""
    with _lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if run_id:
                cursor.execute(
                    "SELECT * FROM pipeline_logs WHERE run_id = ? ORDER BY id DESC LIMIT ?",
                    (run_id, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM pipeline_logs ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
            rows = cursor.fetchall()
            return [dict(r) for r in reversed(rows)]
        finally:
            conn.close()


# ==========================================
# Live Item Display State
# ==========================================

def set_live_item(item_data: Dict[str, Any]):
    """Updates the live item in progress for immediate front-end streaming."""
    with _lock:
        conn = get_db_connection()
        try:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            conn.execute("""
            UPDATE live_item SET
                item_id = ?,
                source = ?,
                title = ?,
                phase = ?,
                raw_text = ?,
                cleaned_text = ?,
                malayalam_density = ?,
                fluency_score = ?,
                chillu_fixes = ?,
                pii_redacted = ?,
                updated_at = ?
            WHERE id = 1
            """, (
                item_data.get("item_id", ""),
                item_data.get("source", ""),
                item_data.get("title", ""),
                item_data.get("phase", "running"),
                item_data.get("raw_text", ""),
                item_data.get("cleaned_text", ""),
                float(item_data.get("malayalam_density", 0.0)),
                float(item_data.get("fluency_score", 0.0)),
                int(item_data.get("chillu_fixes", 0)),
                int(item_data.get("pii_redacted", 0)),
                now
            ))
            conn.commit()
        finally:
            conn.close()


def get_live_item() -> Dict[str, Any]:
    """Retrieves the current live item snapshot."""
    with _lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM live_item WHERE id = 1")
            row = cursor.fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()


# ==========================================
# Review Queue Management
# ==========================================

def add_review_item(item: Dict[str, Any]) -> str:
    """
    Inserts a freshly cleaned and judged item into the Review Queue.
    If confidence >= 0.85, it is automatically marked 'approved' (Auto-Staged).
    Otherwise it is marked 'pending_approval' (HITL review required).
    """
    with _lock:
        conn = get_db_connection()
        try:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            item_id = item.get("id") or item.get("item_id") or f"item_{int(datetime.datetime.now().timestamp() * 1000)}"
            notes = json.dumps(item.get("audit_notes", []), ensure_ascii=False) if isinstance(item.get("audit_notes"), (list, dict)) else str(item.get("audit_notes", "[]"))

            confidence = float(item.get("confidence_score", 0.0))
            is_auto_approved = bool(item.get("is_auto_approved") or item.get("auto_approved") or confidence >= 0.85)
            status = "approved" if is_auto_approved else item.get("status", "pending_approval")
            reviewed_at = now if is_auto_approved else None
            reviewer_notes = f"Auto-approved via Gemma Reviewer (Confidence: {confidence*100:.1f}%)" if is_auto_approved else item.get("reviewer_notes")

            conn.execute("""
            INSERT OR REPLACE INTO review_queue (
                item_id, batch_id, source, title, raw_text, cleaned_text,
                malayalam_density, density_passed, chillu_fixes, pii_redacted,
                fluency_score, confidence_score, auto_approved,
                qwen_extracted_text, gemma_proofread_text,
                quality_rating, audit_notes, status, created_at, reviewed_at, reviewer_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id,
                item.get("batch_id", "batch_autonomous"),
                item.get("source", "Autonomous Ingestion"),
                item.get("title", "Malayalam Dataset Record"),
                item.get("raw_text", ""),
                item.get("cleaned_text", ""),
                float(item.get("malayalam_density", 0.0)),
                1 if item.get("density_passed", True) else 0,
                int(item.get("chillu_fixes", 0)),
                int(item.get("pii_redacted", 0)),
                float(item.get("fluency_score", 1.0)),
                confidence,
                1 if is_auto_approved else 0,
                item.get("qwen_extracted_text", ""),
                item.get("gemma_proofread_text", ""),
                item.get("quality_rating", "High Quality"),
                notes,
                status,
                now,
                reviewed_at,
                reviewer_notes
            ))

            if is_auto_approved:
                conn.execute("UPDATE pipeline_runs SET approved_count = approved_count + 1, auto_approved_count = auto_approved_count + 1 WHERE run_id = 'default_run'")
            else:
                conn.execute("UPDATE pipeline_runs SET hitl_pending_count = hitl_pending_count + 1 WHERE run_id = 'default_run'")

            conn.commit()
            return item_id
        finally:
            conn.close()


def get_review_queue(status: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Fetches items in the review queue with optional status filtering."""
    with _lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if status == "auto_approved":
                cursor.execute(
                    "SELECT * FROM review_queue WHERE status = 'approved' AND auto_approved = 1 ORDER BY reviewed_at DESC, created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            elif status and status != "all":
                cursor.execute(
                    "SELECT * FROM review_queue WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (status, limit, offset)
                )
            else:
                cursor.execute(
                    "SELECT * FROM review_queue ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["audit_notes"] = json.loads(d["audit_notes"])
                except Exception:
                    d["audit_notes"] = [d["audit_notes"]] if d["audit_notes"] else []
                results.append(d)
            return results
        finally:
            conn.close()


def get_review_item(item_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single review item by ID."""
    with _lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM review_queue WHERE item_id = ?", (item_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["audit_notes"] = json.loads(d["audit_notes"])
            except Exception:
                d["audit_notes"] = [d["audit_notes"]] if d["audit_notes"] else []
            return d
        finally:
            conn.close()


def update_review_action(item_id: str, action: str, reviewer_notes: Optional[str] = None, edited_cleaned_text: Optional[str] = None) -> bool:
    """Updates an item status ('approved' or 'rejected') and records timestamp and notes."""
    with _lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            new_status = "approved" if action == "approve" else "rejected"

            if edited_cleaned_text is not None:
                cursor.execute("""
                UPDATE review_queue SET
                    status = ?,
                    cleaned_text = ?,
                    reviewed_at = ?,
                    reviewer_notes = ?
                WHERE item_id = ?
                """, (new_status, edited_cleaned_text, now, reviewer_notes or "", item_id))
            else:
                cursor.execute("""
                UPDATE review_queue SET
                    status = ?,
                    reviewed_at = ?,
                    reviewer_notes = ?
                WHERE item_id = ?
                """, (new_status, now, reviewer_notes or "", item_id))

            conn.commit()

            # Synchronize with approved_count / rejected_count in pipeline_runs
            if action == "approve":
                cursor.execute("UPDATE pipeline_runs SET approved_count = approved_count + 1 WHERE run_id = 'default_run'")
            else:
                cursor.execute("UPDATE pipeline_runs SET rejected_count = rejected_count + 1 WHERE run_id = 'default_run'")
            conn.commit()

            return cursor.rowcount > 0
        finally:
            conn.close()


def get_queue_stats() -> Dict[str, Any]:
    """Returns counts of pending, approved, and rejected items in the review queue."""
    with _lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT
                COUNT(CASE WHEN status = 'pending_approval' THEN 1 END) as pending_count,
                COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_count,
                COUNT(CASE WHEN status = 'approved' AND auto_approved = 1 THEN 1 END) as auto_approved_count,
                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count,
                COUNT(*) as total_count,
                AVG(malayalam_density) as avg_density,
                AVG(fluency_score) as avg_fluency,
                AVG(confidence_score) as avg_confidence,
                SUM(chillu_fixes) as total_chillu_fixes,
                SUM(pii_redacted) as total_pii_redacted
            FROM review_queue
            """)
            row = cursor.fetchone()
            return {
                "pending_count": row["pending_count"] or 0,
                "approved_count": row["approved_count"] or 0,
                "auto_approved_count": row["auto_approved_count"] or 0,
                "rejected_count": row["rejected_count"] or 0,
                "total_count": row["total_count"] or 0,
                "avg_density": round(row["avg_density"] or 0.0, 4),
                "avg_fluency": round(row["avg_fluency"] or 0.0, 3),
                "avg_confidence": round(row["avg_confidence"] or 0.0, 3),
                "total_chillu_fixes": row["total_chillu_fixes"] or 0,
                "total_pii_redacted": row["total_pii_redacted"] or 0
            }
        finally:
            conn.close()


def auto_proofread_pending_items(proofreader_fn, limit: Optional[int] = 20) -> Dict[str, Any]:
    """
    Iterates through pending_approval items in review_queue, passes them through
    Gemma's linguistic proofreader, and auto-approves if confidence >= 0.85 (85%).
    Items < 85% remain in pending_approval with updated critique notes and suggested proofreading.
    
    Concurrency safe: Releases SQLite connection and threading locks during LLM inference.
    """
    # 1. Fetch pending rows quickly without blocking other threads
    with _lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if limit:
                cursor.execute(
                    "SELECT * FROM review_queue WHERE status = 'pending_approval' ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            else:
                cursor.execute("SELECT * FROM review_queue WHERE status = 'pending_approval' ORDER BY created_at DESC")
            rows = [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    total_scanned = len(rows)
    auto_approved_count = 0
    remaining_pending = 0

    # 2. Evaluate each item outside of DB lock
    for row in rows:
        item_id = row["item_id"]
        title = row["title"]
        text_to_review = row["cleaned_text"] or row["raw_text"]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        try:
            result = proofreader_fn(text_to_review, title)
            conf = float(result.get("confidence_score", 0.0))
            proofread_text = result.get("proofread_text") or text_to_review
            quality_rating = result.get("quality_rating", "High Quality")
            critique_notes = result.get("critique_notes", [])
            critique_json = json.dumps(critique_notes, ensure_ascii=False)

            # 3. Perform quick isolated write
            with _lock:
                write_conn = get_db_connection()
                try:
                    w_cur = write_conn.cursor()
                    if conf >= 0.85:
                        # Auto-Approve Gate Triggered
                        w_cur.execute("""
                        UPDATE review_queue SET
                            status = 'approved',
                            auto_approved = 1,
                            confidence_score = ?,
                            cleaned_text = ?,
                            gemma_proofread_text = ?,
                            quality_rating = ?,
                            audit_notes = ?,
                            reviewed_at = ?,
                            reviewer_notes = ?
                        WHERE item_id = ?
                        """, (
                            conf,
                            proofread_text,
                            proofread_text,
                            quality_rating,
                            critique_json,
                            now,
                            f"Auto-approved via Gemma Reviewer (Confidence: {conf*100:.1f}%)",
                            item_id
                        ))
                        w_cur.execute("UPDATE pipeline_runs SET approved_count = approved_count + 1, auto_approved_count = auto_approved_count + 1 WHERE run_id = 'default_run'")
                        auto_approved_count += 1
                    else:
                        # Retain in HITL Pending queue
                        w_cur.execute("""
                        UPDATE review_queue SET
                            confidence_score = ?,
                            gemma_proofread_text = ?,
                            quality_rating = ?,
                            audit_notes = ?,
                            reviewer_notes = ?
                        WHERE item_id = ?
                        """, (
                            conf,
                            proofread_text,
                            quality_rating,
                            critique_json,
                            f"Gemma Flagged for Human Review (Confidence: {conf*100:.1f}% < 85%)",
                            item_id
                        ))
                        remaining_pending += 1
                    write_conn.commit()
                finally:
                    write_conn.close()

        except Exception as e:
            print(f"Error proofreading item {item_id}: {e}", file=sys.stderr)
            remaining_pending += 1

    return {
        "total_scanned": total_scanned,
        "auto_approved": auto_approved_count,
        "remaining_pending": remaining_pending
    }


# Initialize database automatically on module import
init_db()
