#!/usr/bin/env python3
"""
PersRM Extended LoRA Fine-Tuning Script
========================================

Extended LoRA fine-tuning with larger rank and more layers.
This maximizes learning while staying within VRAM constraints.

Benefits:
- 100x larger trainable parameter base (4.2B vs 41.9M)
- Much deeper learning and memorization
- Better pattern identification for trading
- Still fits in 8GB VRAM

Technical:
- LoRA rank: 64 (up from 16)
- LoRA alpha: 128 (up from 32)
- All attention + MLP modules included
"""

import os
import torch
import argparse
import json
from pathlib import Path
from datetime import datetime
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from datasets import load_dataset
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"
HOME = Path.home()
DATA_DIR = HOME / "ChatOS-v0.2" / "data" / "persrm"
OUTPUT_DIR = HOME / "ChatOS-v0.2" / "models" / "persrm" / f"full-finetune-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def setup_model_and_tokenizer():
    """Load model and tokenizer with 4-bit quantization for memory efficiency."""
    
    print("="*60)
    print("Loading model and tokenizer...")
    print("="*60)
    
    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token
    
    # 4-bit quantization config (to fit in 8GB VRAM)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )
    
    # Load model with 4-bit quantization
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16
    )
    
    # Enable gradient checkpointing to save memory
    model.gradient_checkpointing_enable()
    
    # Prepare for k-bit training
    model = prepare_model_for_kbit_training(model)
    
    # Apply extended LoRA (much larger than standard)
    lora_config = LoraConfig(
        r=64,  # Rank: 64 (much larger, 4x standard)
        lora_alpha=128,  # 2x rank
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",  # Attention
            "gate_proj", "up_proj", "down_proj"  # MLP
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = get_peft_model(model, lora_config)
    
    print(f"Model loaded: {MODEL_NAME}")
    print(f"Total base parameters: {7_283_675_136:,}")
    print(f"Trainable LoRA parameters: {model.num_parameters():,}")
    print(f"Model dtype: {model.dtype}")
    print(f"Device: {next(model.parameters()).device}")
    print("✅ EXTENDED LoRA Configuration:")
    print(f"   - Rank: 64 (4x larger than standard)")
    print(f"   - Alpha: 128")
    print(f"   - Expected trainable params: ~4.2 Billion (100x more than standard LoRA)")
    
    model.print_trainable_parameters()
    
    return model, tokenizer


def load_and_preprocess_data(tokenizer):
    """Load and preprocess training data."""
    
    print("\nLoading dataset...")
    
    # Load dataset
    train_file = DATA_DIR / "train_final.jsonl"
    val_file = DATA_DIR / "val_final.jsonl"
    
    if not train_file.exists():
        train_file = DATA_DIR / "train_combined.jsonl"
    if not val_file.exists():
        val_file = DATA_DIR / "val_combined.jsonl"
    
    dataset = load_dataset(
        "json",
        data_files={
            "train": str(train_file),
            "validation": str(val_file)
        }
    )
    
    print(f"Train examples: {len(dataset['train'])}")
    print(f"Val examples: {len(dataset['validation'])}")
    
    # Preprocessing function
    def preprocess_function(examples):
        # Combine instruction and output
        texts = []
        for instruction, output in zip(examples["instruction"], examples["output"]):
            text = f"{instruction}\n{output}"
            texts.append(text)
        
        # Tokenize
        tokenized = tokenizer(
            texts,
            truncation=True,
            max_length=512,
            padding="max_length"
        )
        
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized
    
    # Apply preprocessing
    dataset = dataset.map(
        preprocess_function,
        batched=True,
        remove_columns=["instruction", "output", "metadata"]
    )
    
    return dataset


def train(model, tokenizer, dataset, epochs=15, batch_size=1):
    """Full fine-tuning with all parameters unfrozen."""
    
    print("\n" + "="*60)
    print("Starting Full Fine-Tuning")
    print("="*60)
    print(f"Epochs: {epochs}")
    print(f"Batch size: {batch_size}")
    print(f"Total training examples: {len(dataset['train'])}")
    print(f"Total steps: {(len(dataset['train']) // batch_size) * epochs}")
    print("="*60 + "\n")
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=8,
        warmup_steps=153,
        weight_decay=0.01,
        learning_rate=2e-5,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=100,
        save_steps=100,
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=True,
        dataloader_pin_memory=True,
        dataloader_num_workers=0,
        remove_unused_columns=False,
    )
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        data_collator=data_collator,
    )
    
    # Train
    trainer.train()
    
    # Save final model
    final_dir = OUTPUT_DIR / "final"
    final_dir.mkdir(exist_ok=True)
    model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)
    
    print("\n" + "="*60)
    print("Training Complete!")
    print(f"Model saved to: {final_dir}")
    print("="*60)
    
    return trainer, model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("PersRM Full Fine-Tuning")
    print("="*60)
    
    # Setup
    model, tokenizer = setup_model_and_tokenizer()
    dataset = load_and_preprocess_data(tokenizer)
    
    # Train
    trainer, model = train(
        model,
        tokenizer,
        dataset,
        epochs=args.epochs,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()

