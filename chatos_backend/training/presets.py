"""
presets.py - Training presets for ChatOS and PersRM fine-tuning.

Defines standardized training configurations optimized for different
use cases and hardware constraints (8GB VRAM target).

Supports two training types:
- CHATOS: General chat/conversation fine-tuning
- PERSRM: UI/UX reasoning fine-tuning
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class TrainingType(str, Enum):
    """Available training types."""
    CHATOS = "chatos"
    PERSRM = "persrm"


class PresetName(str, Enum):
    """Available training presets for ChatOS."""
    FAST = "FAST"
    BALANCED = "BALANCED"
    QUALITY = "QUALITY"


class PersRMPresetName(str, Enum):
    """Available training presets for PersRM."""
    FAST = "FAST"
    REASONING = "REASONING"
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


# =============================================================================
# PersRM-Specific Presets
# =============================================================================

PERSRM_PRESET_FAST = TrainingPreset(
    name="FAST",
    description="Quick iteration for PersRM reasoning (~3-5 min)",
    batch_size=1,
    epochs=1.0,
    learning_rate=1.5e-5,
    gradient_accumulation_steps=4,
    eval_steps=10,
    save_steps=25,
    lora_r=8,
    lora_alpha=8,
)

PERSRM_PRESET_REASONING = TrainingPreset(
    name="REASONING",
    description="Optimized for UI/UX reasoning tasks (~15-20 min)",
    batch_size=2,
    epochs=3.0,
    learning_rate=8e-6,  # Lower LR for reasoning tasks
    gradient_accumulation_steps=8,
    warmup_ratio=0.05,  # Slightly longer warmup
    weight_decay=0.01,
    eval_steps=25,
    save_steps=50,
    lora_r=32,
    lora_alpha=32,
)

PERSRM_PRESET_QUALITY = TrainingPreset(
    name="QUALITY",
    description="High-quality PersRM training with more epochs (~25-35 min)",
    batch_size=2,
    epochs=5.0,
    learning_rate=5e-6,  # Even lower for quality
    gradient_accumulation_steps=8,
    warmup_ratio=0.06,
    weight_decay=0.01,
    eval_steps=25,
    save_steps=50,
    lora_r=64,
    lora_alpha=64,
)

# PersRM Standalone preset - optimized for Mistral 7B with chain-of-thought reasoning
PERSRM_PRESET_STANDALONE = TrainingPreset(
    name="STANDALONE",
    description="PersRM Standalone model training on Mistral 7B (~20-30 min)",
    batch_size=2,
    epochs=3.0,
    learning_rate=2e-4,  # QLoRA optimal for Mistral
    gradient_accumulation_steps=8,
    warmup_ratio=0.03,
    weight_decay=0.01,
    eval_steps=25,
    save_steps=50,
    lora_r=64,  # Higher rank for complex reasoning
    lora_alpha=16,  # Standard alpha for stability
)


# PersRM preset registry
PERSRM_PRESETS: Dict[str, TrainingPreset] = {
    "FAST": PERSRM_PRESET_FAST,
    "REASONING": PERSRM_PRESET_REASONING,
    "QUALITY": PERSRM_PRESET_QUALITY,
    "STANDALONE": PERSRM_PRESET_STANDALONE,
}

# Default PersRM preset
DEFAULT_PERSRM_PRESET = "REASONING"


def get_persrm_preset(name: str) -> TrainingPreset:
    """
    Get a PersRM preset by name.
    
    Args:
        name: Preset name (FAST, REASONING, QUALITY)
    
    Returns:
        TrainingPreset
    
    Raises:
        ValueError: If preset name is invalid
    """
    name_upper = name.upper()
    if name_upper not in PERSRM_PRESETS:
        valid = ", ".join(PERSRM_PRESETS.keys())
        raise ValueError(f"Invalid PersRM preset '{name}'. Valid presets: {valid}")
    return PERSRM_PRESETS[name_upper]


def list_persrm_presets() -> Dict[str, Dict[str, Any]]:
    """
    List all available PersRM presets with their configurations.
    
    Returns:
        Dict mapping preset name to configuration
    """
    return {name: preset.to_dict() for name, preset in PERSRM_PRESETS.items()}


# =============================================================================
# PersRM-Specific Model Configs (Best-in-Class for UI/UX Tasks)
# =============================================================================

# PersRM-optimized models for reasoning, coding, and lightweight deployment
PERSRM_MODEL_CONFIGS: Dict[str, ModelConfig] = {
    # Reasoning Models (Recommended for UI/UX analysis)
    "qwen2.5-7b": ModelConfig(
        name="qwen2.5-7b",
        display_name="Qwen 2.5 7B (Recommended)",
        unsloth_name="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
        chat_template="qwen-2.5",
        description="Best overall for UI/UX reasoning - top benchmarks",
        vram_requirement="~6GB",
    ),
    "mistral-7b": ModelConfig(
        name="mistral-7b",
        display_name="Mistral 7B Instruct v0.3 (Fast & Efficient)",
        unsloth_name="unsloth/mistral-7b-instruct-v0.3-bnb-4bit",
        chat_template="mistral",
        description="Fast inference, efficient fine-tuning - great for standalone PersRM",
        vram_requirement="~6GB",
    ),
    "phi-3-mini": ModelConfig(
        name="phi-3-mini",
        display_name="Phi-3 Mini 3.8B (Compact Reasoning)",
        unsloth_name="unsloth/Phi-3-mini-4k-instruct-bnb-4bit",
        chat_template="phi-3",
        description="Best reasoning per parameter - fits smaller GPUs",
        vram_requirement="~4GB",
    ),
    # Coding Models (For component generation)
    "deepseek-coder-6.7b": ModelConfig(
        name="deepseek-coder-6.7b",
        display_name="DeepSeek Coder 6.7B",
        unsloth_name="unsloth/deepseek-coder-6.7b-instruct-bnb-4bit",
        chat_template="deepseek",
        description="Top-tier for UI component code generation",
        vram_requirement="~6GB",
    ),
    "qwen2.5-coder-7b": ModelConfig(
        name="qwen2.5-coder-7b",
        display_name="Qwen 2.5 Coder 7B",
        unsloth_name="unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",
        chat_template="qwen-2.5",
        description="Excellent code + explanation - great for tutorials",
        vram_requirement="~6GB",
    ),
    # Lightweight Models (For fast iteration)
    "qwen2.5-3b": ModelConfig(
        name="qwen2.5-3b",
        display_name="Qwen 2.5 3B (Fast)",
        unsloth_name="unsloth/Qwen2.5-3B-Instruct-bnb-4bit",
        chat_template="qwen-2.5",
        description="Quick iterations, low VRAM - good for testing",
        vram_requirement="~3GB",
    ),
    "llama-3.2-3b": ModelConfig(
        name="llama-3.2-3b",
        display_name="Llama 3.2 3B",
        unsloth_name="unsloth/Llama-3.2-3B-Instruct-bnb-4bit",
        chat_template="llama-3",
        description="Meta's latest compact model - strong reasoning",
        vram_requirement="~3GB",
    ),
}

# Default PersRM model (best for UI/UX reasoning)
DEFAULT_PERSRM_MODEL = "qwen2.5-7b"


def get_persrm_model_config(name: str) -> ModelConfig:
    """
    Get PersRM model configuration by name.
    
    Args:
        name: Model name
    
    Returns:
        ModelConfig
    
    Raises:
        ValueError: If model name is invalid
    """
    name_lower = name.lower()
    if name_lower not in PERSRM_MODEL_CONFIGS:
        valid = ", ".join(PERSRM_MODEL_CONFIGS.keys())
        raise ValueError(f"Invalid PersRM model '{name}'. Valid models: {valid}")
    return PERSRM_MODEL_CONFIGS[name_lower]


def list_persrm_models() -> Dict[str, Dict[str, Any]]:
    """
    List all available PersRM models for fine-tuning.
    
    Returns:
        Dict mapping model name to configuration
    """
    return {
        name: {
            "name": config.name,
            "display_name": config.display_name,
            "description": config.description,
            "vram_requirement": config.vram_requirement,
            "chat_template": config.chat_template,
        }
        for name, config in PERSRM_MODEL_CONFIGS.items()
    }


# =============================================================================
# Unified Preset Access
# =============================================================================

def get_preset_for_type(
    training_type: str,
    preset_name: Optional[str] = None,
) -> TrainingPreset:
    """
    Get a preset for a specific training type.
    
    Args:
        training_type: "chatos" or "persrm"
        preset_name: Optional preset name (uses default if not provided)
    
    Returns:
        TrainingPreset
    """
    if training_type == TrainingType.PERSRM or training_type == "persrm":
        preset_name = preset_name or DEFAULT_PERSRM_PRESET
        return get_persrm_preset(preset_name)
    else:
        preset_name = preset_name or DEFAULT_PRESET
        return get_preset(preset_name)


def list_presets_for_type(training_type: str) -> Dict[str, Dict[str, Any]]:
    """
    List all presets for a specific training type.
    
    Args:
        training_type: "chatos" or "persrm"
    
    Returns:
        Dict mapping preset name to configuration
    """
    if training_type == TrainingType.PERSRM or training_type == "persrm":
        return list_persrm_presets()
    else:
        return list_presets()


def get_default_preset_for_type(training_type: str) -> str:
    """
    Get the default preset name for a training type.
    
    Args:
        training_type: "chatos" or "persrm"
    
    Returns:
        Default preset name
    """
    if training_type == TrainingType.PERSRM or training_type == "persrm":
        return DEFAULT_PERSRM_PRESET
    else:
        return DEFAULT_PRESET

