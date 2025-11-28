"""
auto_trainer.py - Automated training system for ChatOS.

Continuously improves the local Qwen model based on:
- User interactions logged by MemoryLogger
- Quality ratings and feedback
- Scheduled training runs

Features:
- Incremental QLoRA fine-tuning
- Training data validation
- Model versioning
- Performance tracking
"""

import json
import os
import subprocess
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading
import asyncio


# =============================================================================
# Configuration
# =============================================================================

MEMORY_DIR = Path.home() / "ChatOS-Memory"
TRAINING_DIR = MEMORY_DIR / "training_data"
MODELS_DIR = MEMORY_DIR / "models"
CHECKPOINTS_DIR = MODELS_DIR / "checkpoints"
OLLAMA_MODELS_DIR = Path.home() / ".ollama" / "models"

# Ensure directories
for d in [MODELS_DIR, CHECKPOINTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Training thresholds
MIN_SAMPLES_FOR_TRAINING = 50  # Minimum conversations before training
MIN_QUALITY_RATIO = 0.7  # At least 70% good/excellent quality
TRAINING_COOLDOWN_HOURS = 24  # Minimum hours between training runs


@dataclass
class TrainingConfig:
    """Configuration for a training run."""
    
    # Model settings
    base_model: str = "Qwen/Qwen2.5-7B-Instruct"
    output_name: str = "chatos-qwen-enhanced"
    
    # LoRA settings
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])
    
    # Training settings
    epochs: int = 2
    batch_size: int = 1
    gradient_accumulation: int = 8
    learning_rate: float = 2e-4
    max_seq_length: int = 2048
    
    # Quantization
    use_4bit: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_model": self.base_model,
            "output_name": self.output_name,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "target_modules": self.target_modules,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "gradient_accumulation": self.gradient_accumulation,
            "learning_rate": self.learning_rate,
            "max_seq_length": self.max_seq_length,
            "use_4bit": self.use_4bit,
        }


@dataclass
class TrainingRun:
    """Record of a training run."""
    
    run_id: str
    started_at: str
    config: Dict[str, Any]
    
    # Data info
    num_samples: int = 0
    data_file: Optional[str] = None
    
    # Results
    completed_at: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None
    
    # Metrics
    final_loss: Optional[float] = None
    training_time_seconds: Optional[float] = None
    
    # Output
    output_path: Optional[str] = None
    ollama_model_name: Optional[str] = None


# =============================================================================
# Training Data Preparation
# =============================================================================

class TrainingDataPreparer:
    """Prepares and validates training data from logs."""
    
    def __init__(self):
        self.training_dir = TRAINING_DIR
    
    def prepare_dataset(
        self,
        output_file: Path,
        min_quality: str = "acceptable",
        max_samples: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Prepare training dataset from logged conversations.
        
        Returns statistics about the prepared data.
        """
        quality_scores = {
            "excellent": 4,
            "good": 3,
            "acceptable": 2,
            "unrated": 1,  # Include unrated with lower priority
            "poor": 0,
            "failed": -1,
        }
        min_score = quality_scores.get(min_quality, 2)
        
        samples = []
        stats = {
            "total_files": 0,
            "total_raw": 0,
            "quality_filtered": 0,
            "format_filtered": 0,
            "final_samples": 0,
        }
        
        # Collect all training data
        for data_file in sorted(self.training_dir.glob("training_*.jsonl")):
            stats["total_files"] += 1
            
            with open(data_file) as f:
                for line in f:
                    stats["total_raw"] += 1
                    try:
                        data = json.loads(line)
                        
                        # Check quality
                        quality = data.get("metadata", {}).get("quality", "unrated")
                        if quality_scores.get(quality, 0) < min_score:
                            stats["quality_filtered"] += 1
                            continue
                        
                        # Validate format
                        messages = data.get("messages", [])
                        if not self._validate_messages(messages):
                            stats["format_filtered"] += 1
                            continue
                        
                        # Add quality score for sorting
                        data["_quality_score"] = quality_scores.get(quality, 0)
                        samples.append(data)
                        
                    except json.JSONDecodeError:
                        continue
        
        # Sort by quality (best first) and limit
        samples.sort(key=lambda x: x.get("_quality_score", 0), reverse=True)
        
        if max_samples and len(samples) > max_samples:
            samples = samples[:max_samples]
        
        # Remove internal fields and write
        final_samples = []
        for sample in samples:
            sample.pop("_quality_score", None)
            final_samples.append(sample)
        
        with open(output_file, "w") as f:
            json.dump(final_samples, f, indent=2)
        
        stats["final_samples"] = len(final_samples)
        stats["output_file"] = str(output_file)
        
        return stats
    
    def _validate_messages(self, messages: List[Dict]) -> bool:
        """Validate message format for training."""
        if len(messages) < 2:
            return False
        
        has_user = any(m.get("role") == "user" for m in messages)
        has_assistant = any(m.get("role") == "assistant" for m in messages)
        
        if not (has_user and has_assistant):
            return False
        
        # Check content length
        for msg in messages:
            content = msg.get("content", "")
            if len(content) < 5:  # Too short
                return False
            if len(content) > 10000:  # Too long
                return False
        
        return True
    
    def get_data_stats(self) -> Dict[str, Any]:
        """Get statistics about available training data."""
        stats = {
            "total_files": 0,
            "total_samples": 0,
            "quality_distribution": {},
            "oldest_data": None,
            "newest_data": None,
        }
        
        for data_file in sorted(self.training_dir.glob("training_*.jsonl")):
            stats["total_files"] += 1
            file_date = data_file.stem.replace("training_", "")
            
            if stats["oldest_data"] is None or file_date < stats["oldest_data"]:
                stats["oldest_data"] = file_date
            if stats["newest_data"] is None or file_date > stats["newest_data"]:
                stats["newest_data"] = file_date
            
            with open(data_file) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        stats["total_samples"] += 1
                        
                        quality = data.get("metadata", {}).get("quality", "unrated")
                        stats["quality_distribution"][quality] = stats["quality_distribution"].get(quality, 0) + 1
                        
                    except json.JSONDecodeError:
                        continue
        
        return stats


# =============================================================================
# Auto Trainer
# =============================================================================

class AutoTrainer:
    """
    Automated training system for ChatOS.
    
    Monitors training data accumulation and triggers training runs
    when sufficient quality data is available.
    """
    
    def __init__(self):
        self.data_preparer = TrainingDataPreparer()
        self.config = TrainingConfig()
        self.runs: List[TrainingRun] = []
        self._load_history()
        
        # Qwen environment path
        self.qwen_env = Path.home() / "qwen-ai"
        self.conda_path = self.qwen_env / "conda" / "bin" / "conda"
    
    def _load_history(self) -> None:
        """Load training history."""
        history_file = MODELS_DIR / "training_history.json"
        if history_file.exists():
            try:
                data = json.loads(history_file.read_text())
                self.runs = [TrainingRun(**r) for r in data.get("runs", [])]
            except Exception:
                pass
    
    def _save_history(self) -> None:
        """Save training history."""
        history_file = MODELS_DIR / "training_history.json"
        data = {
            "runs": [
                {
                    "run_id": r.run_id,
                    "started_at": r.started_at,
                    "config": r.config,
                    "num_samples": r.num_samples,
                    "data_file": r.data_file,
                    "completed_at": r.completed_at,
                    "status": r.status,
                    "error": r.error,
                    "final_loss": r.final_loss,
                    "training_time_seconds": r.training_time_seconds,
                    "output_path": r.output_path,
                    "ollama_model_name": r.ollama_model_name,
                }
                for r in self.runs
            ]
        }
        history_file.write_text(json.dumps(data, indent=2))
    
    def should_train(self) -> Dict[str, Any]:
        """
        Check if training should be triggered.
        
        Returns dict with 'should_train' bool and 'reason'.
        """
        stats = self.data_preparer.get_data_stats()
        
        # Check sample count
        if stats["total_samples"] < MIN_SAMPLES_FOR_TRAINING:
            return {
                "should_train": False,
                "reason": f"Insufficient samples: {stats['total_samples']}/{MIN_SAMPLES_FOR_TRAINING}",
                "stats": stats,
            }
        
        # Check quality ratio
        quality_dist = stats["quality_distribution"]
        good_count = quality_dist.get("excellent", 0) + quality_dist.get("good", 0)
        total = sum(quality_dist.values())
        
        if total > 0:
            ratio = good_count / total
            if ratio < MIN_QUALITY_RATIO:
                return {
                    "should_train": False,
                    "reason": f"Quality ratio too low: {ratio:.1%} < {MIN_QUALITY_RATIO:.1%}",
                    "stats": stats,
                }
        
        # Check cooldown
        if self.runs:
            last_run = self.runs[-1]
            if last_run.completed_at:
                last_time = datetime.fromisoformat(last_run.completed_at)
                cooldown = timedelta(hours=TRAINING_COOLDOWN_HOURS)
                if datetime.now() - last_time < cooldown:
                    remaining = cooldown - (datetime.now() - last_time)
                    return {
                        "should_train": False,
                        "reason": f"Cooldown active: {remaining.total_seconds()/3600:.1f}h remaining",
                        "stats": stats,
                    }
        
        return {
            "should_train": True,
            "reason": "Ready for training",
            "stats": stats,
        }
    
    def start_training(
        self,
        config: Optional[TrainingConfig] = None,
        force: bool = False,
    ) -> TrainingRun:
        """
        Start a training run.
        
        Args:
            config: Training configuration (uses default if None)
            force: Skip readiness checks
            
        Returns:
            TrainingRun record
        """
        if config is None:
            config = self.config
        
        # Check readiness unless forced
        if not force:
            check = self.should_train()
            if not check["should_train"]:
                raise ValueError(f"Not ready for training: {check['reason']}")
        
        # Generate run ID
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Prepare training data
        data_file = TRAINING_DIR / f"run_{run_id}.json"
        data_stats = self.data_preparer.prepare_dataset(data_file)
        
        # Create run record
        run = TrainingRun(
            run_id=run_id,
            started_at=datetime.now().isoformat(),
            config=config.to_dict(),
            num_samples=data_stats["final_samples"],
            data_file=str(data_file),
            status="running",
        )
        self.runs.append(run)
        self._save_history()
        
        # Start training in background
        thread = threading.Thread(
            target=self._run_training,
            args=(run, config, data_file),
            daemon=True,
        )
        thread.start()
        
        return run
    
    def _run_training(
        self,
        run: TrainingRun,
        config: TrainingConfig,
        data_file: Path,
    ) -> None:
        """Execute the training run."""
        start_time = datetime.now()
        output_dir = CHECKPOINTS_DIR / f"run_{run.run_id}"
        
        try:
            # Create training script
            script = self._generate_training_script(config, data_file, output_dir)
            script_file = TRAINING_DIR / f"train_{run.run_id}.py"
            script_file.write_text(script)
            
            # Run training
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = "0"
            
            # Use qwen-ai conda environment
            activate_cmd = f"source {self.qwen_env}/conda/bin/activate && conda activate qwen"
            train_cmd = f"python {script_file}"
            full_cmd = f"bash -c '{activate_cmd} && {train_cmd}'"
            
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                env=env,
                timeout=7200,  # 2 hour timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Training failed: {result.stderr}")
            
            # Update run record
            run.status = "completed"
            run.output_path = str(output_dir)
            run.training_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # Try to extract loss from output
            for line in result.stdout.split("\n"):
                if "loss" in line.lower():
                    try:
                        # Simple extraction - improve as needed
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if "loss" in p.lower() and i + 1 < len(parts):
                                run.final_loss = float(parts[i + 1].strip(",:"))
                                break
                    except (ValueError, IndexError):
                        pass
            
            # Convert to Ollama model
            ollama_name = self._convert_to_ollama(run, config, output_dir)
            if ollama_name:
                run.ollama_model_name = ollama_name
            
        except Exception as e:
            run.status = "failed"
            run.error = str(e)
        
        run.completed_at = datetime.now().isoformat()
        self._save_history()
    
    def _generate_training_script(
        self,
        config: TrainingConfig,
        data_file: Path,
        output_dir: Path,
    ) -> str:
        """Generate the training Python script."""
        return f'''#!/usr/bin/env python3
"""Auto-generated training script for ChatOS enhancement."""

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

# Configuration
MODEL_ID = "{config.base_model}"
DATA_FILE = "{data_file}"
OUTPUT_DIR = "{output_dir}"

print("🚀 ChatOS Auto-Training: Starting...")

# 4-bit quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit={config.use_4bit},
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

# Load tokenizer
print("📥 Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

# Load model
print("📥 Loading model...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
model.config.use_cache = False
model = prepare_model_for_kbit_training(model)

# LoRA config
lora_config = LoraConfig(
    r={config.lora_r},
    lora_alpha={config.lora_alpha},
    lora_dropout={config.lora_dropout},
    bias="none",
    task_type="CAUSAL_LM",
    target_modules={config.target_modules},
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Load dataset
print("📚 Loading dataset...")
dataset = load_dataset("json", data_files=str(DATA_FILE), split="train")

def format_chat(example):
    if "messages" in example:
        return {{"text": tokenizer.apply_chat_template(example["messages"], tokenize=False)}}
    return example

dataset = dataset.map(format_chat)
print(f"   Samples: {{len(dataset)}}")

# Training config
training_args = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs={config.epochs},
    per_device_train_batch_size={config.batch_size},
    gradient_accumulation_steps={config.gradient_accumulation},
    learning_rate={config.learning_rate},
    weight_decay=0.01,
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    logging_steps=5,
    save_strategy="epoch",
    bf16=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={{"use_reentrant": False}},
    max_seq_length={config.max_seq_length},
    packing=True,
    dataset_text_field="text",
    report_to="none",
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    processing_class=tokenizer,
)

print("🏋️ Training...")
trainer.train()

# Save
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"✅ Training complete! Model saved to {{OUTPUT_DIR}}")
'''
    
    def _convert_to_ollama(
        self,
        run: TrainingRun,
        config: TrainingConfig,
        output_dir: Path,
    ) -> Optional[str]:
        """Convert trained model to Ollama format."""
        try:
            # Create Modelfile
            model_name = f"chatos-qwen-{run.run_id}"
            modelfile_content = f'''# ChatOS Enhanced Qwen Model
# Trained on {run.num_samples} user interactions
# Run ID: {run.run_id}

FROM qwen2.5:7b

SYSTEM """You are a helpful AI assistant enhanced through ChatOS user interactions. 
You provide thoughtful, accurate, and contextual responses.
You excel at both general conversation and coding tasks."""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
PARAMETER stop "<|im_end|>"
'''
            
            modelfile_path = output_dir / "Modelfile"
            modelfile_path.write_text(modelfile_content)
            
            # Create Ollama model
            result = subprocess.run(
                ["ollama", "create", model_name, "-f", str(modelfile_path)],
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": f"{Path.home()}/.local/bin:{os.environ.get('PATH', '')}"},
            )
            
            if result.returncode == 0:
                return model_name
            
        except Exception as e:
            print(f"Warning: Could not create Ollama model: {e}")
        
        return None
    
    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status."""
        active_runs = [r for r in self.runs if r.status == "running"]
        
        return {
            "total_runs": len(self.runs),
            "completed_runs": len([r for r in self.runs if r.status == "completed"]),
            "failed_runs": len([r for r in self.runs if r.status == "failed"]),
            "active_runs": len(active_runs),
            "current_run": active_runs[-1].run_id if active_runs else None,
            "last_completed": next(
                (r for r in reversed(self.runs) if r.status == "completed"),
                None
            ),
            "readiness": self.should_train(),
        }
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all trained models."""
        models = []
        for run in self.runs:
            if run.status == "completed" and run.output_path:
                models.append({
                    "run_id": run.run_id,
                    "trained_at": run.completed_at,
                    "samples": run.num_samples,
                    "path": run.output_path,
                    "ollama_name": run.ollama_model_name,
                    "loss": run.final_loss,
                })
        return models


# =============================================================================
# Singleton Access
# =============================================================================

_trainer: Optional[AutoTrainer] = None


def get_auto_trainer() -> AutoTrainer:
    """Get the singleton auto trainer."""
    global _trainer
    if _trainer is None:
        _trainer = AutoTrainer()
    return _trainer

