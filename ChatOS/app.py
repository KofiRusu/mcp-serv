"""
ChatOS - A PewDiePie-style Local AI Interface

Features:
- Multi-model council with voting/selection
- /research, /deepthinking, /swarm commands
- Coding sandbox with file operations
- Project scaffolding with venv and dependency management
- File attachments for chat context
- Project-specific memory storage

Run with: uvicorn ChatOS.app:app --reload
"""

from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ChatOS import __version__
from ChatOS.config import STATIC_DIR, TEMPLATES_DIR, COMMAND_MODES
from ChatOS.controllers.chat import chat_endpoint, get_council_info, get_available_commands
from ChatOS.controllers.sandbox import get_sandbox, CodeEdit
from ChatOS.controllers.projects import get_project_manager
from ChatOS.controllers.attachments import get_attachment_manager
from ChatOS.controllers.project_memory import get_project_memory_manager
from ChatOS.controllers.model_config import get_model_config_manager, ModelConfig, ModelProvider
from ChatOS.controllers.llm_client import get_llm_client
from ChatOS.controllers.memory_logger import get_memory_logger, InteractionQuality
from ChatOS.controllers.auto_trainer import get_auto_trainer, TrainingConfig
from ChatOS.schemas import (
    ChatRequest,
    ChatResponse,
    CouncilInfoResponse,
    ErrorResponse,
    HealthResponse,
    SandboxFileRequest,
    SandboxExecuteRequest,
    SearchRequest,
    FileTreeResponse,
    FileContentResponse,
    ExecutionResponse,
    SearchResponse,
    SearchResult,
    CommandInfo,
    ProjectCreateRequest,
    ProjectRunRequest,
    ProjectInstallRequest,
    ProjectResponse,
    ProjectStatusResponse,
    ProjectTemplateResponse,
    ProjectListResponse,
    AttachmentUploadRequest,
    AttachmentResponse,
    AttachmentListResponse,
    ProjectMemoryAddRequest,
    TaskCreateRequest,
    ProjectContextResponse,
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigResponse,
    ProviderInfoResponse,
    ProviderStatusResponse,
    GlobalSettingsUpdate,
    GlobalSettingsResponse,
    ApiKeyRequest,
    OllamaModelRequest,
)

# =============================================================================
# App Configuration
# =============================================================================

app = FastAPI(
    title="ChatOS",
    description="A PewDiePie-style local AI interface with council-of-bots, project management, and coding sandbox",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# =============================================================================
# HTML Routes
# =============================================================================

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@app.get("/sandbox", response_class=HTMLResponse, include_in_schema=False)
async def sandbox_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "sandbox.html")


@app.get("/projects", response_class=HTMLResponse, include_in_schema=False)
async def projects_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "projects.html")


@app.get("/settings", response_class=HTMLResponse, include_in_schema=False)
async def settings_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "settings.html")


# =============================================================================
# Chat API
# =============================================================================

@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health() -> HealthResponse:
    info = get_council_info()
    return HealthResponse(
        status="healthy",
        version=__version__,
        models_loaded=len(info["models"]),
        rag_documents=info["rag_documents"],
    )


@app.get("/api/council", response_model=CouncilInfoResponse, tags=["System"])
async def council_info() -> CouncilInfoResponse:
    info = get_council_info()
    return CouncilInfoResponse(**info)


@app.get("/api/commands", response_model=List[CommandInfo], tags=["System"])
async def list_commands() -> List[CommandInfo]:
    commands = get_available_commands()
    return [CommandInfo(name=n, description=i["description"], icon=i["icon"]) for n, i in commands.items()]


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the council with optional project context and attachments."""
    try:
        # Build context from attachments
        attachment_context = ""
        if request.attachment_ids:
            att_mgr = get_attachment_manager()
            for att_id in request.attachment_ids:
                content = att_mgr.get_full_content(att_id)
                if content:
                    attachment_context += content + "\n\n"
        
        # Build context from project memory
        project_context = ""
        if request.project_id:
            proj_mgr = get_project_manager()
            project = proj_mgr.projects.get(request.project_id)
            if project:
                mem_mgr = get_project_memory_manager()
                db = mem_mgr.get_db(request.project_id, project.path)
                ctx = db.get_full_context(project.name)
                project_context = ctx.to_prompt_context()
        
        # Modify message with context if needed
        full_message = request.message
        if attachment_context:
            full_message = f"{attachment_context}\nUser query: {request.message}"
        
        result = await chat_endpoint(
            message=full_message,
            mode=request.mode,
            use_rag=request.use_rag,
            session_id=request.session_id,
            model_id=request.model_id,
        )
        
        # Store in project memory if applicable
        if request.project_id:
            proj_mgr = get_project_manager()
            project = proj_mgr.projects.get(request.project_id)
            if project:
                mem_mgr = get_project_memory_manager()
                db = mem_mgr.get_db(request.project_id, project.path)
                db.add_conversation(
                    request.message,
                    result["answer"],
                    mode=result.get("mode", "normal"),
                    attachments=request.attachment_ids,
                )
        
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Sandbox API
# =============================================================================

@app.get("/api/sandbox/files", response_model=FileTreeResponse, tags=["Sandbox"])
async def get_file_tree():
    sandbox = get_sandbox()
    tree = sandbox.get_file_tree()
    files = sandbox.list_files()
    return FileTreeResponse(root=tree.to_dict(), total_files=len(files))


@app.get("/api/sandbox/file", response_model=FileContentResponse, tags=["Sandbox"])
async def read_file(path: str):
    sandbox = get_sandbox()
    try:
        content = sandbox.read_file(path)
        return FileContentResponse(path=path, content=content, size=len(content))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")


@app.post("/api/sandbox/file", tags=["Sandbox"])
async def write_file(request: SandboxFileRequest):
    sandbox = get_sandbox()
    try:
        sandbox.write_file(request.path, request.content or "")
        return {"success": True, "path": request.path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/sandbox/file", tags=["Sandbox"])
async def delete_file(path: str):
    sandbox = get_sandbox()
    try:
        sandbox.delete_file(path)
        return {"success": True, "path": path}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")


@app.post("/api/sandbox/execute", response_model=ExecutionResponse, tags=["Sandbox"])
async def execute_code(request: SandboxExecuteRequest):
    sandbox = get_sandbox()
    result = sandbox.execute_python(code=request.code, file_path=request.file_path, timeout=request.timeout)
    return ExecutionResponse(**result.__dict__)


@app.post("/api/sandbox/search", response_model=SearchResponse, tags=["Sandbox"])
async def search_files(request: SearchRequest):
    sandbox = get_sandbox()
    matches = sandbox.search_in_files(request.pattern, request.path, request.file_pattern)
    return SearchResponse(pattern=request.pattern, matches=[SearchResult(**m) for m in matches], total_matches=len(matches))


# =============================================================================
# Projects API
# =============================================================================

@app.get("/api/projects", response_model=ProjectListResponse, tags=["Projects"])
async def list_projects():
    """List all registered projects."""
    mgr = get_project_manager()
    projects = mgr.list_projects()
    return ProjectListResponse(
        projects=[ProjectResponse(**p) for p in projects],
        total=len(projects),
    )


@app.get("/api/projects/templates", response_model=List[ProjectTemplateResponse], tags=["Projects"])
async def list_templates():
    """List available project templates."""
    mgr = get_project_manager()
    return [ProjectTemplateResponse(**t) for t in mgr.get_templates()]


@app.post("/api/projects", response_model=ProjectResponse, tags=["Projects"])
async def create_project(request: ProjectCreateRequest):
    """Create a new project from a template."""
    mgr = get_project_manager()
    try:
        project = await mgr.create_project(
            name=request.name,
            template=request.template,
            description=request.description,
            auto_setup=request.auto_setup,
        )
        status = mgr.get_status(project.id)
        return ProjectResponse(**project.to_dict(), status=ProjectStatusResponse(**status.to_dict()))
    except FileExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"])
async def get_project(project_id: str):
    """Get project details."""
    mgr = get_project_manager()
    project = mgr.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    status = mgr.get_status(project_id)
    return ProjectResponse(**project.to_dict(), status=ProjectStatusResponse(**status.to_dict()))


@app.delete("/api/projects/{project_id}", tags=["Projects"])
async def delete_project(project_id: str):
    """Delete a project."""
    mgr = get_project_manager()
    if await mgr.delete_project(project_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Project not found")


@app.post("/api/projects/{project_id}/setup-venv", tags=["Projects"])
async def setup_venv(project_id: str):
    """Create virtual environment for a project."""
    mgr = get_project_manager()
    if project_id not in mgr.projects:
        raise HTTPException(status_code=404, detail="Project not found")
    success = await mgr.setup_venv(project_id)
    return {"success": success}


@app.post("/api/projects/{project_id}/install", response_model=ExecutionResponse, tags=["Projects"])
async def install_dependencies(project_id: str, request: ProjectInstallRequest = None):
    """Install project dependencies."""
    mgr = get_project_manager()
    if project_id not in mgr.projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    extra = request.extra_packages if request else None
    result = await mgr.install_dependencies(project_id, extra)
    return ExecutionResponse(
        success=result.success,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        execution_time=result.execution_time,
    )


@app.post("/api/projects/{project_id}/run", response_model=ExecutionResponse, tags=["Projects"])
async def run_project(project_id: str, request: ProjectRunRequest = None):
    """Run a project."""
    mgr = get_project_manager()
    if project_id not in mgr.projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    req = request or ProjectRunRequest()
    result = await mgr.run_project(
        project_id,
        command=req.command,
        background=req.background,
        timeout=req.timeout,
    )
    return ExecutionResponse(
        success=result.success,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        execution_time=result.execution_time,
    )


@app.post("/api/projects/{project_id}/stop", tags=["Projects"])
async def stop_project(project_id: str):
    """Stop a running project."""
    mgr = get_project_manager()
    if await mgr.stop_project(project_id):
        return {"success": True}
    return {"success": False, "message": "Project not running"}


@app.get("/api/projects/{project_id}/status", response_model=ProjectStatusResponse, tags=["Projects"])
async def get_project_status(project_id: str):
    """Get project status."""
    mgr = get_project_manager()
    status = mgr.get_status(project_id)
    return ProjectStatusResponse(**status.to_dict())


# =============================================================================
# Attachments API
# =============================================================================

@app.post("/api/attachments", response_model=AttachmentResponse, tags=["Attachments"])
async def upload_attachment(request: AttachmentUploadRequest):
    """Upload a file attachment."""
    mgr = get_attachment_manager()
    try:
        attachment = await mgr.upload_base64(
            request.filename,
            request.content_base64,
            request.session_id,
        )
        return AttachmentResponse(**attachment.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/attachments/upload", response_model=AttachmentResponse, tags=["Attachments"])
async def upload_file_multipart(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """Upload a file using multipart form data."""
    mgr = get_attachment_manager()
    try:
        content = await file.read()
        attachment = await mgr.upload_file(file.filename, content, session_id)
        return AttachmentResponse(**attachment.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/attachments/{session_id}", response_model=AttachmentListResponse, tags=["Attachments"])
async def list_attachments(session_id: str):
    """List attachments for a session."""
    mgr = get_attachment_manager()
    attachments = mgr.get_session_attachments(session_id)
    return AttachmentListResponse(
        attachments=[AttachmentResponse(**a.to_dict()) for a in attachments],
        total=len(attachments),
    )


@app.get("/api/attachments/{session_id}/{attachment_id}", tags=["Attachments"])
async def get_attachment_content(session_id: str, attachment_id: str):
    """Get attachment content."""
    mgr = get_attachment_manager()
    content = mgr.read_attachment_text(attachment_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Attachment not found or not readable")
    return {"content": content}


@app.delete("/api/attachments/{session_id}/{attachment_id}", tags=["Attachments"])
async def delete_attachment(session_id: str, attachment_id: str):
    """Delete an attachment."""
    mgr = get_attachment_manager()
    if mgr.delete_attachment(attachment_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Attachment not found")


# =============================================================================
# Project Memory API
# =============================================================================

@app.get("/api/projects/{project_id}/context", response_model=ProjectContextResponse, tags=["Project Memory"])
async def get_project_context(project_id: str):
    """Get the full context for a project."""
    proj_mgr = get_project_manager()
    project = proj_mgr.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    mem_mgr = get_project_memory_manager()
    db = mem_mgr.get_db(project_id, project.path)
    ctx = db.get_full_context(project.name)
    return ProjectContextResponse(**ctx.to_dict())


@app.post("/api/projects/{project_id}/memory", tags=["Project Memory"])
async def add_memory(project_id: str, request: ProjectMemoryAddRequest):
    """Add a memory entry to a project."""
    proj_mgr = get_project_manager()
    project = proj_mgr.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    mem_mgr = get_project_memory_manager()
    db = mem_mgr.get_db(project_id, project.path)
    entry_id = db.add_memory(request.entry_type, request.content, request.metadata)
    return {"success": True, "id": entry_id}


@app.post("/api/projects/{project_id}/tasks", tags=["Project Memory"])
async def add_task(project_id: str, request: TaskCreateRequest):
    """Add a task to a project."""
    proj_mgr = get_project_manager()
    project = proj_mgr.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    mem_mgr = get_project_memory_manager()
    db = mem_mgr.get_db(project_id, project.path)
    task_id = db.add_task(request.title, request.description)
    return {"success": True, "id": task_id}


@app.post("/api/projects/{project_id}/tasks/{task_id}/complete", tags=["Project Memory"])
async def complete_task(project_id: str, task_id: int):
    """Mark a task as complete."""
    proj_mgr = get_project_manager()
    project = proj_mgr.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    mem_mgr = get_project_memory_manager()
    db = mem_mgr.get_db(project_id, project.path)
    if db.complete_task(task_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Task not found")


@app.get("/api/projects/{project_id}/tasks", tags=["Project Memory"])
async def list_tasks(project_id: str):
    """List active tasks for a project."""
    proj_mgr = get_project_manager()
    project = proj_mgr.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    mem_mgr = get_project_memory_manager()
    db = mem_mgr.get_db(project_id, project.path)
    tasks = db.get_active_tasks()
    return {"tasks": tasks}


# =============================================================================
# Settings & Model Configuration API
# =============================================================================

@app.get("/api/settings", response_model=GlobalSettingsResponse, tags=["Settings"])
async def get_settings():
    """Get global settings."""
    mgr = get_model_config_manager()
    settings = mgr.get_settings()
    return GlobalSettingsResponse(
        default_provider=settings.default_provider.value,
        council_enabled=settings.council_enabled,
        council_strategy=settings.council_strategy,
        use_local_only=settings.use_local_only,
        fallback_to_dummy=settings.fallback_to_dummy,
        rag_enabled=settings.rag_enabled,
        rag_top_k=settings.rag_top_k,
        memory_max_turns=settings.memory_max_turns,
    )


@app.patch("/api/settings", response_model=GlobalSettingsResponse, tags=["Settings"])
async def update_settings(request: GlobalSettingsUpdate):
    """Update global settings."""
    mgr = get_model_config_manager()
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    settings = mgr.update_settings(updates)
    return GlobalSettingsResponse(
        default_provider=settings.default_provider.value,
        council_enabled=settings.council_enabled,
        council_strategy=settings.council_strategy,
        use_local_only=settings.use_local_only,
        fallback_to_dummy=settings.fallback_to_dummy,
        rag_enabled=settings.rag_enabled,
        rag_top_k=settings.rag_top_k,
        memory_max_turns=settings.memory_max_turns,
    )


@app.get("/api/providers", response_model=List[ProviderInfoResponse], tags=["Settings"])
async def list_providers():
    """List all available model providers."""
    mgr = get_model_config_manager()
    return [ProviderInfoResponse(**p) for p in mgr.list_providers()]


@app.get("/api/providers/{provider_id}/status", response_model=ProviderStatusResponse, tags=["Settings"])
async def check_provider_status(provider_id: str):
    """Check if a provider is available."""
    mgr = get_model_config_manager()
    try:
        provider = ModelProvider(provider_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")
    
    status = await mgr.check_provider_status(provider)
    return ProviderStatusResponse(
        provider=status.provider.value,
        available=status.available,
        error=status.error,
        models=status.models,
        version=status.version,
    )


@app.get("/api/models", response_model=List[ModelConfigResponse], tags=["Settings"])
async def list_model_configs(enabled_only: bool = False, council_only: bool = False):
    """List configured models."""
    mgr = get_model_config_manager()
    models = mgr.list_models(enabled_only=enabled_only, council_only=council_only)
    return [
        ModelConfigResponse(
            id=m.id,
            name=m.name,
            provider=m.provider.value,
            model_id=m.model_id,
            enabled=m.enabled,
            is_council_member=m.is_council_member,
            base_url=m.base_url,
            temperature=m.temperature,
            max_tokens=m.max_tokens,
            created_at=m.created_at.isoformat(),
        )
        for m in models
    ]


@app.post("/api/models", response_model=ModelConfigResponse, tags=["Settings"])
async def create_model_config(request: ModelConfigCreate):
    """Add a new model configuration."""
    mgr = get_model_config_manager()
    
    try:
        provider = ModelProvider(request.provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider}")
    
    import uuid
    model_id = f"{request.provider}-{str(uuid.uuid4())[:8]}"
    
    config = ModelConfig(
        id=model_id,
        name=request.name,
        provider=provider,
        model_id=request.model_id,
        enabled=request.enabled,
        is_council_member=request.is_council_member,
        base_url=request.base_url,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    
    mgr.add_model(config)
    
    return ModelConfigResponse(
        id=config.id,
        name=config.name,
        provider=config.provider.value,
        model_id=config.model_id,
        enabled=config.enabled,
        is_council_member=config.is_council_member,
        base_url=config.base_url,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        created_at=config.created_at.isoformat(),
    )


@app.patch("/api/models/{model_id}", response_model=ModelConfigResponse, tags=["Settings"])
async def update_model_config(model_id: str, request: ModelConfigUpdate):
    """Update a model configuration."""
    mgr = get_model_config_manager()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    config = mgr.update_model(model_id, updates)
    
    if not config:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return ModelConfigResponse(
        id=config.id,
        name=config.name,
        provider=config.provider.value,
        model_id=config.model_id,
        enabled=config.enabled,
        is_council_member=config.is_council_member,
        base_url=config.base_url,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        created_at=config.created_at.isoformat(),
    )


@app.delete("/api/models/{model_id}", tags=["Settings"])
async def delete_model_config(model_id: str):
    """Delete a model configuration."""
    mgr = get_model_config_manager()
    if mgr.delete_model(model_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Model not found or cannot be deleted")


@app.post("/api/providers/{provider_id}/api-key", tags=["Settings"])
async def set_api_key(provider_id: str, request: ApiKeyRequest):
    """Set API key for a provider."""
    mgr = get_model_config_manager()
    try:
        provider = ModelProvider(provider_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")
    
    mgr.set_api_key(provider, request.api_key)
    return {"success": True}


@app.delete("/api/providers/{provider_id}/api-key", tags=["Settings"])
async def delete_api_key(provider_id: str):
    """Delete API key for a provider."""
    mgr = get_model_config_manager()
    try:
        provider = ModelProvider(provider_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")
    
    mgr.delete_api_key(provider)
    return {"success": True}


@app.get("/api/providers/{provider_id}/has-key", tags=["Settings"])
async def check_api_key(provider_id: str):
    """Check if API key is configured for a provider."""
    mgr = get_model_config_manager()
    try:
        provider = ModelProvider(provider_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")
    
    return {"has_key": mgr.has_api_key(provider)}


# Ollama-specific endpoints
@app.post("/api/ollama/pull", tags=["Ollama"])
async def pull_ollama_model(request: OllamaModelRequest):
    """Pull/install an Ollama model."""
    mgr = get_model_config_manager()
    result = await mgr.pull_ollama_model(request.model_name)
    if result["success"]:
        return result
    raise HTTPException(status_code=500, detail=result.get("error", "Failed to pull model"))


@app.delete("/api/ollama/model/{model_name}", tags=["Ollama"])
async def delete_ollama_model(model_name: str):
    """Delete an Ollama model."""
    mgr = get_model_config_manager()
    result = await mgr.delete_ollama_model(model_name)
    if result["success"]:
        return result
    raise HTTPException(status_code=500, detail=result.get("error", "Failed to delete model"))


# =============================================================================
# Memory & Training API
# =============================================================================

@app.get("/api/memory/stats", tags=["Memory & Training"])
async def get_memory_stats():
    """Get current memory logging statistics."""
    logger = get_memory_logger()
    return logger.get_session_stats()


@app.get("/api/memory/analytics", tags=["Memory & Training"])
async def get_analytics():
    """Generate comprehensive analytics report."""
    logger = get_memory_logger()
    return logger.generate_analytics_report()


@app.post("/api/memory/feedback/{conversation_id}", tags=["Memory & Training"])
async def submit_feedback(
    conversation_id: str,
    thumbs_up: bool,
    feedback: str = None,
):
    """Submit feedback for a conversation."""
    logger = get_memory_logger()
    
    if thumbs_up:
        logger.thumbs_up(conversation_id)
    else:
        logger.thumbs_down(conversation_id, feedback)
    
    return {"success": True, "conversation_id": conversation_id}


@app.post("/api/memory/rate/{conversation_id}", tags=["Memory & Training"])
async def rate_conversation(
    conversation_id: str,
    quality: str,  # excellent, good, acceptable, poor, failed
    feedback: str = None,
):
    """Rate a conversation's quality for training."""
    logger = get_memory_logger()
    
    try:
        q = InteractionQuality(quality)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid quality: {quality}")
    
    logger.rate_conversation(conversation_id, q, feedback)
    return {"success": True}


@app.post("/api/memory/export", tags=["Memory & Training"])
async def export_training_data(
    min_quality: str = "acceptable",
    start_date: str = None,
    end_date: str = None,
):
    """Export logged conversations as training data."""
    logger = get_memory_logger()
    
    try:
        q = InteractionQuality(min_quality)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid quality: {min_quality}")
    
    stats = logger.export_training_data(
        min_quality=q,
        start_date=start_date,
        end_date=end_date,
    )
    return stats


@app.get("/api/training/status", tags=["Memory & Training"])
async def get_training_status():
    """Get current training system status."""
    trainer = get_auto_trainer()
    return trainer.get_training_status()


@app.get("/api/training/data-stats", tags=["Memory & Training"])
async def get_training_data_stats():
    """Get statistics about available training data."""
    trainer = get_auto_trainer()
    return trainer.data_preparer.get_data_stats()


@app.post("/api/training/start", tags=["Memory & Training"])
async def start_training(
    force: bool = False,
    epochs: int = None,
    learning_rate: float = None,
):
    """Start a training run to enhance the model."""
    trainer = get_auto_trainer()
    
    # Check readiness
    if not force:
        check = trainer.should_train()
        if not check["should_train"]:
            raise HTTPException(
                status_code=400,
                detail=f"Not ready for training: {check['reason']}"
            )
    
    # Create custom config if params provided
    config = TrainingConfig()
    if epochs is not None:
        config.epochs = epochs
    if learning_rate is not None:
        config.learning_rate = learning_rate
    
    try:
        run = trainer.start_training(config=config, force=force)
        return {
            "success": True,
            "run_id": run.run_id,
            "num_samples": run.num_samples,
            "status": run.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/training/models", tags=["Memory & Training"])
async def list_trained_models():
    """List all trained/enhanced models."""
    trainer = get_auto_trainer()
    return {"models": trainer.list_models()}


@app.get("/api/training/should-train", tags=["Memory & Training"])
async def check_should_train():
    """Check if the system is ready for training."""
    trainer = get_auto_trainer()
    return trainer.should_train()


# =============================================================================
# Legacy
# =============================================================================

@app.post("/chat", include_in_schema=False)
async def chat_legacy(request: ChatRequest) -> ChatResponse:
    return await chat(request)
