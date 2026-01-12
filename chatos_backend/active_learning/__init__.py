"""
ChatOS Active Learning Engine

Implements active learning strategies for continuous improvement:
- Gap detection (coverage analysis)
- Uncertainty sampling (model confidence)
- Targeted data generation
"""

from chatos_backend.active_learning.gap_detector import (
    GapDetector,
    analyze_coverage,
    get_knowledge_gaps,
    get_coverage_report,
)
from chatos_backend.active_learning.uncertainty_sampler import (
    UncertaintySampler,
    sample_uncertain_examples,
    update_confidence_scores,
)
from chatos_backend.active_learning.data_generator import (
    TargetedDataGenerator,
    generate_for_gap,
    generate_batch,
)

__all__ = [
    # Gap Detection
    "GapDetector",
    "analyze_coverage",
    "get_knowledge_gaps",
    "get_coverage_report",
    # Uncertainty Sampling
    "UncertaintySampler",
    "sample_uncertain_examples",
    "update_confidence_scores",
    # Data Generation
    "TargetedDataGenerator",
    "generate_for_gap",
    "generate_batch",
]

