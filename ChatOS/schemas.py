"""
Pydantic models for API request/response schemas.

These schemas provide validation and documentation for the API endpoints.
"""

from typing import List, Optional

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
        examples=["Hello, how are you?", "Write a Python function to sort a list"]
    )
    
    mode: str = Field(
        default="normal",
        description="Chat mode: 'normal' for general conversation, 'code' for code-focused responses",
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


# =============================================================================
# Response Schemas
# =============================================================================

class ModelResponse(BaseModel):
    """Individual model response within the council."""
    
    model: str = Field(
        ...,
        description="Name of the model that generated this response"
    )
    
    text: str = Field(
        ...,
        description="The model's response text"
    )


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    
    answer: str = Field(
        ...,
        description="The selected/winning response from the council"
    )
    
    chosen_model: str = Field(
        ...,
        description="Name of the model whose response was selected"
    )
    
    responses: List[ModelResponse] = Field(
        ...,
        description="All individual model responses from the council"
    )
    
    memory_summary: Optional[str] = Field(
        default=None,
        description="Brief summary of the conversation memory state"
    )


class HealthResponse(BaseModel):
    """Response from the health check endpoint."""
    
    status: str = Field(
        ...,
        description="Service health status",
        examples=["healthy"]
    )
    
    version: str = Field(
        ...,
        description="API version"
    )
    
    models_loaded: int = Field(
        ...,
        description="Number of models currently loaded in the council"
    )
    
    rag_documents: int = Field(
        ...,
        description="Number of documents loaded for RAG"
    )


class ModelInfo(BaseModel):
    """Information about a single model."""
    
    name: str = Field(..., description="Model display name")
    behavior: str = Field(..., description="Model behavior/personality type")


class CouncilInfoResponse(BaseModel):
    """Response with council configuration info."""
    
    models: List[ModelInfo] = Field(
        ...,
        description="List of models in the council"
    )
    
    strategy: str = Field(
        ...,
        description="Current voting/selection strategy"
    )
    
    rag_documents: int = Field(
        ...,
        description="Number of RAG documents loaded"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Additional error details")

