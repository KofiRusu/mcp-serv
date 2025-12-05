"""
routes_training_submission.py - API for Mac users to submit training examples

Allows remote users (Mac, Linux) to:
1. Submit individual training examples/exercises
2. Create batch training datasets
3. Monitor submission status
4. View training progress

Examples are automatically merged into PersRM training queue.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/training", tags=["Training Submission"])

# Base directories
HOME = Path.home()
CHATOS_HOME = HOME / "ChatOS-v2.0"
DATA_DIR = CHATOS_HOME / "data" / "persrm"
SUBMISSIONS_DIR = DATA_DIR / "submissions"
TRAINING_QUEUE_DIR = DATA_DIR / "training_queue"

# Create directories if they don't exist
SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_QUEUE_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Request/Response Models
# =============================================================================

class TrainingExample(BaseModel):
    """A single training example for PersRM."""
    instruction: str = Field(..., description="User question or task")
    output: str = Field(..., description="Expected response or solution")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata (domain, difficulty, source, etc.)"
    )


class SubmitExampleRequest(BaseModel):
    """Submit a single training example."""
    instruction: str = Field(..., description="User question/task")
    output: str = Field(..., description="Expected response/solution")
    category: str = Field(
        default="general",
        description="Category: trading, investing, risk, crypto, general"
    )
    difficulty: str = Field(
        default="medium",
        description="Difficulty: easy, medium, hard, expert"
    )
    source: Optional[str] = Field(None, description="Source of example")
    notes: Optional[str] = Field(None, description="Additional notes")


class SubmitBatchRequest(BaseModel):
    """Submit multiple training examples."""
    examples: List[SubmitExampleRequest] = Field(
        ...,
        description="List of training examples"
    )
    batch_name: str = Field(
        ...,
        description="Name for this batch (e.g., 'crypto-strategies-batch-1')"
    )
    description: Optional[str] = Field(None, description="Batch description")


class TrainingExercise(BaseModel):
    """A training exercise/problem for users to solve."""
    problem: str = Field(..., description="Problem statement")
    hints: Optional[List[str]] = Field(None, description="Optional hints")
    expected_outcome: str = Field(..., description="Expected outcome/solution")
    category: str = Field(default="general")
    difficulty: str = Field(default="medium")


class SubmitExerciseRequest(BaseModel):
    """Submit an exercise that users should complete."""
    problem: str
    hints: Optional[List[str]] = None
    expected_outcome: str
    category: str = Field(default="general")
    difficulty: str = Field(default="medium")


class SubmissionStatus(BaseModel):
    """Status of a submission."""
    submission_id: str
    status: str  # "received", "processing", "merged", "error"
    created_at: str
    merged_at: Optional[str] = None
    example_count: int
    error_message: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def save_submission(examples: List[Dict[str, Any]], batch_name: str) -> str:
    """Save a submission to disk and return submission ID."""
    submission_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()
    
    submission_file = SUBMISSIONS_DIR / f"{submission_id}_{batch_name}.jsonl"
    
    with open(submission_file, 'w') as f:
        for example in examples:
            example['submission_id'] = submission_id
            example['submitted_at'] = timestamp
            f.write(json.dumps(example) + '\n')
    
    return submission_id


def get_submission_status(submission_id: str) -> Optional[Dict[str, Any]]:
    """Get status of a submission."""
    # Check submissions directory
    for file in SUBMISSIONS_DIR.glob(f"{submission_id}_*.jsonl"):
        if file.exists():
            with open(file, 'r') as f:
                examples = [json.loads(line) for line in f]
            
            return {
                "submission_id": submission_id,
                "status": "received",
                "file": file.name,
                "example_count": len(examples),
                "created_at": examples[0].get("submitted_at") if examples else None,
            }
    
    return None


def merge_submissions_to_training():
    """Merge all submissions into training dataset."""
    train_file = DATA_DIR / "train_final.jsonl"
    val_file = DATA_DIR / "val_final.jsonl"
    
    all_examples = []
    
    # Load existing training data
    if train_file.exists():
        with open(train_file, 'r') as f:
            all_examples.extend([json.loads(line) for line in f])
    
    # Load all submissions
    for submission_file in SUBMISSIONS_DIR.glob("*.jsonl"):
        with open(submission_file, 'r') as f:
            all_examples.extend([json.loads(line) for line in f])
    
    # Split 90/10 train/val
    split_point = int(len(all_examples) * 0.9)
    train_examples = all_examples[:split_point]
    val_examples = all_examples[split_point:]
    
    # Save merged data
    with open(train_file, 'w') as f:
        for example in train_examples:
            f.write(json.dumps(example) + '\n')
    
    with open(val_file, 'w') as f:
        for example in val_examples:
            f.write(json.dumps(example) + '\n')
    
    return len(train_examples), len(val_examples)


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/submit-example")
async def submit_training_example(
    request: SubmitExampleRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a single training example.
    
    This example will be:
    1. Saved to submissions directory
    2. Automatically merged into PersRM training queue
    3. Included in next training epoch
    
    Returns:
        Submission ID and status
    """
    example = {
        "instruction": request.instruction,
        "output": request.output,
        "metadata": {
            "category": request.category,
            "difficulty": request.difficulty,
            "source": request.source or "user-submission",
            "notes": request.notes,
        }
    }
    
    submission_id = save_submission([example], "single-example")
    
    # Queue for merging into training data
    background_tasks.add_task(merge_submissions_to_training)
    
    return {
        "success": True,
        "submission_id": submission_id,
        "message": f"Example submitted successfully. Will be included in next training epoch.",
        "status_url": f"/api/training/status/{submission_id}"
    }


@router.post("/submit-batch")
async def submit_batch_examples(
    request: SubmitBatchRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit multiple training examples as a batch.
    
    All examples are:
    1. Saved with batch metadata
    2. Queued for training
    3. Merged automatically
    
    Returns:
        Batch submission ID and statistics
    """
    if not request.examples:
        raise HTTPException(status_code=400, detail="Batch must contain at least 1 example")
    
    examples = []
    for ex in request.examples:
        examples.append({
            "instruction": ex.instruction,
            "output": ex.output,
            "metadata": {
                "batch_name": request.batch_name,
                "category": ex.category,
                "difficulty": ex.difficulty,
                "source": ex.source or "batch-submission",
                "notes": ex.notes,
            }
        })
    
    submission_id = save_submission(examples, request.batch_name)
    
    # Queue for merging
    background_tasks.add_task(merge_submissions_to_training)
    
    return {
        "success": True,
        "submission_id": submission_id,
        "batch_name": request.batch_name,
        "example_count": len(examples),
        "message": f"Batch of {len(examples)} examples submitted successfully",
        "status_url": f"/api/training/status/{submission_id}",
        "description": request.description,
    }


@router.post("/submit-exercise")
async def submit_training_exercise(
    request: SubmitExerciseRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a training exercise.
    
    This converts the exercise into training examples:
    - Problem → Instruction
    - Expected Outcome → Output
    - Hints → Metadata
    
    Returns:
        Exercise submission ID and converted example count
    """
    # Convert exercise to training example
    example = {
        "instruction": request.problem,
        "output": request.expected_outcome,
        "metadata": {
            "type": "exercise",
            "category": request.category,
            "difficulty": request.difficulty,
            "hints": request.hints or [],
        }
    }
    
    submission_id = save_submission([example], "exercise-submission")
    
    # Queue for merging
    background_tasks.add_task(merge_submissions_to_training)
    
    return {
        "success": True,
        "submission_id": submission_id,
        "type": "exercise",
        "message": "Exercise submitted and converted to training example",
        "status_url": f"/api/training/status/{submission_id}"
    }


@router.post("/submit-file")
async def submit_training_file(
    file: UploadFile = File(...),
    batch_name: str = Form(default="file-upload")
):
    """
    Submit training examples as JSONL file.
    
    File format:
    ```
    {"instruction": "...", "output": "...", "metadata": {...}}
    {"instruction": "...", "output": "...", "metadata": {...}}
    ```
    
    Returns:
        Submission ID and validation results
    """
    content = await file.read()
    
    try:
        lines = content.decode().strip().split('\n')
        examples = []
        errors = []
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                example = json.loads(line)
                if "instruction" not in example or "output" not in example:
                    errors.append(f"Line {i+1}: Missing 'instruction' or 'output'")
                else:
                    examples.append(example)
            except json.JSONDecodeError as e:
                errors.append(f"Line {i+1}: Invalid JSON - {e}")
        
        if not examples:
            raise HTTPException(
                status_code=400,
                detail=f"No valid examples found. Errors: {errors}"
            )
        
        submission_id = save_submission(examples, batch_name)
        
        return {
            "success": True,
            "submission_id": submission_id,
            "example_count": len(examples),
            "error_count": len(errors),
            "errors": errors if errors else None,
            "message": f"Uploaded {len(examples)} examples" + (
                f" ({len(errors)} errors)" if errors else ""
            ),
            "status_url": f"/api/training/status/{submission_id}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File processing error: {e}")


@router.get("/status/{submission_id}")
async def get_submission_status_endpoint(submission_id: str):
    """Get status of a training submission."""
    status = get_submission_status(submission_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return status


@router.get("/queue/status")
async def get_training_queue_status():
    """Get current training queue status."""
    try:
        train_file = DATA_DIR / "train_final.jsonl"
        val_file = DATA_DIR / "val_final.jsonl"
        
        train_count = 0
        val_count = 0
        
        if train_file.exists():
            with open(train_file, 'r') as f:
                train_count = sum(1 for _ in f)
        
        if val_file.exists():
            with open(val_file, 'r') as f:
                val_count = sum(1 for _ in f)
        
        pending_submissions = len(list(SUBMISSIONS_DIR.glob("*.jsonl")))
        
        return {
            "training_examples": train_count,
            "validation_examples": val_count,
            "total_queued": train_count + val_count,
            "pending_submissions": pending_submissions,
            "submission_dir": str(SUBMISSIONS_DIR),
            "training_data_dir": str(DATA_DIR),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying status: {e}")


@router.post("/merge-submissions")
async def merge_all_submissions():
    """
    Manually trigger merging of all submissions into training data.
    
    Typically done before starting training.
    """
    try:
        train_count, val_count = merge_submissions_to_training()
        
        return {
            "success": True,
            "message": "Submissions merged into training data",
            "train_examples": train_count,
            "val_examples": val_count,
            "total": train_count + val_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Merge failed: {e}")


@router.get("/health")
async def training_submission_health():
    """Health check for training submission API."""
    return {
        "status": "healthy",
        "submissions_dir": str(SUBMISSIONS_DIR),
        "submissions_dir_exists": SUBMISSIONS_DIR.exists(),
        "training_data_dir": str(DATA_DIR),
        "training_data_dir_exists": DATA_DIR.exists(),
    }

