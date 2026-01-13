"""
unsloth_runner.py - Spawn and manage Unsloth training processes.

This module handles:
- Generating temporary config files for training jobs
- Spawning Unsloth training processes on the Kali GPU
- Managing process lifecycle
"""

import os
import subprocess
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import yaml

from ChatOS.config.settings import settings
from ChatOS.training.job_spec import TrainingJobSpec
from ChatOS.training.presets import TrainingType


def write_temp_config(job_spec: TrainingJobSpec) -> Path:
    """
    Generate a temporary YAML config file for Unsloth training.
    
    Selects the appropriate base template based on training type:
    - ChatOS: chatos_qlora.yaml
    - PersRM: persrm_qlora.yaml
    - PersRM Standalone (Mistral): persrm_standalone_mistral.yaml
    
    Args:
        job_spec: Training job specification
    
    Returns:
        Path to the generated config file
    """
    # Select base config template based on training type and model
    if job_spec.training_type == TrainingType.PERSRM or job_spec.training_type == "persrm":
        # Check if this is a standalone training on Mistral
        if "mistral" in job_spec.base_model_name.lower() and job_spec.preset_name == "STANDALONE":
            base_config_path = settings.unsloth_configs_dir / "persrm_standalone_mistral.yaml"
        else:
            base_config_path = settings.unsloth_configs_dir / "persrm_qlora.yaml"
    else:
        base_config_path = settings.unsloth_configs_dir / "chatos_qlora.yaml"
    
    # Fallback chain: standalone -> persrm -> chatos
    if not base_config_path.exists():
        fallback_paths = [
            settings.unsloth_configs_dir / "persrm_qlora.yaml",
            settings.unsloth_configs_dir / "chatos_qlora.yaml",
        ]
        for fallback_path in fallback_paths:
            if fallback_path.exists():
                base_config_path = fallback_path
                break
        else:
            raise FileNotFoundError(f"No config found. Tried: {base_config_path}, {fallback_paths}")
    
    with open(base_config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Get overrides from job spec
    overrides = job_spec.to_config_override()
    
    # Deep merge overrides into config
    _deep_merge(config, overrides)
    
    # Ensure output directory exists
    output_dir = Path(job_spec.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write config to training jobs directory
    config_path = settings.training_jobs_dir / f"{job_spec.id}.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    return config_path


def _deep_merge(base: dict, override: dict) -> None:
    """
    Deep merge override dict into base dict in-place.
    
    Args:
        base: Base dictionary to merge into
        override: Dictionary with values to override
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def start_training_process(
    job_spec: TrainingJobSpec,
    config_path: Path,
) -> Tuple[int, Path]:
    """
    Spawn an Unsloth training process.
    
    ⚠️ REQUIRES GPU ⚠️
    This function spawns a subprocess that requires:
    - NVIDIA GPU with CUDA
    - Conda environment with unsloth installed (or virtualenv)
    - Unsloth and dependencies installed with CUDA-enabled PyTorch
    
    Args:
        job_spec: Training job specification
        config_path: Path to the generated config YAML
    
    Returns:
        Tuple of (process PID, log file path)
    """
    # Setup log file
    log_path = settings.training_jobs_dir / f"{job_spec.id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build the command
    unsloth_dir = settings.unsloth_pipelines_dir
    venv_path = settings.unsloth_venv_path
    
    # Detect environment type and build activation command
    # Support both virtualenv (source bin/activate) and conda environments
    if (venv_path / "bin" / "activate").exists():
        # Traditional virtualenv
        activate_cmd = f'source {venv_path}/bin/activate'
    elif (Path.home() / "miniforge3" / "bin" / "conda").exists():
        # Conda environment - use conda activate
        conda_path = Path.home() / "miniforge3"
        env_name = venv_path.name if venv_path.name else "unsloth_py311"
        activate_cmd = f'eval "$({conda_path}/bin/conda shell.bash hook)" && conda activate {env_name}'
    else:
        # Fallback - try direct source
        activate_cmd = f'source {venv_path}/bin/activate'
    
    cmd = (
        f'{activate_cmd} && '
        f'cd {unsloth_dir} && '
        f'CHATOS_JOB_ID={job_spec.id} '
        f'PYTHONUNBUFFERED=1 '
        f'python -u train_qlora.py --config {config_path}'
    )
    
    # Open log file for writing
    log_file = open(log_path, "w")
    
    # Determine training type label
    training_type_label = "PersRM" if (
        job_spec.training_type == TrainingType.PERSRM or 
        job_spec.training_type == "persrm"
    ) else "ChatOS"
    
    # Write header to log
    log_file.write(f"=" * 60 + "\n")
    log_file.write(f"{training_type_label} Training Job: {job_spec.id}\n")
    log_file.write(f"Started: {datetime.now().isoformat()}\n")
    log_file.write(f"Training Type: {training_type_label}\n")
    log_file.write(f"Model: {job_spec.base_model_name}\n")
    log_file.write(f"Config: {config_path}\n")
    log_file.write(f"=" * 60 + "\n\n")
    log_file.flush()
    
    # ⚠️ RUNS ON KALI GPU ⚠️
    # Spawn the training process
    process = subprocess.Popen(
        ["bash", "-lc", cmd],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,  # Detach from parent process group
        env={
            **os.environ,
            "CHATOS_JOB_ID": job_spec.id,
            "PYTHONUNBUFFERED": "1",
        },
    )
    
    return process.pid, log_path


def stop_training_process(pid: int) -> bool:
    """
    Stop a running training process.
    
    Sends SIGTERM to allow graceful shutdown.
    
    Args:
        pid: Process ID to stop
    
    Returns:
        True if signal was sent successfully, False otherwise
    """
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except ProcessLookupError:
        # Process already dead
        return False
    except PermissionError:
        # No permission to kill
        return False


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


def get_process_exit_code(pid: int) -> Optional[int]:
    """
    Try to get the exit code of a finished process.
    
    Note: This only works reliably if we're the parent process.
    For detached processes, we rely on log file analysis.
    
    Args:
        pid: Process ID
    
    Returns:
        Exit code if available, None otherwise
    """
    try:
        # Try waitpid with WNOHANG
        _, status = os.waitpid(pid, os.WNOHANG)
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status)
        return None
    except ChildProcessError:
        # Not our child process
        return None
    except Exception:
        return None
