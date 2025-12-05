#!/usr/bin/env python3
"""
persrm_pytorch_trainer.py - Pure PyTorch Training for PersRM

A clean, reliable training script using vanilla PyTorch with HuggingFace transformers.
No DeepSpeed required.

Features:
- YAML configuration
- 4-bit quantization with BitsAndBytes
- LoRA/PEFT support
- Mixed precision training (FP16/BF16)
- Gradient accumulation
- Checkpointing
- TensorBoard and W&B logging

Usage:
    python -m ChatOS.training.persrm_pytorch_trainer --config configs/persrm_pytorch.yaml
"""

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from torch.cuda.amp import GradScaler, autocast
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR

import yaml

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class TrainingConfig:
    """Training configuration loaded from YAML."""
    
    # Model
    base_model: str = "mistralai/Mistral-7B-Instruct-v0.2"
    use_4bit: bool = True
    use_lora: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])
    
    # Data
    train_path: str = "data/persrm/train.jsonl"
    val_path: str = "data/persrm/val.jsonl"
    max_seq_length: int = 2048
    
    # Training
    batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.03
    num_epochs: int = 3
    max_grad_norm: float = 1.0
    
    # Learning rate schedule
    lr_scheduler_type: str = "cosine"  # "cosine", "linear", "cosine_with_restarts"
    lr_restart_period: int = 5  # Epochs between restarts (for cosine_with_restarts)
    lr_min_ratio: float = 0.1  # Minimum LR as fraction of initial
    
    # Early stopping
    early_stopping: bool = False
    early_stopping_patience: int = 3
    early_stopping_threshold: float = 0.01
    
    # Mixed precision
    fp16: bool = True
    bf16: bool = False
    
    # Output
    output_dir: str = "models/persrm"
    logging_steps: int = 10
    save_steps: int = 100
    save_total_limit: int = 3
    save_best_only: bool = False
    
    # Logging
    use_tensorboard: bool = True
    use_wandb: bool = False
    wandb_project: str = "persrm-training"
    
    # Evaluation
    eval_epochs: int = 1
    eval_samples: int = 5
    
    # Device
    device: str = "auto"
    
    @classmethod
    def from_yaml(cls, path: str) -> 'TrainingConfig':
        """Load config from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Handle nested keys
        flat_data = {}
        for key, value in data.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    flat_data[k] = v
            else:
                flat_data[key] = value
        
        return cls(**{k: v for k, v in flat_data.items() if hasattr(cls, k) or k in cls.__dataclass_fields__})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "base_model": self.base_model,
            "use_4bit": self.use_4bit,
            "use_lora": self.use_lora,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "batch_size": self.batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "learning_rate": self.learning_rate,
            "num_epochs": self.num_epochs,
            "max_seq_length": self.max_seq_length,
            "fp16": self.fp16,
        }


# =============================================================================
# Model Setup
# =============================================================================

def setup_model_and_tokenizer(config: TrainingConfig):
    """
    Load base model and tokenizer, optionally with 4-bit quantization and LoRA.
    
    Returns:
        Tuple of (model, tokenizer)
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    
    print(f"Loading model: {config.base_model}")
    
    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(config.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    # Quantization config
    bnb_config = None
    if config.use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16 if config.fp16 else torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        print("  Using 4-bit quantization")
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        config.base_model,
        quantization_config=bnb_config,
        device_map="auto" if config.device == "auto" else None,
        trust_remote_code=True,
        torch_dtype=torch.float16 if config.fp16 else torch.bfloat16,
    )
    
    # Apply LoRA
    if config.use_lora:
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        
        if config.use_4bit:
            model = prepare_model_for_kbit_training(model)
        
        lora_config = LoraConfig(
            r=config.lora_r,
            lora_alpha=config.lora_alpha,
            lora_dropout=config.lora_dropout,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=config.lora_target_modules,
        )
        
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()
    
    # Enable gradient checkpointing for memory efficiency
    if hasattr(model, 'gradient_checkpointing_enable'):
        model.gradient_checkpointing_enable()
    
    return model, tokenizer


# =============================================================================
# Training Utilities
# =============================================================================

class TrainingMetrics:
    """Track and log training metrics."""
    
    def __init__(self, config: TrainingConfig, output_dir: Path):
        self.config = config
        self.output_dir = output_dir
        self.train_losses: List[float] = []
        self.eval_losses: List[float] = []
        self.learning_rates: List[float] = []
        self.steps: List[int] = []
        
        # TensorBoard
        self.tb_writer = None
        if config.use_tensorboard:
            try:
                from torch.utils.tensorboard import SummaryWriter
                self.tb_writer = SummaryWriter(log_dir=output_dir / "tensorboard")
                print(f"TensorBoard logging to: {output_dir / 'tensorboard'}")
            except ImportError:
                print("TensorBoard not available, skipping")
        
        # W&B
        self.wandb_run = None
        if config.use_wandb:
            try:
                import wandb
                self.wandb_run = wandb.init(
                    project=config.wandb_project,
                    config=config.to_dict(),
                    name=f"persrm-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                )
                print(f"W&B logging to project: {config.wandb_project}")
            except ImportError:
                print("W&B not available, skipping")
    
    def log_train_step(self, step: int, loss: float, lr: float):
        """Log a training step."""
        self.train_losses.append(loss)
        self.learning_rates.append(lr)
        self.steps.append(step)
        
        if self.tb_writer:
            self.tb_writer.add_scalar("train/loss", loss, step)
            self.tb_writer.add_scalar("train/learning_rate", lr, step)
        
        if self.wandb_run:
            import wandb
            wandb.log({"train/loss": loss, "train/lr": lr}, step=step)
    
    def log_eval(self, step: int, loss: float, perplexity: float):
        """Log evaluation metrics."""
        self.eval_losses.append(loss)
        
        if self.tb_writer:
            self.tb_writer.add_scalar("eval/loss", loss, step)
            self.tb_writer.add_scalar("eval/perplexity", perplexity, step)
        
        if self.wandb_run:
            import wandb
            wandb.log({"eval/loss": loss, "eval/perplexity": perplexity}, step=step)
    
    def save_metrics(self):
        """Save metrics to file."""
        metrics_path = self.output_dir / "metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump({
                "train_losses": self.train_losses[-100:],  # Last 100
                "eval_losses": self.eval_losses,
                "steps": self.steps[-100:],
            }, f, indent=2)
    
    def close(self):
        """Close logging resources."""
        if self.tb_writer:
            self.tb_writer.close()
        if self.wandb_run:
            import wandb
            wandb.finish()


def save_checkpoint(
    model,
    optimizer,
    scheduler,
    epoch: int,
    step: int,
    loss: float,
    output_dir: Path,
    config: TrainingConfig,
):
    """Save a training checkpoint."""
    checkpoint_dir = output_dir / f"checkpoint-{step}"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # Save model (LoRA weights if using PEFT)
    if hasattr(model, 'save_pretrained'):
        model.save_pretrained(checkpoint_dir)
    else:
        torch.save(model.state_dict(), checkpoint_dir / "model.pt")
    
    # Save training state
    torch.save({
        "epoch": epoch,
        "step": step,
        "loss": loss,
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict() if scheduler else None,
    }, checkpoint_dir / "training_state.pt")
    
    # Save config
    with open(checkpoint_dir / "config.json", 'w') as f:
        json.dump(config.to_dict(), f, indent=2)
    
    print(f"  Saved checkpoint to {checkpoint_dir}")
    
    # Cleanup old checkpoints
    if config.save_total_limit:
        checkpoints = sorted(output_dir.glob("checkpoint-*"), key=lambda x: int(x.name.split("-")[1]))
        while len(checkpoints) > config.save_total_limit:
            old = checkpoints.pop(0)
            import shutil
            shutil.rmtree(old)


# =============================================================================
# Training Loop
# =============================================================================

def train_epoch(
    model,
    train_loader,
    optimizer,
    scheduler,
    scaler: Optional[GradScaler],
    config: TrainingConfig,
    epoch: int,
    global_step: int,
    metrics: TrainingMetrics,
) -> Tuple[float, int]:
    """
    Train for one epoch.
    
    Returns:
        Tuple of (average_loss, final_global_step)
    """
    model.train()
    total_loss = 0.0
    num_batches = 0
    accumulation_loss = 0.0
    
    device = next(model.parameters()).device
    
    for batch_idx, batch in enumerate(train_loader):
        # Move to device
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)
        
        # Forward pass with mixed precision
        if scaler and config.fp16:
            with autocast():
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )
                loss = outputs.loss / config.gradient_accumulation_steps
        else:
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss / config.gradient_accumulation_steps
        
        # Backward pass
        if scaler:
            scaler.scale(loss).backward()
        else:
            loss.backward()
        
        accumulation_loss += loss.item()
        
        # Optimizer step (with gradient accumulation)
        if (batch_idx + 1) % config.gradient_accumulation_steps == 0:
            if scaler:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
            else:
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)
                optimizer.step()
            
            if scheduler:
                scheduler.step()
            
            optimizer.zero_grad()
            
            global_step += 1
            step_loss = accumulation_loss * config.gradient_accumulation_steps
            total_loss += step_loss
            num_batches += 1
            
            # Logging
            if global_step % config.logging_steps == 0:
                lr = optimizer.param_groups[0]['lr']
                metrics.log_train_step(global_step, step_loss, lr)
                print(f"  Step {global_step}: loss={step_loss:.4f}, lr={lr:.2e}")
            
            accumulation_loss = 0.0
    
    avg_loss = total_loss / max(num_batches, 1)
    return avg_loss, global_step


@torch.no_grad()
def evaluate(
    model,
    val_loader,
    config: TrainingConfig,
) -> Tuple[float, float]:
    """
    Evaluate the model.
    
    Returns:
        Tuple of (average_loss, perplexity)
    """
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    
    device = next(model.parameters()).device
    
    for batch in val_loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)
        
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels,
        )
        
        # Count non-padding tokens for perplexity
        num_tokens = (labels != -100).sum().item()
        total_loss += outputs.loss.item() * num_tokens
        total_tokens += num_tokens
    
    avg_loss = total_loss / max(total_tokens, 1)
    perplexity = math.exp(min(avg_loss, 100))  # Cap to avoid overflow
    
    return avg_loss, perplexity


# =============================================================================
# Main Training Function
# =============================================================================

def train(config: TrainingConfig):
    """Main training function."""
    
    print("=" * 60)
    print("PersRM PyTorch Training")
    print("=" * 60)
    
    # Setup output directory
    output_dir = Path(config.output_dir) / f"run-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")
    
    # Save config
    with open(output_dir / "config.yaml", 'w') as f:
        yaml.dump(config.to_dict(), f)
    
    # Check GPU
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        print("WARNING: No GPU detected!")
    
    # Load model and tokenizer
    print("\nLoading model...")
    model, tokenizer = setup_model_and_tokenizer(config)
    
    # Create datasets and dataloaders
    print("\nLoading data...")
    from ChatOS.training.persrm_dataset import create_dataloaders
    
    train_loader, val_loader = create_dataloaders(
        train_path=config.train_path,
        val_path=config.val_path,
        tokenizer=tokenizer,
        batch_size=config.batch_size,
        max_seq_length=config.max_seq_length,
        num_workers=getattr(config, 'num_workers', 0),
    )
    
    print(f"  Train batches: {len(train_loader)}")
    if val_loader:
        print(f"  Val batches: {len(val_loader)}")
    
    # Calculate training steps
    steps_per_epoch = len(train_loader) // config.gradient_accumulation_steps
    total_steps = steps_per_epoch * config.num_epochs
    warmup_steps = int(total_steps * config.warmup_ratio)
    
    print(f"\nTraining plan:")
    print(f"  Epochs: {config.num_epochs}")
    print(f"  Steps per epoch: {steps_per_epoch}")
    print(f"  Total steps: {total_steps}")
    print(f"  Warmup steps: {warmup_steps}")
    print(f"  Effective batch size: {config.batch_size * config.gradient_accumulation_steps}")
    
    # Optimizer
    optimizer = AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    
    # Scheduler setup
    from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts
    
    min_lr = config.learning_rate * config.lr_min_ratio
    
    if config.lr_scheduler_type == "cosine_with_restarts":
        # Cosine annealing with warm restarts
        restart_steps = steps_per_epoch * config.lr_restart_period
        warmup_scheduler = LinearLR(
            optimizer,
            start_factor=0.1,
            end_factor=1.0,
            total_iters=warmup_steps,
        )
        restart_scheduler = CosineAnnealingWarmRestarts(
            optimizer,
            T_0=restart_steps,
            T_mult=1,
            eta_min=min_lr,
        )
        scheduler = SequentialLR(
            optimizer,
            schedulers=[warmup_scheduler, restart_scheduler],
            milestones=[warmup_steps],
        )
        print(f"  LR Schedule: Cosine with restarts (period={config.lr_restart_period} epochs)")
    else:
        # Standard warmup + cosine decay
        warmup_scheduler = LinearLR(
            optimizer,
            start_factor=0.1,
            end_factor=1.0,
            total_iters=warmup_steps,
        )
        cosine_scheduler = CosineAnnealingLR(
            optimizer,
            T_max=total_steps - warmup_steps,
            eta_min=min_lr,
        )
        scheduler = SequentialLR(
            optimizer,
            schedulers=[warmup_scheduler, cosine_scheduler],
            milestones=[warmup_steps],
        )
        print(f"  LR Schedule: Warmup + Cosine decay")
    
    # Mixed precision scaler
    scaler = None
    if config.fp16 and torch.cuda.is_available():
        scaler = GradScaler()
        print("\nUsing FP16 mixed precision")
    
    # Metrics tracker
    metrics = TrainingMetrics(config, output_dir)
    
    # Training loop
    print("\n" + "=" * 60)
    print("Starting training...")
    if config.early_stopping:
        print(f"Early stopping enabled (patience={config.early_stopping_patience})")
    print("=" * 60)
    
    global_step = 0
    best_val_loss = float('inf')
    epochs_without_improvement = 0
    stopped_early = False
    
    for epoch in range(config.num_epochs):
        print(f"\n--- Epoch {epoch + 1}/{config.num_epochs} ---")
        start_time = time.time()
        
        # Train
        train_loss, global_step = train_epoch(
            model=model,
            train_loader=train_loader,
            optimizer=optimizer,
            scheduler=scheduler,
            scaler=scaler,
            config=config,
            epoch=epoch,
            global_step=global_step,
            metrics=metrics,
        )
        
        epoch_time = time.time() - start_time
        print(f"\nEpoch {epoch + 1} complete: train_loss={train_loss:.4f}, time={epoch_time:.1f}s")
        
        # Evaluate
        if val_loader:
            val_loss, perplexity = evaluate(model, val_loader, config)
            metrics.log_eval(global_step, val_loss, perplexity)
            print(f"Validation: loss={val_loss:.4f}, perplexity={perplexity:.2f}")
            
            # Check for improvement
            improvement = best_val_loss - val_loss
            if improvement > config.early_stopping_threshold:
                print(f"  Improvement: {improvement:.4f} (saving best model)")
                best_val_loss = val_loss
                epochs_without_improvement = 0
                
                # Save best model
                best_dir = output_dir / "best"
                best_dir.mkdir(parents=True, exist_ok=True)
                if hasattr(model, 'save_pretrained'):
                    model.save_pretrained(best_dir)
                tokenizer.save_pretrained(best_dir)
                
                save_checkpoint(
                    model, optimizer, scheduler,
                    epoch, global_step, val_loss,
                    output_dir, config
                )
            else:
                epochs_without_improvement += 1
                print(f"  No improvement for {epochs_without_improvement} epoch(s)")
                
                # Early stopping check
                if config.early_stopping and epochs_without_improvement >= config.early_stopping_patience:
                    print(f"\n⚠ Early stopping triggered after {epoch + 1} epochs")
                    stopped_early = True
                    break
        
        # Save periodic checkpoint (if not save_best_only)
        if not config.save_best_only and (epoch + 1) % config.eval_epochs == 0:
            save_checkpoint(
                model, optimizer, scheduler,
                epoch, global_step, train_loss,
                output_dir, config
            )
    
    # Save final model
    print("\n" + "=" * 60)
    if stopped_early:
        print(f"Training stopped early at epoch {epoch + 1}!")
    else:
        print("Training complete!")
    print("=" * 60)
    
    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    
    if hasattr(model, 'save_pretrained'):
        model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)
    
    # Copy best model to final if early stopping was used and best exists
    best_dir = output_dir / "best"
    if config.early_stopping and best_dir.exists():
        print(f"  Using best model from epoch with val_loss={best_val_loss:.4f}")
        import shutil
        for f in best_dir.glob("*"):
            shutil.copy2(f, final_dir / f.name)
    
    # Save training info
    with open(final_dir / "training_info.json", 'w') as f:
        json.dump({
            "base_model": config.base_model,
            "total_steps": global_step,
            "epochs_completed": epoch + 1,
            "final_train_loss": train_loss,
            "best_val_loss": best_val_loss if val_loader else None,
            "early_stopped": stopped_early,
            "lr_scheduler": config.lr_scheduler_type,
            "completed_at": datetime.now().isoformat(),
        }, f, indent=2)
    
    metrics.save_metrics()
    metrics.close()
    
    print(f"\nFinal model saved to: {final_dir}")
    print(f"Best validation loss: {best_val_loss:.4f}" if val_loader else "")
    
    return output_dir


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Train PersRM with PyTorch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML config file"
    )
    parser.add_argument(
        "--train-path",
        type=str,
        default=None,
        help="Override training data path"
    )
    parser.add_argument(
        "--val-path",
        type=str,
        default=None,
        help="Override validation data path"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override output directory"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Override number of epochs"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override batch size"
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=None,
        help="Override learning rate"
    )
    parser.add_argument(
        "--no-wandb",
        action="store_true",
        help="Disable W&B logging"
    )
    parser.add_argument(
        "--no-tensorboard",
        action="store_true",
        help="Disable TensorBoard logging"
    )
    
    args = parser.parse_args()
    
    # Load config
    if args.config:
        config = TrainingConfig.from_yaml(args.config)
    else:
        config = TrainingConfig()
    
    # Apply overrides
    if args.train_path:
        config.train_path = args.train_path
    if args.val_path:
        config.val_path = args.val_path
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.epochs:
        config.num_epochs = args.epochs
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.lr:
        config.learning_rate = args.lr
    if args.no_wandb:
        config.use_wandb = False
    if args.no_tensorboard:
        config.use_tensorboard = False
    
    # Run training
    train(config)


if __name__ == "__main__":
    main()

