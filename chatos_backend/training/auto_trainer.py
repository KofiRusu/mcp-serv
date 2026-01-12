"""
auto_trainer.py - High-level training orchestration for ChatOS and PersRM.

This module provides the main interface for triggering training jobs,
including data collection, dataset generation, and job spawning.

Supports two training types:
- CHATOS: General chat/conversation fine-tuning from ChatOS logs
- PERSRM: UI/UX reasoning fine-tuning from PersRM data
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from chatos_backend.config.settings import settings
from chatos_backend.training.data_pipeline import (
    generate_training_dataset,
    load_raw_conversations,
    filter_for_training,
    DatasetStats,
)
from chatos_backend.training.job_spec import TrainingJobSpec
from chatos_backend.training.job_store import (
    create_job,
    get_job,
    list_jobs,
    get_running_jobs,
    STATUS_RUNNING,
)
from chatos_backend.training.unsloth_runner import write_temp_config, start_training_process
from chatos_backend.training.presets import (
    get_preset,
    get_model_config,
    get_persrm_model_config,
    list_presets,
    list_models,
    DEFAULT_PRESET,
    DEFAULT_MODEL,
    DEFAULT_PERSRM_MODEL,
    TrainingType,
    get_preset_for_type,
    get_default_preset_for_type,
    list_presets_for_type,
)


logger = logging.getLogger(__name__)


class TrainingError(Exception):
    """Exception raised when training operations fail."""
    pass


def get_training_stats(training_type: str = "chatos") -> Dict[str, Any]:
    """
    Get statistics about available training data.
    
    Args:
        training_type: "chatos" or "persrm"
    
    Returns:
        Dict with stats about data and readiness for training
    """
    if training_type == TrainingType.PERSRM or training_type == "persrm":
        return get_persrm_training_stats()
    
    return get_chatos_training_stats()


def get_chatos_training_stats() -> Dict[str, Any]:
    """
    Get statistics about available ChatOS training data.
    
    Returns:
        Dict with stats about conversations and readiness for training
    """
    try:
        conversations = load_raw_conversations()
        examples, stats = filter_for_training(
            conversations,
            min_score=0,
            include_unrated=True,
        )
        
        # Check if we have enough data
        min_samples = settings.min_samples_for_training
        positive_count = stats.positive_examples
        total_count = len(examples)
        
        # Calculate quality ratio
        quality_ratio = positive_count / total_count if total_count > 0 else 0.0
        
        ready_to_train = (
            total_count >= min_samples and
            quality_ratio >= settings.min_quality_ratio
        )
        
        return {
            "training_type": "chatos",
            "total_conversations": stats.total_conversations,
            "filtered_conversations": stats.filtered_conversations,
            "training_examples": total_count,
            "positive_feedback": positive_count,
            "neutral_unrated": stats.neutral_examples,
            "negative_excluded": stats.negative_excluded,
            "min_samples_required": min_samples,
            "min_quality_ratio": settings.min_quality_ratio,
            "current_quality_ratio": quality_ratio,
            "ready_to_train": ready_to_train,
            "training_enabled": settings.enable_training_features,
        }
    except Exception as e:
        logger.error(f"Error getting ChatOS training stats: {e}")
        return {
            "training_type": "chatos",
            "error": str(e),
            "total_conversations": 0,
            "training_examples": 0,
            "ready_to_train": False,
            "training_enabled": settings.enable_training_features,
        }


def get_persrm_training_stats() -> Dict[str, Any]:
    """
    Get statistics about available PersRM training data.
    
    Returns:
        Dict with stats about reasoning examples and readiness
    """
    try:
        from chatos_backend.training.persrm_data_pipeline import get_persrm_training_stats as _get_stats
        stats = _get_stats()
        stats["training_type"] = "persrm"
        return stats
    except Exception as e:
        logger.error(f"Error getting PersRM training stats: {e}")
        return {
            "training_type": "persrm",
            "error": str(e),
            "total_examples": 0,
            "ready_to_train": False,
            "training_enabled": settings.enable_training_features,
        }


def start_training_job(
    training_type: str = "chatos",
    preset_name: Optional[str] = None,
    model_key: Optional[str] = None,
    description: Optional[str] = None,
    min_score: int = 0,
    force: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """
    Start a new training job with preset configuration.
    
    This function:
    1. Checks if training is enabled and ready
    2. Generates fresh versioned training/eval datasets
    3. Creates a job specification from preset
    4. Writes a config file
    5. Spawns the Unsloth training process
    6. Saves the job record with full metadata
    
    Args:
        training_type: "chatos" for chat training, "persrm" for reasoning training
        preset_name: Training preset. Default varies by type.
        model_key: Model to fine-tune (qwen2.5-7b-instruct, mistral-7b-instruct, etc.)
        description: Optional job description
        min_score: Minimum feedback score for training examples (ChatOS only)
        force: Skip readiness checks
    
    Returns:
        Tuple of (job_id, job_record)
    
    Raises:
        TrainingError: If training cannot be started
    """
    # Normalize training type
    is_persrm = training_type == TrainingType.PERSRM or training_type == "persrm"
    
    # Use defaults if not specified - use appropriate default model for training type
    preset_name = preset_name or get_default_preset_for_type(training_type)
    model_key = model_key or (DEFAULT_PERSRM_MODEL if is_persrm else DEFAULT_MODEL)
    
    # Validate preset and model - use appropriate model config for training type
    try:
        preset = get_preset_for_type(training_type, preset_name)
        if is_persrm:
            model_config = get_persrm_model_config(model_key)
        else:
            model_config = get_model_config(model_key)
    except ValueError as e:
        raise TrainingError(str(e))
    
    # Check if training is enabled
    if not settings.enable_training_features:
        raise TrainingError("Training features are disabled in settings")
    
    # Check for already running jobs
    running = get_running_jobs()
    if running and not force:
        raise TrainingError(
            f"Training job already running: {running[0]['id']}. "
            "Use force=True to start another job."
        )
    
    # Check if we have enough data (unless forcing)
    if not force:
        stats = get_training_stats(training_type)
        if not stats.get("ready_to_train", False):
            if is_persrm:
                raise TrainingError(
                    f"Not ready to train PersRM. Have {stats.get('total_examples', 0)} examples, "
                    f"need {stats.get('min_samples_required', 10)}."
                )
            else:
                raise TrainingError(
                    f"Not ready to train. Have {stats.get('training_examples', 0)} examples, "
                    f"need {settings.min_samples_for_training}. "
                    f"Quality ratio: {stats.get('current_quality_ratio', 0):.2f}"
                )
    
    # Step 1: Generate fresh versioned datasets
    logger.info(f"Generating {training_type} training datasets...")
    try:
        if is_persrm:
            from chatos_backend.training.persrm_data_pipeline import generate_persrm_dataset
            dataset_stats = generate_persrm_dataset(
                include_feedback=True,
                eval_ratio=0.1,
                use_versioning=True,
            )
        else:
            dataset_stats = generate_training_dataset(
                min_score=min_score,
                include_unrated=True,
                eval_ratio=0.1,
                use_versioning=True,
            )
    except Exception as e:
        raise TrainingError(f"Failed to generate datasets: {e}")
    
    example_count = getattr(dataset_stats, 'total_examples', 0) or getattr(dataset_stats, 'train_count', 0)
    if example_count < 1:
        raise TrainingError("No training examples generated")
    
    # Create description
    type_label = "PersRM" if is_persrm else "ChatOS"
    default_description = f"{type_label} {preset_name} training - v{dataset_stats.version} - {dataset_stats.train_count} samples"
    
    # Step 2: Create job specification from preset
    job_spec = TrainingJobSpec.from_preset(
        preset_name=preset_name,
        model_key=model_key,
        train_path=dataset_stats.train_path,
        eval_path=dataset_stats.eval_path,
        dataset_version=dataset_stats.version,
        dataset_sample_count=dataset_stats.train_count,
        description=description or default_description,
        training_type=training_type,  # Pass training type to job spec
    )
    
    logger.info(f"Created job spec: {job_spec.id} (type={training_type}, preset={preset_name}, model={model_key}, dataset_v{dataset_stats.version})")
    
    # Step 3: Write temporary config
    try:
        config_path = write_temp_config(job_spec)
    except Exception as e:
        raise TrainingError(f"Failed to write config: {e}")
    
    logger.info(f"Wrote config to: {config_path}")
    
    # Step 4: Start training process
    # ⚠️ RUNS ON KALI GPU ⚠️
    try:
        pid, log_path = start_training_process(job_spec, config_path)
    except Exception as e:
        raise TrainingError(f"Failed to start training process: {e}")
    
    logger.info(f"Started training process with PID: {pid}")
    
    # Step 5: Save job record with full dataset stats
    if is_persrm:
        dataset_stats_dict = {
            "version": dataset_stats.version,
            "train_count": dataset_stats.train_count,
            "eval_count": dataset_stats.eval_count,
            "total_examples": dataset_stats.total_examples,
            "reasoning_examples": dataset_stats.reasoning_examples,
            "instruction_examples": dataset_stats.instruction_examples,
            "feedback_examples": dataset_stats.feedback_examples,
            "created_at": dataset_stats.created_at,
            "training_type": "persrm",
        }
    else:
        dataset_stats_dict = {
            "version": dataset_stats.version,
            "train_count": dataset_stats.train_count,
            "eval_count": dataset_stats.eval_count,
            "total_conversations": dataset_stats.total_conversations,
            "positive_examples": dataset_stats.positive_examples,
            "neutral_examples": dataset_stats.neutral_examples,
            "negative_excluded": dataset_stats.negative_excluded,
            "created_at": dataset_stats.created_at,
            "training_type": "chatos",
        }
    
    job = create_job(
        job_spec=job_spec,
        pid=pid,
        config_path=config_path,
        log_path=log_path,
        dataset_stats=dataset_stats_dict,
    )
    
    logger.info(f"Training job created: {job['id']}")
    
    return job["id"], job


def get_available_presets() -> Dict[str, Any]:
    """Get all available training presets."""
    return list_presets()


def get_available_models() -> Dict[str, Any]:
    """Get all available models for fine-tuning."""
    return list_models()


def can_start_training(training_type: str = "chatos") -> Tuple[bool, str]:
    """
    Check if training can be started.
    
    Args:
        training_type: "chatos" or "persrm"
    
    Returns:
        Tuple of (can_start, reason)
    """
    if not settings.enable_training_features:
        return False, "Training features are disabled"
    
    running = get_running_jobs()
    if running:
        return False, f"Job already running: {running[0]['id']}"
    
    stats = get_training_stats(training_type)
    if not stats.get("ready_to_train", False):
        is_persrm = training_type == TrainingType.PERSRM or training_type == "persrm"
        if is_persrm:
            examples = stats.get("total_examples", 0)
            required = stats.get("min_samples_required", 10)
            if examples < required:
                return False, f"Need more data: {examples}/{required} examples"
            return False, "Ready to train (force start available)"
        else:
            examples = stats.get("training_examples", 0)
            required = settings.min_samples_for_training
            quality_ratio = stats.get("current_quality_ratio", 0)
            min_quality = stats.get("min_quality_ratio", settings.min_quality_ratio)
            
            if examples < required:
                return False, f"Need more data: {examples}/{required} examples"
            elif quality_ratio < min_quality:
                return False, f"Quality ratio too low: {quality_ratio*100:.1f}% < {min_quality*100:.0f}% (use force start)"
            return False, "Not ready (use force start)"
    
    return True, "Ready to train"


def get_latest_completed_job() -> Optional[Dict[str, Any]]:
    """
    Get the most recently completed training job.
    
    Returns:
        Job record or None
    """
    jobs = list_jobs(limit=100)
    for job in jobs:
        if job.get("status") == "completed":
            return job
    return None


def get_job_summary(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a summary of a training job.
    
    Args:
        job_id: Job ID
    
    Returns:
        Summary dict or None if job not found
    """
    job = get_job(job_id)
    if not job:
        return None
    
    return {
        "id": job["id"],
        "status": job["status"],
        "base_model_name": job["base_model_name"],
        "created_at": job["created_at"],
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "description": job.get("description"),
        "latest_metrics": job.get("latest_metrics"),
        "error_snippet": job.get("error_snippet"),
    }
