"""
settings.py - ChatOS configuration settings.

Centralized configuration for all ChatOS components including
training pipeline, model management, and storage paths.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import os


@dataclass
class Settings:
    """ChatOS application settings."""
    
    # ==========================================================================
    # Storage Paths
    # ==========================================================================
    
    # Base directory for all ChatOS data
    memory_dir: Path = field(default_factory=lambda: Path.home() / "ChatOS-Memory")
    
    # Subdirectories
    @property
    def logs_dir(self) -> Path:
        return self.memory_dir / "logs"
    
    @property
    def training_data_dir(self) -> Path:
        return self.memory_dir / "training_data"
    
    @property
    def training_jobs_dir(self) -> Path:
        return self.memory_dir / "training_jobs"
    
    @property
    def training_metrics_dir(self) -> Path:
        return self.memory_dir / "training_metrics"
    
    @property
    def models_dir(self) -> Path:
        return self.memory_dir / "models"
    
    @property
    def feedback_dir(self) -> Path:
        return self.memory_dir / "feedback"
    
    # ==========================================================================
    # Unsloth Integration
    # ==========================================================================
    
    # Path to Unsloth repository
    unsloth_repo_dir: Path = field(default_factory=lambda: Path.home() / "unsloth")
    
    @property
    def unsloth_pipelines_dir(self) -> Path:
        return self.unsloth_repo_dir / "local_kali_pipelines"
    
    @property
    def unsloth_configs_dir(self) -> Path:
        return self.unsloth_pipelines_dir / "configs"
    
    @property
    def unsloth_datasets_dir(self) -> Path:
        return self.unsloth_pipelines_dir / "datasets"
    
    @property
    def unsloth_outputs_dir(self) -> Path:
        return self.unsloth_pipelines_dir / "outputs"
    
    # Virtual environment for Unsloth training
    # Can be a virtualenv path (~/unsloth_env) or conda env name (unsloth_py311)
    unsloth_venv_path: Path = field(default_factory=lambda: Path.home() / "miniforge3" / "envs" / "unsloth_py311")
    
    # ==========================================================================
    # Training Configuration
    # ==========================================================================
    
    # Minimum samples required before training
    min_samples_for_training: int = 50
    
    # Minimum quality ratio (percentage of positive feedback)
    min_quality_ratio: float = 0.7
    
    # Minimum hours between training runs
    training_cooldown_hours: int = 24
    
    # Default base model for training
    default_base_model: str = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
    
    # Default QLoRA config template
    default_qlora_config: str = "chatos_qlora.yaml"
    
    # ==========================================================================
    # Feature Flags
    # ==========================================================================
    
    # Enable training features (disable if no GPU)
    enable_training_features: bool = True
    
    # Enable feedback collection
    enable_feedback: bool = True
    
    # ==========================================================================
    # Learning Loop Database
    # ==========================================================================
    
    # PostgreSQL connection
    database_url: str = "postgresql://chatos:chatos@localhost:5432/chatos_learning"
    
    # SQLite fallback for development
    use_sqlite_fallback: bool = False
    
    @property
    def sqlite_path(self) -> Path:
        return self.memory_dir / "learning_loop.db"
    
    # ==========================================================================
    # Ollama Configuration
    # ==========================================================================
    
    ollama_host: str = "http://localhost:11434"
    
    # Available Ollama models
    default_ollama_models: List[str] = field(default_factory=lambda: [
        "qwen2.5:7b",
        "qwen2.5-coder:7b",
        "mistral:7b",
    ])
    
    # ==========================================================================
    # Methods
    # ==========================================================================
    
    def ensure_directories(self) -> None:
        """Create all required directories."""
        dirs = [
            self.memory_dir,
            self.logs_dir,
            self.training_data_dir,
            self.training_jobs_dir,
            self.training_metrics_dir,
            self.models_dir,
            self.feedback_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def get_unsloth_config_path(self, config_name: str) -> Path:
        """Get full path to an Unsloth config file."""
        return self.unsloth_configs_dir / config_name
    
    def get_training_job_path(self, job_id: str) -> Path:
        """Get path to a training job's metadata file."""
        return self.training_jobs_dir / f"{job_id}.json"
    
    def get_training_log_path(self, job_id: str) -> Path:
        """Get path to a training job's log file."""
        return self.training_jobs_dir / f"{job_id}.log"
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        settings = cls()
        
        # Override from environment
        if os.environ.get("CHATOS_MEMORY_DIR"):
            settings.memory_dir = Path(os.environ["CHATOS_MEMORY_DIR"])
        
        if os.environ.get("UNSLOTH_REPO_DIR"):
            settings.unsloth_repo_dir = Path(os.environ["UNSLOTH_REPO_DIR"])
        
        if os.environ.get("UNSLOTH_VENV_PATH"):
            settings.unsloth_venv_path = Path(os.environ["UNSLOTH_VENV_PATH"])
        
        if os.environ.get("CHATOS_ENABLE_TRAINING"):
            settings.enable_training_features = os.environ["CHATOS_ENABLE_TRAINING"].lower() == "true"
        
        return settings


# Global settings instance
settings = Settings.from_env()
settings.ensure_directories()

