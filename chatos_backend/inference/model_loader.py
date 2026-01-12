"""
model_loader.py - Fine-tuned model discovery and loading for ChatOS.

Scans the ChatOS models directory for exported fine-tuned models
and makes them available for inference.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from chatos_backend.config.settings import settings


@dataclass
class FineTunedModel:
    """Information about a fine-tuned model."""
    id: str
    display_name: str
    base_model: str
    dataset_version: int
    job_id: str
    created_at: str
    preset_name: Optional[str]
    sample_count: int
    final_loss: Optional[float]
    # Paths
    adapter_path: Optional[str]
    gguf_path: Optional[str]
    modelfile_path: Optional[str]
    # Status
    ollama_registered: bool = False
    ollama_model_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "base_model": self.base_model,
            "dataset_version": self.dataset_version,
            "job_id": self.job_id,
            "created_at": self.created_at,
            "preset_name": self.preset_name,
            "sample_count": self.sample_count,
            "final_loss": self.final_loss,
            "adapter_path": self.adapter_path,
            "gguf_path": self.gguf_path,
            "modelfile_path": self.modelfile_path,
            "ollama_registered": self.ollama_registered,
            "ollama_model_name": self.ollama_model_name,
        }


def scan_fine_tuned_models() -> List[FineTunedModel]:
    """
    Scan the models directory for exported fine-tuned models.
    
    Looks for directories with:
    - adapter/ folder (LoRA adapter)
    - *.gguf file (quantized model)
    - Modelfile (Ollama config)
    - model_info.json (metadata)
    
    Returns:
        List of FineTunedModel objects
    """
    models_dir = settings.models_dir
    if not models_dir.exists():
        return []
    
    models = []
    
    for model_dir in models_dir.iterdir():
        if not model_dir.is_dir():
            continue
        
        model_info = _scan_model_directory(model_dir)
        if model_info:
            models.append(model_info)
    
    # Sort by created_at descending
    models.sort(key=lambda m: m.created_at or "", reverse=True)
    
    return models


def _scan_model_directory(model_dir: Path) -> Optional[FineTunedModel]:
    """Scan a single model directory for model artifacts."""
    
    # Check for model info JSON
    info_file = model_dir / "model_info.json"
    job_info_file = model_dir / "job_info.json"
    
    # Get metadata from files
    metadata = {}
    if info_file.exists():
        try:
            with open(info_file) as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    if job_info_file.exists() and not metadata:
        try:
            with open(job_info_file) as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Find adapter path
    adapter_path = None
    adapter_dir = model_dir / "adapter"
    if adapter_dir.exists() and (adapter_dir / "adapter_model.safetensors").exists():
        adapter_path = str(adapter_dir)
    # Also check if adapter is in root of model_dir
    if (model_dir / "adapter_model.safetensors").exists():
        adapter_path = str(model_dir)
    
    # Find GGUF file
    gguf_path = None
    for gguf_file in model_dir.glob("*.gguf"):
        gguf_path = str(gguf_file)
        break
    
    # Find Modelfile
    modelfile_path = None
    modelfile = model_dir / "Modelfile"
    if modelfile.exists():
        modelfile_path = str(modelfile)
    
    # If no artifacts found, skip
    if not adapter_path and not gguf_path:
        return None
    
    # Build display name
    job_id = model_dir.name
    dataset_version = metadata.get("dataset_version", 0)
    base_model = metadata.get("model_key", metadata.get("base_model", "unknown"))
    preset_name = metadata.get("preset_name", "")
    
    display_name = _generate_display_name(base_model, dataset_version, job_id, preset_name)
    
    # Check if model info has ollama info, otherwise generate/check
    ollama_model_name = metadata.get("ollama_model_name") or _get_ollama_model_name(display_name)
    ollama_registered = metadata.get("ollama_registered", False)
    
    # If model_info says registered, verify with actual ollama
    if ollama_registered or modelfile_path:
        ollama_registered = _check_ollama_registered(ollama_model_name)
    
    return FineTunedModel(
        id=job_id,
        display_name=metadata.get("display_name") or display_name,
        base_model=base_model,
        dataset_version=dataset_version,
        job_id=job_id,
        created_at=metadata.get("created_at", ""),
        preset_name=preset_name,
        sample_count=metadata.get("dataset_sample_count", 0),
        final_loss=metadata.get("final_loss"),
        adapter_path=adapter_path,
        gguf_path=gguf_path,
        modelfile_path=modelfile_path,
        ollama_registered=ollama_registered,
        ollama_model_name=ollama_model_name if ollama_registered else None,
    )


def _generate_display_name(base_model: str, version: int, job_id: str, preset: str = "") -> str:
    """
    Generate a display name for a fine-tuned model.
    
    Format: FT-{Model}-V{version}-{preset}
    Example: FT-Qwen25-V1-QUALITY
    """
    # Shorten base model name
    model_short = base_model.replace("qwen2.5-7b-instruct", "Qwen25")\
                           .replace("qwen2.5-coder-7b", "Qwen25C")\
                           .replace("mistral-7b-instruct", "Mistral")
    
    # Build name
    parts = ["FT", model_short, f"V{version}"]
    if preset:
        parts.append(preset)
    
    return "-".join(parts)


def get_model_display_name(job_id: str) -> Optional[str]:
    """Get the display name for a fine-tuned model by job ID."""
    models = scan_fine_tuned_models()
    for model in models:
        if model.job_id == job_id:
            return model.display_name
    return None


def get_fine_tuned_models() -> List[Dict[str, Any]]:
    """
    Get all fine-tuned models as dictionaries.
    
    Returns:
        List of model info dicts suitable for API response
    """
    models = scan_fine_tuned_models()
    return [m.to_dict() for m in models]


def _check_ollama_registered(model_name: str) -> bool:
    """Check if a model is registered with Ollama."""
    import subprocess
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Parse ollama list output
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if model_name.lower() in line.lower():
                    return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False


def _get_ollama_model_name(display_name: str) -> str:
    """Generate the Ollama model name."""
    # Keep dashes, just lowercase
    return display_name.lower()


def export_model_for_ollama(
    job_id: str,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Prepare a training job's output for use with Ollama.
    
    This function:
    1. Copies the adapter files to the models directory
    2. Creates a model_info.json with metadata
    3. Optionally generates a Modelfile (if GGUF is available)
    
    Args:
        job_id: ID of the completed training job
        output_dir: Override output directory (defaults to models_dir/job_id)
    
    Returns:
        Dict with export status and paths
    """
    from chatos_backend.training.job_store import get_job
    
    job = get_job(job_id)
    if not job:
        raise ValueError(f"Job not found: {job_id}")
    
    if job["status"] != "completed":
        raise ValueError(f"Job is not completed: {job['status']}")
    
    training_output = Path(job["output_dir"])
    if not training_output.exists():
        raise ValueError(f"Training output not found: {training_output}")
    
    # Create export directory
    if output_dir is None:
        output_dir = settings.models_dir / job_id
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy adapter files
    import shutil
    adapter_files = [
        "adapter_config.json",
        "adapter_model.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "added_tokens.json",
        "chat_template.jinja",
        "merges.txt",
        "vocab.json",
    ]
    
    for filename in adapter_files:
        src = training_output / filename
        if src.exists():
            shutil.copy2(src, output_dir / filename)
    
    # Create model_info.json
    model_info = {
        "job_id": job_id,
        "base_model": job.get("base_model_name"),
        "model_key": job.get("model_key"),
        "dataset_version": job.get("dataset_version"),
        "dataset_sample_count": job.get("dataset_sample_count"),
        "preset_name": job.get("preset_name"),
        "created_at": job.get("created_at"),
        "finished_at": job.get("finished_at"),
        "final_loss": job.get("latest_metrics", {}).get("final_loss"),
        "hyperparameters": job.get("hyperparameters"),
        "dataset_stats": job.get("dataset_stats"),
    }
    
    info_path = output_dir / "model_info.json"
    with open(info_path, "w") as f:
        json.dump(model_info, f, indent=2)
    
    # Generate display name
    display_name = _generate_display_name(
        model_info.get("model_key", "unknown"),
        model_info.get("dataset_version", 0),
        job_id,
        model_info.get("preset_name", ""),
    )
    
    # Generate a basic Modelfile template (GGUF would be added later by export script)
    modelfile_content = f"""# Modelfile for {display_name}
# Generated by ChatOS Fine-Tuning Pipeline

# Base model - use the full path to the GGUF file when available
# FROM ./model.gguf

# System prompt
SYSTEM \"\"\"You are a helpful AI assistant fine-tuned by ChatOS. You provide accurate, helpful, and conversational responses.\"\"\"

# Parameters
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 2048

# Chat template (Qwen format)
TEMPLATE \"\"\"{{{{- if .System }}}}
<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{- end }}}}
<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
<|im_start|>assistant
{{{{ .Response }}}}<|im_end|>\"\"\"
"""
    
    modelfile_path = output_dir / "Modelfile.template"
    with open(modelfile_path, "w") as f:
        f.write(modelfile_content)
    
    return {
        "success": True,
        "job_id": job_id,
        "display_name": display_name,
        "output_dir": str(output_dir),
        "model_info_path": str(info_path),
        "modelfile_template_path": str(modelfile_path),
        "adapter_files": [f for f in adapter_files if (output_dir / f).exists()],
    }

