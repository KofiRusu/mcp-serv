"""
routes_training_exercises.py - API routes for training exercise creation and management.

Provides REST endpoints for:
- Creating single exercises
- Testing exercises against PersRM
- Batch importing exercises
- Listing and managing exercises
- Exercise statistics
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from dataclasses import asdict


router = APIRouter(prefix="/api/training/exercises", tags=["Training Exercises"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateExerciseRequest(BaseModel):
    """Request to create a new training exercise."""
    prompt: str = Field(..., description="The input prompt/instruction")
    expected_output: str = Field(..., description="Expected output with CoT format")
    domain: str = Field("general", description="Domain: coding, trading, reasoning, general, math, science")
    quality: float = Field(0.8, ge=0.0, le=1.0, description="Quality score 0.0-1.0")
    validate_cot: bool = Field(True, description="Validate CoT format in expected output")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ExerciseResponse(BaseModel):
    """Response containing exercise data."""
    id: str
    prompt: str
    expected_output: str
    domain: str
    quality: float
    created_at: str
    metadata: Dict[str, Any] = {}


class TestExerciseRequest(BaseModel):
    """Request to test an exercise against a model."""
    exercise_id: str = Field(..., description="ID of the exercise to test")
    model: str = Field("persrm-standalone", description="Model name for inference")


class TestResultResponse(BaseModel):
    """Response containing test results."""
    exercise_id: str
    model_output: str
    similarity_score: float
    passed: bool
    execution_time_ms: float
    error: Optional[str] = None


class BatchImportRequest(BaseModel):
    """Request for batch import metadata."""
    file_type: str = Field("json", description="File type: json or csv")


class BatchResultResponse(BaseModel):
    """Response containing batch import results."""
    total: int
    successful: int
    failed: int
    duplicates: int
    errors: List[str] = []


class StatsResponse(BaseModel):
    """Response containing exercise statistics."""
    cached_exercises: int
    training_examples: int
    domains: Dict[str, int]
    valid_domains: List[str]


class RecentExampleResponse(BaseModel):
    """Response containing a recent training example."""
    prompt: str
    full_prompt: str = ""
    expected_output: str = ""
    domain: str
    quality: float
    source: str
    created_at: str
    variation_type: str
    exercise_id: str
    index: int = 0


class TestSavedExerciseRequest(BaseModel):
    """Request to test a saved training example."""
    prompt: str
    expected_output: str
    model: str = "persrm-standalone"


class TestSavedExerciseResponse(BaseModel):
    """Response from testing a saved exercise."""
    prompt: str
    expected_output: str
    model_output: str
    similarity: float
    passed: bool
    model: str


class SaveExerciseRequest(BaseModel):
    """Request to save an exercise to training data."""
    exercise_id: str = Field(..., description="ID of the exercise to save")


class CoTTemplateResponse(BaseModel):
    """Response containing CoT format template."""
    template: str
    example: str
    domains: List[str]


class CreateWithVariationsRequest(BaseModel):
    """Request to create exercise with auto-generated variations."""
    prompt: str = Field(..., description="Base prompt for the exercise")
    expected_output: str = Field(..., description="Expected output with CoT format")
    domain: str = Field("general", description="Domain: coding, trading, reasoning, general, math, science")
    quality: float = Field(0.8, ge=0.0, le=1.0, description="Base quality score")
    variation_count: int = Field(100, ge=10, le=500, description="Number of variations to generate (10-500)")
    auto_save: bool = Field(True, description="Auto-save variations to training data")


class VariationsResultResponse(BaseModel):
    """Response containing variation generation results."""
    total_generated: int
    successfully_saved: int
    duplicates_skipped: int
    errors: List[str]
    message: str


# =============================================================================
# Routes
# =============================================================================

@router.post("/create", response_model=ExerciseResponse)
async def create_exercise(request: CreateExerciseRequest):
    """
    Create a new training exercise.
    
    The expected_output should follow the Chain-of-Thought format:
    <think>reasoning steps...</think>
    <answer>final answer...</answer>
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    
    exercise, error = manager.create_exercise(
        prompt=request.prompt,
        expected_output=request.expected_output,
        domain=request.domain,
        quality=request.quality,
        metadata=request.metadata,
        validate_cot=request.validate_cot
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return ExerciseResponse(
        id=exercise.id,
        prompt=exercise.prompt,
        expected_output=exercise.expected_output,
        domain=exercise.domain,
        quality=exercise.quality,
        created_at=exercise.created_at,
        metadata=exercise.metadata
    )


@router.post("/create-with-variations", response_model=VariationsResultResponse)
async def create_exercise_with_variations(request: CreateWithVariationsRequest):
    """
    Create an exercise and automatically generate 100+ variations for training.
    
    This is the PRIMARY method for adding training exercises. It:
    1. Validates the base exercise (prompt + expected output with CoT format)
    2. Generates diverse variations of the prompt (paraphrasing, formality, context, etc.)
    3. Automatically saves all valid variations to the training data file
    
    The variations improve model robustness by teaching it to handle the same
    concept expressed in many different ways.
    
    Example:
    - Original: "Write a Python function to calculate factorial"
    - Variation 1: "Can you help me write a factorial function in Python?"
    - Variation 2: "I need a Python factorial implementation"
    - Variation 3: "As a developer, I need to implement factorial in Python"
    - ... (97 more variations)
    
    All variations use the same expected output, reinforcing the correct response.
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    
    # Generate exercise with variations
    total_generated, saved_count, errors = await manager.create_with_variations_async(
        prompt=request.prompt,
        expected_output=request.expected_output,
        domain=request.domain,
        quality=request.quality,
        variation_count=request.variation_count,
        auto_save=request.auto_save
    )
    
    # Calculate duplicates (generated but not saved and not errors)
    duplicates = total_generated - saved_count - len([e for e in errors if "already exists" not in e.lower()])
    
    # Generate result message
    if saved_count == 0:
        if errors:
            message = f"Failed to save any exercises. First error: {errors[0]}"
        else:
            message = "All exercises were duplicates of existing training data."
    elif saved_count < total_generated // 2:
        message = f"Saved {saved_count} exercises. Some variations were duplicates or had errors."
    else:
        message = f"Successfully generated and saved {saved_count} training examples!"
    
    return VariationsResultResponse(
        total_generated=total_generated,
        successfully_saved=saved_count,
        duplicates_skipped=max(0, duplicates),
        errors=errors[:20],  # Limit errors in response
        message=message
    )


@router.post("/test", response_model=TestResultResponse)
async def test_exercise(request: TestExerciseRequest):
    """
    Test an exercise against a model (e.g., PersRM).
    
    Runs inference and computes similarity between expected and actual output.
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    
    result = await manager.test_exercise(
        exercise_id=request.exercise_id,
        model=request.model
    )
    
    return TestResultResponse(
        exercise_id=result.exercise_id,
        model_output=result.model_output,
        similarity_score=result.similarity_score,
        passed=result.passed,
        execution_time_ms=result.execution_time_ms,
        error=result.error
    )


@router.post("/save")
async def save_exercise(request: SaveExerciseRequest):
    """
    Save an exercise to the training data file (train.jsonl).
    
    This makes the exercise permanent and removes it from the cache.
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    
    success, message = manager.save_to_training(request.exercise_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message}


@router.post("/batch", response_model=BatchResultResponse)
async def batch_import(
    file: UploadFile = File(...),
    file_type: str = Form("json")
):
    """
    Batch import exercises from a JSON or CSV file.
    
    JSON format (array or newline-delimited):
    [{"prompt": "...", "expected_output": "...", "domain": "...", "quality": 0.8}]
    
    CSV format (with headers):
    prompt,expected_output,domain,quality
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    
    # Read file content
    content = await file.read()
    try:
        content_str = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
    
    # Determine file type from extension if not specified
    if file_type == "auto":
        if file.filename.endswith('.csv'):
            file_type = "csv"
        else:
            file_type = "json"
    
    result = manager.batch_import(content_str, file_type)
    
    return BatchResultResponse(
        total=result.total,
        successful=result.successful,
        failed=result.failed,
        duplicates=result.duplicates,
        errors=result.errors[:20]  # Limit error messages
    )


@router.get("/list", response_model=List[ExerciseResponse])
async def list_exercises(limit: int = 50):
    """
    List cached exercises (not yet saved to training data).
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    exercises = manager.list_exercises(limit=limit)
    
    return [
        ExerciseResponse(
            id=ex.id,
            prompt=ex.prompt,
            expected_output=ex.expected_output,
            domain=ex.domain,
            quality=ex.quality,
            created_at=ex.created_at,
            metadata=ex.metadata
        )
        for ex in exercises
    ]


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get statistics about exercises and training data.
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    stats = manager.get_stats()
    
    return StatsResponse(**stats)


@router.get("/recent", response_model=List[RecentExampleResponse])
async def get_recent_training_examples(limit: int = 20):
    """
    Get the most recent training examples that have been saved.
    
    This shows exercises that were auto-saved directly to training data,
    which won't appear in the cached exercises list.
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    examples = manager.get_recent_training_examples(limit=limit)
    
    return [RecentExampleResponse(**ex) for ex in examples]


@router.post("/test-saved", response_model=TestSavedExerciseResponse)
async def test_saved_exercise(request: TestSavedExerciseRequest):
    """
    Test a saved training example against a model.
    
    This allows you to verify how well the trained model performs
    on exercises that were previously saved to training data.
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    
    # Run the test using the exercise manager's test functionality
    result = manager.test_with_model(
        prompt=request.prompt,
        expected_output=request.expected_output,
        model=request.model
    )
    
    return TestSavedExerciseResponse(
        prompt=request.prompt,
        expected_output=request.expected_output,
        model_output=result.get("model_output", ""),
        similarity=result.get("similarity", 0.0),
        passed=result.get("passed", False),
        model=request.model
    )


@router.get("/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(exercise_id: str):
    """
    Get a specific exercise by ID.
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    exercise = manager.get_exercise(exercise_id)
    
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    return ExerciseResponse(
        id=exercise.id,
        prompt=exercise.prompt,
        expected_output=exercise.expected_output,
        domain=exercise.domain,
        quality=exercise.quality,
        created_at=exercise.created_at,
        metadata=exercise.metadata
    )


@router.delete("/{exercise_id}")
async def delete_exercise(exercise_id: str):
    """
    Delete a cached exercise.
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    
    if not manager.delete_exercise(exercise_id):
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    return {"success": True, "message": "Exercise deleted"}


@router.get("/template/cot", response_model=CoTTemplateResponse)
async def get_cot_template():
    """
    Get the Chain-of-Thought format template and example.
    """
    from ChatOS.training.exercise_manager import get_exercise_manager
    
    manager = get_exercise_manager()
    
    template = """<think>
Step 1: [Analyze the problem]
- What is being asked?
- What are the key constraints?

Step 2: [Plan the approach]
- Break down the solution
- Consider edge cases

Step 3: [Execute]
- Implement the solution
- Verify correctness
</think>

<answer>
[Your final answer here]
</answer>"""

    example = """<think>
Step 1: Understanding the problem
The user is asking to calculate the factorial of 5.
Factorial is the product of all positive integers up to n.

Step 2: Planning the approach
I'll multiply: 5 × 4 × 3 × 2 × 1

Step 3: Executing
5 × 4 = 20
20 × 3 = 60
60 × 2 = 120
120 × 1 = 120
</think>

<answer>
The factorial of 5 (5!) is 120.
</answer>"""

    return CoTTemplateResponse(
        template=template,
        example=example,
        domains=manager.VALID_DOMAINS
    )

