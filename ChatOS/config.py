"""
Configuration settings for ChatOS.

This module centralizes all configurable parameters so they can be
easily adjusted without modifying core logic.
"""

from pathlib import Path
from typing import Literal

# =============================================================================
# Path Configuration
# =============================================================================

# Base directory of the ChatOS package
PACKAGE_DIR = Path(__file__).parent

# Directory containing RAG documents
DATA_DIR = PACKAGE_DIR / "data"

# Static files and templates
STATIC_DIR = PACKAGE_DIR / "static"
TEMPLATES_DIR = PACKAGE_DIR / "templates"

# Sandbox directory for code editing
SANDBOX_DIR = Path.home() / "ChatOS-Sandbox"


# =============================================================================
# Memory Configuration
# =============================================================================

# Number of conversation turns to keep in memory
MEMORY_MAX_TURNS: int = 10


# =============================================================================
# Council Configuration
# =============================================================================

# Number of dummy models in the council
NUM_COUNCIL_MODELS: int = 4

# Selection strategy for choosing the best response
# Options: "longest", "shortest", "random", "first"
COUNCIL_STRATEGY: Literal["longest", "shortest", "random", "first"] = "longest"

# Model behaviors to cycle through for dummy models
MODEL_BEHAVIORS = ["thoughtful", "concise", "creative", "analytical"]


# =============================================================================
# RAG Configuration
# =============================================================================

# File extensions to scan for RAG documents
RAG_FILE_EXTENSIONS = [".txt", ".md"]

# Maximum snippet length to return from RAG
RAG_SNIPPET_MAX_LENGTH: int = 500

# Minimum query length to trigger RAG search
RAG_MIN_QUERY_LENGTH: int = 3


# =============================================================================
# Server Configuration
# =============================================================================

# Default server host and port
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# API prefix
API_PREFIX = "/api"


# =============================================================================
# Command Modes Configuration
# =============================================================================

# Available command modes (triggered with /command)
COMMAND_MODES = {
    "research": {
        "name": "Research Mode",
        "description": "Deep research using web search and internet context",
        "icon": "🔬",
    },
    "deepthinking": {
        "name": "Deep Thinking Mode", 
        "description": "Extended chain-of-thought reflection for complex problems",
        "icon": "🧠",
    },
    "swarm": {
        "name": "Swarm Mode",
        "description": "Multi-agent coding collaboration",
        "icon": "🐝",
    },
    "code": {
        "name": "Code Mode",
        "description": "Code-focused responses with syntax highlighting",
        "icon": "⌨️",
    },
}


# =============================================================================
# Deep Thinking Configuration
# =============================================================================

# Number of reflection iterations for deep thinking
DEEPTHINKING_ITERATIONS: int = 3

# Reflection prompts for chain-of-thought
DEEPTHINKING_PROMPTS = [
    "Let me reconsider this problem from first principles...",
    "What assumptions am I making? Let me challenge them...",
    "Are there edge cases or alternative perspectives I'm missing?",
    "How can I make this solution more robust and complete?",
]


# =============================================================================
# Swarm Configuration
# =============================================================================

# Swarm agent roles for coding tasks
SWARM_AGENTS = {
    "architect": {
        "name": "Architect",
        "role": "System design and architecture decisions",
        "icon": "🏗️",
    },
    "implementer": {
        "name": "Implementer",
        "role": "Write clean, efficient code",
        "icon": "💻",
    },
    "reviewer": {
        "name": "Reviewer",
        "role": "Code review and quality assurance",
        "icon": "🔍",
    },
    "tester": {
        "name": "Tester",
        "role": "Test generation and edge case analysis",
        "icon": "🧪",
    },
    "documenter": {
        "name": "Documenter",
        "role": "Documentation and comments",
        "icon": "📝",
    },
}


# =============================================================================
# Research Configuration
# =============================================================================

# Web search configuration
RESEARCH_MAX_SOURCES: int = 5
RESEARCH_SNIPPET_LENGTH: int = 300

# Simulated search domains (for demo, replace with real API)
RESEARCH_DOMAINS = [
    "stackoverflow.com",
    "github.com",
    "docs.python.org",
    "developer.mozilla.org",
    "medium.com",
]


# =============================================================================
# Sandbox Configuration
# =============================================================================

# Allowed file extensions in sandbox
SANDBOX_ALLOWED_EXTENSIONS = [
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".html", ".css", ".json", ".yaml", ".yml",
    ".md", ".txt", ".sh", ".sql",
    ".java", ".go", ".rs", ".cpp", ".c", ".h",
]

# Maximum file size in sandbox (bytes)
SANDBOX_MAX_FILE_SIZE: int = 1024 * 1024  # 1MB
