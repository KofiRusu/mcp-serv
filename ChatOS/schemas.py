"""
Pydantic models for API request/response schemas.

These schemas provide validation and documentation for the API endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Chat Request/Response
# =============================================================================

class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user's message to send to the council",
    )
    mode: str = Field(default="normal", description="Chat mode")
    use_rag: bool = Field(default=True, description="Include RAG context")
    session_id: Optional[str] = Field(None, description="Session identifier")
    project_id: Optional[str] = Field(None, description="Project ID for project-specific context")
    attachment_ids: Optional[List[str]] = Field(None, description="IDs of attached files")
    model_id: Optional[str] = Field(None, description="Specific model ID to use (bypasses council voting)")


class ModelResponse(BaseModel):
    """Individual model response."""
    model: str
    text: str


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    answer: str
    chosen_model: str
    responses: List[ModelResponse]
    memory_summary: Optional[str] = None
    mode: Optional[str] = None
    command: Optional[str] = None
    research_context: Optional[Dict[str, Any]] = None
    thinking_result: Optional[Dict[str, Any]] = None
    swarm_result: Optional[Dict[str, Any]] = None


# =============================================================================
# System
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    version: str
    models_loaded: int
    rag_documents: int


class ModelInfo(BaseModel):
    name: str
    behavior: str


class CommandInfo(BaseModel):
    name: str
    description: str
    icon: str


class CouncilInfoResponse(BaseModel):
    models: List[ModelInfo]
    strategy: str
    rag_documents: int
    available_commands: List[str]


# =============================================================================
# Sandbox
# =============================================================================

class SandboxFileRequest(BaseModel):
    path: str
    content: Optional[str] = None


class SandboxExecuteRequest(BaseModel):
    code: Optional[str] = None
    file_path: Optional[str] = None
    timeout: int = 30


class SearchRequest(BaseModel):
    pattern: str
    path: str = ""
    file_pattern: str = "*"


class FileInfo(BaseModel):
    name: str
    path: str
    extension: str
    size: int
    modified: str
    is_directory: bool
    children: List["FileInfo"] = []


class FileTreeResponse(BaseModel):
    root: Dict[str, Any]
    total_files: int


class FileContentResponse(BaseModel):
    path: str
    content: str
    size: int


class ExecutionResponse(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int
    execution_time: float


class SearchResult(BaseModel):
    file: str
    line: int
    content: str


class SearchResponse(BaseModel):
    pattern: str
    matches: List[SearchResult]
    total_matches: int


# =============================================================================
# Projects
# =============================================================================

class ProjectCreateRequest(BaseModel):
    """Request to create a new project."""
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    template: str = Field(default="python-basic", description="Project template")
    description: str = Field(default="", description="Project description")
    auto_setup: bool = Field(default=True, description="Auto-create venv and install deps")


class ProjectRunRequest(BaseModel):
    """Request to run a project."""
    command: Optional[str] = Field(None, description="Custom run command")
    background: bool = Field(default=False, description="Run in background")
    timeout: int = Field(default=60, description="Execution timeout")


class ProjectInstallRequest(BaseModel):
    """Request to install dependencies."""
    extra_packages: Optional[List[str]] = Field(None, description="Additional packages")


class ProjectStatusResponse(BaseModel):
    """Project status response."""
    exists: bool
    has_venv: bool = False
    venv_path: Optional[str] = None
    has_requirements: bool = False
    dependencies_installed: bool = False
    is_running: bool = False
    process_pid: Optional[int] = None
    files_count: int = 0


class ProjectResponse(BaseModel):
    """Full project response."""
    id: str
    name: str
    path: str
    template: str
    description: str
    created_at: str
    has_venv: bool
    dependencies_installed: bool
    status: Optional[ProjectStatusResponse] = None


class ProjectTemplateResponse(BaseModel):
    """Project template info."""
    id: str
    name: str
    description: str


class ProjectListResponse(BaseModel):
    """List of projects."""
    projects: List[ProjectResponse]
    total: int


# =============================================================================
# Attachments
# =============================================================================

class AttachmentUploadRequest(BaseModel):
    """Request to upload a file."""
    filename: str = Field(..., description="Original filename")
    content_base64: str = Field(..., description="Base64-encoded file content")
    session_id: str = Field(..., description="Session ID")


class AttachmentResponse(BaseModel):
    """Attachment info response."""
    id: str
    filename: str
    original_filename: str
    mime_type: str
    size: int
    session_id: str
    created_at: str
    content_preview: str = ""


class AttachmentListResponse(BaseModel):
    """List of attachments."""
    attachments: List[AttachmentResponse]
    total: int


# =============================================================================
# Project Memory
# =============================================================================

class ProjectMemoryAddRequest(BaseModel):
    """Request to add a memory entry."""
    entry_type: str = Field(..., description="Type: conversation, decision, note, task")
    content: str = Field(..., description="Memory content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TaskCreateRequest(BaseModel):
    """Request to create a task."""
    title: str
    description: str = ""


class ProjectContextResponse(BaseModel):
    """Project context response."""
    project_id: str
    project_name: str
    summary: str = ""
    recent_conversations: List[Dict[str, str]] = []
    key_decisions: List[str] = []
    active_tasks: List[str] = []
    file_history: List[Dict[str, Any]] = []
    notes: List[str] = []


# =============================================================================
# Model Configuration
# =============================================================================

class ModelConfigCreate(BaseModel):
    """Request to create a model configuration."""
    name: str = Field(..., description="Display name for the model")
    provider: str = Field(..., description="Provider ID (ollama, openai, etc.)")
    model_id: str = Field(..., description="Model identifier (e.g., llama3.2, gpt-4o)")
    enabled: bool = Field(default=True)
    is_council_member: bool = Field(default=True, description="Include in council voting")
    base_url: Optional[str] = Field(None, description="Custom API endpoint URL")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2048)


class ModelConfigUpdate(BaseModel):
    """Request to update a model configuration."""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    is_council_member: Optional[bool] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ModelConfigResponse(BaseModel):
    """Model configuration response."""
    id: str
    name: str
    provider: str
    model_id: str
    enabled: bool
    is_council_member: bool
    base_url: Optional[str]
    temperature: float
    max_tokens: int
    created_at: str


class ProviderInfoResponse(BaseModel):
    """Provider information."""
    id: str
    name: str
    description: str
    type: str  # "local", "api", "builtin"
    requires_key: bool
    default_models: List[str]


class ProviderStatusResponse(BaseModel):
    """Provider status check result."""
    provider: str
    available: bool
    error: Optional[str]
    models: List[str]
    version: Optional[str]


class GlobalSettingsUpdate(BaseModel):
    """Update global settings."""
    default_provider: Optional[str] = None
    council_enabled: Optional[bool] = None
    council_strategy: Optional[str] = None
    use_local_only: Optional[bool] = None
    fallback_to_dummy: Optional[bool] = None
    rag_enabled: Optional[bool] = None
    rag_top_k: Optional[int] = None
    memory_max_turns: Optional[int] = None


class GlobalSettingsResponse(BaseModel):
    """Global settings response."""
    default_provider: str
    council_enabled: bool
    council_strategy: str
    use_local_only: bool
    fallback_to_dummy: bool
    rag_enabled: bool
    rag_top_k: int
    memory_max_turns: int


class ApiKeyRequest(BaseModel):
    """Request to set API key."""
    provider: str
    api_key: str


class OllamaModelRequest(BaseModel):
    """Request for Ollama model operations."""
    model_name: str


# =============================================================================
# Error
# =============================================================================

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# Fix forward references
FileInfo.model_rebuild()
