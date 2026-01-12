"""
Reasoning Traces for AGI Core

Records and stores reasoning traces for:
- Debugging and analysis
- Training data extraction
- Self-improvement
"""

from .recorder import TraceStep, TraceSession, TraceRecorder

__all__ = [
    "TraceStep",
    "TraceSession",
    "TraceRecorder",
]

