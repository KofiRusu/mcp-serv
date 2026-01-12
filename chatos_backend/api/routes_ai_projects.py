"""
routes_ai_projects.py - REST API endpoints for AI Projects.

AI Projects are preset configurations for AI chats, including system prompts,
default models, temperature settings, and feature flags. Now with file upload
support for project-specific knowledge bases.

Endpoints:
- GET    /api/ai-projects              List all AI projects
- GET    /api/ai-projects/templates    List available project templates
- GET    /api/ai-projects/{id}         Get project details
- POST   /api/ai-projects              Create new project
- POST   /api/ai-projects/from-template Create project from template
- PUT    /api/ai-projects/{id}         Update project
- DELETE /api/ai-projects/{id}         Delete project
- POST   /api/ai-projects/{id}/new-chat Create chat bound to project
- GET    /api/ai-projects/{id}/files   List project files
- POST   /api/ai-projects/{id}/files   Upload file to project
- DELETE /api/ai-projects/{id}/files/{filename} Remove file from project
- POST   /api/ai-projects/{id}/chats/{chat_id} Associate chat with project
"""

import uuid
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response

from chatos_backend.projects import get_ai_project_store, AIProjectCreate, AIProjectUpdate
from chatos_backend.schemas import (
    AIProjectCreateRequest,
    AIProjectUpdateRequest,
    AIProjectResponse,
    AIProjectListResponse,
    AIProjectTemplateResponse,
    AIProjectTemplateListResponse,
    AIProjectNewChatRequest,
    AIProjectNewChatResponse,
)

router = APIRouter(prefix="/api/ai-projects", tags=["AI Projects"])


def _project_to_response(project) -> AIProjectResponse:
    """Convert AIProject dataclass to Pydantic response model."""
    return AIProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        color=project.color,
        icon=project.icon,
        system_prompt=project.system_prompt,
        default_model_id=project.default_model_id,
        default_temperature=project.default_temperature,
        training_enabled=project.training_enabled,
        rag_enabled=project.rag_enabled,
        code_mode=project.code_mode,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


# =============================================================================
# List & Templates
# =============================================================================

@router.get("", response_model=AIProjectListResponse)
async def list_ai_projects() -> AIProjectListResponse:
    """
    List all AI projects.
    
    Returns projects sorted by name.
    """
    store = get_ai_project_store()
    projects = store.list_projects()
    
    return AIProjectListResponse(
        projects=[_project_to_response(p) for p in projects],
        total=len(projects),
    )


@router.get("/templates", response_model=AIProjectTemplateListResponse)
async def list_templates() -> AIProjectTemplateListResponse:
    """
    List available AI project templates.
    
    Templates provide pre-configured system prompts and settings
    for common use cases like coding, creative writing, etc.
    """
    store = get_ai_project_store()
    templates = store.get_templates()
    
    return AIProjectTemplateListResponse(
        templates=[
            AIProjectTemplateResponse(
                key=key,
                name=data.get("name", key),
                icon=data.get("icon", "📁"),
                color=data.get("color", "#2B26FE"),
                description=data.get("description"),
            )
            for key, data in templates.items()
        ]
    )


# =============================================================================
# CRUD Operations
# =============================================================================

@router.get("/{project_id}", response_model=AIProjectResponse)
async def get_ai_project(project_id: str) -> AIProjectResponse:
    """
    Get an AI project by ID.
    
    Returns full project details including system prompt.
    """
    store = get_ai_project_store()
    project = store.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    return _project_to_response(project)


@router.post("", response_model=AIProjectResponse, status_code=201)
async def create_ai_project(request: AIProjectCreateRequest) -> AIProjectResponse:
    """
    Create a new AI project.
    
    The project will have a unique ID and URL-friendly slug generated
    from the name.
    """
    store = get_ai_project_store()
    
    # Validate model_id if provided
    if request.default_model_id:
        # Import here to avoid circular imports
        from chatos_backend.controllers.model_config import get_model_config_manager
        mgr = get_model_config_manager()
        model = mgr.get_model(request.default_model_id)
        if not model:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model ID: {request.default_model_id}"
            )
    
    payload = AIProjectCreate(
        name=request.name,
        description=request.description,
        color=request.color,
        icon=request.icon,
        system_prompt=request.system_prompt,
        default_model_id=request.default_model_id,
        default_temperature=request.default_temperature,
        training_enabled=request.training_enabled,
        rag_enabled=request.rag_enabled,
        code_mode=request.code_mode,
    )
    
    project = store.create_project(payload)
    return _project_to_response(project)


@router.post("/from-template", response_model=AIProjectResponse, status_code=201)
async def create_from_template(template_key: str) -> AIProjectResponse:
    """
    Create a new AI project from a built-in template.
    
    Available templates: coding-assistant, creative-writer, 
    research-analyst, pirate-mode.
    """
    store = get_ai_project_store()
    
    project = store.create_from_template(template_key)
    if not project:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown template: {template_key}"
        )
    
    return _project_to_response(project)


@router.put("/{project_id}", response_model=AIProjectResponse)
async def update_ai_project(
    project_id: str,
    request: AIProjectUpdateRequest,
) -> AIProjectResponse:
    """
    Update an existing AI project.
    
    Only fields provided in the request will be updated.
    """
    store = get_ai_project_store()
    
    # Check project exists
    existing = store.get_project(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    # Validate model_id if being updated
    if request.default_model_id is not None:
        from chatos_backend.controllers.model_config import get_model_config_manager
        mgr = get_model_config_manager()
        model = mgr.get_model(request.default_model_id)
        if not model and request.default_model_id != "":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model ID: {request.default_model_id}"
            )
    
    payload = AIProjectUpdate(
        name=request.name,
        description=request.description,
        color=request.color,
        icon=request.icon,
        system_prompt=request.system_prompt,
        default_model_id=request.default_model_id,
        default_temperature=request.default_temperature,
        training_enabled=request.training_enabled,
        rag_enabled=request.rag_enabled,
        code_mode=request.code_mode,
    )
    
    project = store.update_project(project_id, payload)
    if not project:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    return _project_to_response(project)


@router.delete("/{project_id}")
async def delete_ai_project(project_id: str):
    """
    Delete an AI project.
    
    This does not delete any chats that were created with this project;
    they will continue to work with their stored system_snapshot.
    """
    store = get_ai_project_store()
    
    if not store.delete_project(project_id):
        raise HTTPException(status_code=404, detail="AI project not found")
    
    return {"success": True, "deleted_id": project_id}


# =============================================================================
# Chat Integration
# =============================================================================

@router.post("/{project_id}/new-chat", response_model=AIProjectNewChatResponse)
async def create_project_chat(
    project_id: str,
    request: AIProjectNewChatRequest = None,
) -> AIProjectNewChatResponse:
    """
    Create a new chat session bound to an AI project.
    
    The chat will inherit the project's system prompt, model settings,
    and feature flags. A snapshot of these settings is stored with the
    chat so future project edits don't affect existing chats.
    
    Returns the chat_id and session_id to use for subsequent messages.
    """
    store = get_ai_project_store()
    project = store.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    # Generate session ID if not provided
    session_id = (
        request.session_id if request and request.session_id
        else f"ai_project_{project_id}_{uuid.uuid4().hex[:8]}"
    )
    
    # Create system snapshot
    system_snapshot = project.create_system_snapshot()
    
    return AIProjectNewChatResponse(
        chat_id=f"chat_{uuid.uuid4().hex[:12]}",
        session_id=session_id,
        project_id=project_id,
        project_name=project.name,
        system_snapshot=system_snapshot,
    )


@router.get("/{project_id}/settings-summary")
async def get_project_settings_summary(project_id: str):
    """
    Get a quick summary of project settings for display in UI.
    
    Returns minimal info: model name, temperature, active flags.
    """
    store = get_ai_project_store()
    project = store.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    # Try to get model name
    model_name = None
    if project.default_model_id:
        try:
            from chatos_backend.controllers.model_config import get_model_config_manager
            mgr = get_model_config_manager()
            model = mgr.get_model(project.default_model_id)
            if model:
                model_name = model.name
        except Exception:
            pass
    
    return {
        "id": project.id,
        "name": project.name,
        "icon": project.icon,
        "color": project.color,
        "model_id": project.default_model_id,
        "model_name": model_name,
        "temperature": project.default_temperature,
        "flags": {
            "training": project.training_enabled,
            "rag": project.rag_enabled,
            "code": project.code_mode,
        },
        "has_system_prompt": bool(project.system_prompt.strip()),
        "file_count": len(project.files),
        "chat_count": len(project.chat_ids),
    }


# =============================================================================
# File Management
# =============================================================================

@router.get("/{project_id}/files")
async def list_project_files(project_id: str):
    """
    List all files in a project's knowledge base.
    
    Returns file names, sizes, and modification dates.
    """
    store = get_ai_project_store()
    project = store.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    files = store.list_project_files(project_id)
    
    return {
        "project_id": project_id,
        "files": files,
        "total": len(files),
    }


@router.post("/{project_id}/files")
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(...),
):
    """
    Upload a file to a project's knowledge base.
    
    Supported file types: .txt, .md, .pdf, .docx, code files (.py, .js, etc.)
    Max file size: 10MB
    """
    store = get_ai_project_store()
    project = store.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    # Check file size (10MB limit)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    
    success, result = store.add_file_to_project(
        project_id,
        file.filename or "unnamed",
        content,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=result)
    
    return {
        "success": True,
        "filename": result,
        "size": len(content),
        "project_id": project_id,
    }


@router.delete("/{project_id}/files/{filename}")
async def delete_project_file(project_id: str, filename: str):
    """
    Remove a file from a project's knowledge base.
    """
    store = get_ai_project_store()
    project = store.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    if filename not in project.files:
        raise HTTPException(status_code=404, detail="File not found in project")
    
    store.remove_file_from_project(project_id, filename)
    
    return {
        "success": True,
        "deleted": filename,
        "project_id": project_id,
    }


@router.get("/{project_id}/files/{filename}")
async def download_project_file(project_id: str, filename: str):
    """
    Download a file from a project's knowledge base.
    """
    store = get_ai_project_store()
    project = store.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    content = store.get_file_content(project_id, filename)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine content type
    ext = filename.split('.')[-1].lower() if '.' in filename else 'txt'
    content_types = {
        'txt': 'text/plain',
        'md': 'text/markdown',
        'pdf': 'application/pdf',
        'json': 'application/json',
        'py': 'text/x-python',
        'js': 'application/javascript',
    }
    content_type = content_types.get(ext, 'application/octet-stream')
    
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# Chat Association
# =============================================================================

@router.post("/{project_id}/chats/{chat_id}")
async def associate_chat_with_project(project_id: str, chat_id: str):
    """
    Associate a chat/conversation with a project.
    
    The chat will be listed under this project and use its settings.
    """
    store = get_ai_project_store()
    project = store.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    store.add_chat_to_project(project_id, chat_id)
    
    return {
        "success": True,
        "project_id": project_id,
        "chat_id": chat_id,
    }


@router.delete("/{project_id}/chats/{chat_id}")
async def remove_chat_from_project(project_id: str, chat_id: str):
    """
    Remove a chat association from a project.
    """
    store = get_ai_project_store()
    project = store.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    store.remove_chat_from_project(project_id, chat_id)
    
    return {
        "success": True,
        "project_id": project_id,
        "chat_id": chat_id,
    }


@router.get("/{project_id}/chats")
async def list_project_chats(project_id: str):
    """
    List all chats associated with a project.
    """
    store = get_ai_project_store()
    project = store.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="AI project not found")
    
    return {
        "project_id": project_id,
        "chat_ids": project.chat_ids,
        "total": len(project.chat_ids),
    }

