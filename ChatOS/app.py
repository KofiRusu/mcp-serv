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
# Legacy
# =============================================================================

@app.post("/chat", include_in_schema=False)
async def chat_legacy(request: ChatRequest) -> ChatResponse:
    return await chat(request)
