"""
uncertainty_sampler.py - Sample examples based on model uncertainty.

Uses model confidence scores to identify examples where the model
is uncertain, which are good candidates for active learning.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import func

from chatos_backend.config.settings import settings
from chatos_backend.database.connection import DatabaseSession
from chatos_backend.database.models import (
    ExampleStatus,
    KnowledgeDomain,
    TrainingExample,
)


@dataclass
class UncertainExample:
    """An example with uncertainty metrics."""
    example_id: int
    user_input: str
    assistant_output: str
    domain_name: str
    confidence_score: float
    quality_score: float
    uncertainty_reason: str


class UncertaintySampler:
    """
    Sample examples based on model uncertainty.
    
    Uses Ollama to evaluate model confidence on examples and
    identifies areas where the model is uncertain.
    """
    
    def __init__(
        self,
        ollama_host: Optional[str] = None,
        model: str = "qwen2.5:7b",
    ):
        """
        Initialize the uncertainty sampler.
        
        Args:
            ollama_host: Ollama API host
            model: Model to use for confidence evaluation
        """
        self.ollama_host = ollama_host or settings.ollama_host
        self.model = model
    
    async def evaluate_confidence(
        self,
        user_input: str,
        expected_output: str,
    ) -> Tuple[float, str]:
        """
        Evaluate model confidence on an example.
        
        This generates a response and compares it to the expected output
        to estimate confidence.
        
        Args:
            user_input: The input/question
            expected_output: The expected response
        
        Returns:
            Tuple of (confidence_score, reason)
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Generate response
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": user_input,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Low temp for confidence
                            "num_predict": 500,
                        },
                    },
                )
                
                if response.status_code != 200:
                    return 0.5, "API error"
                
                data = response.json()
                generated = data.get("response", "")
                
                # Calculate similarity-based confidence
                confidence, reason = self._calculate_confidence(
                    generated, expected_output
                )
                
                return confidence, reason
                
        except Exception as e:
            return 0.5, f"Error: {str(e)}"
    
    def _calculate_confidence(
        self,
        generated: str,
        expected: str,
    ) -> Tuple[float, str]:
        """
        Calculate confidence based on output similarity.
        
        This is a simplified version - in production you might use:
        - Token-level entropy
        - Multiple generations and consistency
        - Embedding similarity
        """
        if not generated or not expected:
            return 0.5, "Empty response"
        
        # Normalize
        gen_lower = generated.lower().strip()
        exp_lower = expected.lower().strip()
        
        # Calculate word overlap (simple metric)
        gen_words = set(gen_lower.split())
        exp_words = set(exp_lower.split())
        
        if not gen_words or not exp_words:
            return 0.5, "No content to compare"
        
        intersection = gen_words & exp_words
        union = gen_words | exp_words
        
        jaccard = len(intersection) / len(union) if union else 0
        
        # Length similarity
        len_ratio = min(len(generated), len(expected)) / max(len(generated), len(expected))
        
        # Combined score
        confidence = (jaccard * 0.6) + (len_ratio * 0.4)
        
        # Determine reason
        if confidence > 0.8:
            reason = "High similarity - confident"
        elif confidence > 0.5:
            reason = "Moderate similarity - some uncertainty"
        elif confidence > 0.3:
            reason = "Low similarity - significant uncertainty"
        else:
            reason = "Very low similarity - high uncertainty"
        
        return round(confidence, 3), reason
    
    async def update_confidence_batch(
        self,
        example_ids: List[int],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        """
        Update confidence scores for a batch of examples.
        
        Args:
            example_ids: List of example IDs to evaluate
            progress_callback: Optional progress callback
        
        Returns:
            Number of examples updated
        """
        updated = 0
        total = len(example_ids)
        
        for idx, example_id in enumerate(example_ids):
            with DatabaseSession() as db:
                example = db.query(TrainingExample).filter(
                    TrainingExample.id == example_id
                ).first()
                
                if not example:
                    continue
                
                # Evaluate confidence
                confidence, reason = await self.evaluate_confidence(
                    example.user_input,
                    example.assistant_output,
                )
                
                # Update example
                example.confidence_score = confidence
                example.extra_data = example.extra_data or {}
                example.extra_data["uncertainty_reason"] = reason
                example.extra_data["confidence_evaluated_at"] = datetime.utcnow().isoformat()
                
                updated += 1
            
            if progress_callback:
                progress_callback(idx + 1, total)
            
            # Small delay to avoid overwhelming Ollama
            await asyncio.sleep(0.1)
        
        return updated
    
    def get_uncertain_examples(
        self,
        threshold: float = 0.5,
        limit: int = 50,
        domain_id: Optional[int] = None,
    ) -> List[UncertainExample]:
        """
        Get examples with low confidence scores.
        
        Args:
            threshold: Confidence threshold (below = uncertain)
            limit: Maximum examples to return
            domain_id: Optional domain filter
        
        Returns:
            List of uncertain examples
        """
        with DatabaseSession() as db:
            query = db.query(TrainingExample).filter(
                TrainingExample.confidence_score.isnot(None),
                TrainingExample.confidence_score < threshold,
                TrainingExample.status == ExampleStatus.PROCESSED,
            )
            
            if domain_id:
                query = query.filter(TrainingExample.domain_id == domain_id)
            
            # Order by confidence (lowest first)
            query = query.order_by(TrainingExample.confidence_score.asc())
            examples = query.limit(limit).all()
            
            results = []
            for ex in examples:
                domain = db.query(KnowledgeDomain).filter(
                    KnowledgeDomain.id == ex.domain_id
                ).first()
                
                results.append(UncertainExample(
                    example_id=ex.id,
                    user_input=ex.user_input[:500],
                    assistant_output=ex.assistant_output[:500],
                    domain_name=domain.name if domain else "unknown",
                    confidence_score=ex.confidence_score,
                    quality_score=ex.quality_score or 0,
                    uncertainty_reason=ex.extra_data.get("uncertainty_reason", "") if ex.extra_data else "",
                ))
            
            return results
    
    def get_examples_without_confidence(
        self,
        limit: int = 100,
    ) -> List[int]:
        """
        Get examples that haven't been evaluated for confidence.
        
        Args:
            limit: Maximum IDs to return
        
        Returns:
            List of example IDs
        """
        with DatabaseSession() as db:
            examples = db.query(TrainingExample.id).filter(
                TrainingExample.confidence_score.is_(None),
                TrainingExample.status == ExampleStatus.PROCESSED,
            ).limit(limit).all()
            
            return [ex[0] for ex in examples]
    
    def get_uncertainty_stats(self) -> Dict[str, Any]:
        """
        Get statistics about confidence scores.
        
        Returns:
            Dict with confidence statistics
        """
        with DatabaseSession() as db:
            total = db.query(TrainingExample).filter(
                TrainingExample.status == ExampleStatus.PROCESSED
            ).count()
            
            evaluated = db.query(TrainingExample).filter(
                TrainingExample.confidence_score.isnot(None),
                TrainingExample.status == ExampleStatus.PROCESSED,
            ).count()
            
            avg_confidence = db.query(
                func.avg(TrainingExample.confidence_score)
            ).filter(
                TrainingExample.confidence_score.isnot(None)
            ).scalar() or 0
            
            # Count by confidence bands
            high_conf = db.query(TrainingExample).filter(
                TrainingExample.confidence_score >= 0.8
            ).count()
            
            medium_conf = db.query(TrainingExample).filter(
                TrainingExample.confidence_score >= 0.5,
                TrainingExample.confidence_score < 0.8,
            ).count()
            
            low_conf = db.query(TrainingExample).filter(
                TrainingExample.confidence_score < 0.5,
                TrainingExample.confidence_score.isnot(None),
            ).count()
        
        return {
            "total_examples": total,
            "evaluated": evaluated,
            "not_evaluated": total - evaluated,
            "evaluation_ratio": round(evaluated / total if total > 0 else 0, 3),
            "avg_confidence": round(avg_confidence, 3),
            "high_confidence": high_conf,
            "medium_confidence": medium_conf,
            "low_confidence": low_conf,
        }


# =============================================================================
# Convenience Functions
# =============================================================================

async def sample_uncertain_examples(
    threshold: float = 0.5,
    limit: int = 50,
    domain_id: Optional[int] = None,
) -> List[UncertainExample]:
    """
    Get examples where the model is uncertain.
    
    Args:
        threshold: Confidence threshold
        limit: Maximum examples
        domain_id: Optional domain filter
    
    Returns:
        List of uncertain examples
    """
    sampler = UncertaintySampler()
    return sampler.get_uncertain_examples(threshold, limit, domain_id)


async def update_confidence_scores(
    limit: int = 100,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> int:
    """
    Update confidence scores for examples that haven't been evaluated.
    
    Args:
        limit: Maximum examples to evaluate
        progress_callback: Optional progress callback
    
    Returns:
        Number of examples updated
    """
    sampler = UncertaintySampler()
    example_ids = sampler.get_examples_without_confidence(limit)
    
    if not example_ids:
        return 0
    
    return await sampler.update_confidence_batch(example_ids, progress_callback)


def get_uncertainty_stats() -> Dict[str, Any]:
    """Get uncertainty statistics."""
    sampler = UncertaintySampler()
    return sampler.get_uncertainty_stats()

