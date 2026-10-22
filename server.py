import http.server
import socketserver
import os
import sys
import json
import shutil
import urllib.request
import urllib.error

# Fix Windows console UTF-8 encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PORT = 8080
OLLAMA_BASE_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PENDING_DIR = os.path.join(BASE_DIR, "data", "pending_approval")
APPROVED_DIR = os.path.join(BASE_DIR, "data", "approved_training")
REJECTED_DIR = os.path.join(BASE_DIR, "data", "rejected_feedback")

for d in [PENDING_DIR, APPROVED_DIR, REJECTED_DIR]:
    os.makedirs(d, exist_ok=True)

# Add base dir to sys.path for utils import
sys.path.insert(0, BASE_DIR)


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS and caching headers for dev
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        # API Endpoints
        if self.path == '/api/ollama/tags':
            self.handle_ollama_tags()
            return
        elif self.path == '/api/health':
            self.send_json({
                "status": "healthy",
                "server": "CrewAI Operations Center Local Server",
                "version": "2.2.0"
            })
            return
        elif self.path == '/api/dataset/pending':
            self.handle_list_dataset(PENDING_DIR)
            return
        elif self.path == '/api/dataset/approved':
            self.handle_list_dataset(APPROVED_DIR)
            return
        elif self.path == '/api/dataset/rejected':
            self.handle_list_dataset(REJECTED_DIR)
            return
        elif self.path == '/api/training/colab_script':
            self.handle_colab_script()
            return
        elif self.path == '/api/key_rotator/status':
            self.handle_key_rotator_status()
            return

        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            payload = json.loads(body.decode('utf-8')) if body else {}
        except Exception:
            payload = {}

        if self.path == '/api/dataset/approve':
            self.handle_dataset_approve(payload)
            return
        elif self.path == '/api/dataset/reject':
            self.handle_dataset_reject(payload)
            return
        elif self.path == '/api/dataset/seed_demo':
            self.handle_seed_demo()
            return

        self.send_json({"error": "Endpoint not found"}, 404)

    def handle_list_dataset(self, target_dir):
        batches = []
        try:
            for fname in sorted(os.listdir(target_dir), reverse=True):
                if fname.endswith(".json"):
                    fpath = os.path.join(target_dir, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        batches.append(data)
            self.send_json({"success": True, "count": len(batches), "batches": batches})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_dataset_approve(self, payload):
        batch_id = payload.get("batch_id")
        if not batch_id:
            self.send_json({"success": False, "error": "Missing batch_id"}, 400)
            return

        source_file = os.path.join(PENDING_DIR, f"{batch_id}.json")
        if not os.path.exists(source_file):
            self.send_json({"success": False, "error": f"Batch {batch_id} not found in pending queue"}, 404)
            return

        try:
            with open(source_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["status"] = "approved_training"
            data["approved_at"] = payload.get("timestamp", "2026-10-22")
            data["operator_notes"] = payload.get("notes", "Approved by Human Operator for Malayalam LLM QLoRA Training")

            dest_file = os.path.join(APPROVED_DIR, f"{batch_id}.json")
            with open(dest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            os.remove(source_file)
            self.send_json({"success": True, "message": f"Batch {batch_id} moved to approved training storage"})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_dataset_reject(self, payload):
        batch_id = payload.get("batch_id")
        feedback = payload.get("feedback", "Rejected due to quality audit or noise")
        if not batch_id:
            self.send_json({"success": False, "error": "Missing batch_id"}, 400)
            return

        source_file = os.path.join(PENDING_DIR, f"{batch_id}.json")
        if not os.path.exists(source_file):
            self.send_json({"success": False, "error": f"Batch {batch_id} not found in pending queue"}, 404)
            return

        try:
            with open(source_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["status"] = "rejected"
            data["rejected_at"] = payload.get("timestamp", "2026-10-22")
            data["rejection_feedback"] = feedback

            dest_file = os.path.join(REJECTED_DIR, f"{batch_id}.json")
            with open(dest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            os.remove(source_file)
            self.send_json({"success": True, "message": f"Batch {batch_id} archived to rejected feedback queue"})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_seed_demo(self):
        try:
            from utils.seed_dataset import generate_seed_data
            generate_seed_data()
            self.send_json({"success": True, "message": "Demo pending batches seeded successfully"})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_colab_script(self):
        try:
            from utils.colab_trainer_loader import get_colab_script
            self.send_json({"success": True, "script": get_colab_script()})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_key_rotator_status(self):
        try:
            from utils.key_rotator import key_rotator
            self.send_json({"success": True, "pools": key_rotator.get_summary_status()})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_ollama_tags(self):
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", headers={"User-Agent": "CrewAI-Operations-Center"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = resp.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            err_payload = json.dumps({
                "status": "offline",
                "error": str(e),
                "models": []
            }).encode('utf-8')
            self.wfile.write(err_payload)


def run_server():
    os.chdir(BASE_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=============================================================")
        print("🚀 CrewAI Professional Operations Center is running!")
        print(f"👉 Local URL: {url}")
        print("⚡ Malayalam Data Pipeline & HITL Review APIs active.")
        print("=============================================================")
        print("Press Ctrl+C to stop the server.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")


if __name__ == '__main__':
    run_server()

