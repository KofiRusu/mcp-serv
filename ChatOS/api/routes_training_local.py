"""
routes_training_local.py - Local model training routes for any device.

Provides user-friendly training capabilities that:
- Auto-detect available Ollama models
- Check system requirements (GPU, VRAM, etc.)
- Work out-of-the-box without hardcoded paths
- Guide users through setup if needed
"""

import asyncio
import subprocess
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/training/local", tags=["Training (Local)"])


# =============================================================================
# Request/Response Models
# =============================================================================

class SystemRequirements(BaseModel):
    """System requirements check result."""
    ollama_installed: bool = False
    ollama_running: bool = False
    ollama_models: List[str] = []
    gpu_available: bool = False
    gpu_name: Optional[str] = None
    gpu_vram_gb: Optional[float] = None
    python_version: str = ""
    has_unsloth: bool = False
    has_transformers: bool = False
    ready_for_training: bool = False
    setup_steps: List[str] = []


class LocalTrainingRequest(BaseModel):
    """Request to start local training."""
    base_model: str = Field(..., description="Ollama model name to fine-tune")
    training_data_source: str = Field(
        "chatos",
        description="Data source: 'chatos' (chat history) or 'custom'"
    )
    epochs: int = Field(2, ge=1, le=10, description="Number of training epochs")
    learning_rate: float = Field(2e-4, description="Learning rate")
    output_name: str = Field("", description="Name for the fine-tuned model")
    force: bool = Field(False, description="Skip readiness checks")


# =============================================================================
# Helper Functions
# =============================================================================

async def check_ollama_status() -> tuple[bool, bool, List[str]]:
    """
    Check if Ollama is installed, running, and list available models.
    
    Returns:
        Tuple of (installed, running, model_list)
    """
    installed = shutil.which("ollama") is not None
    running = False
    models = []
    
    if installed:
        try:
            # Check if Ollama is running by listing models
            result = await asyncio.to_thread(
                subprocess.run,
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            running = result.returncode == 0
            
            if running and result.stdout:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip():
                        # Format: NAME ID SIZE MODIFIED
                        parts = line.split()
                        if parts:
                            models.append(parts[0])
        except Exception:
            pass
    
    return installed, running, models


async def check_gpu_status() -> tuple[bool, Optional[str], Optional[float]]:
    """
    Check GPU availability using nvidia-smi.
    
    Returns:
        Tuple of (available, gpu_name, vram_gb)
    """
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(',')
            if len(parts) >= 2:
                gpu_name = parts[0].strip()
                vram_mb = float(parts[1].strip())
                vram_gb = vram_mb / 1024
                return True, gpu_name, round(vram_gb, 1)
    except Exception:
        pass
    
    return False, None, None


def check_python_packages() -> tuple[str, bool, bool]:
    """
    Check Python version and key packages.
    
    Returns:
        Tuple of (python_version, has_unsloth, has_transformers)
    """
    import sys
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    has_unsloth = False
    has_transformers = False
    
    try:
        import unsloth
        has_unsloth = True
    except ImportError:
        pass
    
    try:
        import transformers
        has_transformers = True
    except ImportError:
        pass
    
    return python_version, has_unsloth, has_transformers


# =============================================================================
# Routes
# =============================================================================

@router.get("/system-check")
async def check_system_requirements() -> SystemRequirements:
    """
    Check system requirements for local model training.
    
    Returns comprehensive status of:
    - Ollama installation and available models
    - GPU availability and VRAM
    - Required Python packages
    - Setup steps if anything is missing
    """
    # Run checks in parallel
    ollama_task = check_ollama_status()
    gpu_task = check_gpu_status()
    
    ollama_installed, ollama_running, ollama_models = await ollama_task
    gpu_available, gpu_name, gpu_vram_gb = await gpu_task
    python_version, has_unsloth, has_transformers = check_python_packages()
    
    # Determine setup steps needed
    setup_steps = []
    
    if not ollama_installed:
        setup_steps.append("Install Ollama: curl -fsSL https://ollama.ai/install.sh | sh")
    elif not ollama_running:
        setup_steps.append("Start Ollama: ollama serve &")
    elif not ollama_models:
        setup_steps.append("Pull a model: ollama pull qwen2.5:7b or ollama pull mistral:7b")
    
    if not gpu_available:
        setup_steps.append("GPU not detected - training will be slow or unavailable")
    elif gpu_vram_gb and gpu_vram_gb < 6:
        setup_steps.append(f"GPU has {gpu_vram_gb}GB VRAM - recommend 8GB+ for training")
    
    if not has_transformers:
        setup_steps.append("Install transformers: pip install transformers")
    
    # Determine readiness
    ready = (
        ollama_installed and 
        ollama_running and 
        len(ollama_models) > 0 and
        has_transformers
    )
    
    return SystemRequirements(
        ollama_installed=ollama_installed,
        ollama_running=ollama_running,
        ollama_models=ollama_models,
        gpu_available=gpu_available,
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram_gb,
        python_version=python_version,
        has_unsloth=has_unsloth,
        has_transformers=has_transformers,
        ready_for_training=ready,
        setup_steps=setup_steps,
    )


@router.get("/ollama-models")
async def list_ollama_models():
    """
    List all models available in Ollama for fine-tuning.
    
    Returns models with metadata suitable for training selection.
    """
    _, running, models = await check_ollama_status()
    
    if not running:
        raise HTTPException(
            status_code=503,
            detail="Ollama is not running. Start it with: ollama serve"
        )
    
    # Categorize models
    categorized = {
        "recommended": [],
        "available": [],
        "all": models,
    }
    
    # Models known to work well for fine-tuning
    recommended_patterns = ["qwen", "mistral", "llama", "phi", "deepseek"]
    
    for model in models:
        model_lower = model.lower()
        is_recommended = any(p in model_lower for p in recommended_patterns)
        
        model_info = {
            "name": model,
            "display_name": model.replace(":", " ").title(),
            "recommended": is_recommended,
            "size_estimate": _estimate_model_size(model),
        }
        
        if is_recommended:
            categorized["recommended"].append(model_info)
        categorized["available"].append(model_info)
    
    return {
        "models": categorized,
        "total": len(models),
        "default": categorized["recommended"][0]["name"] if categorized["recommended"] else (models[0] if models else None),
    }


def _estimate_model_size(model_name: str) -> str:
    """Estimate model size from name."""
    name_lower = model_name.lower()
    
    if "70b" in name_lower:
        return "~70GB"
    elif "32b" in name_lower or "33b" in name_lower:
        return "~32GB"
    elif "13b" in name_lower or "14b" in name_lower:
        return "~14GB"
    elif "7b" in name_lower or "8b" in name_lower:
        return "~4-8GB"
    elif "3b" in name_lower or "4b" in name_lower:
        return "~2-4GB"
    elif "1b" in name_lower or "2b" in name_lower:
        return "~1-2GB"
    else:
        return "Unknown"


@router.get("/training-data-stats")
async def get_training_data_stats():
    """
    Get statistics about available training data from ChatOS.
    
    Shows how much data is available for fine-tuning.
    """
    try:
        from ChatOS.training.auto_trainer import get_training_stats
        stats = get_training_stats("chatos")
        
        return {
            "source": "chatos",
            "total_conversations": stats.get("total_conversations", 0),
            "training_examples": stats.get("training_examples", 0),
            "positive_feedback": stats.get("positive_feedback", 0),
            "ready_to_train": stats.get("ready_to_train", False),
            "min_required": stats.get("min_samples_required", 50),
            "message": _get_data_status_message(stats),
        }
    except Exception as e:
        return {
            "source": "chatos",
            "total_conversations": 0,
            "training_examples": 0,
            "ready_to_train": False,
            "error": str(e),
            "message": "Chat more to collect training data!",
        }


def _get_data_status_message(stats: dict) -> str:
    """Generate a user-friendly status message."""
    examples = stats.get("training_examples", 0)
    required = stats.get("min_samples_required", 50)
    
    if examples == 0:
        return "No training data yet. Chat with the AI and rate responses with 👍/👎!"
    elif examples < required:
        return f"Collecting data: {examples}/{required} examples. Keep chatting and rating!"
    elif stats.get("ready_to_train"):
        return f"✅ Ready to train with {examples} examples!"
    else:
        quality = stats.get("current_quality_ratio", 0) * 100
        return f"Have {examples} examples but quality is {quality:.0f}%. Rate more responses!"


@router.post("/start")
async def start_local_training(request: LocalTrainingRequest):
    """
    Start a local fine-tuning job.
    
    This simplified endpoint handles training with sensible defaults
    and works with any Ollama model.
    """
    # Verify system is ready
    system = await check_system_requirements()
    
    if not system.ollama_running:
        raise HTTPException(
            status_code=503,
            detail="Ollama is not running. Start it with: ollama serve"
        )
    
    if request.base_model not in system.ollama_models:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.base_model}' not found in Ollama. "
                   f"Available: {', '.join(system.ollama_models[:5])}"
        )
    
    # Check for sufficient training data
    data_stats = await get_training_data_stats()
    if not data_stats.get("ready_to_train") and not request.force:
        raise HTTPException(
            status_code=400,
            detail=data_stats.get("message", "Not enough training data")
        )
    
    # Start training job
    try:
        from ChatOS.training.auto_trainer import start_training_job, TrainingError
        
        # Map Ollama model name to internal model key if possible
        model_key = _ollama_to_model_key(request.base_model)
        
        job_id, job = start_training_job(
            training_type="chatos",
            preset_name="BALANCED",
            model_key=model_key,
            description=f"Local training: {request.base_model}",
            force=request.force,
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Training started! Job ID: {job_id}",
            "model": request.base_model,
        }
        
    except TrainingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {e}")


def _ollama_to_model_key(ollama_name: str) -> str:
    """Map Ollama model name to internal model key."""
    name_lower = ollama_name.lower()
    
    if "qwen2.5" in name_lower and "coder" in name_lower:
        return "qwen2.5-coder-7b"
    elif "qwen2.5" in name_lower or "qwen" in name_lower:
        return "qwen2.5-7b-instruct"
    elif "mistral" in name_lower:
        return "mistral-7b-instruct"
    else:
        # Default to qwen for unknown models
        return "qwen2.5-7b-instruct"


@router.get("/quick-setup")
async def get_quick_setup_guide():
    """
    Get a step-by-step setup guide for training.
    
    Returns personalized setup instructions based on current system state.
    """
    system = await check_system_requirements()
    
    steps = []
    current_step = 1
    
    # Step 1: Ollama
    if not system.ollama_installed:
        steps.append({
            "step": current_step,
            "title": "Install Ollama",
            "status": "pending",
            "command": "curl -fsSL https://ollama.ai/install.sh | sh",
            "description": "Ollama lets you run LLMs locally",
        })
    elif not system.ollama_running:
        steps.append({
            "step": current_step,
            "title": "Start Ollama",
            "status": "pending",
            "command": "ollama serve &",
            "description": "Start the Ollama service",
        })
    else:
        steps.append({
            "step": current_step,
            "title": "Ollama Ready",
            "status": "complete",
            "description": f"Ollama is running with {len(system.ollama_models)} models",
        })
    current_step += 1
    
    # Step 2: Model
    if system.ollama_running and not system.ollama_models:
        steps.append({
            "step": current_step,
            "title": "Download a Model",
            "status": "pending",
            "command": "ollama pull qwen2.5:7b",
            "description": "Download a base model for training",
        })
    elif system.ollama_models:
        steps.append({
            "step": current_step,
            "title": "Model Available",
            "status": "complete",
            "description": f"Available: {', '.join(system.ollama_models[:3])}",
        })
    else:
        steps.append({
            "step": current_step,
            "title": "Download a Model",
            "status": "waiting",
            "command": "ollama pull qwen2.5:7b",
            "description": "First complete Ollama setup",
        })
    current_step += 1
    
    # Step 3: Training Data
    data_stats = await get_training_data_stats()
    examples = data_stats.get("training_examples", 0)
    required = data_stats.get("min_required", 50)
    
    if examples >= required:
        steps.append({
            "step": current_step,
            "title": "Training Data Ready",
            "status": "complete",
            "description": f"{examples} examples collected",
        })
    else:
        steps.append({
            "step": current_step,
            "title": "Collect Training Data",
            "status": "in_progress",
            "description": f"{examples}/{required} examples. Chat and rate responses!",
            "progress": examples / required if required > 0 else 0,
        })
    current_step += 1
    
    # Step 4: GPU (optional)
    if system.gpu_available:
        steps.append({
            "step": current_step,
            "title": "GPU Ready",
            "status": "complete",
            "description": f"{system.gpu_name} ({system.gpu_vram_gb}GB VRAM)",
        })
    else:
        steps.append({
            "step": current_step,
            "title": "GPU (Optional)",
            "status": "info",
            "description": "Training possible without GPU but slower",
        })
    
    return {
        "steps": steps,
        "ready_to_train": system.ready_for_training and data_stats.get("ready_to_train", False),
        "next_action": _get_next_action(steps, data_stats),
    }


def _get_next_action(steps: list, data_stats: dict) -> dict:
    """Get the next recommended action."""
    for step in steps:
        if step["status"] == "pending":
            return {
                "action": step["title"],
                "command": step.get("command"),
                "description": step["description"],
            }
    
    if data_stats.get("ready_to_train"):
        return {
            "action": "Start Training",
            "description": "You're ready to fine-tune a model!",
        }
    
    return {
        "action": "Collect More Data",
        "description": "Keep chatting and rating responses",
    }

