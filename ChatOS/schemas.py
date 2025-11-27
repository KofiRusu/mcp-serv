"""
Pydantic models for API request/response schemas.

These schemas provide validation and documentation for the API endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Request Schemas
# =============================================================================

class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user's message to send to the council",
        examples=["Hello!", "/research FastAPI best practices", "/swarm Build a REST API"]
    )
    
    mode: str = Field(
        default="normal",
        description="Chat mode: 'normal', 'code', or auto-detected from /commands",
        examples=["normal", "code"]
    )
    
    use_rag: bool = Field(
        default=True,
        description="Whether to include context from local documents (RAG)"
    )
    
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session identifier for conversation memory"
    )


class SandboxFileRequest(BaseModel):
    """Request for sandbox file operations."""
    
    path: str = Field(..., description="File path relative to sandbox")
    content: Optional[str] = Field(None, description="File content for write operations")


class SandboxExecuteRequest(BaseModel):
    """Request for code execution in sandbox."""
    
    code: Optional[str] = Field(None, description="Python code to execute")
    file_path: Optional[str] = Field(None, description="Path to Python file to execute")
    timeout: int = Field(default=30, description="Execution timeout in seconds")


class SearchRequest(BaseModel):
    """Request for searching in sandbox files."""
    
    pattern: str = Field(..., description="Search pattern")
    path: str = Field(default="", description="Directory to search")
    file_pattern: str = Field(default="*", description="Glob pattern for files")


# =============================================================================
# Response Schemas
# =============================================================================

class ModelResponse(BaseModel):
    """Individual model response within the council."""
    
    model: str = Field(..., description="Name of the model/agent")
    text: str = Field(..., description="The response text")


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    
    answer: str = Field(..., description="The selected/winning response")
    chosen_model: str = Field(..., description="Name of the model whose response was selected")
    responses: List[ModelResponse] = Field(..., description="All individual responses")
    memory_summary: Optional[str] = Field(None, description="Conversation memory state")
    mode: Optional[str] = Field(None, description="Mode used for this response")
    command: Optional[str] = Field(None, description="Command if a /command was used")
    
    # Special mode results
    research_context: Optional[Dict[str, Any]] = Field(None, description="Research mode results")
    thinking_result: Optional[Dict[str, Any]] = Field(None, description="Deep thinking results")
    swarm_result: Optional[Dict[str, Any]] = Field(None, description="Swarm mode results")


class HealthResponse(BaseModel):
    """Response from the health check endpoint."""
    
    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="API version")
    models_loaded: int = Field(..., description="Number of models loaded")
    rag_documents: int = Field(..., description="Number of RAG documents")


class ModelInfo(BaseModel):
    """Information about a single model."""
    
    name: str = Field(..., description="Model display name")
    behavior: str = Field(..., description="Model behavior/personality type")


class CommandInfo(BaseModel):
    """Information about a command."""
    
    name: str = Field(..., description="Command name (without /)")
    description: str = Field(..., description="What the command does")
    icon: str = Field(..., description="Command icon emoji")


class CouncilInfoResponse(BaseModel):
    """Response with council configuration info."""
    
    models: List[ModelInfo] = Field(..., description="List of models in the council")
    strategy: str = Field(..., description="Current voting/selection strategy")
    rag_documents: int = Field(..., description="Number of RAG documents loaded")
    available_commands: List[str] = Field(..., description="Available /commands")


class FileInfo(BaseModel):
    """Information about a file in the sandbox."""
    
    name: str = Field(..., description="File name")
    path: str = Field(..., description="Relative path")
    extension: str = Field(..., description="File extension")
    size: int = Field(..., description="File size in bytes")
    modified: str = Field(..., description="Last modified timestamp")
    is_directory: bool = Field(..., description="Whether this is a directory")
    children: List["FileInfo"] = Field(default=[], description="Child files/folders")


class FileTreeResponse(BaseModel):
    """Response with file tree structure."""
    
    root: FileInfo = Field(..., description="Root directory info")
    total_files: int = Field(..., description="Total file count")


class FileContentResponse(BaseModel):
    """Response with file content."""
    
    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content")
    size: int = Field(..., description="File size")


class ExecutionResponse(BaseModel):
    """Response from code execution."""
    
    success: bool = Field(..., description="Whether execution succeeded")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    exit_code: int = Field(..., description="Process exit code")
    execution_time: float = Field(..., description="Execution time in seconds")


class SearchResult(BaseModel):
    """A single search result."""
    
    file: str = Field(..., description="File path")
    line: int = Field(..., description="Line number")
    content: str = Field(..., description="Matching line content")


class SearchResponse(BaseModel):
    """Response from file search."""
    
    pattern: str = Field(..., description="Search pattern used")
    matches: List[SearchResult] = Field(..., description="List of matches")
    total_matches: int = Field(..., description="Total match count")


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")


# Fix forward reference
FileInfo.model_rebuild()
