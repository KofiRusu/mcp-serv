"""
ChatOS Training Module

This module provides integration between ChatOS and Unsloth for
fine-tuning local LLMs on conversation data.

Components:
- data_pipeline: Convert ChatOS logs to Unsloth training format
- job_spec: Training job specifications
- unsloth_runner: Spawn and manage Unsloth training processes
- job_store: CRUD operations for training jobs
- monitor: Read training metrics and status
- auto_trainer: High-level training orchestration
"""

from .data_pipeline import (
    load_raw_conversations,
    filter_for_training,
    to_unsloth_jsonl,
    generate_training_dataset,
)

from .job_spec import TrainingJobSpec

from .unsloth_runner import (
    write_temp_config,
    start_training_process,
    stop_training_process,
    is_process_alive,
)

from .job_store import (
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

__all__ = [
    # Data pipeline
    "load_raw_conversations",
    "filter_for_training",
    "to_unsloth_jsonl",
    "generate_training_dataset",
    # Job spec
    "TrainingJobSpec",
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
]
