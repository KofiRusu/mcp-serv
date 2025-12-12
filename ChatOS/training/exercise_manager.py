"""
exercise_manager.py - Core logic for training exercise creation and management.

Provides functionality to:
- Create and validate training exercises
- Test exercises against PersRM model
- Save quality exercises to training data
- Batch import from JSON/CSV files
- Compute similarity between expected and actual outputs
"""

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import csv
import io


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Exercise:
    """Represents a single training exercise."""
    id: str
    prompt: str
    expected_output: str
    domain: str
    quality: float
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_training_format(self) -> Dict[str, Any]:
        """Convert to JSONL training format."""
        return {
            "instruction": self.prompt,
            "output": self.expected_output,
            "metadata": {
                "source": "user_exercise",
                "quality": self.quality,
                "domain": self.domain,
                "exercise_id": self.id,
                "created_at": self.created_at,
                **self.metadata
            }
        }


@dataclass
class TestResult:
    """Result of testing an exercise against PersRM."""
    exercise_id: str
    model_output: str
    similarity_score: float
    passed: bool
    execution_time_ms: float
    error: Optional[str] = None
    
    
@dataclass
class BatchResult:
    """Result of batch importing exercises."""
    total: int
    successful: int
    failed: int
    duplicates: int
    errors: List[str] = field(default_factory=list)


# =============================================================================
# Exercise Manager
# =============================================================================

class ExerciseManager:
    """
    Manages training exercise creation, testing, and storage.
    """
    
    VALID_DOMAINS = ["coding", "trading", "reasoning", "general", "math", "science"]
    COT_PATTERN = re.compile(r'<think>.*?</think>.*?<answer>.*?</answer>', re.DOTALL)
    
    def __init__(
        self,
        training_data_path: Path = None,
        exercises_cache_path: Path = None
    ):
        """
        Initialize the ExerciseManager.
        
        Args:
            training_data_path: Path to train.jsonl file
            exercises_cache_path: Path to cache temporary exercises
        """
        self.training_data_path = training_data_path or Path("data/persrm/train.jsonl")
        self.exercises_cache_path = exercises_cache_path or Path("data/persrm/exercises_cache.json")
        
        # Ensure directories exist
        self.training_data_path.parent.mkdir(parents=True, exist_ok=True)
        self.exercises_cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing exercises from cache
        self._exercises: Dict[str, Exercise] = {}
        self._load_cache()
        
        # Load existing training data hashes for deduplication
        self._training_hashes: set = set()
        self._load_training_hashes()
    
    def _load_cache(self) -> None:
        """Load exercises from cache file."""
        if self.exercises_cache_path.exists():
            try:
                with open(self.exercises_cache_path, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        ex = Exercise(**item)
                        self._exercises[ex.id] = ex
            except Exception as e:
                print(f"Warning: Failed to load exercise cache: {e}")
    
    def _save_cache(self) -> None:
        """Save exercises to cache file."""
        try:
            with open(self.exercises_cache_path, 'w') as f:
                data = [asdict(ex) for ex in self._exercises.values()]
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save exercise cache: {e}")
    
    def _load_training_hashes(self) -> None:
        """Load hashes of existing training examples for deduplication."""
        if self.training_data_path.exists():
            try:
                with open(self.training_data_path, 'r') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            content_hash = self._hash_example(
                                data.get("instruction", ""),
                                data.get("output", "")
                            )
                            self._training_hashes.add(content_hash)
            except Exception as e:
                print(f"Warning: Failed to load training hashes: {e}")
    
    def _hash_example(self, prompt: str, output: str) -> str:
        """Generate a hash for deduplication."""
        content = f"{prompt.strip().lower()}||{output.strip().lower()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _validate_cot_format(self, text: str) -> Tuple[bool, str]:
        """
        Validate that text contains proper CoT format.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text.strip():
            return False, "Output cannot be empty"
        
        has_think = '<think>' in text and '</think>' in text
        has_answer = '<answer>' in text and '</answer>' in text
        
        if not has_think:
            return False, "Missing <think>...</think> tags"
        if not has_answer:
            return False, "Missing <answer>...</answer> tags"
        
        # Check order: think should come before answer
        think_start = text.find('<think>')
        answer_start = text.find('<answer>')
        
        if answer_start < think_start:
            return False, "<think> tags should come before <answer> tags"
        
        return True, ""
    
    def create_exercise(
        self,
        prompt: str,
        expected_output: str,
        domain: str = "general",
        quality: float = 0.8,
        metadata: Dict[str, Any] = None,
        validate_cot: bool = True
    ) -> Tuple[Optional[Exercise], Optional[str]]:
        """
        Create a new training exercise.
        
        Args:
            prompt: The input prompt/instruction
            expected_output: The expected model output (with CoT format)
            domain: Category (coding, trading, reasoning, general)
            quality: Quality score 0.0-1.0
            metadata: Additional metadata
            validate_cot: Whether to validate CoT format
            
        Returns:
            Tuple of (Exercise or None, error message or None)
        """
        # Validate inputs
        if not prompt.strip():
            return None, "Prompt cannot be empty"
        
        if not expected_output.strip():
            return None, "Expected output cannot be empty"
        
        if domain not in self.VALID_DOMAINS:
            return None, f"Invalid domain. Must be one of: {', '.join(self.VALID_DOMAINS)}"
        
        if not 0.0 <= quality <= 1.0:
            return None, "Quality must be between 0.0 and 1.0"
        
        # Validate CoT format if required
        if validate_cot:
            is_valid, error = self._validate_cot_format(expected_output)
            if not is_valid:
                return None, f"Invalid CoT format: {error}"
        
        # Check for duplicates
        content_hash = self._hash_example(prompt, expected_output)
        if content_hash in self._training_hashes:
            return None, "This exercise already exists in training data"
        
        # Create exercise
        exercise = Exercise(
            id=str(uuid.uuid4())[:8],
            prompt=prompt.strip(),
            expected_output=expected_output.strip(),
            domain=domain,
            quality=quality,
            created_at=datetime.utcnow().isoformat(),
            metadata=metadata or {}
        )
        
        # Cache the exercise
        self._exercises[exercise.id] = exercise
        self._save_cache()
        
        return exercise, None
    
    def get_exercise(self, exercise_id: str) -> Optional[Exercise]:
        """Get an exercise by ID."""
        return self._exercises.get(exercise_id)
    
    def list_exercises(self, limit: int = 50) -> List[Exercise]:
        """List recent exercises."""
        exercises = list(self._exercises.values())
        exercises.sort(key=lambda x: x.created_at, reverse=True)
        return exercises[:limit]
    
    def delete_exercise(self, exercise_id: str) -> bool:
        """Delete an exercise from cache."""
        if exercise_id in self._exercises:
            del self._exercises[exercise_id]
            self._save_cache()
            return True
        return False
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts.
        
        Uses multiple metrics and returns average score.
        """
        # Normalize texts
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        
        # SequenceMatcher ratio
        seq_ratio = SequenceMatcher(None, t1, t2).ratio()
        
        # Word overlap (Jaccard similarity)
        words1 = set(t1.split())
        words2 = set(t2.split())
        if words1 or words2:
            jaccard = len(words1 & words2) / len(words1 | words2)
        else:
            jaccard = 0.0
        
        # Extract answer sections and compare
        answer_sim = 0.0
        answer1 = self._extract_answer(text1)
        answer2 = self._extract_answer(text2)
        if answer1 and answer2:
            answer_sim = SequenceMatcher(None, answer1.lower(), answer2.lower()).ratio()
        
        # Weighted average (answer content is most important)
        if answer_sim > 0:
            return 0.3 * seq_ratio + 0.2 * jaccard + 0.5 * answer_sim
        else:
            return 0.6 * seq_ratio + 0.4 * jaccard
    
    def _extract_answer(self, text: str) -> Optional[str]:
        """Extract content from <answer> tags."""
        match = re.search(r'<answer>(.*?)</answer>', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    async def test_exercise(
        self,
        exercise_id: str,
        model: str = "persrm-standalone"
    ) -> TestResult:
        """
        Test an exercise against a model.
        
        Args:
            exercise_id: ID of the exercise to test
            model: Model name to use for inference
            
        Returns:
            TestResult with model output and similarity score
        """
        import time
        
        exercise = self.get_exercise(exercise_id)
        if not exercise:
            return TestResult(
                exercise_id=exercise_id,
                model_output="",
                similarity_score=0.0,
                passed=False,
                execution_time_ms=0,
                error="Exercise not found"
            )
        
        start_time = time.time()
        
        try:
            # Try to use Ollama for inference
            import subprocess
            
            result = subprocess.run(
                ["ollama", "run", model, exercise.prompt],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                # Fallback error
                return TestResult(
                    exercise_id=exercise_id,
                    model_output="",
                    similarity_score=0.0,
                    passed=False,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    error=f"Model error: {result.stderr[:200]}"
                )
            
            model_output = result.stdout.strip()
            execution_time = (time.time() - start_time) * 1000
            
            # Compute similarity
            similarity = self.compute_similarity(exercise.expected_output, model_output)
            
            # Pass threshold is 0.6 by default
            passed = similarity >= 0.6
            
            return TestResult(
                exercise_id=exercise_id,
                model_output=model_output,
                similarity_score=similarity,
                passed=passed,
                execution_time_ms=execution_time
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                exercise_id=exercise_id,
                model_output="",
                similarity_score=0.0,
                passed=False,
                execution_time_ms=60000,
                error="Model inference timed out (60s)"
            )
        except FileNotFoundError:
            return TestResult(
                exercise_id=exercise_id,
                model_output="",
                similarity_score=0.0,
                passed=False,
                execution_time_ms=(time.time() - start_time) * 1000,
                error="Ollama not found. Please install and start Ollama."
            )
        except Exception as e:
            return TestResult(
                exercise_id=exercise_id,
                model_output="",
                similarity_score=0.0,
                passed=False,
                execution_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    def test_with_model(
        self,
        prompt: str,
        expected_output: str,
        model: str = "persrm-standalone"
    ) -> Dict[str, Any]:
        """
        Test a prompt/expected output pair against a model.
        
        This is useful for testing saved training examples to see
        how well the model has learned them.
        
        Args:
            prompt: The input prompt
            expected_output: The expected output
            model: Model to test with
            
        Returns:
            Dict with model_output, similarity, and passed status
        """
        import time
        import subprocess
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["ollama", "run", model, prompt],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for longer responses
            )
            
            if result.returncode != 0:
                return {
                    "model_output": f"Error: {result.stderr[:500]}",
                    "similarity": 0.0,
                    "passed": False,
                    "execution_time_ms": (time.time() - start_time) * 1000,
                    "error": result.stderr[:200]
                }
            
            model_output = result.stdout.strip()
            execution_time = (time.time() - start_time) * 1000
            
            # Compute similarity
            similarity = self.compute_similarity(expected_output, model_output)
            
            # Pass threshold is 0.5 for saved examples (slightly more lenient)
            passed = similarity >= 0.5
            
            return {
                "model_output": model_output,
                "similarity": similarity,
                "passed": passed,
                "execution_time_ms": execution_time
            }
            
        except subprocess.TimeoutExpired:
            return {
                "model_output": "Error: Model inference timed out (120s)",
                "similarity": 0.0,
                "passed": False,
                "execution_time_ms": 120000,
                "error": "Timeout"
            }
        except FileNotFoundError:
            return {
                "model_output": "Error: Ollama not found. Please install and start Ollama.",
                "similarity": 0.0,
                "passed": False,
                "execution_time_ms": (time.time() - start_time) * 1000,
                "error": "Ollama not found"
            }
        except Exception as e:
            return {
                "model_output": f"Error: {str(e)}",
                "similarity": 0.0,
                "passed": False,
                "execution_time_ms": (time.time() - start_time) * 1000,
                "error": str(e)
            }
    
    def save_to_training(self, exercise_id: str) -> Tuple[bool, str]:
        """
        Save an exercise to the training data file.
        
        Args:
            exercise_id: ID of the exercise to save
            
        Returns:
            Tuple of (success, message)
        """
        exercise = self.get_exercise(exercise_id)
        if not exercise:
            return False, "Exercise not found"
        
        # Check for duplicates again
        content_hash = self._hash_example(exercise.prompt, exercise.expected_output)
        if content_hash in self._training_hashes:
            return False, "Exercise already exists in training data"
        
        try:
            # Append to training file
            training_entry = exercise.to_training_format()
            
            with open(self.training_data_path, 'a') as f:
                f.write(json.dumps(training_entry) + '\n')
            
            # Update hash set
            self._training_hashes.add(content_hash)
            
            # Remove from cache (it's now in training data)
            del self._exercises[exercise_id]
            self._save_cache()
            
            return True, f"Exercise saved to {self.training_data_path}"
            
        except Exception as e:
            return False, f"Failed to save: {str(e)}"
    
    def batch_import(
        self,
        file_content: str,
        file_type: str = "json"
    ) -> BatchResult:
        """
        Batch import exercises from file content.
        
        Args:
            file_content: File content as string
            file_type: "json" or "csv"
            
        Returns:
            BatchResult with import statistics
        """
        result = BatchResult(total=0, successful=0, failed=0, duplicates=0)
        exercises_to_import = []
        
        try:
            if file_type == "json":
                # Parse JSON (can be array or newline-delimited)
                try:
                    data = json.loads(file_content)
                    if isinstance(data, list):
                        exercises_to_import = data
                    else:
                        exercises_to_import = [data]
                except json.JSONDecodeError:
                    # Try line-by-line
                    for line in file_content.strip().split('\n'):
                        if line.strip():
                            exercises_to_import.append(json.loads(line))
                            
            elif file_type == "csv":
                reader = csv.DictReader(io.StringIO(file_content))
                for row in reader:
                    exercises_to_import.append(row)
            else:
                result.errors.append(f"Unsupported file type: {file_type}")
                return result
                
        except Exception as e:
            result.errors.append(f"Failed to parse file: {str(e)}")
            return result
        
        result.total = len(exercises_to_import)
        
        # Process each exercise
        for i, item in enumerate(exercises_to_import):
            try:
                prompt = item.get("prompt") or item.get("instruction") or item.get("input", "")
                expected = item.get("expected_output") or item.get("output") or item.get("expected", "")
                domain = item.get("domain", "general")
                quality = float(item.get("quality", 0.8))
                
                exercise, error = self.create_exercise(
                    prompt=prompt,
                    expected_output=expected,
                    domain=domain,
                    quality=quality,
                    validate_cot=True
                )
                
                if exercise:
                    # Save directly to training data
                    success, msg = self.save_to_training(exercise.id)
                    if success:
                        result.successful += 1
                    elif "already exists" in msg:
                        result.duplicates += 1
                    else:
                        result.failed += 1
                        result.errors.append(f"Row {i+1}: {msg}")
                else:
                    if error and "already exists" in error:
                        result.duplicates += 1
                    else:
                        result.failed += 1
                        result.errors.append(f"Row {i+1}: {error}")
                        
            except Exception as e:
                result.failed += 1
                result.errors.append(f"Row {i+1}: {str(e)}")
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about exercises and training data."""
        training_count = 0
        domain_counts = {domain: 0 for domain in self.VALID_DOMAINS}
        
        if self.training_data_path.exists():
            with open(self.training_data_path, 'r') as f:
                for line in f:
                    if line.strip():
                        training_count += 1
                        try:
                            data = json.loads(line)
                            domain = data.get("metadata", {}).get("domain", "general")
                            if domain in domain_counts:
                                domain_counts[domain] += 1
                        except:
                            pass
        
        return {
            "cached_exercises": len(self._exercises),
            "training_examples": training_count,
            "domains": domain_counts,
            "valid_domains": self.VALID_DOMAINS
        }
    
    def get_training_example_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific training example by its line index (from the end).
        
        Args:
            index: Index from the end (0 = most recent)
            
        Returns:
            Full training example with all fields
        """
        if not self.training_data_path.exists():
            return None
        
        try:
            import subprocess
            # Get specific line from end
            result = subprocess.run(
                ['tail', '-n', str(index + 1), str(self.training_data_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines:
                    # Get the first line (which is the Nth from end)
                    line = lines[0]
                    if line.strip():
                        data = json.loads(line)
                        return {
                            "instruction": data.get("instruction", ""),
                            "output": data.get("output", ""),
                            "metadata": data.get("metadata", {}),
                            "index": index
                        }
        except Exception as e:
            print(f"Error getting training example: {e}")
        
        return None
    
    def get_recent_training_examples(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get the most recent training examples from train.jsonl.
        
        Args:
            limit: Maximum number of examples to return
            
        Returns:
            List of recent training examples with metadata
        """
        examples = []
        
        if not self.training_data_path.exists():
            return examples
        
        try:
            import subprocess
            # Use tail command for efficiency on large files
            result = subprocess.run(
                ['tail', '-n', str(limit), str(self.training_data_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Reverse to show most recent first
                lines.reverse()
                
                for idx, line in enumerate(lines):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            prompt = data.get("instruction", "")
                            full_prompt = prompt  # Keep full version
                            # Truncate prompt for display
                            if len(prompt) > 100:
                                prompt = prompt[:100] + "..."
                            
                            examples.append({
                                "prompt": prompt,
                                "full_prompt": full_prompt,
                                "expected_output": data.get("output", ""),
                                "domain": data.get("metadata", {}).get("domain", "general"),
                                "quality": data.get("metadata", {}).get("quality", 0.8),
                                "source": data.get("metadata", {}).get("source", "unknown"),
                                "created_at": data.get("metadata", {}).get("created_at", ""),
                                "variation_type": data.get("metadata", {}).get("variation_type", "original"),
                                "exercise_id": data.get("metadata", {}).get("exercise_id", ""),
                                "index": idx,  # Index for retrieval
                            })
                        except json.JSONDecodeError:
                            pass
                        
        except Exception as e:
            print(f"Error reading recent examples: {e}")
        
        return examples
    
    def create_with_variations(
        self,
        prompt: str,
        expected_output: str,
        domain: str = "general",
        quality: float = 0.8,
        variation_count: int = 100,
        auto_save: bool = True
    ) -> Tuple[int, int, List[str]]:
        """
        Create an exercise and automatically generate variations for training.
        
        Args:
            prompt: Base prompt
            expected_output: Expected output (CoT format)
            domain: Domain category
            quality: Base quality score
            variation_count: Number of variations to generate (default 100)
            auto_save: Whether to auto-save to training data
            
        Returns:
            Tuple of (total_generated, successfully_saved, error_messages)
        """
        from ChatOS.training.prompt_variation_generator import get_variation_generator
        
        errors = []
        saved_count = 0
        
        # First, validate and create the original exercise
        original_ex, error = self.create_exercise(
            prompt=prompt,
            expected_output=expected_output,
            domain=domain,
            quality=quality,
            validate_cot=True
        )
        
        if error:
            errors.append(f"Original: {error}")
        elif auto_save:
            success, msg = self.save_to_training(original_ex.id)
            if success:
                saved_count += 1
            else:
                errors.append(f"Original save failed: {msg}")
        
        # Generate variations
        generator = get_variation_generator()
        result = generator.generate_variations(
            prompt=prompt,
            expected_output=expected_output,
            domain=domain,
            count=variation_count,
            quality_base=quality
        )
        
        # Process each variation
        for i, var in enumerate(result.variations):
            try:
                # Create exercise for variation
                var_ex, var_error = self.create_exercise(
                    prompt=var["prompt"],
                    expected_output=var["expected_output"],
                    domain=var["domain"],
                    quality=var["quality"],
                    metadata={
                        "variation_type": var["variation_type"],
                        "original_prompt": var["original_prompt"],
                        "variation_index": i,
                    },
                    validate_cot=True
                )
                
                if var_error:
                    if "already exists" not in var_error:
                        errors.append(f"Variation {i+1}: {var_error}")
                elif auto_save:
                    success, msg = self.save_to_training(var_ex.id)
                    if success:
                        saved_count += 1
                    elif "already exists" not in msg:
                        errors.append(f"Variation {i+1} save: {msg}")
                        
            except Exception as e:
                errors.append(f"Variation {i+1}: {str(e)}")
        
        total_generated = 1 + result.count  # Original + variations
        return total_generated, saved_count, errors[:50]  # Limit error messages
    
    async def create_with_variations_async(
        self,
        prompt: str,
        expected_output: str,
        domain: str = "general",
        quality: float = 0.8,
        variation_count: int = 100,
        auto_save: bool = True,
        progress_callback: callable = None
    ) -> Tuple[int, int, List[str]]:
        """
        Async version of create_with_variations with optional progress callback.
        
        Args:
            prompt: Base prompt
            expected_output: Expected output (CoT format)
            domain: Domain category
            quality: Base quality score
            variation_count: Number of variations to generate
            auto_save: Whether to auto-save to training data
            progress_callback: Optional async callback(current, total, message)
            
        Returns:
            Tuple of (total_generated, successfully_saved, error_messages)
        """
        import asyncio
        from ChatOS.training.prompt_variation_generator import get_variation_generator
        
        errors = []
        saved_count = 0
        
        if progress_callback:
            await progress_callback(0, variation_count + 1, "Creating original exercise...")
        
        # First, validate and create the original exercise
        original_ex, error = self.create_exercise(
            prompt=prompt,
            expected_output=expected_output,
            domain=domain,
            quality=quality,
            validate_cot=True
        )
        
        if error:
            errors.append(f"Original: {error}")
        elif auto_save:
            success, msg = self.save_to_training(original_ex.id)
            if success:
                saved_count += 1
            else:
                errors.append(f"Original save failed: {msg}")
        
        if progress_callback:
            await progress_callback(1, variation_count + 1, "Generating variations...")
        
        # Generate variations
        generator = get_variation_generator()
        result = generator.generate_variations(
            prompt=prompt,
            expected_output=expected_output,
            domain=domain,
            count=variation_count,
            quality_base=quality
        )
        
        # Process each variation with progress updates
        for i, var in enumerate(result.variations):
            try:
                # Yield control periodically to prevent blocking
                if i % 10 == 0:
                    await asyncio.sleep(0)
                    if progress_callback:
                        await progress_callback(
                            i + 2, 
                            variation_count + 1, 
                            f"Processing variation {i+1}/{result.count}..."
                        )
                
                # Create exercise for variation
                var_ex, var_error = self.create_exercise(
                    prompt=var["prompt"],
                    expected_output=var["expected_output"],
                    domain=var["domain"],
                    quality=var["quality"],
                    metadata={
                        "variation_type": var["variation_type"],
                        "original_prompt": var["original_prompt"],
                        "variation_index": i,
                    },
                    validate_cot=True
                )
                
                if var_error:
                    if "already exists" not in var_error:
                        errors.append(f"Variation {i+1}: {var_error}")
                elif auto_save:
                    success, msg = self.save_to_training(var_ex.id)
                    if success:
                        saved_count += 1
                    elif "already exists" not in msg:
                        errors.append(f"Variation {i+1} save: {msg}")
                        
            except Exception as e:
                errors.append(f"Variation {i+1}: {str(e)}")
        
        if progress_callback:
            await progress_callback(
                variation_count + 1, 
                variation_count + 1, 
                f"Complete! Saved {saved_count} examples."
            )
        
        total_generated = 1 + result.count
        return total_generated, saved_count, errors[:50]


# =============================================================================
# Module-level singleton
# =============================================================================

_manager: Optional[ExerciseManager] = None


def get_exercise_manager() -> ExerciseManager:
    """Get or create the singleton ExerciseManager instance."""
    global _manager
    if _manager is None:
        _manager = ExerciseManager()
    return _manager

