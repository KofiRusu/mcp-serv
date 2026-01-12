"""
Training Loop for AGI Core

Autonomous training data extraction:
- Collect examples from traces
- Export datasets for fine-tuning
- Integration with QLoRA training
"""

from .loop import TrainingDataCollector, export_training_dataset

__all__ = [
    "TrainingDataCollector",
    "export_training_dataset",
]

