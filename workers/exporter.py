"""
malayaLLM v2.3.0 - Staging & Training Exporter Worker
Bundles approved batches into structured JSONL, JSON, and Google Colab QLoRA / Unsloth training scripts.
Outputs:
- Single Unified Dataset: data/approved_training/malayalam_dataset_unified.jsonl
- Explicit Train Split (90%): data/approved_training/train.jsonl
- Explicit Validation Split (10%): data/approved_training/val.jsonl
- Training Manifest: data/approved_training/dataset_manifest.json
- Google Colab Unsloth Script: data/approved_training/colab_qlora_unsloth.py
"""

import os
import sys
import json
import random
import datetime
from typing import Dict, List, Any, Optional

# Windows console UTF-8 safety
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from backend.db import get_db_connection

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
APPROVED_DIR = os.path.join(DATA_DIR, "approved_training")
os.makedirs(APPROVED_DIR, exist_ok=True)


COLAB_UNSLOTH_TEMPLATE = '''"""
========================================================================================
malayaLLM v2.3.0 - Turnkey Google Colab QLoRA 3B Training Notebook / Script
Target Base: Qwen 2.5 3B Instruct (or Llama 3.2 3B Instruct) via Unsloth 4-bit
Hardware: Free Google Colab T4 GPU (16GB VRAM)
========================================================================================
How to Run:
1. Open Google Colab (https://colab.research.google.com).
2. Set Runtime -> Change runtime type -> Hardware accelerator: T4 GPU.
3. Upload `train.jsonl` (downloaded from malayaLLM Operations Center) to the file browser.
4. Run this script!
========================================================================================
"""

import os
import sys
import torch

print("=== malayaLLM v2.3.0: Google Colab 3B Training Engine ===")
print("CUDA Available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Device Name:", torch.cuda.get_device_name(0))

# -------------------------------------------------------------
# 1. Install Unsloth and Fast Optimization Dependencies
# -------------------------------------------------------------
os.system("pip install --quiet --upgrade unsloth xformers trl peft accelerate datasets bitsandbytes")

# -------------------------------------------------------------
# 2. Mount Google Drive for Automatic Checkpoint Relay
# -------------------------------------------------------------
try:
    from google.colab import drive
    drive.mount('/content/drive')
    CHECKPOINT_DIR = "/content/drive/MyDrive/malayaLLM_3B_Checkpoints"
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    print("✓ Google Drive Connected! Checkpoints will relay to:", CHECKPOINT_DIR)
except Exception:
    CHECKPOINT_DIR = "./malayaLLM_3B_checkpoints"
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    print("Running in local container. Checkpoint directory:", CHECKPOINT_DIR)

# -------------------------------------------------------------
# 3. Load 4-bit Qwen 2.5 3B Base Model with Unsloth
# -------------------------------------------------------------
from unsloth import FastLanguageModel

# Qwen 2.5 3B has high-efficiency Dravidian tokenization (best for Malayalam)
# Alternative 3B: "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"
MODEL_NAME = "unsloth/Qwen2.5-3B-Instruct-bnb-4bit"
MAX_SEQ_LENGTH = 2048
LOAD_IN_4BIT = True

print(f"Loading 4-bit base model: {MODEL_NAME}...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = MODEL_NAME,
    max_seq_length = MAX_SEQ_LENGTH,
    dtype = None, # Auto-detects bfloat16 / float16
    load_in_4bit = LOAD_IN_4BIT,
)

# -------------------------------------------------------------
# 4. Attach QLoRA Adapters for Malayalam Morphological Nuances
# -------------------------------------------------------------
model = FastLanguageModel.get_peft_model(
    model,
    r = 16, # LoRA Rank
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 32, # LoRA Alpha
    lora_dropout = 0, # Unsloth optimized (0 dropout is fastest)
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
)

# -------------------------------------------------------------
# 5. Load and Format Dataset (ChatML & Alpaca format)
# -------------------------------------------------------------
from datasets import load_dataset

dataset_file = None
for candidate in ["train.jsonl", "malayalam_dataset_unified.jsonl", "val.jsonl"]:
    if os.path.exists(candidate):
        dataset_file = candidate
        break

if not dataset_file:
    raise FileNotFoundError("Please upload 'train.jsonl' from malayaLLM Operations Center to the Colab files pane!")

print(f"Loading training records from: {dataset_file}...")
raw_dataset = load_dataset("json", data_files=dataset_file, split="train")

alpaca_template = """<|im_start|>system
നിങ്ങൾ ആധികാരികവും ശുദ്ധവുമായ മലയാളത്തിൽ സംസാരിക്കുന്ന ഒരു എഐ സഹായിയാണ്.<|im_end|>
<|im_start|>user
{instruction} {input}<|im_end|>
<|im_start|>assistant
{output}<|im_end|>"""

EOS_TOKEN = tokenizer.eos_token

def format_prompt(examples):
    instructions = examples.get("instruction", [])
    inputs = examples.get("input", [""] * len(instructions))
    outputs = examples.get("output", [])
    texts = []
    for inst, inp, out in zip(instructions, inputs, outputs):
        inp_str = f"\\nസന്ദർഭം: {inp}" if inp and str(inp).strip() else ""
        text = alpaca_template.format(instruction=inst, input=inp_str, output=out) + EOS_TOKEN
        texts.append(text)
    return {"text": texts}

train_dataset = raw_dataset.map(format_prompt, batched=True)
print(f"✓ Formatted {len(train_dataset)} Malayalam instruction pairs for SFT!")

# -------------------------------------------------------------
# 6. SFT Training Configuration (Optimized for Free T4 GPU)
# -------------------------------------------------------------
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = train_dataset,
    dataset_text_field = "text",
    max_seq_length = MAX_SEQ_LENGTH,
    dataset_num_proc = 2,
    packing = False,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4, # Effective batch size = 8
        warmup_steps = 10,
        max_steps = 120, # ~2-3 epochs on pilot corpus
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 10,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "cosine",
        seed = 3407,
        output_dir = CHECKPOINT_DIR,
        save_strategy = "steps",
        save_steps = 50,
    ),
)

print("\\n🚀 Starting 3B Malayalam Fine-Tuning...")
trainer_stats = trainer.train()
print("✓ Fine-Tuning Completed successfully!")

# -------------------------------------------------------------
# 7. Test Malayalam Generation (Inference Verification)
# -------------------------------------------------------------
FastLanguageModel.for_inference(model)
test_prompt = alpaca_template.format(
    instruction="കേരളത്തിന്റെ പരമ്പരാഗത ജലസംരക്ഷണ രീതികളെക്കുറിച്ച് വിശദീകരിക്കുക.",
    input="",
    output=""
)
inputs = tokenizer([test_prompt], return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_new_tokens=150, use_cache=True, temperature=0.7)
print("\\n--- Model Generation Test ---")
print(tokenizer.batch_decode(outputs)[0])

# -------------------------------------------------------------
# 8. Export Model (GGUF & LoRA Adapters for Local Ollama)
# -------------------------------------------------------------
print("\\nExporting LoRA adapters to Google Drive...")
model.save_pretrained(os.path.join(CHECKPOINT_DIR, "malayaLLM_3B_lora"))
tokenizer.save_pretrained(os.path.join(CHECKPOINT_DIR, "malayaLLM_3B_lora"))

print("Exporting GGUF (Q4_K_M) for 100% offline local Ollama deployment...")
try:
    model.save_pretrained_gguf(
        os.path.join(CHECKPOINT_DIR, "malayaLLM_3B_GGUF"),
        tokenizer,
        quantization_method = "q4_k_m"
    )
    print("✓ GGUF Exported! Download and run with: ollama create malayaLLM -f Modelfile")
except Exception as e:
    print(f"GGUF export note: {e}")
'''


class TrainingExporter:
    """Staging and Training Exporter Worker."""

    @classmethod
    def export_approved_dataset(cls) -> Dict[str, Any]:
        """
        Gathers all approved (and auto-approved) records from SQLite and writes them into:
        1. Unified JSONL instruction format: malayalam_dataset_unified.jsonl
        2. Explicit Train split (90%): train.jsonl
        3. Explicit Validation split (10%): val.jsonl
        4. Dataset Manifest: dataset_manifest.json
        5. Clean JSON bundle for Hugging Face: malayalam_corpus_<timestamp>.json
        6. Turnkey Colab QLoRA / Unsloth training script: colab_qlora_unsloth.py
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Select approved or auto-approved items
            cursor.execute("""
                SELECT * FROM review_queue 
                WHERE status = 'approved' OR auto_approved = 1
                ORDER BY reviewed_at DESC, created_at DESC
            """)
            approved_rows = cursor.fetchall()

            is_fallback_preview = False
            if not approved_rows:
                # If no items approved yet, preview from latest queue items
                cursor.execute("SELECT * FROM review_queue ORDER BY created_at DESC LIMIT 50")
                approved_rows = cursor.fetchall()
                is_fallback_preview = True

            records = [dict(r) for r in approved_rows]
        finally:
            conn.close()

        # 2. Also load all open datasets from data/sources/open_datasets/
        open_datasets_dir = os.path.join(DATA_DIR, "sources", "open_datasets")
        open_records = []
        if os.path.exists(open_datasets_dir):
            for fname in sorted(os.listdir(open_datasets_dir)):
                if fname.endswith(".jsonl"):
                    fpath = os.path.join(open_datasets_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f_in:
                            for line in f_in:
                                line = line.strip()
                                if line:
                                    open_records.append(json.loads(line))
                    except Exception as e:
                        print(f"Error loading open dataset {fname}: {e}", file=sys.stderr)

        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # Primary file targets
        unified_jsonl_path = os.path.join(APPROVED_DIR, "malayalam_dataset_unified.jsonl")
        train_jsonl_path = os.path.join(APPROVED_DIR, "train.jsonl")
        val_jsonl_path = os.path.join(APPROVED_DIR, "val.jsonl")
        manifest_path = os.path.join(APPROVED_DIR, "dataset_manifest.json")
        legacy_jsonl_path = os.path.join(APPROVED_DIR, "malayalam_instruct_train.jsonl")
        json_path = os.path.join(APPROVED_DIR, f"malayalam_corpus_{timestamp}.json")
        colab_path = os.path.join(APPROVED_DIR, "colab_qlora_unsloth.py")

        total_chars = 0
        density_sum = 0.0
        fluency_sum = 0.0
        seen_hashes = set()
        formatted_entries = []

        # Process SQLite staged & approved records
        for rec in records:
            cleaned = rec.get("gemma_proofread_text") or rec.get("cleaned_text") or rec.get("raw_text", "")
            cleaned = cleaned.strip()
            if not cleaned or len(cleaned) < 20:
                continue
            h = hash(cleaned[:100])
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            total_chars += len(cleaned)
            density = float(rec.get("malayalam_density", 0.90))
            fluency = float(rec.get("fluency_score", 1.0))
            density_sum += density
            fluency_sum += fluency

            title = rec.get("title") or "സാഹിത്യ/വിജ്ഞാന കുറിപ്പ്"
            instruction = rec.get("instruction") or f"മലയാളത്തിൽ വിശദീകരിക്കുക: {title}"
            input_text = rec.get("input", "")
            user_content = f"{instruction}\n\nസന്ദർഭം: {input_text}" if input_text else instruction
            
            entry = {
                "id": rec.get("item_id") or f"db_{int(datetime.datetime.now().timestamp()*1000)}",
                "instruction": instruction,
                "input": input_text,
                "output": cleaned,
                "messages": [
                    {"role": "system", "content": "നിങ്ങൾ ആധികാരികവും ശുദ്ധവുമായ മലയാളത്തിൽ പ്രതികരിക്കുന്ന കൃത്യതയുള്ള ഒരു എഐ സഹായിയാണ്."},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": cleaned}
                ],
                "metadata": {
                    "source": rec.get("source", "SQLite Review Queue"),
                    "dataset_origin": "live_curated",
                    "malayalam_density": density,
                    "fluency_score": fluency,
                    "confidence_score": float(rec.get("confidence_score", 0.90)),
                    "auto_approved": bool(rec.get("auto_approved", 0)),
                    "chillu_fixes": rec.get("chillu_fixes", 0),
                    "pii_redacted": rec.get("pii_redacted", 0)
                }
            }
            formatted_entries.append(entry)

        # Process Open Datasets (Alpaca SFT, CulturaX, Wikipedia)
        for rec in open_records:
            cleaned = rec.get("output") or rec.get("cleaned_text") or rec.get("raw_text", "")
            cleaned = cleaned.strip()
            if not cleaned or len(cleaned) < 20:
                continue
            h = hash(cleaned[:100])
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            total_chars += len(cleaned)
            density_sum += 0.95
            fluency_sum += 1.0

            title = rec.get("title") or "വിജ്ഞാന കുറിപ്പ്"
            instruction = rec.get("instruction") or f"മലയാളത്തിൽ വിശദീകരിക്കുക: {title}"
            input_text = rec.get("input", "")
            user_content = f"{instruction}\n\nസന്ദർഭം: {input_text}" if input_text else instruction

            entry = {
                "id": rec.get("id") or f"open_{int(datetime.datetime.now().timestamp()*1000)}",
                "instruction": instruction,
                "input": input_text,
                "output": cleaned,
                "messages": [
                    {"role": "system", "content": "നിങ്ങൾ ആധികാരികവും ശുദ്ധവുമായ മലയാളത്തിൽ പ്രതികരിക്കുന്ന കൃത്യതയുള്ള ഒരു എഐ സഹായിയാണ്."},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": cleaned}
                ],
                "metadata": {
                    "source": rec.get("source", "Open Datasets Repository"),
                    "dataset_origin": rec.get("dataset_name", "open_dataset"),
                    "malayalam_density": 0.95,
                    "fluency_score": 1.0,
                    "confidence_score": 0.95,
                    "auto_approved": True,
                    "chillu_fixes": 0,
                    "pii_redacted": 0
                }
            }
            formatted_entries.append(entry)

        # Shuffle deterministically for 90/10 train/validation split
        rng = random.Random(3407)
        shuffled = list(formatted_entries)
        rng.shuffle(shuffled)

        if len(shuffled) <= 1:
            train_entries = shuffled
            val_entries = shuffled  # Fallback for single item
        else:
            split_idx = max(1, int(len(shuffled) * 0.90))
            train_entries = shuffled[:split_idx]
            val_entries = shuffled[split_idx:]

        # 1. Write Unified JSONL
        with open(unified_jsonl_path, "w", encoding="utf-8") as f_u:
            for entry in formatted_entries:
                f_u.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # 2. Write Train JSONL (90%)
        with open(train_jsonl_path, "w", encoding="utf-8") as f_tr:
            for entry in train_entries:
                f_tr.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # 3. Write Validation JSONL (10%)
        with open(val_jsonl_path, "w", encoding="utf-8") as f_va:
            for entry in val_entries:
                f_va.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # 4. Backward compatibility copy for malayalam_instruct_train.jsonl
        with open(legacy_jsonl_path, "w", encoding="utf-8") as f_leg:
            for entry in train_entries:
                f_leg.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # 5. Write Manifest
        manifest = {
            "name": "malayaLLM Malayalam Instruction Fine-Tuning Corpus",
            "version": "2.3.0",
            "exported_at": timestamp,
            "total_records": len(formatted_entries),
            "train_records": len(train_entries),
            "validation_records": len(val_entries),
            "total_characters": total_chars,
            "avg_density": round(density_sum / max(1, len(records)), 4),
            "avg_fluency": round(fluency_sum / max(1, len(records)), 3),
            "format": "JSONL (ChatML and Alpaca compatible)",
            "files": {
                "unified": "malayalam_dataset_unified.jsonl",
                "train": "train.jsonl",
                "validation": "val.jsonl",
                "legacy_train": "malayalam_instruct_train.jsonl",
                "colab_script": "colab_qlora_unsloth.py"
            },
            "unsloth_compatible": True,
            "qlora_ready": True
        }
        with open(manifest_path, "w", encoding="utf-8") as f_man:
            json.dump(manifest, f_man, ensure_ascii=False, indent=2)

        # 6. Write structured JSON bundle
        with open(json_path, "w", encoding="utf-8") as f_json:
            json.dump({
                "schema": "malayaLLM_v2.3.0_curated_corpus",
                "manifest": manifest,
                "data": records
            }, f_json, ensure_ascii=False, indent=2)

        # 7. Write Colab script
        with open(colab_path, "w", encoding="utf-8") as f_colab:
            f_colab.write(COLAB_UNSLOTH_TEMPLATE.strip())

        return {
            "success": True,
            "total_records": len(formatted_entries),
            "train_records": len(train_entries),
            "val_records": len(val_entries),
            "is_preview_from_queue": is_fallback_preview,
            "total_characters": total_chars,
            "avg_density": round(density_sum / max(1, len(records)), 4),
            "avg_fluency": round(fluency_sum / max(1, len(records)), 3),
            "files": {
                "unified": unified_jsonl_path,
                "train": train_jsonl_path,
                "validation": val_jsonl_path,
                "manifest": manifest_path,
                "jsonl": unified_jsonl_path,
                "json": json_path,
                "colab_script": colab_path
            },
            "timestamp": timestamp
        }

    @classmethod
    def get_colab_script_text(cls) -> str:
        """Returns the Colab training script text for direct UI copying."""
        return COLAB_UNSLOTH_TEMPLATE.strip()


# Global singleton exporter
staging_exporter = TrainingExporter()
