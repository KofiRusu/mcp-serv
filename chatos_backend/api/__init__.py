"""
ChatOS API Routes

This module provides additional API routes organized by feature.
"""

from .routes_training import router as training_router

__all__ = ["training_router"]

