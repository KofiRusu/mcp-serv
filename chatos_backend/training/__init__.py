"""
ChatOS Training Module - Compatibility Shim

⚠️ DEPRECATION NOTICE ⚠️
This module is a backward-compatibility shim. The canonical training module
is now located at `/persrm_training/`. All imports from `chatos_backend.training`
are re-exported from `persrm_training`.

Migration: Update your imports to use `persrm_training` directly:
    # Old (deprecated):
    from chatos_backend.training import job_store
    
    # New (preferred):
    from persrm_training import job_store

This shim will be removed in a future release.
"""

import warnings

# Emit deprecation warning on import (once per session)
warnings.warn(
    "chatos_backend.training is deprecated. Use persrm_training instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export core items from persrm_training (these have minimal dependencies)
from persrm_training import (
    # Data pipeline
    load_raw_conversations,
    filter_for_training,
    to_unsloth_jsonl,
    generate_training_dataset,
    get_current_dataset_version,
    list_dataset_versions,
    DatasetStats,
    # Job spec
    TrainingJobSpec,
    # Presets
    TrainingPreset,
    get_preset,
    list_presets,
    get_model_config,
    list_models,
    PRESET_FAST,
    PRESET_BALANCED,
    PRESET_QUALITY,
    DEFAULT_PRESET,
    DEFAULT_MODEL,
    # Unsloth runner
    write_temp_config,
    start_training_process,
    stop_training_process,
    is_process_alive,
    # Job store
    create_job,
    update_job,
    get_job,
    list_jobs,
    delete_job,
    mark_job_completed,
    mark_job_failed,
    update_job_metrics,
    get_running_jobs,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_COMPLETED,
    STATUS_FAILED,
)

# Lightweight submodule re-exports (no heavy dependencies like torch)
from persrm_training import data_pipeline
from persrm_training import job_spec
from persrm_training import job_store
from persrm_training import presets
from persrm_training import unsloth_runner
from persrm_training import monitor

# Heavy submodules (require torch, etc.) - use lazy import pattern
# These will be imported on first access via __getattr__
_LAZY_SUBMODULES = {
    "auto_trainer",
    "exercise_manager",
    "learning_loop_integration",
    "persrm_data_generator",
    "persrm_data_pipeline",
    "persrm_full_finetune",
    "persrm_pytorch_trainer",
    "persrm_standalone_generator",
    "run_persrm_standalone",
}

def __getattr__(name):
    """Lazy import for heavy submodules that require torch."""
    if name in _LAZY_SUBMODULES:
        import importlib
        module = importlib.import_module(f"persrm_training.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Data pipeline
    "load_raw_conversations",
    "filter_for_training",
    "to_unsloth_jsonl",
    "generate_training_dataset",
    "get_current_dataset_version",
    "list_dataset_versions",
    "DatasetStats",
    # Job spec
    "TrainingJobSpec",
    # Presets
    "TrainingPreset",
    "get_preset",
    "list_presets",
    "get_model_config",
    "list_models",
    "PRESET_FAST",
    "PRESET_BALANCED",
    "PRESET_QUALITY",
    "DEFAULT_PRESET",
    "DEFAULT_MODEL",
    # Unsloth runner
    "write_temp_config",
    "start_training_process",
    "stop_training_process",
    "is_process_alive",
    # Job store
    "create_job",
    "update_job",
    "get_job",
    "list_jobs",
    "delete_job",
    "mark_job_completed",
    "mark_job_failed",
    "update_job_metrics",
    "get_running_jobs",
    "STATUS_PENDING",
    "STATUS_RUNNING",
    "STATUS_COMPLETED",
    "STATUS_FAILED",
    # Submodules (lightweight)
    "data_pipeline",
    "job_spec",
    "job_store",
    "presets",
    "unsloth_runner",
    "monitor",
    # Submodules (lazy-loaded)
    "auto_trainer",
    "exercise_manager",
    "learning_loop_integration",
    "persrm_data_generator",
    "persrm_data_pipeline",
    "persrm_full_finetune",
    "persrm_pytorch_trainer",
    "persrm_standalone_generator",
    "run_persrm_standalone",
]
