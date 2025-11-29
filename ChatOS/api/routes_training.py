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

from ChatOS.config.settings import settings


router = APIRouter(prefix="/api/training/unsloth", tags=["Training (Unsloth)"])


# =============================================================================
# Request/Response Models
# =============================================================================

class StartTrainingRequest(BaseModel):
    """Request to start a new training job."""
    model_name: Optional[str] = Field(
        None,
        description="Base model to fine-tune (default: Qwen2.5-7B-Instruct)"
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
    
    from ChatOS.training.auto_trainer import get_training_stats
    return get_training_stats()


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
    
    from ChatOS.training.job_store import list_jobs
    from ChatOS.training.monitor import refresh_all_running_jobs
    
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
    
    from ChatOS.training.job_store import get_job
    from ChatOS.training.monitor import (
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
    Start a new Unsloth training job.
    
    This will:
    1. Generate fresh training/eval datasets from ChatOS logs
    2. Create a job specification
    3. Spawn the Unsloth training process on Kali GPU
    4. Return the job ID for monitoring
    
    Returns:
        Job ID and initial job record
    """
    _check_training_enabled()
    
    from ChatOS.training.auto_trainer import start_training_job, TrainingError
    
    try:
        job_id, job = start_training_job(
            model_name=request.model_name,
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
                "base_model_name": job["base_model_name"],
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
    
    from ChatOS.training.job_store import get_job, mark_job_failed
    from ChatOS.training.unsloth_runner import stop_training_process
    
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
    
    from ChatOS.training.auto_trainer import can_start_training, get_training_stats
    
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
    
    from ChatOS.training.job_store import get_job
    from ChatOS.training.monitor import read_log_tail
    
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
    
    from ChatOS.training.job_store import list_jobs
    
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
    
    from ChatOS.training.job_store import get_job
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

