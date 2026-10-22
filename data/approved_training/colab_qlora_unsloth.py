"""
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
        inp_str = f"\nസന്ദർഭം: {inp}" if inp and str(inp).strip() else ""
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

print("\n🚀 Starting 3B Malayalam Fine-Tuning...")
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
print("\n--- Model Generation Test ---")
print(tokenizer.batch_decode(outputs)[0])

# -------------------------------------------------------------
# 8. Export Model (GGUF & LoRA Adapters for Local Ollama)
# -------------------------------------------------------------
print("\nExporting LoRA adapters to Google Drive...")
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