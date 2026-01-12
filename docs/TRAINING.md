# Qwen Training & Enhancement Guide

This document covers how to train, fine-tune, and enhance your local Qwen model for use with ChatOS.

---

## Prerequisites

- **Ollama** installed and running (`ollama serve`)
- **Qwen model** pulled: `ollama pull qwen2.5` (or your preferred variant)
- **GPU** (recommended): NVIDIA with CUDA for faster training
- **Python 3.9+** with training dependencies

---

## Quick Setup: Using Qwen as Primary Model

### 1. Verify Qwen is Installed

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# List available models
ollama list

# If Qwen not installed, pull it
ollama pull qwen2.5        # Base model (7B)
ollama pull qwen2.5:14b    # Larger variant
ollama pull qwen2.5-coder  # Code-focused variant
```

### 2. Configure ChatOS to Use Qwen

In the ChatOS Settings page (`/settings`):
1. Go to **Providers** → Verify Ollama shows ✅ available
2. Go to **Models** → Click **Add Model**
3. Select:
   - Provider: `Ollama`
   - Model: `qwen2.5` (or your installed variant)
   - Name: `Qwen-Primary`
   - Include in Council: ✅

Or via API:
```bash
curl -X POST http://localhost:8000/api/models \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model_id": "qwen2.5",
    "name": "Qwen-Primary",
    "is_council_member": true,
    "temperature": 0.7,
    "max_tokens": 4096
  }'
```

---

## Fine-Tuning Qwen

### Option 1: Ollama Modelfile (Recommended for Quick Customization)

Create a custom Modelfile to adjust behavior:

```dockerfile
# Modelfile
FROM qwen2.5

# Set system prompt for ChatOS
SYSTEM """You are a helpful AI assistant in the ChatOS council. You provide thoughtful, accurate responses and excel at coding tasks. Always explain your reasoning clearly."""

# Adjust parameters
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
PARAMETER stop "<|im_end|>"
```

Create and use:
```bash
ollama create chatos-qwen -f Modelfile
ollama run chatos-qwen
```

### Option 2: LoRA Fine-Tuning with Unsloth (Advanced)

For custom training on your data:

```bash
# Install Unsloth (fastest LoRA training)
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"

# Or with standard transformers
pip install transformers datasets peft accelerate bitsandbytes
```

Training script (`train_qwen.py`):

```python
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments

# Load model with 4-bit quantization
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-7B-bnb-4bit",
    max_seq_length=4096,
    load_in_4bit=True,
)

# Add LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                   "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0,
    bias="none",
)

# Load your custom dataset
# Format: {"instruction": "...", "input": "...", "output": "..."}
dataset = load_dataset("json", data_files="training_data.json")

# Training
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset["train"],
    tokenizer=tokenizer,
    args=TrainingArguments(
        output_dir="./qwen-chatos-lora",
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_strategy="epoch",
    ),
)

trainer.train()

# Save LoRA adapter
model.save_pretrained("./qwen-chatos-lora")
```

### Option 3: Full Fine-Tuning with QLoRA

For deeper customization:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# 4-bit quantization config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype="float16",
    bnb_4bit_use_double_quant=True,
)

# Load base model
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-7B-Instruct",
    quantization_config=bnb_config,
    device_map="auto",
)

# Prepare for training
model = prepare_model_for_kbit_training(model)

# LoRA config
lora_config = LoraConfig(
    r=64,
    lora_alpha=128,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)
```

---

## Creating Training Data

### Format for ChatOS Tasks

Create `training_data.json`:

```json
[
  {
    "instruction": "You are a coding assistant. Write clean, efficient code.",
    "input": "Write a Python function to calculate fibonacci numbers",
    "output": "```python\ndef fibonacci(n: int) -> int:\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b\n```\n\nThis iterative approach has O(n) time complexity and O(1) space complexity."
  },
  {
    "instruction": "You are a helpful assistant providing thoughtful responses.",
    "input": "Explain how RAG works in AI systems",
    "output": "RAG (Retrieval-Augmented Generation) enhances AI responses by:\n\n1. **Retrieval**: Search a knowledge base for relevant documents\n2. **Augmentation**: Add retrieved context to the prompt\n3. **Generation**: Generate response using both query and context\n\nThis helps ground responses in factual information and reduces hallucinations."
  }
]
```

### Collecting Data from ChatOS

Export your best conversations:

```python
# In ChatOS, after good conversations
import json
from pathlib import Path

def export_training_data(conversations, output_file="training_data.json"):
    """Export conversations as training data."""
    training_data = []
    for conv in conversations:
        training_data.append({
            "instruction": "You are a helpful AI assistant.",
            "input": conv["user_message"],
            "output": conv["assistant_response"],
        })
    
    Path(output_file).write_text(json.dumps(training_data, indent=2))
```

---

## Deploying Fine-Tuned Model to Ollama

### Convert LoRA to GGUF

```bash
# Clone llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Convert to GGUF format
python convert_hf_to_gguf.py ../qwen-chatos-lora --outfile qwen-chatos.gguf

# Quantize (optional, for smaller size)
./llama-quantize qwen-chatos.gguf qwen-chatos-q4.gguf q4_k_m
```

### Create Ollama Model

```dockerfile
# Modelfile.chatos
FROM ./qwen-chatos-q4.gguf

TEMPLATE """<|im_start|>system
{{ .System }}<|im_end|>
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

PARAMETER temperature 0.7
PARAMETER stop "<|im_end|>"
```

```bash
ollama create chatos-qwen-finetuned -f Modelfile.chatos
```

---

## Performance Optimization

### GPU Memory Management

```bash
# Set environment variables before running
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

### Ollama GPU Settings

```bash
# Edit ~/.ollama/config
# or set environment variable
export OLLAMA_NUM_GPU=999  # Use all available GPU layers
```

### Batch Processing for Training

```python
# Use gradient checkpointing for large models
model.gradient_checkpointing_enable()

# Or use DeepSpeed for multi-GPU
from accelerate import Accelerator
accelerator = Accelerator()
model, optimizer, train_dataloader = accelerator.prepare(
    model, optimizer, train_dataloader
)
```

---

## Monitoring & Evaluation

### Test Your Model

```python
import httpx

async def test_model(prompt: str, model: str = "qwen2.5"):
    """Test model response quality."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False}
        )
        return response.json()["response"]

# Test coding ability
print(await test_model("Write a Python decorator for caching"))

# Test reasoning
print(await test_model("Explain the difference between async and threading"))
```

### Evaluation Metrics

```python
from evaluate import load

# Load metrics
bleu = load("bleu")
rouge = load("rouge")

# Compare outputs
scores = {
    "bleu": bleu.compute(predictions=preds, references=refs),
    "rouge": rouge.compute(predictions=preds, references=refs),
}
```

---

## Resources

- **Qwen Official**: https://github.com/QwenLM/Qwen2.5
- **Ollama Docs**: https://ollama.ai/library/qwen2.5
- **Unsloth**: https://github.com/unslothai/unsloth
- **PEFT/LoRA**: https://github.com/huggingface/peft
- **llama.cpp**: https://github.com/ggerganov/llama.cpp

---

## Troubleshooting

### "CUDA out of memory"
- Use smaller batch size: `per_device_train_batch_size=1`
- Enable gradient checkpointing
- Use 4-bit quantization

### "Model not responding"
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Check model is loaded: `ollama list`
- Restart Ollama: `ollama serve`

### "Slow generation"
- Ensure GPU is being used: `nvidia-smi`
- Use quantized model (Q4/Q8)
- Reduce context length

---

*Last updated: November 2024*

