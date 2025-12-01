"""
routes_learning_loop.py - API routes for the Learning Loop database.

Provides REST endpoints for:
- Data source management
- Training example CRUD
- Coverage analysis and gap detection
- HuggingFace dataset loading
- Web scraping management
- Active learning tasks
- Dataset export for training
"""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from ChatOS.config.settings import settings


router = APIRouter(prefix="/api/learning-loop", tags=["Learning Loop"])


# =============================================================================
# Request/Response Models
# =============================================================================

class LoadHuggingFaceRequest(BaseModel):
    """Request to load a HuggingFace dataset."""
    dataset_key: str = Field(..., description="Dataset key or HuggingFace path")
    max_examples: Optional[int] = Field(None, description="Maximum examples to load")


class AddScrapeTargetRequest(BaseModel):
    """Request to add a web scrape target."""
    name: str
    url_pattern: str
    scrape_type: str = "documentation"
    target_domain: str = "instruction_following"
    selectors: Optional[Dict[str, str]] = None


class ScrapeURLRequest(BaseModel):
    """Request to scrape a single URL."""
    url: str
    scrape_type: str = "documentation"


class GenerateDataRequest(BaseModel):
    """Request to generate training data."""
    domain_name: str
    count: int = 20


class ExportDatasetRequest(BaseModel):
    """Request to export training dataset."""
    domains: Optional[List[str]] = Field(None, description="Domains to include (None = all)")
    min_quality: float = Field(0.5, description="Minimum quality score")
    max_examples: Optional[int] = Field(None, description="Maximum examples per domain")
    include_synthetic: bool = Field(True, description="Include synthetic data")
    eval_ratio: float = Field(0.1, description="Evaluation split ratio")


# =============================================================================
# Database Status
# =============================================================================

@router.get("/status")
async def get_database_status():
    """
    Get the status of the learning loop database.
    
    Returns connection status, table counts, and basic statistics.
    """
    from ChatOS.database.connection import check_database_connection, get_database_url, DatabaseSession
    from ChatOS.database.models import DataSource, TrainingExample, KnowledgeDomain
    
    connected = check_database_connection()
    
    if not connected:
        return {
            "connected": False,
            "database_url": get_database_url()[:50] + "...",
            "error": "Could not connect to database",
        }
    
    with DatabaseSession() as db:
        source_count = db.query(DataSource).count()
        example_count = db.query(TrainingExample).count()
        domain_count = db.query(KnowledgeDomain).count()
    
    return {
        "connected": True,
        "database_url": get_database_url()[:50] + "...",
        "counts": {
            "data_sources": source_count,
            "training_examples": example_count,
            "knowledge_domains": domain_count,
        },
    }


@router.post("/init")
async def initialize_database(drop_existing: bool = False):
    """
    Initialize the learning loop database.
    
    Creates all tables and seeds default data.
    
    **Warning**: If drop_existing is True, all data will be deleted!
    """
    from ChatOS.database.connection import init_database
    
    try:
        init_database(drop_existing=drop_existing)
        return {"success": True, "message": "Database initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Data Sources
# =============================================================================

@router.get("/sources")
async def list_data_sources():
    """List all configured data sources."""
    from ChatOS.database.connection import DatabaseSession
    from ChatOS.database.models import DataSource
    
    with DatabaseSession() as db:
        sources = db.query(DataSource).all()
        return {
            "sources": [s.to_dict() for s in sources],
            "total": len(sources),
        }


@router.get("/sources/{source_id}")
async def get_data_source(source_id: int):
    """Get details of a specific data source."""
    from ChatOS.database.connection import DatabaseSession
    from ChatOS.database.models import DataSource
    
    with DatabaseSession() as db:
        source = db.query(DataSource).filter(DataSource.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source.to_dict()


# =============================================================================
# Knowledge Domains
# =============================================================================

@router.get("/domains")
async def list_knowledge_domains():
    """List all knowledge domains."""
    from ChatOS.database.connection import DatabaseSession
    from ChatOS.database.models import KnowledgeDomain
    
    with DatabaseSession() as db:
        domains = db.query(KnowledgeDomain).all()
        return {
            "domains": [d.to_dict() for d in domains],
            "total": len(domains),
        }


# =============================================================================
# Training Examples
# =============================================================================

@router.get("/examples")
async def list_training_examples(
    domain_id: Optional[int] = None,
    source_id: Optional[int] = None,
    status: Optional[str] = None,
    min_quality: Optional[float] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    """
    List training examples with optional filtering.
    
    Args:
        domain_id: Filter by knowledge domain
        source_id: Filter by data source
        status: Filter by status (pending, processed, flagged, excluded)
        min_quality: Minimum quality score
        limit: Maximum results (max 500)
        offset: Pagination offset
    """
    from ChatOS.database.connection import DatabaseSession
    from ChatOS.database.models import TrainingExample, ExampleStatus
    
    with DatabaseSession() as db:
        query = db.query(TrainingExample)
        
        if domain_id:
            query = query.filter(TrainingExample.domain_id == domain_id)
        if source_id:
            query = query.filter(TrainingExample.source_id == source_id)
        if status:
            try:
                status_enum = ExampleStatus(status)
                query = query.filter(TrainingExample.status == status_enum)
            except ValueError:
                pass
        if min_quality is not None:
            query = query.filter(TrainingExample.quality_score >= min_quality)
        
        total = query.count()
        examples = query.offset(offset).limit(limit).all()
        
        return {
            "examples": [e.to_dict() for e in examples],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.get("/examples/{example_id}")
async def get_training_example(example_id: int):
    """Get a specific training example."""
    from ChatOS.database.connection import DatabaseSession
    from ChatOS.database.models import TrainingExample
    
    with DatabaseSession() as db:
        example = db.query(TrainingExample).filter(
            TrainingExample.id == example_id
        ).first()
        
        if not example:
            raise HTTPException(status_code=404, detail="Example not found")
        
        return example.to_dict()


@router.patch("/examples/{example_id}/status")
async def update_example_status(example_id: int, status: str):
    """Update the status of a training example."""
    from ChatOS.database.connection import DatabaseSession
    from ChatOS.database.models import TrainingExample, ExampleStatus
    
    try:
        new_status = ExampleStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid: {[s.value for s in ExampleStatus]}"
        )
    
    with DatabaseSession() as db:
        example = db.query(TrainingExample).filter(
            TrainingExample.id == example_id
        ).first()
        
        if not example:
            raise HTTPException(status_code=404, detail="Example not found")
        
        example.status = new_status
    
    return {"success": True, "new_status": status}


# =============================================================================
# HuggingFace Integration
# =============================================================================

@router.get("/huggingface/datasets")
async def list_recommended_datasets():
    """List recommended HuggingFace datasets for training."""
    from ChatOS.ingestion.huggingface_loader import get_recommended_datasets
    
    return {
        "datasets": get_recommended_datasets(),
    }


@router.post("/huggingface/load")
async def load_huggingface_dataset(
    request: LoadHuggingFaceRequest,
    background_tasks: BackgroundTasks,
):
    """
    Load a HuggingFace dataset into the learning loop database.
    
    This is a background task - returns immediately with task status.
    """
    from ChatOS.ingestion.huggingface_loader import HuggingFaceLoader
    
    loader = HuggingFaceLoader()
    
    # For small loads, do synchronously
    if request.max_examples and request.max_examples <= 100:
        try:
            loaded, skipped = loader.load_dataset(
                request.dataset_key,
                request.max_examples,
            )
            return {
                "success": True,
                "loaded": loaded,
                "skipped": skipped,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # For larger loads, queue as background task
    def load_task():
        loader.load_dataset(request.dataset_key, request.max_examples)
    
    background_tasks.add_task(load_task)
    
    return {
        "success": True,
        "message": f"Loading {request.dataset_key} in background",
        "status": "queued",
    }


# =============================================================================
# Web Scraping
# =============================================================================

@router.get("/scraping/targets")
async def list_scrape_targets():
    """List all configured web scrape targets."""
    from ChatOS.ingestion.web_scraper import list_scrape_targets
    
    return {
        "targets": list_scrape_targets(),
    }


@router.post("/scraping/targets")
async def add_scrape_target(request: AddScrapeTargetRequest):
    """Add a new web scrape target."""
    from ChatOS.ingestion.web_scraper import WebScraper
    
    scraper = WebScraper()
    target_id = scraper.add_scrape_target(
        name=request.name,
        url_pattern=request.url_pattern,
        scrape_type=request.scrape_type,
        target_domain=request.target_domain,
        selectors=request.selectors,
    )
    
    return {"success": True, "target_id": target_id}


@router.post("/scraping/setup-defaults")
async def setup_default_scrape_targets():
    """Set up default scrape targets (MDN, React docs, etc.)."""
    from ChatOS.ingestion.web_scraper import setup_default_scrape_targets
    
    count = setup_default_scrape_targets()
    return {"success": True, "targets_created": count}


@router.post("/scraping/scrape")
async def scrape_url(request: ScrapeURLRequest):
    """Scrape a single URL and extract training data."""
    from ChatOS.ingestion.web_scraper import WebScraper
    
    scraper = WebScraper()
    
    try:
        result = await scraper.scrape_url(request.url, request.scrape_type)
        
        if result and result.extracted_content:
            return {
                "success": True,
                "title": result.title,
                "content_preview": str(result.extracted_content)[:500],
                "result_id": result.id,
            }
        else:
            return {
                "success": False,
                "error": result.error_message if result else "Failed to scrape",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Internal Data Sync
# =============================================================================

@router.post("/sync/chatos")
async def sync_chatos_conversations(min_score: int = 0):
    """Sync ChatOS conversation logs to the database."""
    from ChatOS.ingestion.chatos_sync import sync_chatos_conversations
    
    synced, skipped = sync_chatos_conversations(min_score)
    return {
        "success": True,
        "synced": synced,
        "skipped": skipped,
    }


@router.post("/sync/persrm")
async def sync_persrm_data():
    """Sync PersRM reasoning data to the database."""
    from ChatOS.ingestion.chatos_sync import sync_persrm_data
    
    synced, skipped = sync_persrm_data()
    return {
        "success": True,
        "synced": synced,
        "skipped": skipped,
    }


@router.post("/sync/all")
async def sync_all_internal():
    """Sync all internal data sources."""
    from ChatOS.ingestion.chatos_sync import sync_all_internal_data
    
    results = sync_all_internal_data()
    return {
        "success": True,
        "results": {
            k: {"synced": v[0], "skipped": v[1]}
            for k, v in results.items()
        },
    }


# =============================================================================
# Coverage Analysis & Gaps
# =============================================================================

@router.get("/coverage")
async def get_coverage_analysis():
    """
    Get coverage analysis for all knowledge domains.
    
    Returns coverage ratios, gaps, and recommendations.
    """
    from ChatOS.active_learning.gap_detector import get_coverage_report
    
    return get_coverage_report()


@router.get("/coverage/{domain_name}")
async def get_domain_coverage(domain_name: str):
    """Get coverage analysis for a specific domain."""
    from ChatOS.active_learning.gap_detector import GapDetector
    from ChatOS.database.connection import DatabaseSession
    from ChatOS.database.models import KnowledgeDomain
    
    with DatabaseSession() as db:
        domain = db.query(KnowledgeDomain).filter(
            KnowledgeDomain.name == domain_name
        ).first()
        
        if not domain:
            raise HTTPException(status_code=404, detail=f"Domain '{domain_name}' not found")
        
        detector = GapDetector()
        return detector.analyze_domain_coverage(domain.id)


@router.get("/gaps")
async def get_knowledge_gaps(include_low_coverage: bool = True):
    """
    Get all knowledge gaps that need attention.
    
    Args:
        include_low_coverage: Include domains below target (not just below minimum)
    """
    from ChatOS.active_learning.gap_detector import get_knowledge_gaps
    
    gaps = get_knowledge_gaps(include_low_coverage)
    return {
        "gaps": [
            {
                "domain_name": g.domain_name,
                "category": g.category,
                "current_count": g.current_count,
                "target_count": g.target_count,
                "coverage_ratio": g.coverage_ratio,
                "is_critical": g.is_critical,
                "priority_score": g.priority_score,
                "recommended_actions": g.recommended_actions,
            }
            for g in gaps
        ],
        "total_gaps": len(gaps),
        "critical_count": sum(1 for g in gaps if g.is_critical),
    }


@router.post("/coverage/analyze")
async def run_coverage_analysis():
    """Run and save coverage analysis."""
    from ChatOS.active_learning.gap_detector import save_coverage_analysis
    
    saved = save_coverage_analysis()
    return {"success": True, "analyses_saved": saved}


# =============================================================================
# Active Learning - Data Generation
# =============================================================================

@router.get("/generate/domains")
async def list_generation_domains():
    """List domains available for data generation."""
    from ChatOS.active_learning.data_generator import get_available_domains
    
    return {"domains": get_available_domains()}


@router.post("/generate")
async def generate_training_data(request: GenerateDataRequest):
    """
    Generate synthetic training data for a domain.
    
    Uses Ollama to create training examples.
    """
    from ChatOS.active_learning.data_generator import generate_for_gap
    
    try:
        result = await generate_for_gap(request.domain_name, request.count)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/fill-gaps")
async def fill_all_gaps(max_per_domain: int = 20):
    """
    Generate data for all knowledge gaps.
    
    Generates up to max_per_domain examples for each gap.
    """
    from ChatOS.active_learning.gap_detector import get_knowledge_gaps
    from ChatOS.active_learning.data_generator import generate_for_gap
    
    gaps = get_knowledge_gaps(include_low_coverage=False)  # Only critical
    results = []
    
    for gap in gaps[:5]:  # Limit to top 5 gaps
        result = await generate_for_gap(gap.domain_name, max_per_domain)
        results.append(result)
    
    return {
        "success": True,
        "domains_processed": len(results),
        "results": results,
    }


# =============================================================================
# Deduplication
# =============================================================================

@router.get("/duplicates/stats")
async def get_duplicate_stats():
    """Get statistics about duplicate examples."""
    from ChatOS.ingestion.deduplicator import get_duplicate_stats
    
    return get_duplicate_stats()


@router.post("/duplicates/remove")
async def remove_duplicates(keep_strategy: str = "first"):
    """
    Find and mark duplicate examples as excluded.
    
    Args:
        keep_strategy: Which to keep - "first", "highest_quality", or "newest"
    """
    from ChatOS.ingestion.deduplicator import remove_duplicates
    
    removed = remove_duplicates(keep_strategy)
    return {"success": True, "duplicates_removed": removed}


# =============================================================================
# Dataset Export
# =============================================================================

@router.post("/export")
async def export_training_dataset(request: ExportDatasetRequest):
    """
    Export training examples to JSONL format for Unsloth training.
    
    Creates versioned train/eval splits in the Unsloth datasets directory.
    """
    from ChatOS.database.connection import DatabaseSession
    from ChatOS.database.models import (
        TrainingExample, ExampleStatus, KnowledgeDomain, SourceType
    )
    from ChatOS.config.settings import settings
    from datetime import datetime
    import json
    import random
    
    with DatabaseSession() as db:
        query = db.query(TrainingExample).filter(
            TrainingExample.status == ExampleStatus.PROCESSED,
        )
        
        # Quality filter
        if request.min_quality > 0:
            query = query.filter(TrainingExample.quality_score >= request.min_quality)
        
        # Domain filter
        if request.domains:
            domain_ids = db.query(KnowledgeDomain.id).filter(
                KnowledgeDomain.name.in_(request.domains)
            ).all()
            domain_id_list = [d[0] for d in domain_ids]
            query = query.filter(TrainingExample.domain_id.in_(domain_id_list))
        
        # Exclude synthetic if requested
        if not request.include_synthetic:
            query = query.join(TrainingExample.source).filter(
                TrainingExample.source.has(source_type != SourceType.SYNTHETIC)
            )
        
        examples = query.all()
        
        if not examples:
            raise HTTPException(status_code=400, detail="No examples match criteria")
        
        # Convert to training format while session is active
        training_data = []
        for ex in examples:
            training_data.append({
                "domain_id": ex.domain_id,
                "format": ex.to_training_format(),
            })
    
    # Limit per domain if specified
    if request.max_examples:
        # Group by domain and limit
        by_domain: Dict[int, List] = {}
        for item in training_data:
            domain_id = item["domain_id"] or 0
            if domain_id not in by_domain:
                by_domain[domain_id] = []
            by_domain[domain_id].append(item)
        
        limited = []
        for domain_id, domain_items in by_domain.items():
            limited.extend(domain_items[:request.max_examples])
        training_data = limited
    
    # Split train/eval
    random.seed(42)
    random.shuffle(training_data)
    split_idx = int(len(training_data) * (1 - request.eval_ratio))
    train_data = training_data[:split_idx]
    eval_data = training_data[split_idx:]
    
    # Create versioned output directory
    version = int(datetime.now().timestamp())
    output_dir = settings.unsloth_datasets_dir / f"learning_loop_v{version}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write train file
    train_path = output_dir / "train.jsonl"
    with open(train_path, "w") as f:
        for item in train_data:
            f.write(json.dumps(item["format"], ensure_ascii=False) + "\n")
    
    # Write eval file
    eval_path = output_dir / "eval.jsonl"
    with open(eval_path, "w") as f:
        for item in eval_data:
            f.write(json.dumps(item["format"], ensure_ascii=False) + "\n")
    
    # Write stats
    stats = {
        "version": version,
        "train_count": len(train_data),
        "eval_count": len(eval_data),
        "min_quality": request.min_quality,
        "domains": request.domains,
        "created_at": datetime.now().isoformat(),
    }
    
    stats_path = output_dir / "stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    
    return {
        "success": True,
        "version": version,
        "train_count": len(train_data),
        "eval_count": len(eval_data),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "output_dir": str(output_dir),
    }


@router.get("/export/versions")
async def list_export_versions():
    """List all exported dataset versions."""
    from ChatOS.config.settings import settings
    import json
    
    versions = []
    datasets_dir = settings.unsloth_datasets_dir
    
    if not datasets_dir.exists():
        return {"versions": []}
    
    for path in datasets_dir.glob("learning_loop_v*"):
        if path.is_dir():
            stats_file = path / "stats.json"
            if stats_file.exists():
                try:
                    with open(stats_file) as f:
                        stats = json.load(f)
                    stats["path"] = str(path)
                    versions.append(stats)
                except:
                    pass
    
    versions.sort(key=lambda v: v.get("version", 0), reverse=True)
    return {"versions": versions}

