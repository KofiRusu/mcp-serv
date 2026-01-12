"""
monitor.py - Training job monitoring for ChatOS.

This module provides functions to:
- Check if training processes are alive
- Read latest metrics from training output
- Refresh job status based on process state and metrics
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from chatos_backend.config.settings import settings
from chatos_backend.training.job_store import (
    get_job,
    update_job,
    mark_job_completed,
    mark_job_failed,
    STATUS_RUNNING,
    STATUS_COMPLETED,
    STATUS_FAILED,
)


def is_process_alive(pid: int) -> bool:
    """
    Check if a process is still running.
    
    Args:
        pid: Process ID to check
    
    Returns:
        True if process is alive, False otherwise
    """
    if pid <= 0:
        return False
    
    try:
        # Signal 0 doesn't kill but checks if process exists
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it
        return True
    except Exception:
        return False


def read_latest_metrics(output_dir: str) -> Optional[Dict[str, Any]]:
    """
    Read the latest metrics from a training job's output directory.
    
    Efficiently reads only the last line of the metrics.jsonl file
    to avoid loading the entire file for large logs.
    
    Args:
        output_dir: Path to training output directory
    
    Returns:
        Latest metrics dict, or None if no metrics available
    """
    metrics_path = Path(output_dir) / "metrics.jsonl"
    
    if not metrics_path.exists():
        return None
    
    try:
        # Read last line efficiently
        with open(metrics_path, "rb") as f:
            # Seek to end
            f.seek(0, 2)
            file_size = f.tell()
            
            if file_size == 0:
                return None
            
            # Read backwards to find last newline
            pos = file_size - 1
            while pos > 0:
                f.seek(pos)
                char = f.read(1)
                if char == b'\n' and pos != file_size - 1:
                    break
                pos -= 1
            
            # Read the last line
            if pos > 0:
                f.seek(pos + 1)
            else:
                f.seek(0)
            
            last_line = f.read().decode('utf-8').strip()
            
            if last_line:
                return json.loads(last_line)
    except (IOError, json.JSONDecodeError) as e:
        return None
    
    return None


def read_all_metrics(output_dir: str) -> List[Dict[str, Any]]:
    """
    Read all metrics from a training job's metrics file.
    
    Args:
        output_dir: Path to training output directory
    
    Returns:
        List of all metrics entries
    """
    metrics_path = Path(output_dir) / "metrics.jsonl"
    
    if not metrics_path.exists():
        return []
    
    metrics = []
    try:
        with open(metrics_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        metrics.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except IOError:
        return []
    
    return metrics


def get_training_metrics_summary(output_dir: str) -> Dict[str, Any]:
    """
    Get a summary of training metrics.
    
    Args:
        output_dir: Path to training output directory
    
    Returns:
        Summary dict with loss curves and key metrics
    """
    metrics = read_all_metrics(output_dir)
    
    if not metrics:
        return {"has_metrics": False}
    
    # Extract loss values
    train_losses = []
    eval_losses = []
    steps = []
    
    for m in metrics:
        if m.get("event"):  # Skip event entries (job_started, job_finished)
            continue
        
        step = m.get("step")
        if step is not None and step >= 0:
            steps.append(step)
            if m.get("train_loss") is not None:
                train_losses.append({"step": step, "loss": m["train_loss"]})
            if m.get("eval_loss") is not None:
                eval_losses.append({"step": step, "loss": m["eval_loss"]})
    
    # Find job status events
    job_started = None
    job_finished = None
    for m in metrics:
        if m.get("event") == "job_started":
            job_started = m
        elif m.get("event") == "job_finished":
            job_finished = m
    
    summary = {
        "has_metrics": True,
        "total_logged_steps": len(steps),
        "train_loss_history": train_losses[-50:],  # Last 50 points
        "eval_loss_history": eval_losses[-20:],    # Last 20 eval points
        "latest_train_loss": train_losses[-1]["loss"] if train_losses else None,
        "latest_eval_loss": eval_losses[-1]["loss"] if eval_losses else None,
        "min_train_loss": min(t["loss"] for t in train_losses) if train_losses else None,
        "min_eval_loss": min(e["loss"] for e in eval_losses) if eval_losses else None,
    }
    
    if job_started:
        summary["started_at"] = job_started.get("timestamp")
        summary["model_name"] = job_started.get("model_name")
        summary["train_samples"] = job_started.get("train_samples")
    
    if job_finished:
        summary["finished_at"] = job_finished.get("timestamp")
        summary["final_status"] = job_finished.get("status")
        summary["total_steps"] = job_finished.get("total_steps")
        summary["runtime_seconds"] = job_finished.get("runtime_seconds")
        if job_finished.get("error"):
            summary["error"] = job_finished["error"]
    
    return summary


def read_log_tail(log_path: str, lines: int = 50) -> List[str]:
    """
    Read the last N lines from a log file.
    
    Args:
        log_path: Path to log file
        lines: Number of lines to read
    
    Returns:
        List of log lines
    """
    path = Path(log_path)
    if not path.exists():
        return []
    
    try:
        with open(path, "r") as f:
            all_lines = f.readlines()
            return [line.rstrip() for line in all_lines[-lines:]]
    except IOError:
        return []


def check_log_for_errors(log_path: str) -> Optional[str]:
    """
    Check log file for error indicators.
    
    Args:
        log_path: Path to log file
    
    Returns:
        Error snippet if found, None otherwise
    """
    error_markers = [
        "ERROR:",
        "CUDA out of memory",
        "RuntimeError:",
        "ValueError:",
        "AssertionError:",
        "Traceback (most recent call last):",
        "torch.cuda.OutOfMemoryError",
        "OOM",
        "OutOfMemory",
        "FAILED",
        "Exception:",
        "KeyError:",
        "TypeError:",
        "ModuleNotFoundError:",
        "ImportError:",
    ]
    
    tail = read_log_tail(log_path, lines=150)
    
    error_lines = []
    in_error = False
    
    for line in tail:
        if any(marker in line for marker in error_markers):
            in_error = True
        
        if in_error:
            error_lines.append(line)
            if len(error_lines) > 30:  # Limit error snippet
                break
    
    if error_lines:
        return "\n".join(error_lines)
    
    # If no explicit errors found, return last 10 lines for context
    if tail:
        return f"[No explicit error found. Last 10 lines:]\n" + "\n".join(tail[-10:])
    
    return None


def refresh_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Refresh the status of a training job based on process state and metrics.
    
    This function:
    1. Checks if the training process is still alive
    2. Reads the latest metrics
    3. Updates the job status accordingly
    
    Args:
        job_id: ID of the job to refresh
    
    Returns:
        Updated job record, or None if job not found
    """
    job = get_job(job_id)
    if not job:
        return None
    
    # Skip if job is already in a terminal state
    if job["status"] in [STATUS_COMPLETED, STATUS_FAILED]:
        return job
    
    pid = job.get("pid", 0)
    output_dir = job.get("output_dir", "")
    log_path = job.get("log_path", "")
    
    # Check process status
    process_alive = is_process_alive(pid)
    
    # Read latest metrics
    latest_metrics = read_latest_metrics(output_dir)
    
    # Update latest metrics in job record
    if latest_metrics:
        # Check for job_finished event
        if latest_metrics.get("event") == "job_finished":
            status = latest_metrics.get("status", "completed")
            if status == "completed":
                return mark_job_completed(
                    job_id,
                    metrics={
                        "final_loss": latest_metrics.get("final_loss"),
                        "total_steps": latest_metrics.get("total_steps"),
                        "runtime_seconds": latest_metrics.get("runtime_seconds"),
                    }
                )
            else:
                return mark_job_failed(
                    job_id,
                    error_snippet=latest_metrics.get("error"),
                )
        
        # Update running job with latest metrics
        update_job(job_id, latest_metrics={
            "step": latest_metrics.get("step"),
            "train_loss": latest_metrics.get("train_loss"),
            "eval_loss": latest_metrics.get("eval_loss"),
            "epoch": latest_metrics.get("epoch"),
        })
    
    # If process is dead but no job_finished event, check for errors
    if not process_alive and job["status"] == STATUS_RUNNING:
        # Check log for errors
        error_snippet = check_log_for_errors(log_path) if log_path else None
        
        if error_snippet:
            return mark_job_failed(job_id, error_snippet=error_snippet)
        
        # If no errors found but process dead, mark as completed
        # (This handles the case where job finished but we missed the event)
        metrics_summary = get_training_metrics_summary(output_dir)
        if metrics_summary.get("final_status") == "completed":
            return mark_job_completed(job_id, metrics={
                "final_loss": metrics_summary.get("latest_train_loss"),
                "total_steps": metrics_summary.get("total_steps"),
            })
        
        # Otherwise mark as failed with unknown reason
        return mark_job_failed(
            job_id,
            error_snippet="Process terminated unexpectedly. Check logs for details."
        )
    
    return get_job(job_id)


def refresh_all_running_jobs() -> List[Dict[str, Any]]:
    """
    Refresh status for all running jobs.
    
    Returns:
        List of updated job records
    """
    from chatos_backend.training.job_store import get_running_jobs
    
    updated_jobs = []
    for job in get_running_jobs():
        updated = refresh_job_status(job["id"])
        if updated:
            updated_jobs.append(updated)
    
    return updated_jobs

