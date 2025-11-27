"""
Models package for ChatOS.

Contains model implementations and the loader for orchestrating
multiple models in the council.
"""

from .dummy_model import DummyModel
from .loader import load_models

__all__ = ["DummyModel", "load_models"]

