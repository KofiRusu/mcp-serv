"""
ChatOS - A PewDiePie-style Local AI Interface

This FastAPI application provides a web interface to chat with
multiple local models orchestrated as a "council of bots".

Features:
- Multi-model council with voting/selection
- Conversation memory (sliding window)
- Simple RAG over local text files
- Normal and coding modes
- Clean, modern chat UI

Run with: uvicorn ChatOS.app:app --reload
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ChatOS import __version__
from ChatOS.config import STATIC_DIR, TEMPLATES_DIR
from ChatOS.controllers.chat import chat_endpoint, get_council_info
from ChatOS.schemas import (
    ChatRequest,
    ChatResponse,
    CouncilInfoResponse,
    ErrorResponse,
    HealthResponse,
)

# =============================================================================
# App Configuration
# =============================================================================

app = FastAPI(
    title="ChatOS",
    description="A PewDiePie-style local AI interface with council-of-bots architecture",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration for same-origin + local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local development
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


# =============================================================================
# API Routes
# =============================================================================

@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check endpoint",
)
async def health() -> HealthResponse:
    """
    Check the health status of the ChatOS service.
    
    Returns information about loaded models and RAG documents.
    """
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
    """
    Get information about the current council configuration.
    
    Returns the list of models, voting strategy, and RAG status.
    """
    info = get_council_info()
    return CouncilInfoResponse(**info)


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
    
    The council queries all available models and uses a voting strategy
    to select the best response. Individual model responses are also
    returned for transparency.
    
    **Modes:**
    - `normal`: General conversation mode
    - `code`: Code-focused responses with syntax highlighting
    
    **RAG:**
    When `use_rag` is enabled, the system retrieves relevant context
    from local documents to enhance responses.
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
# Legacy endpoint for backward compatibility
# =============================================================================

@app.post("/chat", include_in_schema=False)
async def chat_legacy(request: ChatRequest) -> ChatResponse:
    """Legacy chat endpoint - redirects to /api/chat."""
    return await chat(request)

