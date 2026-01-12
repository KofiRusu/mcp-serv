"""
gap_detector.py - Detect knowledge gaps in training data coverage.

Analyzes training examples across knowledge domains to identify areas
that need more data for effective model training.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func

from chatos_backend.database.connection import DatabaseSession
from chatos_backend.database.models import (
    CoverageAnalysis,
    DifficultyLevel,
    ExampleStatus,
    KnowledgeDomain,
    TrainingExample,
)


@dataclass
class GapReport:
    """Report on a knowledge gap."""
    domain_id: int
    domain_name: str
    category: str
    current_count: int
    min_required: int
    target_count: int
    coverage_ratio: float
    avg_quality: float
    is_critical: bool
    priority_score: float
    recommended_actions: List[str]


class GapDetector:
    """
    Analyze training data coverage and detect knowledge gaps.
    
    Uses domain coverage analysis to identify areas that need
    more training examples.
    """
    
    def __init__(self):
        """Initialize the gap detector."""
        pass
    
    def analyze_domain_coverage(self, domain_id: int) -> Dict[str, Any]:
        """
        Analyze coverage for a specific domain.
        
        Args:
            domain_id: Knowledge domain ID
        
        Returns:
            Dict with coverage statistics
        """
        with DatabaseSession() as db:
            domain = db.query(KnowledgeDomain).filter(
                KnowledgeDomain.id == domain_id
            ).first()
            
            if not domain:
                return {"error": f"Domain {domain_id} not found"}
            
            # Count examples by status
            example_counts = db.query(
                TrainingExample.status,
                func.count(TrainingExample.id)
            ).filter(
                TrainingExample.domain_id == domain_id
            ).group_by(TrainingExample.status).all()
            
            counts = {status.value: count for status, count in example_counts}
            total = sum(counts.values())
            processed = counts.get("processed", 0)
            
            # Average quality
            avg_quality = db.query(
                func.avg(TrainingExample.quality_score)
            ).filter(
                TrainingExample.domain_id == domain_id,
                TrainingExample.status == ExampleStatus.PROCESSED,
            ).scalar() or 0.0
            
            # Difficulty distribution
            difficulty_dist = db.query(
                TrainingExample.difficulty,
                func.count(TrainingExample.id)
            ).filter(
                TrainingExample.domain_id == domain_id,
                TrainingExample.status == ExampleStatus.PROCESSED,
            ).group_by(TrainingExample.difficulty).all()
            
            difficulty_map = {
                d.value if d else "unknown": c for d, c in difficulty_dist
            }
            
            # Calculate coverage ratio
            coverage_ratio = processed / domain.target_examples if domain.target_examples > 0 else 0.0
            is_gap = processed < domain.min_examples_required
            
            # Priority score (higher = more urgent)
            priority = 0.0
            if is_gap:
                # Critical gap - boost priority
                priority = 10.0 * (1.0 - (processed / domain.min_examples_required if domain.min_examples_required > 0 else 0))
            elif coverage_ratio < 0.5:
                # Below 50% coverage
                priority = 5.0 * (1.0 - coverage_ratio)
            elif coverage_ratio < 1.0:
                # Below target
                priority = 2.0 * (1.0 - coverage_ratio)
            
            # Quality factor
            if avg_quality < 0.5:
                priority *= 1.5  # Boost priority for low quality domains
            
            return {
                "domain_id": domain_id,
                "domain_name": domain.name,
                "category": domain.category,
                "total_examples": total,
                "processed_examples": processed,
                "min_required": domain.min_examples_required,
                "target_count": domain.target_examples,
                "coverage_ratio": round(coverage_ratio, 3),
                "avg_quality": round(avg_quality, 3),
                "difficulty_distribution": difficulty_map,
                "is_gap": is_gap,
                "priority_score": round(priority, 2),
                "by_status": counts,
            }
    
    def analyze_all_coverage(self) -> List[Dict[str, Any]]:
        """
        Analyze coverage for all knowledge domains.
        
        Returns:
            List of coverage reports for each domain
        """
        with DatabaseSession() as db:
            # Get all domain IDs while session is active
            domain_ids = [d.id for d in db.query(KnowledgeDomain).all()]
        
        reports = []
        for domain_id in domain_ids:
            report = self.analyze_domain_coverage(domain_id)
            reports.append(report)
        
        # Sort by priority (highest first)
        reports.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        return reports
    
    def get_gaps(self, include_low_coverage: bool = True) -> List[GapReport]:
        """
        Get all knowledge gaps.
        
        Args:
            include_low_coverage: Include domains below target (not just below minimum)
        
        Returns:
            List of GapReport objects
        """
        reports = self.analyze_all_coverage()
        gaps = []
        
        for report in reports:
            is_gap = report.get("is_gap", False)
            coverage_ratio = report.get("coverage_ratio", 0)
            
            # Include if below minimum, or if below target and flag is set
            if is_gap or (include_low_coverage and coverage_ratio < 1.0):
                # Generate recommendations
                actions = self._generate_recommendations(report)
                
                gap = GapReport(
                    domain_id=report["domain_id"],
                    domain_name=report["domain_name"],
                    category=report.get("category", "unknown"),
                    current_count=report.get("processed_examples", 0),
                    min_required=report.get("min_required", 50),
                    target_count=report.get("target_count", 200),
                    coverage_ratio=coverage_ratio,
                    avg_quality=report.get("avg_quality", 0),
                    is_critical=is_gap,
                    priority_score=report.get("priority_score", 0),
                    recommended_actions=actions,
                )
                gaps.append(gap)
        
        return gaps
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate recommended actions for a coverage report."""
        actions = []
        
        domain_name = report.get("domain_name", "")
        current = report.get("processed_examples", 0)
        target = report.get("target_count", 200)
        avg_quality = report.get("avg_quality", 0)
        is_gap = report.get("is_gap", False)
        
        needed = target - current
        
        if is_gap:
            actions.append(f"CRITICAL: Add {needed} examples to reach minimum")
        
        if current < target * 0.25:
            actions.append("generate_synthetic")
            actions.append("load_huggingface_dataset")
        elif current < target * 0.5:
            actions.append("generate_synthetic")
        elif current < target:
            actions.append("scrape_targeted")
        
        if avg_quality < 0.5:
            actions.append("review_quality")
            actions.append("curate_existing")
        
        # Domain-specific recommendations
        if domain_name in ["python", "javascript", "react"]:
            actions.append("scrape_documentation")
            actions.append("scrape_stackoverflow")
        elif domain_name in ["ui_components", "layout", "accessibility"]:
            actions.append("generate_persrm_style")
        
        return actions
    
    def save_coverage_analysis(self) -> int:
        """
        Run coverage analysis and save results to database.
        
        Returns:
            Number of analysis records saved
        """
        reports = self.analyze_all_coverage()
        saved = 0
        
        with DatabaseSession() as db:
            for report in reports:
                domain_id = report["domain_id"]
                
                # Check for existing analysis
                existing = db.query(CoverageAnalysis).filter(
                    CoverageAnalysis.domain_id == domain_id
                ).first()
                
                if existing:
                    # Update existing
                    existing.example_count = report.get("processed_examples", 0)
                    existing.avg_quality_score = report.get("avg_quality")
                    existing.difficulty_distribution = report.get("difficulty_distribution")
                    existing.coverage_ratio = report.get("coverage_ratio")
                    existing.is_gap = report.get("is_gap", False)
                    existing.priority_score = report.get("priority_score")
                    existing.recommended_actions = self._generate_recommendations(report)
                    existing.analyzed_at = datetime.utcnow()
                else:
                    # Create new
                    analysis = CoverageAnalysis(
                        domain_id=domain_id,
                        example_count=report.get("processed_examples", 0),
                        avg_quality_score=report.get("avg_quality"),
                        difficulty_distribution=report.get("difficulty_distribution"),
                        coverage_ratio=report.get("coverage_ratio"),
                        is_gap=report.get("is_gap", False),
                        priority_score=report.get("priority_score"),
                        recommended_actions=self._generate_recommendations(report),
                        analyzed_at=datetime.utcnow(),
                    )
                    db.add(analysis)
                
                saved += 1
        
        return saved
    
    def get_priority_domains(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get highest priority domains for data collection.
        
        Args:
            limit: Maximum domains to return
        
        Returns:
            List of priority domains with recommendations
        """
        gaps = self.get_gaps(include_low_coverage=True)
        
        priority_list = []
        for gap in gaps[:limit]:
            priority_list.append({
                "domain_id": gap.domain_id,
                "domain_name": gap.domain_name,
                "category": gap.category,
                "current_count": gap.current_count,
                "target_count": gap.target_count,
                "needed": gap.target_count - gap.current_count,
                "priority_score": gap.priority_score,
                "is_critical": gap.is_critical,
                "recommended_actions": gap.recommended_actions,
            })
        
        return priority_list


# =============================================================================
# Convenience Functions
# =============================================================================

def analyze_coverage() -> List[Dict[str, Any]]:
    """
    Analyze coverage for all knowledge domains.
    
    Returns:
        List of coverage reports
    """
    detector = GapDetector()
    return detector.analyze_all_coverage()


def get_knowledge_gaps(include_low_coverage: bool = True) -> List[GapReport]:
    """
    Get all knowledge gaps.
    
    Returns:
        List of GapReport objects
    """
    detector = GapDetector()
    return detector.get_gaps(include_low_coverage)


def get_coverage_report() -> Dict[str, Any]:
    """
    Get a summary coverage report.
    
    Returns:
        Dict with overall statistics and gaps
    """
    detector = GapDetector()
    reports = detector.analyze_all_coverage()
    gaps = detector.get_gaps()
    
    total_examples = sum(r.get("processed_examples", 0) for r in reports)
    total_domains = len(reports)
    critical_gaps = sum(1 for g in gaps if g.is_critical)
    below_target = sum(1 for r in reports if r.get("coverage_ratio", 0) < 1.0)
    
    return {
        "total_examples": total_examples,
        "total_domains": total_domains,
        "critical_gaps": critical_gaps,
        "below_target": below_target,
        "avg_coverage_ratio": round(
            sum(r.get("coverage_ratio", 0) for r in reports) / total_domains
            if total_domains > 0 else 0, 3
        ),
        "priority_domains": detector.get_priority_domains(5),
        "all_domains": reports,
    }


def save_coverage_analysis() -> int:
    """Run and save coverage analysis."""
    detector = GapDetector()
    return detector.save_coverage_analysis()

