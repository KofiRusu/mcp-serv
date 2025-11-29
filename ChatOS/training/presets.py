"""
presets.py - Training presets for ChatOS fine-tuning.

Defines standardized training configurations optimized for different
use cases and hardware constraints (8GB VRAM target).
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class PresetName(str, Enum):
    """Available training presets."""
    FAST = "FAST"
    BALANCED = "BALANCED"
    QUALITY = "QUALITY"


@dataclass
class TrainingPreset:
    """
    A predefined training configuration.
    
    Attributes:
        name: Preset identifier
        description: Human-readable description
        batch_size: Per-device batch size
        epochs: Number of training epochs
        learning_rate: Learning rate
        gradient_accumulation_steps: Gradient accumulation steps
        warmup_ratio: Warmup ratio
        weight_decay: Weight decay
        lora_r: LoRA rank
        lora_alpha: LoRA alpha
        eval_steps: Steps between evaluations
        save_steps: Steps between checkpoints
    """
    name: str
    description: str
    batch_size: int
    epochs: float
    learning_rate: float
    gradient_accumulation_steps: int = 8
    warmup_ratio: float = 0.03
    weight_decay: float = 0.01
    lora_r: int = 16
    lora_alpha: int = 16
    eval_steps: int = 50
    save_steps: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "warmup_ratio": self.warmup_ratio,
            "weight_decay": self.weight_decay,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "eval_steps": self.eval_steps,
            "save_steps": self.save_steps,
        }


# =============================================================================
# Preset Definitions
# =============================================================================

PRESET_FAST = TrainingPreset(
    name="FAST",
    description="Quick training for testing and iteration (~2-5 min)",
    batch_size=1,
    epochs=1.0,
    learning_rate=2e-5,
    gradient_accumulation_steps=4,
    eval_steps=20,
    save_steps=50,
    lora_r=8,
    lora_alpha=8,
)

PRESET_BALANCED = TrainingPreset(
    name="BALANCED",
    description="Balanced speed and quality for most use cases (~10-15 min)",
    batch_size=2,
    epochs=2.0,
    learning_rate=1.5e-5,
    gradient_accumulation_steps=8,
    eval_steps=50,
    save_steps=100,
    lora_r=16,
    lora_alpha=16,
)

PRESET_QUALITY = TrainingPreset(
    name="QUALITY",
    description="High-quality training with more epochs (~20-30 min)",
    batch_size=2,
    epochs=3.0,
    learning_rate=1e-5,
    gradient_accumulation_steps=8,
    eval_steps=50,
    save_steps=100,
    lora_r=32,
    lora_alpha=32,
)


# Preset registry
PRESETS: Dict[str, TrainingPreset] = {
    "FAST": PRESET_FAST,
    "BALANCED": PRESET_BALANCED,
    "QUALITY": PRESET_QUALITY,
}

# Default preset
DEFAULT_PRESET = "BALANCED"


def get_preset(name: str) -> TrainingPreset:
    """
    Get a preset by name.
    
    Args:
        name: Preset name (FAST, BALANCED, QUALITY)
    
    Returns:
        TrainingPreset
    
    Raises:
        ValueError: If preset name is invalid
    """
    name_upper = name.upper()
    if name_upper not in PRESETS:
        valid = ", ".join(PRESETS.keys())
        raise ValueError(f"Invalid preset '{name}'. Valid presets: {valid}")
    return PRESETS[name_upper]


def list_presets() -> Dict[str, Dict[str, Any]]:
    """
    List all available presets with their configurations.
    
    Returns:
        Dict mapping preset name to configuration
    """
    return {name: preset.to_dict() for name, preset in PRESETS.items()}


# =============================================================================
# Model Presets
# =============================================================================

@dataclass
class ModelConfig:
    """Configuration for a base model."""
    name: str
    display_name: str
    unsloth_name: str
    chat_template: str
    description: str
    vram_requirement: str


# Supported models for fine-tuning
MODEL_CONFIGS: Dict[str, ModelConfig] = {
    "qwen2.5-7b-instruct": ModelConfig(
        name="qwen2.5-7b-instruct",
        display_name="Qwen 2.5 7B Instruct",
        unsloth_name="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
        chat_template="qwen-2.5",
        description="Excellent general-purpose model with strong reasoning",
        vram_requirement="~6GB",
    ),
    "qwen2.5-coder-7b": ModelConfig(
        name="qwen2.5-coder-7b",
        display_name="Qwen 2.5 Coder 7B",
        unsloth_name="unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",
        chat_template="qwen-2.5",
        description="Specialized for code generation and understanding",
        vram_requirement="~6GB",
    ),
    "mistral-7b-instruct": ModelConfig(
        name="mistral-7b-instruct",
        display_name="Mistral 7B Instruct",
        unsloth_name="unsloth/mistral-7b-instruct-v0.3-bnb-4bit",
        chat_template="mistral",
        description="Fast, efficient model with good general performance",
        vram_requirement="~6GB",
    ),
}

DEFAULT_MODEL = "qwen2.5-7b-instruct"


def get_model_config(name: str) -> ModelConfig:
    """
    Get model configuration by name.
    
    Args:
        name: Model name
    
    Returns:
        ModelConfig
    
    Raises:
        ValueError: If model name is invalid
    """
    name_lower = name.lower()
    if name_lower not in MODEL_CONFIGS:
        valid = ", ".join(MODEL_CONFIGS.keys())
        raise ValueError(f"Invalid model '{name}'. Valid models: {valid}")
    return MODEL_CONFIGS[name_lower]


def list_models() -> Dict[str, Dict[str, Any]]:
    """
    List all available models for fine-tuning.
    
    Returns:
        Dict mapping model name to configuration
    """
    return {
        name: {
            "name": config.name,
            "display_name": config.display_name,
            "description": config.description,
            "vram_requirement": config.vram_requirement,
        }
        for name, config in MODEL_CONFIGS.items()
    }

