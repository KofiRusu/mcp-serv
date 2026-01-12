"""
job_store.py - CRUD operations for training job records.

Stores job metadata as JSON files for simplicity.
Location: ~/ChatOS-Memory/training_jobs/{job_id}.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from chatos_backend.config.settings import settings
from chatos_backend.training.job_spec import TrainingJobSpec


# Job status constants
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


def _get_job_path(job_id: str) -> Path:
    """Get the path to a job's JSON file."""
    return settings.training_jobs_dir / f"{job_id}.json"


def _load_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Load a job record from disk."""
    path = _get_job_path(job_id)
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _save_job(job: Dict[str, Any]) -> None:
    """Save a job record to disk."""
    path = _get_job_path(job["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(job, f, indent=2, default=str)


def create_job(
    job_spec: TrainingJobSpec,
    pid: int,
    config_path: Path,
    log_path: Path,
    dataset_stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a new job record.
    
    Args:
        job_spec: Training job specification
        pid: Process ID of the training process
        config_path: Path to the config YAML file
        log_path: Path to the log file
        dataset_stats: Optional dataset statistics
    
    Returns:
        The created job record
    """
    now = datetime.now().isoformat()
    
    def _spec_attr(name: str, default: Any = None) -> Any:
        return getattr(job_spec, name, default)
    
    job = {
        "id": job_spec.id,
        "status": STATUS_RUNNING,
        "pid": pid,
        "config_path": str(config_path),
        "log_path": str(log_path),
        "output_dir": job_spec.output_dir,
        "base_model_name": job_spec.base_model_name,
        "model_key": _spec_attr("model_key", job_spec.base_model_name),
        "dataset_train_path": job_spec.dataset_train_path,
        "dataset_eval_path": job_spec.dataset_eval_path,
        "description": job_spec.description,
        "created_at": now,
        "started_at": now,
        "finished_at": None,
        "latest_metrics": None,
        "error_snippet": None,
        # New versioning and preset fields (with backwards-compatible defaults)
        "preset_name": _spec_attr("preset_name", "BALANCED"),
        "dataset_version": _spec_attr("dataset_version", 1),
        "dataset_sample_count": _spec_attr("dataset_sample_count", 0),
        "dataset_stats": dataset_stats,
        "hyperparameters": {
            "learning_rate": _spec_attr("learning_rate"),
            "num_epochs": _spec_attr("num_epochs"),
            "max_steps": _spec_attr("max_steps"),
            "per_device_batch_size": _spec_attr("per_device_batch_size"),
            "gradient_accumulation_steps": _spec_attr("gradient_accumulation_steps"),
            "lora_r": _spec_attr("lora_r"),
            "lora_alpha": _spec_attr("lora_alpha"),
            "warmup_ratio": _spec_attr("warmup_ratio", 0.0),
            "weight_decay": _spec_attr("weight_decay", 0.0),
        },
        # Export info (filled in after training)
        "export_info": None,
    }
    
    _save_job(job)
    return job


def update_job(job_id: str, **fields) -> Optional[Dict[str, Any]]:
    """
    Update fields in a job record.
    
    Args:
        job_id: ID of the job to update
        **fields: Fields to update
    
    Returns:
        Updated job record, or None if job not found
    """
    job = _load_job(job_id)
    if job is None:
        return None
    
    for key, value in fields.items():
        if key in job:
            job[key] = value
    
    _save_job(job)
    return job


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a job record by ID.
    
    Args:
        job_id: ID of the job
    
    Returns:
        Job record, or None if not found
    """
    return _load_job(job_id)


def list_jobs(limit: int = 50, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all job records.
    
    Args:
        limit: Maximum number of jobs to return
        status_filter: Optional status to filter by
    
    Returns:
        List of job records, sorted by created_at descending
    """
    jobs_dir = settings.training_jobs_dir
    if not jobs_dir.exists():
        return []
    
    jobs = []
    for path in jobs_dir.glob("*.json"):
        try:
            with open(path, "r") as f:
                job = json.load(f)
                if status_filter is None or job.get("status") == status_filter:
                    jobs.append(job)
        except (json.JSONDecodeError, IOError):
            continue
    
    # Sort by created_at descending
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    
    return jobs[:limit]


def delete_job(job_id: str) -> bool:
    """
    Delete a job record.
    
    Args:
        job_id: ID of the job to delete
    
    Returns:
        True if deleted, False if not found
    """
    path = _get_job_path(job_id)
    if path.exists():
        path.unlink()
        return True
    return False


def mark_job_completed(job_id: str, metrics: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Mark a job as completed.
    
    Args:
        job_id: ID of the job
        metrics: Final metrics to store
    
    Returns:
        Updated job record
    """
    return update_job(
        job_id,
        status=STATUS_COMPLETED,
        finished_at=datetime.now().isoformat(),
        latest_metrics=metrics,
    )


def mark_job_failed(
    job_id: str,
    error_snippet: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Mark a job as failed.
    
    Args:
        job_id: ID of the job
        error_snippet: Error message or log snippet
    
    Returns:
        Updated job record
    """
    return update_job(
        job_id,
        status=STATUS_FAILED,
        finished_at=datetime.now().isoformat(),
        error_snippet=error_snippet,
    )


def update_job_metrics(job_id: str, metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update the latest metrics for a job.
    
    Args:
        job_id: ID of the job
        metrics: Latest metrics dict
    
    Returns:
        Updated job record
    """
    return update_job(job_id, latest_metrics=metrics)


def get_running_jobs() -> List[Dict[str, Any]]:
    """
    Get all jobs with 'running' status.
    
    Returns:
        List of running job records
    """
    return list_jobs(status_filter=STATUS_RUNNING)


def get_job_count_by_status() -> Dict[str, int]:
    """
    Get count of jobs by status.
    
    Returns:
        Dict mapping status to count
    """
    jobs = list_jobs(limit=1000)
    counts = {
        STATUS_PENDING: 0,
        STATUS_RUNNING: 0,
        STATUS_COMPLETED: 0,
        STATUS_FAILED: 0,
    }
    for job in jobs:
        status = job.get("status", STATUS_PENDING)
        if status in counts:
            counts[status] += 1
    return counts
