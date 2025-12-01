"""
PersRM Integration Routes for ChatOS

This module provides API routes for the ChatOS ↔ PersRM integration,
including:
- Interaction logging configuration
- Manual flush/export triggers
- Statistics and monitoring
- Learning triggers
"""

import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ChatOS.controllers.interaction_logger import (
    get_interaction_logger,
    init_interaction_logger,
    InteractionType,
)

router = APIRouter(prefix="/api/persrm", tags=["PersRM Integration"])


# =============================================================================
# Request/Response Models
# =============================================================================

class InteractionLogConfig(BaseModel):
    """Configuration for interaction logging."""
    persrm_url: Optional[str] = None
    storage_dir: Optional[str] = None
    batch_size: int = 10
    flush_interval: float = 30.0
    auto_forward: bool = True


class InteractionStats(BaseModel):
    """Statistics about logged interactions."""
    total_logged: int
    total_forwarded: int
    total_errors: int
    buffer_size: int
    session_id: str
    last_flush: Optional[float] = None


class ExportRequest(BaseModel):
    """Request to export training data."""
    output_path: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ExportResponse(BaseModel):
    """Response from export operation."""
    success: bool
    path: str
    count: int


class ManualLogRequest(BaseModel):
    """Request to manually log an interaction."""
    type: str
    content: Optional[str] = None
    response: Optional[str] = None
    model: Optional[str] = None
    file_path: Optional[str] = None
    language: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# Routes
# =============================================================================

@router.get("/status")
async def get_status():
    """Get the status of PersRM integration."""
    logger = get_interaction_logger()
    return {
        "enabled": True,
        "session_id": logger.session_id,
        "stats": logger.get_stats(),
    }


@router.get("/stats", response_model=InteractionStats)
async def get_stats():
    """Get interaction logging statistics."""
    logger = get_interaction_logger()
    stats = logger.get_stats()
    return InteractionStats(**stats)


@router.post("/configure")
async def configure_logging(config: InteractionLogConfig):
    """Configure interaction logging settings."""
    try:
        await init_interaction_logger(
            persrm_url=config.persrm_url,
            storage_dir=config.storage_dir,
            batch_size=config.batch_size,
            flush_interval=config.flush_interval,
            auto_forward=config.auto_forward,
        )
        return {"success": True, "message": "Configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flush")
async def flush_buffer():
    """Manually flush the interaction buffer."""
    logger = get_interaction_logger()
    count = await logger.flush()
    return {"success": True, "flushed": count}


@router.post("/new-session")
async def new_session():
    """Start a new interaction session."""
    logger = get_interaction_logger()
    session_id = logger.new_session()
    return {"success": True, "session_id": session_id}


@router.post("/export", response_model=ExportResponse)
async def export_training_data(request: ExportRequest, background_tasks: BackgroundTasks):
    """Export interactions as training data."""
    logger = get_interaction_logger()
    
    try:
        path = await logger.export_training_data(
            output_path=request.output_path,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        
        # Count exported examples
        count = 0
        try:
            with open(path, "r") as f:
                count = sum(1 for _ in f)
        except:
            pass
        
        return ExportResponse(success=True, path=path, count=count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log")
async def manual_log(request: ManualLogRequest):
    """Manually log an interaction (for testing or external integrations)."""
    logger = get_interaction_logger()
    
    try:
        interaction_type = InteractionType(request.type)
    except ValueError:
        interaction_type = request.type
    
    interaction = await logger.log(
        interaction_type=interaction_type,
        content=request.content,
        response=request.response,
        model=request.model,
        file_path=request.file_path,
        language=request.language,
        metadata=request.metadata or {},
    )
    
    return {
        "success": True,
        "interaction_id": f"{interaction.session_id}_{int(interaction.timestamp * 1000)}",
    }


@router.post("/trigger-learning")
async def trigger_learning(background_tasks: BackgroundTasks):
    """Trigger the PersRM learning process."""
    import httpx
    
    logger = get_interaction_logger()
    
    # First flush any pending interactions
    await logger.flush()
    
    # Then trigger learning on PersRM
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{logger.persrm_url}/interactions/trigger-learning"
            )
            if response.status_code == 200:
                return {"success": True, "message": "Learning triggered on PersRM"}
            else:
                return {
                    "success": False,
                    "message": f"PersRM returned status {response.status_code}",
                }
    except httpx.ConnectError:
        return {
            "success": False,
            "message": "Could not connect to PersRM. Is it running?",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Check health of PersRM integration."""
    import httpx
    
    logger = get_interaction_logger()
    
    health = {
        "local_logger": "healthy",
        "buffer_size": len(logger._buffer),
        "persrm_connection": "unknown",
    }
    
    # Check PersRM connection
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{logger.persrm_url}/stats")
            if response.status_code == 200:
                health["persrm_connection"] = "healthy"
                health["persrm_stats"] = response.json()
            else:
                health["persrm_connection"] = f"error: status {response.status_code}"
    except httpx.ConnectError:
        health["persrm_connection"] = "disconnected"
    except Exception as e:
        health["persrm_connection"] = f"error: {str(e)}"
    
    return health


# =============================================================================
# PersRM Standalone Model Routes
# =============================================================================

@router.get("/standalone/status")
async def get_standalone_status():
    """
    Get the status of the PersRM Standalone model.
    
    Returns:
        Status of the fine-tuned standalone model
    """
    from ChatOS.controllers.model_config import get_model_config_manager
    
    manager = get_model_config_manager()
    model = manager.get_persrm_standalone_model()
    
    if model:
        return {
            "available": True,
            "model_id": model.id,
            "name": model.name,
            "provider": model.provider.value,
            "model_name": model.model_id,
            "enabled": model.enabled,
            "is_council_member": model.is_council_member,
        }
    else:
        return {
            "available": False,
            "message": "PersRM Standalone model not found. Train and deploy it first.",
        }


@router.post("/standalone/detect")
async def detect_standalone_model():
    """
    Detect and register the PersRM Standalone model from Ollama.
    
    Checks if the fine-tuned model is available in Ollama and registers it.
    """
    from ChatOS.controllers.model_config import get_model_config_manager
    
    manager = get_model_config_manager()
    model = await manager.detect_persrm_standalone()
    
    if model:
        return {
            "success": True,
            "message": "PersRM Standalone model detected and registered",
            "model": {
                "id": model.id,
                "name": model.name,
                "model_id": model.model_id,
            }
        }
    else:
        return {
            "success": False,
            "message": "PersRM Standalone model not found in Ollama. Deploy it first.",
        }


@router.post("/standalone/register")
async def register_standalone_model(model_name: str = "persrm-standalone-mistral"):
    """
    Manually register a PersRM Standalone model.
    
    Args:
        model_name: Name of the model in Ollama (default: persrm-standalone-mistral)
    """
    from ChatOS.controllers.model_config import get_model_config_manager
    
    manager = get_model_config_manager()
    
    try:
        model = await manager.register_persrm_standalone(model_name)
        return {
            "success": True,
            "message": f"Model '{model_name}' registered successfully",
            "model": {
                "id": model.id,
                "name": model.name,
                "model_id": model.model_id,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/standalone/training-stats")
async def get_training_data_stats():
    """
    Get statistics about available training data for PersRM Standalone.
    """
    from ChatOS.training.persrm_standalone_generator import get_training_data_stats
    
    return get_training_data_stats()


@router.post("/standalone/export-training-data")
async def export_persrm_training_data(
    min_quality: float = 0.5,
    include_reasoning_only: bool = False,
):
    """
    Export training data in PersRM format with reasoning traces.
    
    Args:
        min_quality: Minimum quality score (0-1)
        include_reasoning_only: Only include interactions with reasoning traces
    """
    logger = get_interaction_logger()
    
    try:
        stats = await logger.export_persrm_training_data(
            min_quality=min_quality,
            include_reasoning_only=include_reasoning_only,
        )
        return {
            "success": True,
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

