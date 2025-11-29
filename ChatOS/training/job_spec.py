"""
job_spec.py - Training job specifications for ChatOS-Unsloth integration.

Defines the TrainingJobSpec dataclass that encapsulates all parameters
needed to configure and run a QLoRA fine-tuning job via Unsloth.
"""

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ChatOS.config.settings import settings


@dataclass
class TrainingJobSpec:
    """
    Specification for a training job.
    
    Contains all parameters needed to configure Unsloth QLoRA training.
    Optimized defaults for 8GB VRAM on Kali Linux.
    """
    
    # Job identification
    id: str = field(default_factory=lambda: f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}")
    description: Optional[str] = None
    
    # Preset and model info
    preset_name: str = "BALANCED"
    model_key: str = "qwen2.5-7b-instruct"  # Key in MODEL_CONFIGS
    
    # Dataset versioning
    dataset_version: int = 0
    dataset_sample_count: int = 0
    
    # Model configuration
    base_model_name: str = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
    max_seq_length: int = 2048
    
    # Dataset paths (absolute paths)
    dataset_train_path: str = ""
    dataset_eval_path: str = ""
    
    # Training hyperparameters (optimized for 8GB VRAM)
    num_epochs: Optional[float] = 2.0
    max_steps: Optional[int] = None  # If set, overrides num_epochs
    learning_rate: float = 2e-4
    per_device_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    warmup_ratio: float = 0.03
    weight_decay: float = 0.01
    
    # LoRA configuration
    lora_r: int = 16
    lora_alpha: int = 16
    lora_dropout: float = 0.0
    
    # Output configuration
    output_dir: str = ""
    logging_steps: int = 1
    save_steps: int = 100
    eval_steps: int = 50
    
    # Chat template (for non-Qwen models, change this)
    chat_template: str = "qwen-2.5"
    
    def __post_init__(self):
        """Set default paths if not provided."""
        if not self.dataset_train_path:
            self.dataset_train_path = str(settings.unsloth_datasets_dir / "chatos_train.jsonl")
        if not self.dataset_eval_path:
            self.dataset_eval_path = str(settings.unsloth_datasets_dir / "chatos_eval.jsonl")
        if not self.output_dir:
            self.output_dir = str(settings.unsloth_outputs_dir / self.id)
    
    @classmethod
    def from_defaults(
        cls,
        model_name: Optional[str] = None,
        train_path: Optional[str] = None,
        eval_path: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "TrainingJobSpec":
        """
        Create a TrainingJobSpec with safe defaults for 8GB VRAM.
        
        Args:
            model_name: Base model to fine-tune (default: Qwen2.5-7B-Instruct-bnb-4bit)
            train_path: Path to training dataset JSONL
            eval_path: Path to evaluation dataset JSONL
            description: Optional description for the job
        
        Returns:
            TrainingJobSpec with sensible defaults
        """
        spec = cls(description=description)
        
        if model_name:
            spec.base_model_name = model_name
            # Adjust chat template based on model
            if "qwen" in model_name.lower():
                spec.chat_template = "qwen-2.5"
            elif "mistral" in model_name.lower():
                spec.chat_template = "mistral"
            elif "llama" in model_name.lower():
                spec.chat_template = "llama-3"
            else:
                spec.chat_template = "chatml"
        
        if train_path:
            spec.dataset_train_path = str(Path(train_path).resolve())
        if eval_path:
            spec.dataset_eval_path = str(Path(eval_path).resolve())
        
        return spec
    
    @classmethod
    def from_preset(
        cls,
        preset_name: str = "BALANCED",
        model_key: str = "qwen2.5-7b-instruct",
        train_path: Optional[str] = None,
        eval_path: Optional[str] = None,
        dataset_version: int = 0,
        dataset_sample_count: int = 0,
        description: Optional[str] = None,
    ) -> "TrainingJobSpec":
        """
        Create a TrainingJobSpec from a preset and model configuration.
        
        Args:
            preset_name: Name of the preset (FAST, BALANCED, QUALITY)
            model_key: Model key from MODEL_CONFIGS
            train_path: Path to training dataset
            eval_path: Path to evaluation dataset
            dataset_version: Dataset version number
            dataset_sample_count: Number of samples in dataset
            description: Optional job description
        
        Returns:
            TrainingJobSpec configured from preset
        """
        from ChatOS.training.presets import get_preset, get_model_config
        
        preset = get_preset(preset_name)
        model_config = get_model_config(model_key)
        
        spec = cls(
            description=description,
            preset_name=preset_name,
            model_key=model_key,
            dataset_version=dataset_version,
            dataset_sample_count=dataset_sample_count,
            base_model_name=model_config.unsloth_name,
            chat_template=model_config.chat_template,
            # From preset
            num_epochs=preset.epochs,
            learning_rate=preset.learning_rate,
            per_device_batch_size=preset.batch_size,
            gradient_accumulation_steps=preset.gradient_accumulation_steps,
            warmup_ratio=preset.warmup_ratio,
            weight_decay=preset.weight_decay,
            lora_r=preset.lora_r,
            lora_alpha=preset.lora_alpha,
            eval_steps=preset.eval_steps,
            save_steps=preset.save_steps,
        )
        
        if train_path:
            spec.dataset_train_path = str(Path(train_path).resolve())
        if eval_path:
            spec.dataset_eval_path = str(Path(eval_path).resolve())
        
        return spec
    
    def to_config_override(self) -> Dict[str, Any]:
        """
        Generate a dict of fields to override in the Unsloth YAML config.
        
        Returns:
            Dictionary with config overrides for Unsloth training
        """
        override = {
            "job_id": self.id,
            "model": {
                "name": self.base_model_name,
                "max_seq_length": self.max_seq_length,
                "chat_template": self.chat_template,
            },
            "dataset": {
                "train_path": self.dataset_train_path,
                "eval_path": self.dataset_eval_path,
            },
            "training": {
                "output_dir": self.output_dir,
                "learning_rate": self.learning_rate,
                "per_device_train_batch_size": self.per_device_batch_size,
                "gradient_accumulation_steps": self.gradient_accumulation_steps,
                "warmup_ratio": self.warmup_ratio,
                "weight_decay": self.weight_decay,
                "logging_steps": self.logging_steps,
                "save_steps": self.save_steps,
                "eval_steps": self.eval_steps,
            },
            "lora": {
                "r": self.lora_r,
                "lora_alpha": self.lora_alpha,
                "lora_dropout": self.lora_dropout,
            },
            "metrics": {
                "output_path": str(Path(self.output_dir) / "metrics.jsonl"),
                "log_every_n_steps": self.logging_steps,
            },
        }
        
        # Set epochs or max_steps (not both)
        if self.max_steps is not None and self.max_steps > 0:
            override["training"]["max_steps"] = self.max_steps
            override["training"]["num_train_epochs"] = 1  # Will be ignored
        else:
            override["training"]["num_train_epochs"] = self.num_epochs or 2
            override["training"]["max_steps"] = -1
        
        return override
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingJobSpec":
        """Create from dictionary."""
        return cls(**data)

