"""
routes_vscode.py - VSCode Sandbox API endpoints.

Provides endpoints for:
- Project root management
- code-server lifecycle control
- Command execution with allowlist
- LLM model assist for code
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ChatOS.controllers.vscode_manager import (
    CommandResult,
    ProjectInfo,
    VSCodeStatus,
    get_vscode_manager,
)
from ChatOS.controllers.llm_client import get_llm_client
from ChatOS.controllers.model_config import get_model_config_manager


router = APIRouter(prefix="/api/sandbox", tags=["VSCode Sandbox"])


# =============================================================================
# Request/Response Models
# =============================================================================

class VSCodeStartRequest(BaseModel):
    """Request to start code-server."""
    workspace: Optional[str] = Field(
        None,
        description="Workspace directory path (must be within allowed roots)",
    )
    port: Optional[int] = Field(
        None,
        description="Port to run code-server on (defaults to config)",
    )


class VSCodeStatusResponse(BaseModel):
    """Response with code-server status."""
    running: bool
    pid: Optional[int] = None
    port: int
    host: str
    workspace: Optional[str] = None
    url: Optional[str] = None
    started_at: Optional[str] = None
    error: Optional[str] = None


class ProjectInfoResponse(BaseModel):
    """Response with project information."""
    path: str
    name: str
    exists: bool
    is_git: bool = False
    file_count: int = 0


class CommandRunRequest(BaseModel):
    """Request to run a command."""
    command: str = Field(
        ...,
        description="The command to execute (must be in allowlist)",
    )
    args: Optional[List[str]] = Field(
        None,
        description="Optional list of arguments",
    )
    cwd: Optional[str] = Field(
        None,
        description="Working directory (must be within project roots)",
    )
    timeout: Optional[int] = Field(
        None,
        description="Execution timeout in seconds",
    )


class CommandRunResponse(BaseModel):
    """Response from command execution."""
    success: bool
    command: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    truncated: bool = False


class ModelAssistRequest(BaseModel):
    """Request for LLM code assistance."""
    instruction: str = Field(
        ...,
        description="What you want the AI to do (explain, refactor, test, etc.)",
    )
    code: str = Field(
        ...,
        description="The code to analyze or modify",
    )
    language: str = Field(
        "python",
        description="Programming language of the code",
    )
    file_path: Optional[str] = Field(
        None,
        description="Optional file path for context",
    )
    extra_context: Optional[str] = Field(
        None,
        description="Additional context to include",
    )


class ModelAssistResponse(BaseModel):
    """Response from model assist."""
    message: str
    suggestions: Optional[List[str]] = None
    patches: Optional[List[dict]] = None
    model_used: str


# =============================================================================
# Project Endpoints
# =============================================================================

@router.get("/projects", response_model=List[ProjectInfoResponse])
async def list_projects():
    """
    List all configured project roots.
    
    Returns information about each allowed project directory including
    whether it exists, if it's a git repo, and file count.
    """
    manager = get_vscode_manager()
    projects = manager.list_project_roots()
    
    return [
        ProjectInfoResponse(
            path=p.path,
            name=p.name,
            exists=p.exists,
            is_git=p.is_git,
            file_count=p.file_count,
        )
        for p in projects
    ]


# =============================================================================
# VSCode Server Endpoints
# =============================================================================

@router.get("/vscode/status", response_model=VSCodeStatusResponse)
async def get_vscode_status():
    """
    Get the current status of code-server.
    
    Returns whether code-server is running, its URL, and workspace info.
    """
    manager = get_vscode_manager()
    status = manager.get_status()
    
    return VSCodeStatusResponse(
        running=status.running,
        pid=status.pid,
        port=status.port,
        host=status.host,
        workspace=status.workspace,
        url=status.url,
        started_at=status.started_at.isoformat() if status.started_at else None,
        error=status.error,
    )


@router.post("/vscode/start", response_model=VSCodeStatusResponse)
async def start_vscode(request: VSCodeStartRequest = None):
    """
    Start code-server for a workspace.
    
    The workspace must be within one of the configured project roots.
    If not specified, defaults to the first project root.
    """
    manager = get_vscode_manager()
    
    workspace = request.workspace if request else None
    port = request.port if request else None
    
    status = await manager.start_server(workspace=workspace, port=port)
    
    if status.error and not status.running:
        raise HTTPException(status_code=400, detail=status.error)
    
    return VSCodeStatusResponse(
        running=status.running,
        pid=status.pid,
        port=status.port,
        host=status.host,
        workspace=status.workspace,
        url=status.url,
        started_at=status.started_at.isoformat() if status.started_at else None,
        error=status.error,
    )


@router.post("/vscode/stop")
async def stop_vscode():
    """
    Stop the running code-server instance.
    """
    manager = get_vscode_manager()
    success = await manager.stop_server()
    
    return {"success": success}


@router.get("/vscode/health")
async def vscode_health():
    """
    Check if code-server is healthy and responding.
    """
    manager = get_vscode_manager()
    healthy = await manager.is_healthy()
    
    return {"healthy": healthy}


# =============================================================================
# Command Execution Endpoints
# =============================================================================

@router.post("/run", response_model=CommandRunResponse)
async def run_command(request: CommandRunRequest):
    """
    Execute a command in the sandbox.
    
    The command must be in the allowlist (python, node, npm, git, etc.).
    Working directory must be within configured project roots.
    """
    manager = get_vscode_manager()
    
    result = await manager.run_command(
        command=request.command,
        args=request.args,
        cwd=request.cwd,
        timeout=request.timeout,
    )
    
    return CommandRunResponse(
        success=result.success,
        command=result.command,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        execution_time=result.execution_time,
        truncated=result.truncated,
    )


@router.get("/allowed-commands")
async def list_allowed_commands():
    """
    List all commands that are allowed to be executed.
    """
    from ChatOS.config import SANDBOX_ALLOWED_COMMANDS
    return {"commands": SANDBOX_ALLOWED_COMMANDS}


# =============================================================================
# Model Assist Endpoints
# =============================================================================

@router.post("/model-assist", response_model=ModelAssistResponse)
async def model_assist(request: ModelAssistRequest):
    """
    Get AI assistance for code.
    
    Supports instructions like:
    - "explain this code"
    - "refactor for better performance"
    - "add error handling"
    - "generate unit tests"
    - "document this function"
    - "find bugs"
    """
    # Build the prompt for the LLM
    system_prompt = f"""You are a helpful coding assistant. You help developers understand, improve, and test their code.

When responding:
- Be concise and practical
- Provide code examples when relevant
- Explain your reasoning
- Consider best practices for {request.language}

The user is working on: {request.file_path or 'a code snippet'}
"""

    user_prompt = f"""Instruction: {request.instruction}

Language: {request.language}

Code:
```{request.language}
{request.code}
```
"""

    if request.extra_context:
        user_prompt += f"\nAdditional context:\n{request.extra_context}\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Get the LLM client and model config
    llm_client = get_llm_client()
    config_manager = get_model_config_manager()
    
    # Try to get an enabled model, preferring code-focused ones
    models = config_manager.list_models(enabled_only=True)
    
    if not models:
        raise HTTPException(
            status_code=503,
            detail="No LLM models available. Configure a model in settings.",
        )
    
    # Use the first available model
    model_config = models[0]
    
    # Generate response
    response = await llm_client.generate(
        model_config=model_config,
        messages=messages,
        temperature=0.3,  # Lower temperature for code tasks
    )
    
    if response.error:
        raise HTTPException(status_code=500, detail=response.error)
    
    # Parse the response for suggestions (simple extraction)
    suggestions = []
    message = response.text
    
    # Try to extract code blocks as suggestions
    import re
    code_blocks = re.findall(r'```[\w]*\n(.*?)```', message, re.DOTALL)
    if code_blocks:
        suggestions = [block.strip() for block in code_blocks]
    
    return ModelAssistResponse(
        message=message,
        suggestions=suggestions if suggestions else None,
        patches=None,  # Could implement diff patches in future
        model_used=response.model,
    )


@router.post("/model-assist/explain")
async def explain_code(code: str, language: str = "python"):
    """
    Shortcut endpoint to explain code.
    """
    return await model_assist(ModelAssistRequest(
        instruction="Explain this code in detail. What does it do? How does it work?",
        code=code,
        language=language,
    ))


@router.post("/model-assist/refactor")
async def refactor_code(code: str, language: str = "python"):
    """
    Shortcut endpoint to get refactoring suggestions.
    """
    return await model_assist(ModelAssistRequest(
        instruction="Suggest improvements to make this code cleaner, more efficient, and more maintainable. Provide the refactored version.",
        code=code,
        language=language,
    ))


@router.post("/model-assist/tests")
async def generate_tests(code: str, language: str = "python"):
    """
    Shortcut endpoint to generate tests.
    """
    return await model_assist(ModelAssistRequest(
        instruction="Generate comprehensive unit tests for this code. Cover edge cases and common scenarios.",
        code=code,
        language=language,
    ))

