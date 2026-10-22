"""
malayaLLM v2.3.0 - Open-Source Malayalam Dataset Harvester & Importer
Downloads, verifies, and stages curated open-source Malayalam corpora:
1. VishnuPJ/Alpaca_Instruct_Malayalam (Alpaca Instruction-Response SFT dataset)
2. VishnuPJ/Malayalam_CultureX_IndicCorp_SMC (CulturaX / IndicCorp foundational corpus)
3. Malayalam Wikipedia (Structured encyclopedic articles)
4. siyah1/malayalam-dataset-llm (Gated web text metadata connector)
"""

import os
import re
import sys
import json
import time
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional

# Windows console UTF-8 safety
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OPEN_DATASETS_DIR = os.path.join(DATA_DIR, "sources", "open_datasets")
os.makedirs(OPEN_DATASETS_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "malayaLLM-DatasetImporter/2.3.0 (https://github.com/ShorrohS/malayaLLM)"
}


class OpenDatasetImporter:
    """Manages harvesting, parsing, and caching of open Malayalam datasets."""

    def __init__(self):
        self.datasets_dir = OPEN_DATASETS_DIR

    def fetch_alpaca_instruct(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetches structured instruction-input-response pairs from
        VishnuPJ/Alpaca_Instruct_Malayalam on Hugging Face.
        """
        url = f"https://datasets-server.huggingface.co/rows?dataset=VishnuPJ/Alpaca_Instruct_Malayalam&config=default&split=train&offset=0&limit={limit}"
        req = urllib.request.Request(url, headers=HEADERS)
        records = []
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                rows = data.get("rows", [])
                for idx, r in enumerate(rows):
                    row_data = r.get("row", {})
                    prompt = row_data.get("Prompt", "")
                    if not prompt:
                        continue

                    # Extract Instruction, Input, and Response from Alpaca Prompt
                    inst_match = re.search(r'### Instruction:\s*(.*?)(?=\n### Input:|\n### Response:|$)', prompt, re.DOTALL)
                    input_match = re.search(r'### Input:\s*(.*?)(?=\n### Response:|$)', prompt, re.DOTALL)
                    resp_match = re.search(r'### Response:\s*(.*)', prompt, re.DOTALL)

                    instruction = inst_match.group(1).strip() if inst_match else "മലയാളത്തിൽ പ്രതികരിക്കുക"
                    input_text = input_match.group(1).strip() if input_match else ""
                    response = resp_match.group(1).strip() if resp_match else prompt

                    rec = {
                        "id": f"alpaca_instruct_{idx+1:04d}",
                        "source": "https://huggingface.co/datasets/VishnuPJ/Alpaca_Instruct_Malayalam",
                        "title": f"Alpaca SFT: {instruction[:45]}...",
                        "instruction": instruction,
                        "input": input_text,
                        "output": response,
                        "raw_text": f"നിർദ്ദേശം: {instruction}\n\nഇൻപുട്ട്: {input_text}\n\nപ്രതികരണം:\n{response}" if input_text else f"നിർദ്ദേശം: {instruction}\n\nപ്രതികരണം:\n{response}",
                        "dataset_name": "Alpaca_Instruct_Malayalam",
                        "type": "instruction_tuning"
                    }
                    records.append(rec)
        except Exception as e:
            print(f"Error fetching Alpaca Instruct Malayalam: {e}", file=sys.stderr)

        # Save to local file
        out_path = os.path.join(self.datasets_dir, "alpaca_instruct_malayalam.jsonl")
        if records:
            with open(out_path, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

        return records

    def fetch_culturax_indiccorp(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetches curated pre-training records from
        VishnuPJ/Malayalam_CultureX_IndicCorp_SMC on Hugging Face.
        """
        url = f"https://datasets-server.huggingface.co/rows?dataset=VishnuPJ/Malayalam_CultureX_IndicCorp_SMC&config=default&split=train&offset=0&limit={limit}"
        req = urllib.request.Request(url, headers=HEADERS)
        records = []
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                rows = data.get("rows", [])
                for idx, r in enumerate(rows):
                    row_data = r.get("row", {})
                    text = row_data.get("text", "").strip()
                    if not text or len(text) < 40:
                        continue

                    # Create concise title from first sentence
                    first_line = text.split("\n")[0].split(".")[0].strip()
                    title = first_line[:50] if first_line else f"CulturaX IndicCorp Record #{idx+1}"

                    rec = {
                        "id": f"culturax_smc_{idx+1:04d}",
                        "source": "https://huggingface.co/datasets/VishnuPJ/Malayalam_CultureX_IndicCorp_SMC",
                        "title": title,
                        "raw_text": text,
                        "cleaned_text": text,
                        "instruction": f"വിശദമായി വിവരിക്കുക: {title}",
                        "input": "",
                        "output": text,
                        "dataset_name": "CulturaX_IndicCorp_SMC",
                        "type": "foundational_pretraining"
                    }
                    records.append(rec)
        except Exception as e:
            print(f"Error fetching CulturaX IndicCorp Malayalam: {e}", file=sys.stderr)

        # Save to local file
        out_path = os.path.join(self.datasets_dir, "culturax_indiccorp_malayalam.jsonl")
        if records:
            with open(out_path, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

        return records

    def fetch_malayalam_wikipedia(self) -> List[Dict[str, Any]]:
        """
        Fetches high-quality encyclopedic Malayalam articles directly from Wikimedia API.
        """
        titles = [
            "കേരളം", "മലയാളസാഹിത്യം", "കമ്പ്യൂട്ടർ ശാസ്ത്രം", "വൈക്കം മുഹമ്മദ് ബഷീർ",
            "തകഴി ശിവശങ്കരപ്പിള്ള", "ഇന്ത്യ", "ജ്യോതിശാസ്ത്രം", "ആയുർവേദം", "ഓണം",
            "കേരളത്തിലെ നദികൾ", "പരിസ്ഥിതി ശാസ്ത്രം", "നിർമ്മിത ബുദ്ധി"
        ]
        records = []
        for idx, title in enumerate(titles):
            try:
                url = f"https://ml.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&explaintext=1&titles={urllib.parse.quote(title)}"
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    pages = data.get("query", {}).get("pages", {})
                    for pid, page in pages.items():
                        extract = page.get("extract", "").strip()
                        if extract and len(extract) > 40:
                            records.append({
                                "id": f"wiki_ml_{idx+1:04d}",
                                "source": f"https://ml.wikipedia.org/wiki/{urllib.parse.quote(title)}",
                                "title": f"വിക്കിപീഡിയ: {title}",
                                "raw_text": extract[:2500],
                                "cleaned_text": extract[:2500],
                                "instruction": f"വിജ്ഞാനകോശ കുറിപ്പ് എഴുതുക: {title}",
                                "input": "",
                                "output": extract[:2500],
                                "dataset_name": "Malayalam_Wikipedia",
                                "type": "encyclopedic_knowledge"
                            })
            except Exception as e:
                print(f"Error fetching Wikipedia title '{title}': {e}", file=sys.stderr)

        # Save to local file
        out_path = os.path.join(self.datasets_dir, "malayalam_wikipedia_corpus.jsonl")
        if records:
            with open(out_path, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

        return records

    def sync_all_open_datasets(self) -> Dict[str, Any]:
        """
        Downloads all available open datasets, saves them locally,
        and generates an index manifest for UI display and training staging.
        """
        print("Syncing open Malayalam datasets...")
        alpaca_records = self.fetch_alpaca_instruct(limit=40)
        culturax_records = self.fetch_culturax_indiccorp(limit=40)
        wiki_records = self.fetch_malayalam_wikipedia()

        all_records = alpaca_records + culturax_records + wiki_records

        manifest = {
            "version": "2.3.0",
            "last_synced": time.strftime("%Y-%m-%d %H:%M:%S"),
            "storage_path": self.datasets_dir,
            "datasets": {
                "Alpaca_Instruct_Malayalam": {
                    "source": "https://huggingface.co/datasets/VishnuPJ/Alpaca_Instruct_Malayalam",
                    "type": "Supervised Instruction Tuning (SFT)",
                    "records_cached": len(alpaca_records),
                    "file": "alpaca_instruct_malayalam.jsonl",
                    "status": "ready"
                },
                "CulturaX_IndicCorp_SMC": {
                    "source": "https://huggingface.co/datasets/VishnuPJ/Malayalam_CultureX_IndicCorp_SMC",
                    "type": "Foundational Web & Monolingual Pretraining",
                    "records_cached": len(culturax_records),
                    "file": "culturax_indiccorp_malayalam.jsonl",
                    "status": "ready"
                },
                "Malayalam_Wikipedia": {
                    "source": "https://ml.wikipedia.org/",
                    "type": "Clean Encyclopedic Malayalam Knowledge",
                    "records_cached": len(wiki_records),
                    "file": "malayalam_wikipedia_corpus.jsonl",
                    "status": "ready"
                },
                "Malayalam_Web_Text_Cleaned": {
                    "source": "https://huggingface.co/datasets/siyah1/malayalam-dataset-llm",
                    "type": "Deduplicated Web Text (Gated)",
                    "records_cached": 0,
                    "status": "gated_requires_hf_login",
                    "instructions": "Accept terms at https://huggingface.co/datasets/siyah1/malayalam-dataset-llm and paste HF token in Key Rotator"
                }
            },
            "total_records": len(all_records)
        }

        # Write dataset manifest index
        manifest_path = os.path.join(self.datasets_dir, "dataset_index.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "total_imported": len(all_records),
            "manifest": manifest,
            "alpaca_count": len(alpaca_records),
            "culturax_count": len(culturax_records),
            "wiki_count": len(wiki_records)
        }

    def get_manifest(self) -> Dict[str, Any]:
        """Returns the cached open datasets manifest enriched with live sample lines and file sizes."""
        manifest_path = os.path.join(self.datasets_dir, "dataset_index.json")
        manifest = {}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                pass
        if not manifest:
            manifest = self.sync_all_open_datasets().get("manifest", {})

        # Enrich with live sample lines, local paths, and file sizes
        datasets = manifest.get("datasets", {})
        for name, info in datasets.items():
            fname = info.get("file")
            if fname:
                fpath = os.path.join(self.datasets_dir, fname)
                info["local_path"] = f"data/sources/open_datasets/{fname}"
                if os.path.exists(fpath):
                    info["file_size_bytes"] = os.path.getsize(fpath)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f_in:
                            first_line = f_in.readline().strip()
                            if first_line:
                                info["sample_record"] = json.loads(first_line)
                    except Exception:
                        pass
        return manifest


# Global singleton
dataset_importer = OpenDatasetImporter()
