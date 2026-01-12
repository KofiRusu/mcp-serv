"""
learning_loop_integration.py - Integration between Learning Loop DB and Unsloth training.

Provides functions to:
- Export learning loop data to Unsloth-compatible format
- Create versioned datasets from the database
- Track training runs in the learning loop
- Integrate with existing ChatOS training pipeline
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from chatos_backend.config.settings import settings
from chatos_backend.database.connection import DatabaseSession
from chatos_backend.database.models import (
    CoverageAnalysis,
    DataSource,
    ExampleStatus,
    KnowledgeDomain,
    TrainingExample,
    TrainingRun,
)


# =============================================================================
# Dataset Export
# =============================================================================

def export_learning_loop_dataset(
    output_dir: Optional[Path] = None,
    min_quality: float = 0.5,
    domains: Optional[List[str]] = None,
    max_per_domain: Optional[int] = None,
    include_synthetic: bool = True,
    eval_ratio: float = 0.1,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Export training examples from the learning loop database.
    
    Creates Unsloth-compatible JSONL files with train/eval splits.
    
    Args:
        output_dir: Output directory (defaults to Unsloth datasets dir)
        min_quality: Minimum quality score to include
        domains: Specific domains to include (None = all)
        max_per_domain: Maximum examples per domain
        include_synthetic: Include synthetically generated data
        eval_ratio: Fraction for evaluation split
        seed: Random seed for reproducibility
    
    Returns:
        Dict with export statistics and paths
    """
    from chatos_backend.database.models import SourceType
    
    # Determine output directory
    if output_dir is None:
        version = int(datetime.now().timestamp())
        output_dir = settings.unsloth_datasets_dir / f"learning_loop_v{version}"
    else:
        output_dir = Path(output_dir)
        version = 0
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Query examples
    with DatabaseSession() as db:
        query = db.query(TrainingExample).filter(
            TrainingExample.status == ExampleStatus.PROCESSED,
        )
        
        # Quality filter
        if min_quality > 0:
            query = query.filter(
                (TrainingExample.quality_score >= min_quality) |
                (TrainingExample.quality_score.is_(None))
            )
        
        # Domain filter
        if domains:
            domain_ids = db.query(KnowledgeDomain.id).filter(
                KnowledgeDomain.name.in_(domains)
            ).all()
            domain_id_list = [d[0] for d in domain_ids]
            query = query.filter(TrainingExample.domain_id.in_(domain_id_list))
        
        # Synthetic filter
        if not include_synthetic:
            synthetic_sources = db.query(DataSource.id).filter(
                DataSource.source_type == SourceType.SYNTHETIC
            ).all()
            synthetic_ids = [s[0] for s in synthetic_sources]
            query = query.filter(~TrainingExample.source_id.in_(synthetic_ids))
        
        examples = query.all()
    
    if not examples:
        return {
            "success": False,
            "error": "No examples match the criteria",
            "total": 0,
        }
    
    # Group by domain and limit if needed
    if max_per_domain:
        by_domain: Dict[int, List[TrainingExample]] = {}
        for ex in examples:
            domain_id = ex.domain_id or 0
            if domain_id not in by_domain:
                by_domain[domain_id] = []
            by_domain[domain_id].append(ex)
        
        limited = []
        for domain_id, domain_examples in by_domain.items():
            random.seed(seed)
            random.shuffle(domain_examples)
            limited.extend(domain_examples[:max_per_domain])
        examples = limited
    
    # Split train/eval
    random.seed(seed)
    shuffled = examples.copy()
    random.shuffle(shuffled)
    split_idx = int(len(shuffled) * (1 - eval_ratio))
    train_examples = shuffled[:split_idx]
    eval_examples = shuffled[split_idx:]
    
    # Write train file
    train_path = output_dir / "train.jsonl"
    with open(train_path, "w", encoding="utf-8") as f:
        for ex in train_examples:
            data = ex.to_training_format()
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    
    # Write eval file
    eval_path = output_dir / "eval.jsonl"
    with open(eval_path, "w", encoding="utf-8") as f:
        for ex in eval_examples:
            data = ex.to_training_format()
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    
    # Calculate domain distribution
    domain_dist = {}
    with DatabaseSession() as db:
        for ex in examples:
            if ex.domain_id:
                domain = db.query(KnowledgeDomain).filter(
                    KnowledgeDomain.id == ex.domain_id
                ).first()
                name = domain.name if domain else "unknown"
            else:
                name = "unknown"
            domain_dist[name] = domain_dist.get(name, 0) + 1
    
    # Write stats
    stats = {
        "version": version,
        "train_count": len(train_examples),
        "eval_count": len(eval_examples),
        "total": len(examples),
        "min_quality": min_quality,
        "domains": domains,
        "domain_distribution": domain_dist,
        "include_synthetic": include_synthetic,
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "created_at": datetime.now().isoformat(),
    }
    
    stats_path = output_dir / "stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    
    return {
        "success": True,
        "version": version,
        "train_count": len(train_examples),
        "eval_count": len(eval_examples),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "output_dir": str(output_dir),
        "domain_distribution": domain_dist,
    }


def get_dataset_for_training(
    training_type: str = "chatos",
    min_quality: float = 0.5,
) -> Tuple[Optional[str], Optional[str], int]:
    """
    Get the latest learning loop dataset for training.
    
    If no recent dataset exists, exports a new one.
    
    Args:
        training_type: "chatos" or "persrm" for domain filtering
        min_quality: Minimum quality score
    
    Returns:
        Tuple of (train_path, eval_path, total_count)
    """
    # Domain mapping
    if training_type == "persrm":
        domains = ["ui_components", "layout", "accessibility", "design_systems"]
    else:
        domains = None  # All domains
    
    # Check for recent export
    datasets_dir = settings.unsloth_datasets_dir
    latest_version = None
    latest_time = 0
    
    for path in datasets_dir.glob("learning_loop_v*"):
        if path.is_dir():
            try:
                version = int(path.name.replace("learning_loop_v", ""))
                if version > latest_time:
                    stats_file = path / "stats.json"
                    if stats_file.exists():
                        latest_version = path
                        latest_time = version
            except ValueError:
                continue
    
    # Use recent export if available (within last hour)
    current_time = int(datetime.now().timestamp())
    if latest_version and (current_time - latest_time) < 3600:
        stats_file = latest_version / "stats.json"
        with open(stats_file) as f:
            stats = json.load(f)
        return (
            stats.get("train_path"),
            stats.get("eval_path"),
            stats.get("train_count", 0),
        )
    
    # Export fresh dataset
    result = export_learning_loop_dataset(
        min_quality=min_quality,
        domains=domains,
    )
    
    if result.get("success"):
        return (
            result.get("train_path"),
            result.get("eval_path"),
            result.get("train_count", 0),
        )
    
    return None, None, 0


# =============================================================================
# Training Run Tracking
# =============================================================================

def create_training_run(
    job_id: str,
    dataset_version: int,
    example_ids: List[int],
    domain_distribution: Dict[str, int],
) -> int:
    """
    Create a training run record in the learning loop database.
    
    Args:
        job_id: ID from the job store
        dataset_version: Version of the dataset used
        example_ids: List of TrainingExample IDs used
        domain_distribution: Distribution of domains
    
    Returns:
        TrainingRun ID
    """
    # Calculate average quality
    avg_quality = None
    if example_ids:
        with DatabaseSession() as db:
            from sqlalchemy import func
            avg_quality = db.query(
                func.avg(TrainingExample.quality_score)
            ).filter(
                TrainingExample.id.in_(example_ids)
            ).scalar()
    
    with DatabaseSession() as db:
        run = TrainingRun(
            job_id=job_id,
            dataset_version=dataset_version,
            total_examples=len(example_ids),
            example_ids=example_ids,
            domain_distribution=domain_distribution,
            avg_quality_score=avg_quality,
            created_at=datetime.utcnow(),
        )
        db.add(run)
        db.flush()
        return run.id


def complete_training_run(
    job_id: str,
    final_loss: float,
    eval_metrics: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Mark a training run as complete with final metrics.
    
    Args:
        job_id: Job ID from job store
        final_loss: Final training loss
        eval_metrics: Optional evaluation metrics
    """
    with DatabaseSession() as db:
        run = db.query(TrainingRun).filter(
            TrainingRun.job_id == job_id
        ).first()
        
        if run:
            run.final_loss = final_loss
            run.eval_metrics = eval_metrics
            run.completed_at = datetime.utcnow()


def mark_examples_used(example_ids: List[int]) -> int:
    """
    Mark examples as used in training.
    
    Args:
        example_ids: IDs of examples to mark
    
    Returns:
        Number of examples updated
    """
    with DatabaseSession() as db:
        updated = db.query(TrainingExample).filter(
            TrainingExample.id.in_(example_ids)
        ).update(
            {
                TrainingExample.status: ExampleStatus.USED,
                TrainingExample.used_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )
        return updated


# =============================================================================
# Integration with Existing Pipeline
# =============================================================================

def get_learning_loop_stats() -> Dict[str, Any]:
    """
    Get statistics for the learning loop integration.
    
    Returns:
        Dict with counts and readiness info
    """
    try:
        with DatabaseSession() as db:
            total = db.query(TrainingExample).filter(
                TrainingExample.status == ExampleStatus.PROCESSED
            ).count()
            
            high_quality = db.query(TrainingExample).filter(
                TrainingExample.status == ExampleStatus.PROCESSED,
                TrainingExample.quality_score >= 0.7,
            ).count()
            
            by_source = {}
            sources = db.query(DataSource).all()
            for source in sources:
                count = db.query(TrainingExample).filter(
                    TrainingExample.source_id == source.id,
                    TrainingExample.status == ExampleStatus.PROCESSED,
                ).count()
                if count > 0:
                    by_source[source.name] = count
            
            training_runs = db.query(TrainingRun).count()
        
        return {
            "total_examples": total,
            "high_quality_examples": high_quality,
            "by_source": by_source,
            "training_runs": training_runs,
            "ready_to_train": total >= 50,
            "min_required": 50,
        }
    except Exception as e:
        return {
            "error": str(e),
            "ready_to_train": False,
        }


def can_use_learning_loop() -> Tuple[bool, str]:
    """
    Check if the learning loop database can be used for training.
    
    Returns:
        Tuple of (can_use, reason)
    """
    from chatos_backend.database.connection import check_database_connection
    
    # Check database connection
    if not check_database_connection():
        return False, "Database not connected"
    
    # Check for sufficient examples
    stats = get_learning_loop_stats()
    
    if stats.get("error"):
        return False, f"Database error: {stats['error']}"
    
    if stats.get("total_examples", 0) < 50:
        return False, f"Insufficient examples: {stats['total_examples']}/50"
    
    return True, "Learning loop ready"


def initialize_learning_loop() -> Dict[str, Any]:
    """
    Initialize the learning loop database and sync existing data.
    
    This should be called once to set up the database and import
    existing ChatOS/PersRM data.
    
    Returns:
        Dict with initialization results
    """
    from chatos_backend.database.connection import init_database
    from chatos_backend.ingestion.chatos_sync import sync_all_internal_data
    
    results = {
        "database_initialized": False,
        "data_synced": {},
        "errors": [],
    }
    
    # Initialize database
    try:
        init_database(drop_existing=False)
        results["database_initialized"] = True
    except Exception as e:
        results["errors"].append(f"Database init failed: {e}")
        return results
    
    # Sync existing data
    try:
        sync_results = sync_all_internal_data(min_score=0)
        results["data_synced"] = {
            k: {"synced": v[0], "skipped": v[1]}
            for k, v in sync_results.items()
        }
    except Exception as e:
        results["errors"].append(f"Data sync failed: {e}")
    
    return results


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Learning Loop Integration CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # init command
    init_parser = subparsers.add_parser("init", help="Initialize learning loop")
    
    # export command
    export_parser = subparsers.add_parser("export", help="Export dataset")
    export_parser.add_argument("--min-quality", type=float, default=0.5)
    export_parser.add_argument("--domains", nargs="+")
    export_parser.add_argument("--max-per-domain", type=int)
    
    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    
    args = parser.parse_args()
    
    if args.command == "init":
        result = initialize_learning_loop()
        print(json.dumps(result, indent=2))
    
    elif args.command == "export":
        result = export_learning_loop_dataset(
            min_quality=args.min_quality,
            domains=args.domains,
            max_per_domain=args.max_per_domain,
        )
        print(json.dumps(result, indent=2))
    
    elif args.command == "stats":
        stats = get_learning_loop_stats()
        print(json.dumps(stats, indent=2))
    
    else:
        parser.print_help()

