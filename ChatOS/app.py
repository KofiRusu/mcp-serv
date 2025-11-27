"""
ChatOS - A PewDiePie-style Local AI Interface

This FastAPI application provides a web interface to chat with
multiple local models orchestrated as a "council of bots".

Features:
- Multi-model council with voting/selection
- Conversation memory (sliding window)
- Simple RAG over local text files
- Normal and coding modes
- /research - Deep research with web context
- /deepthinking - Chain-of-thought reflection
- /swarm - Multi-agent coding collaboration
- Coding sandbox with file operations

Run with: uvicorn ChatOS.app:app --reload
"""

from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ChatOS import __version__
from ChatOS.config import STATIC_DIR, TEMPLATES_DIR, COMMAND_MODES
from ChatOS.controllers.chat import chat_endpoint, get_council_info, get_available_commands
from ChatOS.controllers.sandbox import get_sandbox, CodeEdit
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
)

# =============================================================================
# App Configuration
# =============================================================================

app = FastAPI(
    title="ChatOS",
    description="A PewDiePie-style local AI interface with council-of-bots, /research, /deepthinking, /swarm modes",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# =============================================================================
# HTML Routes
# =============================================================================

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    """Serve the main chat page."""
    return templates.TemplateResponse(request, "index.html")


@app.get("/sandbox", response_class=HTMLResponse, include_in_schema=False)
async def sandbox_page(request: Request) -> HTMLResponse:
    """Serve the coding sandbox page."""
    return templates.TemplateResponse(request, "sandbox.html")


# =============================================================================
# Chat API Routes
# =============================================================================

@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check endpoint",
)
async def health() -> HealthResponse:
    """Check the health status of the ChatOS service."""
    info = get_council_info()
    return HealthResponse(
        status="healthy",
        version=__version__,
        models_loaded=len(info["models"]),
        rag_documents=info["rag_documents"],
    )


@app.get(
    "/api/council",
    response_model=CouncilInfoResponse,
    tags=["System"],
    summary="Get council configuration",
)
async def council_info() -> CouncilInfoResponse:
    """Get information about the current council configuration."""
    info = get_council_info()
    return CouncilInfoResponse(**info)


@app.get(
    "/api/commands",
    response_model=List[CommandInfo],
    tags=["System"],
    summary="Get available commands",
)
async def list_commands() -> List[CommandInfo]:
    """Get list of available /commands."""
    commands = get_available_commands()
    return [
        CommandInfo(name=name, description=info["description"], icon=info["icon"])
        for name, info in commands.items()
    ]


@app.post(
    "/api/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["Chat"],
    summary="Send a message to the council",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a message to the model council and receive a response.
    
    **Commands:**
    - `/research <query>` - Deep research with web context
    - `/deepthinking <query>` - Chain-of-thought reflection
    - `/swarm <task>` - Multi-agent coding collaboration
    - `/code <query>` - Code-focused responses
    
    **Examples:**
    - `Hello, how are you?` - Normal chat
    - `/research FastAPI best practices` - Research mode
    - `/deepthinking Solve this optimization problem` - Deep thinking
    - `/swarm Build a REST API for user management` - Swarm mode
    """
    try:
        result = await chat_endpoint(
            message=request.message,
            mode=request.mode,
            use_rag=request.use_rag,
            session_id=request.session_id,
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )


# =============================================================================
# Sandbox API Routes
# =============================================================================

@app.get(
    "/api/sandbox/files",
    response_model=FileTreeResponse,
    tags=["Sandbox"],
    summary="Get file tree",
)
async def get_file_tree():
    """Get the file tree of the sandbox directory."""
    sandbox = get_sandbox()
    tree = sandbox.get_file_tree()
    files = sandbox.list_files()
    return FileTreeResponse(
        root=tree.to_dict(),
        total_files=len(files),
    )


@app.get(
    "/api/sandbox/file",
    response_model=FileContentResponse,
    tags=["Sandbox"],
    summary="Read file content",
)
async def read_file(path: str):
    """Read the content of a file in the sandbox."""
    sandbox = get_sandbox()
    try:
        content = sandbox.read_file(path)
        return FileContentResponse(
            path=path,
            content=content,
            size=len(content),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/api/sandbox/file",
    tags=["Sandbox"],
    summary="Write file content",
)
async def write_file(request: SandboxFileRequest):
    """Write content to a file in the sandbox."""
    sandbox = get_sandbox()
    try:
        sandbox.write_file(request.path, request.content or "")
        return {"success": True, "path": request.path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete(
    "/api/sandbox/file",
    tags=["Sandbox"],
    summary="Delete file",
)
async def delete_file(path: str):
    """Delete a file or directory in the sandbox."""
    sandbox = get_sandbox()
    try:
        sandbox.delete_file(path)
        return {"success": True, "path": path}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")


@app.post(
    "/api/sandbox/directory",
    tags=["Sandbox"],
    summary="Create directory",
)
async def create_directory(path: str):
    """Create a new directory in the sandbox."""
    sandbox = get_sandbox()
    try:
        sandbox.create_directory(path)
        return {"success": True, "path": path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/api/sandbox/execute",
    response_model=ExecutionResponse,
    tags=["Sandbox"],
    summary="Execute Python code",
)
async def execute_code(request: SandboxExecuteRequest):
    """Execute Python code in the sandbox."""
    sandbox = get_sandbox()
    result = sandbox.execute_python(
        code=request.code,
        file_path=request.file_path,
        timeout=request.timeout,
    )
    return ExecutionResponse(
        success=result.success,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        execution_time=result.execution_time,
    )


@app.post(
    "/api/sandbox/search",
    response_model=SearchResponse,
    tags=["Sandbox"],
    summary="Search in files",
)
async def search_files(request: SearchRequest):
    """Search for a pattern in sandbox files."""
    sandbox = get_sandbox()
    matches = sandbox.search_in_files(
        pattern=request.pattern,
        path=request.path,
        file_pattern=request.file_pattern,
    )
    return SearchResponse(
        pattern=request.pattern,
        matches=[SearchResult(**m) for m in matches],
        total_matches=len(matches),
    )


@app.post(
    "/api/sandbox/undo",
    tags=["Sandbox"],
    summary="Undo last edit",
)
async def undo_edit():
    """Undo the last file edit."""
    sandbox = get_sandbox()
    undone_file = sandbox.undo_last_edit()
    if undone_file:
        return {"success": True, "file": undone_file}
    return {"success": False, "message": "No edits to undo"}


# =============================================================================
# Legacy endpoint for backward compatibility
# =============================================================================

@app.post("/chat", include_in_schema=False)
async def chat_legacy(request: ChatRequest) -> ChatResponse:
    """Legacy chat endpoint - redirects to /api/chat."""
    return await chat(request)
