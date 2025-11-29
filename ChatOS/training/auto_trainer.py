"""
auto_trainer.py - High-level training orchestration for ChatOS.

This module provides the main interface for triggering training jobs,
including data collection, dataset generation, and job spawning.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ChatOS.config.settings import settings
from ChatOS.training.data_pipeline import (
    generate_training_dataset,
    load_raw_conversations,
    filter_for_training,
    DatasetStats,
)
from ChatOS.training.job_spec import TrainingJobSpec
from ChatOS.training.job_store import (
    create_job,
    get_job,
    list_jobs,
    get_running_jobs,
    STATUS_RUNNING,
)
from ChatOS.training.unsloth_runner import write_temp_config, start_training_process
from ChatOS.training.presets import (
    get_preset,
    get_model_config,
    list_presets,
    list_models,
    DEFAULT_PRESET,
    DEFAULT_MODEL,
)


logger = logging.getLogger(__name__)


class TrainingError(Exception):
    """Exception raised when training operations fail."""
    pass


def get_training_stats() -> Dict[str, Any]:
    """
    Get statistics about available training data.
    
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
        logger.error(f"Error getting training stats: {e}")
        return {
            "error": str(e),
            "total_conversations": 0,
            "training_examples": 0,
            "ready_to_train": False,
            "training_enabled": settings.enable_training_features,
        }


def start_training_job(
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
        preset_name: Training preset (FAST, BALANCED, QUALITY). Default: BALANCED
        model_key: Model to fine-tune (qwen2.5-7b-instruct, mistral-7b-instruct, etc.)
        description: Optional job description
        min_score: Minimum feedback score for training examples
        force: Skip readiness checks
    
    Returns:
        Tuple of (job_id, job_record)
    
    Raises:
        TrainingError: If training cannot be started
    """
    # Use defaults if not specified
    preset_name = preset_name or DEFAULT_PRESET
    model_key = model_key or DEFAULT_MODEL
    
    # Validate preset and model
    try:
        preset = get_preset(preset_name)
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
        stats = get_training_stats()
        if not stats.get("ready_to_train", False):
            raise TrainingError(
                f"Not ready to train. Have {stats.get('training_examples', 0)} examples, "
                f"need {settings.min_samples_for_training}. "
                f"Quality ratio: {stats.get('current_quality_ratio', 0):.2f}"
            )
    
    # Step 1: Generate fresh versioned datasets
    logger.info("Generating training datasets...")
    try:
        dataset_stats = generate_training_dataset(
            min_score=min_score,
            include_unrated=True,
            eval_ratio=0.1,
            use_versioning=True,
        )
    except Exception as e:
        raise TrainingError(f"Failed to generate datasets: {e}")
    
    if dataset_stats.total_examples < 1:
        raise TrainingError("No training examples generated")
    
    # Step 2: Create job specification from preset
    job_spec = TrainingJobSpec.from_preset(
        preset_name=preset_name,
        model_key=model_key,
        train_path=dataset_stats.train_path,
        eval_path=dataset_stats.eval_path,
        dataset_version=dataset_stats.version,
        dataset_sample_count=dataset_stats.train_count,
        description=description or f"ChatOS {preset_name} training - v{dataset_stats.version} - {dataset_stats.train_count} samples",
    )
    
    logger.info(f"Created job spec: {job_spec.id} (preset={preset_name}, model={model_key}, dataset_v{dataset_stats.version})")
    
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
    dataset_stats_dict = {
        "version": dataset_stats.version,
        "train_count": dataset_stats.train_count,
        "eval_count": dataset_stats.eval_count,
        "total_conversations": dataset_stats.total_conversations,
        "positive_examples": dataset_stats.positive_examples,
        "neutral_examples": dataset_stats.neutral_examples,
        "negative_excluded": dataset_stats.negative_excluded,
        "created_at": dataset_stats.created_at,
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


def can_start_training() -> Tuple[bool, str]:
    """
    Check if training can be started.
    
    Returns:
        Tuple of (can_start, reason)
    """
    if not settings.enable_training_features:
        return False, "Training features are disabled"
    
    running = get_running_jobs()
    if running:
        return False, f"Job already running: {running[0]['id']}"
    
    stats = get_training_stats()
    if not stats.get("ready_to_train", False):
        examples = stats.get("training_examples", 0)
        required = settings.min_samples_for_training
        return False, f"Need more data: {examples}/{required} examples"
    
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

