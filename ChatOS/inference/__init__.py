"""
ChatOS Inference Module

Manages fine-tuned model loading and inference.
"""

from .model_loader import (
    get_fine_tuned_models,
    get_model_display_name,
    FineTunedModel,
)

__all__ = [
    "get_fine_tuned_models",
    "get_model_display_name",
    "FineTunedModel",
]

