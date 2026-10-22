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
malayaLLM v2.3.0 - Google Colab Turnkey QLoRA Unsloth Training Script
Autonomous Dravidian Instruction Fine-Tuning with Google Drive Checkpoint Relay
========================================================================================
To run in Google Colab (Free T4 or A100 GPU):
1. Runtime -> Change runtime type -> Hardware accelerator: GPU (T4 / A100)
2. Run this script. It connects Google Drive, mounts dataset, fine-tunes Llama-3-8B / Gemma,
   and relays checkpoints every 50 steps to survive Colab 12-hour disconnects.
========================================================================================
"""

import os
import sys
import torch

print("=== malayaLLM v2.3.0: Google Colab Training Engine ===")
print("CUDA Available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Device Name:", torch.cuda.get_device_name(0))

# Step 1: Install Unsloth and Dependencies
os.system("pip install --quiet --upgrade unsloth xformers trl peft accelerate datasets bitsandbytes")

# Step 2: Mount Google Drive for Resilient Checkpoint Relay
try:
    from google.colab import drive
    drive.mount('/content/drive')
    CHECKPOINT_DIR = "/content/drive/MyDrive/malayaLLM_Checkpoints"
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    print("Google Drive Mounted! Checkpoints will relay to:", CHECKPOINT_DIR)
except Exception as e:
    CHECKPOINT_DIR = "./local_checkpoints"
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    print("Drive mounting skipped. Local checkpoints:", CHECKPOINT_DIR)

# Step 3: Load 4-bit Base Model with Unsloth
from unsloth import FastLanguageModel
max_seq_length = 2048
dtype = None # Auto detection
load_in_4bit = True

# Supports unsloth/llama-3-8b-Instruct-bnb-4bit, unsloth/gemma-2-9b-bnb-4bit, or unsloth/Qwen2.5-7B-bnb-4bit
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/llama-3-8b-Instruct-bnb-4bit",
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
)

# Step 4: Configure LoRA Adapters for Malayalam Language Inflections
model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 16,
    lora_dropout = 0, # Optimized 0 for Unsloth
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
    use_rslora = False,
    loftq_config = None,
)

# Step 5: Format Malayalam Instruct Prompt
alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request in natural, fluent Malayalam.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

EOS_TOKEN = tokenizer.eos_token

def formatting_prompts_func(examples):
    instructions = examples["instruction"]
    inputs       = examples["input"]
    outputs      = examples["output"]
    texts = []
    for instruction, input_text, output in zip(instructions, inputs, outputs):
        text = alpaca_prompt.format(instruction, input_text or "", output) + EOS_TOKEN
        texts.append(text)
    return {"text": texts}

# Step 6: Load malayaLLM Curated Training Dataset (Train / Val Split or Unified)
from datasets import load_dataset

train_file = "train.jsonl" if os.path.exists("train.jsonl") else ("malayalam_dataset_unified.jsonl" if os.path.exists("malayalam_dataset_unified.jsonl") else "malayalam_instruct_train.jsonl")
val_file = "val.jsonl" if os.path.exists("val.jsonl") else None

if not os.path.exists(train_file):
    print(f"Warning: {train_file} not found locally. Upload from malayaLLM Operations Center.")
    train_dataset = None
    val_dataset = None
else:
    train_dataset = load_dataset("json", data_files=train_file, split="train")
    train_dataset = train_dataset.map(formatting_prompts_func, batched=True)
    print("Loaded training records:", len(train_dataset))
    
    if val_file and os.path.exists(val_file):
        val_dataset = load_dataset("json", data_files=val_file, split="train")
        val_dataset = val_dataset.map(formatting_prompts_func, batched=True)
        print("Loaded validation records:", len(val_dataset))
    else:
        val_dataset = None

# Step 7: Define SFT Trainer with Auto Checkpoint Relay
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = train_dataset,
    eval_dataset = val_dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    dataset_num_proc = 2,
    packing = False,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 10,
        max_steps = 150,
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 10,
        evaluation_strategy = "steps" if val_dataset else "no",
        eval_steps = 50 if val_dataset else None,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = CHECKPOINT_DIR,
        save_strategy = "steps",
        save_steps = 50,
    ),
)

if train_dataset:
    print("Starting fine-tuning...")
    trainer.train()
    print("Training Complete! Exporting GGUF 16-bit / 4-bit...")
    model.save_pretrained_merged(os.path.join(CHECKPOINT_DIR, "malayaLLM_v2.3_final"), tokenizer, save_method = "merged_16bit")
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
        formatted_entries = []

        for rec in records:
            # Use Gemma proofread text if available, else cleaned_text
            cleaned = rec.get("gemma_proofread_text") or rec.get("cleaned_text", "")
            total_chars += len(cleaned)
            density = float(rec.get("malayalam_density", 0.0))
            fluency = float(rec.get("fluency_score", 1.0))
            density_sum += density
            fluency_sum += fluency

            title = rec.get("title", "")
            if not title or title.strip() == "":
                title = "സാഹിത്യ/വിജ്ഞാന കുറിപ്പ്"

            instruction = f"മലയാളത്തിൽ വിശദീകരിക്കുക: {title}"
            
            entry = {
                "id": rec.get("item_id"),
                "instruction": instruction,
                "input": "",
                "output": cleaned,
                # ChatML / OpenAI messages schema for modern fine-tuning toolchains
                "messages": [
                    {"role": "system", "content": "നിങ്ങൾ ആധികാരികവും ശുദ്ധവുമായ മലയാളത്തിൽ പ്രതികരിക്കുന്ന കൃത്യതയുള്ള ഒരു എഐ സഹായിയാണ്."},
                    {"role": "user", "content": instruction},
                    {"role": "assistant", "content": cleaned}
                ],
                "metadata": {
                    "source": rec.get("source"),
                    "malayalam_density": density,
                    "fluency_score": fluency,
                    "confidence_score": float(rec.get("confidence_score", 0.90)),
                    "auto_approved": bool(rec.get("auto_approved", 0)),
                    "chillu_fixes": rec.get("chillu_fixes", 0),
                    "pii_redacted": rec.get("pii_redacted", 0)
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
