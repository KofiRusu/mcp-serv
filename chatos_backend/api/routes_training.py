"""
routes_training.py - API routes for Unsloth training integration.

Provides REST endpoints for:
- Training job management (list, start, stop)
- Job status and metrics
- Export to Ollama/GGUF
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from chatos_backend.config.settings import settings


router = APIRouter(prefix="/api/training/unsloth", tags=["Training (Unsloth)"])


# =============================================================================
# Request/Response Models
# =============================================================================

class StartTrainingRequest(BaseModel):
    """Request to start a new training job."""
    preset: Optional[str] = Field(
        None,
        description="Training preset: FAST, BALANCED, or QUALITY (default: BALANCED)"
    )
    model: Optional[str] = Field(
        None,
        description="Model to fine-tune: qwen2.5-7b-instruct, qwen2.5-coder-7b, mistral-7b-instruct"
    )
    description: Optional[str] = Field(
        None,
        description="Optional description for the job"
    )
    min_score: int = Field(
        0,
        description="Minimum feedback score for training examples (-1, 0, or 1)"
    )
    force: bool = Field(
        False,
        description="Skip readiness checks and start training anyway"
    )


class ExportRequest(BaseModel):
    """Request to export a trained model."""
    job_id: str = Field(..., description="ID of the completed training job")
    format: str = Field("gguf", description="Export format: 'gguf' or 'lora'")
    generate_modelfile: bool = Field(True, description="Generate Ollama Modelfile")


class StopJobRequest(BaseModel):
    """Request to stop a running training job."""
    force: bool = Field(False, description="Force kill the process")


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
async def get_training_stats():
    """
    Get statistics about available training data.
    
    Returns:
        Statistics including total conversations, examples, readiness status
    """
    _check_training_enabled()
    
    from chatos_backend.training.auto_trainer import get_training_stats
    return get_training_stats()


@router.get("/presets")
async def get_presets():
    """
    Get available training presets.
    
    Returns:
        Dict of preset configurations
    """
    from chatos_backend.training.presets import list_presets, DEFAULT_PRESET
    
    return {
        "presets": list_presets(),
        "default": DEFAULT_PRESET,
    }


@router.get("/models")
async def get_available_models():
    """
    Get available models for fine-tuning.
    
    Returns:
        Dict of model configurations
    """
    from chatos_backend.training.presets import list_models, DEFAULT_MODEL
    
    return {
        "models": list_models(),
        "default": DEFAULT_MODEL,
    }


@router.get("/dataset-versions")
async def get_dataset_versions():
    """
    Get all available dataset versions.
    
    Returns:
        List of dataset versions with paths and stats
    """
    _check_training_enabled()
    
    from chatos_backend.training.data_pipeline import list_dataset_versions, get_current_dataset_version
    
    return {
        "versions": list_dataset_versions(),
        "current_version": get_current_dataset_version(),
    }


@router.get("/jobs")
async def list_training_jobs(
    limit: int = 20,
    status: Optional[str] = None,
):
    """
    List training jobs.
    
    Args:
        limit: Maximum number of jobs to return
        status: Filter by status (pending, running, completed, failed)
    
    Returns:
        List of job summaries
    """
    _check_training_enabled()
    
    from chatos_backend.training.job_store import list_jobs
    from chatos_backend.training.monitor import refresh_all_running_jobs
    
    # Refresh running jobs first
    refresh_all_running_jobs()
    
    jobs = list_jobs(limit=limit, status_filter=status)
    
    # Return summaries
    return {
        "jobs": [
            {
                "id": j["id"],
                "status": j["status"],
                "base_model_name": j["base_model_name"],
                "created_at": j["created_at"],
                "started_at": j.get("started_at"),
                "finished_at": j.get("finished_at"),
                "description": j.get("description"),
                "latest_metrics": j.get("latest_metrics"),
            }
            for j in jobs
        ],
        "total": len(jobs),
    }


@router.get("/jobs/{job_id}")
async def get_training_job(job_id: str, include_metrics_history: bool = False):
    """
    Get detailed information about a training job.
    
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
    
    # Add metrics summary if requested
    if include_metrics_history and job.get("output_dir"):
        result["metrics_summary"] = get_training_metrics_summary(job["output_dir"])
    
    return result


@router.post("/start")
async def start_training(request: StartTrainingRequest):
    """
    Start a new Unsloth training job with preset configuration.
    
    This will:
    1. Generate fresh versioned training/eval datasets from ChatOS logs
    2. Create a job specification from preset
    3. Spawn the Unsloth training process on Kali GPU
    4. Return the job ID for monitoring
    
    Presets:
    - FAST: Quick iteration (1 epoch, low LR)
    - BALANCED: Good balance (2 epochs, medium LR)  [default]
    - QUALITY: Best results (3 epochs, low LR)
    
    Models:
    - qwen2.5-7b-instruct (default)
    - qwen2.5-coder-7b
    - mistral-7b-instruct
    
    Returns:
        Job ID and initial job record
    """
    _check_training_enabled()
    
    from chatos_backend.training.auto_trainer import start_training_job, TrainingError
    
    try:
        job_id, job = start_training_job(
            preset_name=request.preset,
            model_key=request.model,
            description=request.description,
            min_score=request.min_score,
            force=request.force,
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "job": {
                "id": job["id"],
                "status": job["status"],
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
        raise HTTPException(status_code=500, detail=f"Failed to start training: {e}")


@router.post("/stop/{job_id}")
async def stop_training_job(job_id: str, request: StopJobRequest = None):
    """
    Stop a running training job.
    
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
async def check_can_train():
    """
    Check if training can be started.
    
    Returns:
        Whether training can start and the reason
    """
    _check_training_enabled()
    
    from chatos_backend.training.auto_trainer import can_start_training, get_training_stats
    
    can_start, reason = can_start_training()
    stats = get_training_stats()
    
    return {
        "can_train": can_start,
        "reason": reason,
        "stats": stats,
    }


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str, lines: int = 100):
    """
    Get the tail of a job's log file.
    
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
async def get_completed_jobs():
    """
    Get all completed training jobs.
    
    Returns:
        List of completed jobs that can be exported
    """
    _check_training_enabled()
    
    from chatos_backend.training.job_store import list_jobs
    
    jobs = list_jobs(limit=100, status_filter="completed")
    
    return {
        "jobs": [
            {
                "id": j["id"],
                "base_model_name": j["base_model_name"],
                "created_at": j["created_at"],
                "finished_at": j.get("finished_at"),
                "output_dir": j.get("output_dir"),
                "description": j.get("description"),
                "latest_metrics": j.get("latest_metrics"),
            }
            for j in jobs
        ]
    }


@router.post("/export")
async def export_model(request: ExportRequest):
    """
    Export a trained model to GGUF/Ollama format.
    
    This will spawn an export process on Kali GPU.
    
    Args:
        request: Export configuration
    
    Returns:
        Export status and output paths
    """
    _check_training_enabled()
    
    from chatos_backend.training.job_store import get_job
    from pathlib import Path
    import subprocess
    import os
    
    job = get_job(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {request.job_id}")
    
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed (status: {job['status']})"
        )
    
    output_dir = job.get("output_dir")
    if not output_dir or not Path(output_dir).exists():
        raise HTTPException(status_code=400, detail="Training output not found")
    
    # Check for export script
    export_script = settings.unsloth_pipelines_dir / "export_lora_to_ollama_or_gguf.py"
    if not export_script.exists():
        raise HTTPException(
            status_code=500,
            detail="Export script not found. Please run Phase 5 setup."
        )
    
    # Build export command
    # ⚠️ RUNS ON KALI GPU ⚠️
    export_output_dir = settings.models_dir / request.job_id
    export_output_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = (
        f'source {settings.unsloth_venv_path}/bin/activate && '
        f'cd {settings.unsloth_pipelines_dir} && '
        f'python export_lora_to_ollama_or_gguf.py '
        f'--adapter_path {output_dir} '
        f'--output_dir {export_output_dir} '
        f'--export_format {request.format}'
    )
    
    if request.generate_modelfile:
        cmd += ' --generate_modelfile'
    
    try:
        # ⚠️ RUNS ON KALI GPU ⚠️
        result = subprocess.run(
            ["bash", "-lc", cmd],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min timeout for export
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Export failed: {result.stderr[-500:]}"
            )
        
        return {
            "success": True,
            "job_id": request.job_id,
            "output_dir": str(export_output_dir),
            "format": request.format,
            "message": "Export completed successfully",
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Export timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {e}")


@router.post("/export-for-chatos/{job_id}")
async def export_for_chatos(job_id: str):
    """
    Export a completed training job for use in ChatOS.
    
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


@router.get("/fine-tuned-models")
async def list_fine_tuned_models():
    """
    List all fine-tuned models available in ChatOS.
    
    Scans ~/ChatOS-Memory/models/ for exported model adapters.
    
    Returns:
        List of fine-tuned model info
    """
    from chatos_backend.inference.model_loader import get_fine_tuned_models
    
    models = get_fine_tuned_models()
    
    return {
        "models": models,
        "total": len(models),
    }

