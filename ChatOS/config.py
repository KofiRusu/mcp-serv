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

