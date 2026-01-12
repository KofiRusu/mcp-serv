"""
routes_persrm_training.py - API routes for PersRM training integration.

Provides REST endpoints for:
- PersRM training job management (list, start, stop)
- PersRM training data statistics
- PersRM-specific presets
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from chatos_backend.config.settings import settings


router = APIRouter(prefix="/api/training/persrm", tags=["Training (PersRM)"])


# =============================================================================
# Request/Response Models
# =============================================================================

class StartPersRMTrainingRequest(BaseModel):
    """Request to start a new PersRM training job."""
    preset: Optional[str] = Field(
        None,
        description="Training preset: FAST, REASONING, or QUALITY (default: REASONING)"
    )
    model: Optional[str] = Field(
        None,
        description="Model to fine-tune: qwen2.5-7b-instruct, qwen2.5-coder-7b, mistral-7b-instruct"
    )
    description: Optional[str] = Field(
        None,
        description="Optional description for the job"
    )
    include_feedback: bool = Field(
        True,
        description="Include feedback-derived examples in training data"
    )
    force: bool = Field(
        False,
        description="Skip readiness checks and start training anyway"
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _check_training_enabled():
    """Check if training features are enabled."""
    if not settings.enable_training_features:
        raise HTTPException(
            status_code=403,
            detail="Training features are disabled. Enable in settings."
        )


# =============================================================================
# Routes
# =============================================================================

@router.get("/stats")
async def get_persrm_training_stats():
    """
    Get statistics about available PersRM training data.
    
    Returns:
        Statistics including reasoning examples, instruction examples, readiness status
    """
    _check_training_enabled()
    
    from chatos_backend.training.auto_trainer import get_training_stats
    return get_training_stats(training_type="persrm")


@router.get("/presets")
async def get_persrm_presets():
    """
    Get available PersRM training presets.
    
    Returns:
        Dict of preset configurations
    """
    from chatos_backend.training.presets import list_persrm_presets, DEFAULT_PERSRM_PRESET
    
    return {
        "presets": list_persrm_presets(),
        "default": DEFAULT_PERSRM_PRESET,
    }


@router.get("/models")
async def get_available_models():
    """
    Get available models for PersRM fine-tuning.
    
    Returns PersRM-specific models optimized for UI/UX reasoning and code generation:
    - Qwen 2.5 7B (Recommended) - Best overall reasoning
    - Phi-3 Mini 3.8B - Compact reasoning
    - DeepSeek Coder 6.7B - UI component generation
    - Qwen 2.5 Coder 7B - Code + explanation
    - Qwen 2.5 3B - Fast iterations
    - Llama 3.2 3B - Compact reasoning
    
    Returns:
        Dict of PersRM model configurations
    """
    from chatos_backend.training.presets import list_persrm_models, DEFAULT_PERSRM_MODEL
    
    return {
        "models": list_persrm_models(),
        "default": DEFAULT_PERSRM_MODEL,
    }


@router.get("/dataset-versions")
async def get_persrm_dataset_versions():
    """
    Get all available PersRM dataset versions.
    
    Returns:
        List of dataset versions with paths and stats
    """
    _check_training_enabled()
    
    from chatos_backend.training.persrm_data_pipeline import (
        list_persrm_dataset_versions,
        get_current_persrm_version,
    )
    
    return {
        "versions": list_persrm_dataset_versions(),
        "current_version": get_current_persrm_version(),
    }


@router.get("/jobs")
async def list_persrm_training_jobs(
    limit: int = 20,
    status: Optional[str] = None,
):
    """
    List PersRM training jobs.
    
    Args:
        limit: Maximum number of jobs to return
        status: Filter by status (pending, running, completed, failed)
    
    Returns:
        List of job summaries for PersRM training jobs
    """
    _check_training_enabled()
    
    from chatos_backend.training.job_store import list_jobs
    from chatos_backend.training.monitor import refresh_all_running_jobs
    
    # Refresh running jobs first
    refresh_all_running_jobs()
    
    # Get all jobs and filter for PersRM type
    jobs = list_jobs(limit=limit * 2, status_filter=status)
    persrm_jobs = [j for j in jobs if j.get("training_type") == "persrm" or 
                   j.get("dataset_stats", {}).get("training_type") == "persrm"]
    
    # Limit results
    persrm_jobs = persrm_jobs[:limit]
    
    return {
        "jobs": [
            {
                "id": j["id"],
                "status": j["status"],
                "training_type": "persrm",
                "base_model_name": j["base_model_name"],
                "created_at": j["created_at"],
                "started_at": j.get("started_at"),
                "finished_at": j.get("finished_at"),
                "description": j.get("description"),
                "latest_metrics": j.get("latest_metrics"),
            }
            for j in persrm_jobs
        ],
        "total": len(persrm_jobs),
    }


@router.get("/jobs/{job_id}")
async def get_persrm_training_job(job_id: str, include_metrics_history: bool = False):
    """
    Get detailed information about a PersRM training job.
    
    Args:
        job_id: ID of the job
        include_metrics_history: Include full metrics history (for charts)
    
    Returns:
        Full job record with optional metrics history
    """
    _check_training_enabled()
    
    from chatos_backend.training.job_store import get_job
    from chatos_backend.training.monitor import (
        refresh_job_status,
        get_training_metrics_summary,
    )
    
    # Refresh status first
    job = refresh_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    result = dict(job)
    result["training_type"] = "persrm"
    
    # Add metrics summary if requested
    if include_metrics_history and job.get("output_dir"):
        result["metrics_summary"] = get_training_metrics_summary(job["output_dir"])
    
    return result


@router.post("/start")
async def start_persrm_training(request: StartPersRMTrainingRequest):
    """
    Start a new PersRM training job with preset configuration.
    
    This will:
    1. Generate fresh versioned training/eval datasets from PersRM data
    2. Create a job specification from preset
    3. Spawn the Unsloth training process on Kali GPU
    4. Return the job ID for monitoring
    
    Presets:
    - FAST: Quick iteration (1 epoch)
    - REASONING: Optimized for UI/UX reasoning (3 epochs, low LR) [default]
    - QUALITY: Best results (5 epochs, very low LR)
    
    Returns:
        Job ID and initial job record
    """
    _check_training_enabled()
    
    from chatos_backend.training.auto_trainer import start_training_job, TrainingError
    
    try:
        job_id, job = start_training_job(
            training_type="persrm",
            preset_name=request.preset,
            model_key=request.model,
            description=request.description,
            force=request.force,
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "job": {
                "id": job["id"],
                "status": job["status"],
                "training_type": "persrm",
                "preset_name": job.get("preset_name"),
                "model_key": job.get("model_key"),
                "base_model_name": job["base_model_name"],
                "dataset_version": job.get("dataset_version"),
                "dataset_sample_count": job.get("dataset_sample_count"),
                "created_at": job["created_at"],
            }
        }
    except TrainingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start PersRM training: {e}")


@router.post("/stop/{job_id}")
async def stop_persrm_training_job(job_id: str):
    """
    Stop a running PersRM training job.
    
    Sends SIGTERM to the training process for graceful shutdown.
    
    Args:
        job_id: ID of the job to stop
    """
    _check_training_enabled()
    
    from chatos_backend.training.job_store import get_job, mark_job_failed
    from chatos_backend.training.unsloth_runner import stop_training_process
    
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    if job["status"] != "running":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not running (status: {job['status']})"
        )
    
    pid = job.get("pid", 0)
    if pid <= 0:
        raise HTTPException(status_code=400, detail="No valid PID for job")
    
    stopped = stop_training_process(pid)
    
    if stopped:
        mark_job_failed(job_id, error_snippet="Stopped by user request")
        return {"success": True, "message": f"Stop signal sent to job {job_id}"}
    else:
        return {"success": False, "message": "Failed to send stop signal"}


@router.get("/can-train")
async def check_can_train_persrm():
    """
    Check if PersRM training can be started.
    
    Returns:
        Whether training can start and the reason
    """
    _check_training_enabled()
    
    from chatos_backend.training.auto_trainer import can_start_training, get_training_stats
    
    can_start, reason = can_start_training(training_type="persrm")
    stats = get_training_stats(training_type="persrm")
    
    return {
        "can_train": can_start,
        "reason": reason,
        "stats": stats,
    }


@router.get("/jobs/{job_id}/logs")
async def get_persrm_job_logs(job_id: str, lines: int = 100):
    """
    Get the tail of a PersRM job's log file.
    
    Args:
        job_id: ID of the job
        lines: Number of lines to return (max 500)
    
    Returns:
        Log lines
    """
    _check_training_enabled()
    
    from chatos_backend.training.job_store import get_job
    from chatos_backend.training.monitor import read_log_tail
    
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    log_path = job.get("log_path")
    if not log_path:
        return {"lines": [], "message": "No log file available"}
    
    lines = min(lines, 500)  # Cap at 500 lines
    log_lines = read_log_tail(log_path, lines=lines)
    
    return {"lines": log_lines, "total_lines": len(log_lines)}


@router.get("/completed")
async def get_completed_persrm_jobs():
    """
    Get all completed PersRM training jobs.
    
    Returns:
        List of completed jobs that can be exported
    """
    _check_training_enabled()
    
    from chatos_backend.training.job_store import list_jobs
    
    jobs = list_jobs(limit=100, status_filter="completed")
    
    # Filter for PersRM jobs
    persrm_jobs = [j for j in jobs if j.get("training_type") == "persrm" or 
                   j.get("dataset_stats", {}).get("training_type") == "persrm"]
    
    return {
        "jobs": [
            {
                "id": j["id"],
                "training_type": "persrm",
                "base_model_name": j["base_model_name"],
                "created_at": j["created_at"],
                "finished_at": j.get("finished_at"),
                "output_dir": j.get("output_dir"),
                "description": j.get("description"),
                "latest_metrics": j.get("latest_metrics"),
            }
            for j in persrm_jobs
        ]
    }


@router.post("/export-for-chatos/{job_id}")
async def export_persrm_for_chatos(job_id: str):
    """
    Export a completed PersRM training job for use in ChatOS.
    
    This prepares the model adapter for local inference by:
    1. Copying adapter files to ~/ChatOS-Memory/models/{job_id}/
    2. Creating model_info.json with full metadata
    3. Generating a Modelfile template for Ollama
    
    Args:
        job_id: ID of the completed training job
    
    Returns:
        Export status with paths and display name
    """
    _check_training_enabled()
    
    from chatos_backend.inference.model_loader import export_model_for_ollama
    
    try:
        result = export_model_for_ollama(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {e}")


# =============================================================================
# Data Generation Endpoints
# =============================================================================

class GenerateDataRequest(BaseModel):
    """Request to generate synthetic PersRM training data."""
    categories: Optional[List[str]] = Field(
        None,
        description="Categories to generate: component_analysis, layout_reasoning, code_generation, accessibility, design_tokens. None for all."
    )
    count_per_category: Optional[int] = Field(
        None,
        description="Number of examples per category (uses defaults if not specified)"
    )
    model: str = Field(
        "qwen2.5:7b",
        description="Ollama model to use for generation"
    )


@router.get("/generate-data/categories")
async def get_generation_categories():
    """
    Get available categories for synthetic data generation.
    
    Returns:
        List of categories with descriptions and target counts
    """
    from chatos_backend.training.persrm_data_generator import get_available_categories
    
    return {
        "categories": get_available_categories(),
    }


@router.post("/generate-data")
async def generate_synthetic_data(request: GenerateDataRequest):
    """
    Generate synthetic PersRM training data.
    
    This uses an Ollama model to generate UI/UX reasoning examples
    across multiple categories:
    - Component Analysis (200 examples)
    - Layout Reasoning (200 examples)
    - Code Generation (300 examples)
    - Accessibility (150 examples)
    - Design Tokens (150 examples)
    
    Total: 1000+ examples for effective fine-tuning.
    
    **Note**: This is a long-running operation. For large datasets,
    consider running the generator CLI directly.
    
    Returns:
        Generation statistics and output file paths
    """
    _check_training_enabled()
    
    from chatos_backend.training.persrm_data_generator import generate_training_data
    import asyncio
    
    try:
        total_count, paths = await generate_training_data(
            categories=request.categories,
            count_per_category=request.count_per_category,
            model=request.model,
        )
        
        return {
            "success": True,
            "total_generated": total_count,
            "output_files": {k: str(v) for k, v in paths.items()},
            "message": f"Generated {total_count} training examples",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Data generation failed: {e}"
        )


@router.get("/generate-data/status")
async def get_generation_status():
    """
    Get the current status of data generation.
    
    Returns:
        Whether generation is running, progress if available
    """
    # For now, just return that no generation is in progress
    # In a full implementation, this would track background tasks
    return {
        "in_progress": False,
        "message": "No data generation in progress",
    }

