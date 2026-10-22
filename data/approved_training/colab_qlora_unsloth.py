"""
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