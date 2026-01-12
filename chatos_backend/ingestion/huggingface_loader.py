"""
huggingface_loader.py - Load training data from HuggingFace datasets.

Supports popular instruction/chat datasets and converts them to
the unified training example format.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from chatos_backend.database.connection import DatabaseSession
from chatos_backend.database.models import (
    DataSource,
    ExampleStatus,
    KnowledgeDomain,
    SourceType,
    TrainingExample,
)


# =============================================================================
# Recommended Datasets
# =============================================================================

@dataclass
class DatasetConfig:
    """Configuration for a HuggingFace dataset."""
    name: str
    description: str
    hf_path: str
    hf_split: str = "train"
    subset: Optional[str] = None
    
    # Field mappings
    input_field: str = "instruction"
    output_field: str = "output"
    system_field: Optional[str] = None
    messages_field: Optional[str] = None  # For chat format datasets
    
    # Target domain
    default_domain: str = "instruction_following"
    
    # Quality hints
    estimated_examples: int = 0
    quality_tier: str = "high"  # high, medium, low


RECOMMENDED_DATASETS: Dict[str, DatasetConfig] = {
    # High-quality instruction datasets
    "openassistant": DatasetConfig(
        name="OpenAssistant OASST1",
        description="High-quality human-annotated conversations",
        hf_path="OpenAssistant/oasst1",
        messages_field="messages",  # Chat format
        default_domain="conversation",
        estimated_examples=84437,
        quality_tier="high",
    ),
    "code_alpaca": DatasetConfig(
        name="Code Alpaca 20k",
        description="Code instruction-following dataset",
        hf_path="sahil2801/CodeAlpaca-20k",
        input_field="instruction",
        output_field="output",
        default_domain="python",
        estimated_examples=20022,
        quality_tier="high",
    ),
    "gpteacher": DatasetConfig(
        name="GPTeacher General Instruct",
        description="General instruction following",
        hf_path="teknium/GPTeacher-General-Instruct",
        input_field="instruction",
        output_field="response",
        default_domain="instruction_following",
        estimated_examples=29013,
        quality_tier="high",
    ),
    "dolly": DatasetConfig(
        name="Databricks Dolly 15k",
        description="Human-generated instruction dataset",
        hf_path="databricks/databricks-dolly-15k",
        input_field="instruction",
        output_field="response",
        system_field="context",
        default_domain="instruction_following",
        estimated_examples=15011,
        quality_tier="high",
    ),
    "sharegpt_vicuna": DatasetConfig(
        name="ShareGPT Vicuna",
        description="Filtered ShareGPT conversations",
        hf_path="anon8231489123/ShareGPT_Vicuna_unfiltered",
        subset="ShareGPT_V3_unfiltered_cleaned_split",
        messages_field="conversations",
        default_domain="conversation",
        estimated_examples=90000,
        quality_tier="medium",
    ),
    "alpaca": DatasetConfig(
        name="Stanford Alpaca",
        description="Classic instruction-tuning dataset",
        hf_path="tatsu-lab/alpaca",
        input_field="instruction",
        output_field="output",
        system_field="input",  # Context/input field
        default_domain="instruction_following",
        estimated_examples=52002,
        quality_tier="medium",
    ),
    "evol_instruct": DatasetConfig(
        name="Evol-Instruct",
        description="Evolved instruction complexity",
        hf_path="WizardLM/WizardLM_evol_instruct_70k",
        input_field="instruction",
        output_field="output",
        default_domain="reasoning",
        estimated_examples=70000,
        quality_tier="high",
    ),
}


# =============================================================================
# HuggingFace Loader
# =============================================================================

class HuggingFaceLoader:
    """
    Load and process HuggingFace datasets into the learning loop database.
    """
    
    def __init__(self):
        """Initialize the loader."""
        self._datasets_available = False
        try:
            import datasets
            self._datasets_available = True
        except ImportError:
            print("Warning: 'datasets' library not installed. Run: pip install datasets")
    
    def list_available_datasets(self) -> List[Dict[str, Any]]:
        """List all recommended datasets with their configurations."""
        return [
            {
                "key": key,
                "name": config.name,
                "description": config.description,
                "hf_path": config.hf_path,
                "estimated_examples": config.estimated_examples,
                "quality_tier": config.quality_tier,
                "default_domain": config.default_domain,
            }
            for key, config in RECOMMENDED_DATASETS.items()
        ]
    
    def _ensure_data_source(self, config: DatasetConfig) -> DataSource:
        """Get or create a DataSource for the HuggingFace dataset."""
        with DatabaseSession() as db:
            source = db.query(DataSource).filter(
                DataSource.name == f"hf_{config.hf_path.replace('/', '_')}"
            ).first()
            
            if not source:
                source = DataSource(
                    name=f"hf_{config.hf_path.replace('/', '_')}",
                    source_type=SourceType.HUGGINGFACE,
                    description=config.description,
                    config={
                        "hf_path": config.hf_path,
                        "hf_split": config.hf_split,
                        "subset": config.subset,
                        "quality_tier": config.quality_tier,
                    },
                    is_active=True,
                )
                db.add(source)
                db.flush()
            
            source_id = source.id
        
        return source_id
    
    def _get_domain_id(self, domain_name: str) -> Optional[int]:
        """Get domain ID by name."""
        with DatabaseSession() as db:
            domain = db.query(KnowledgeDomain).filter(
                KnowledgeDomain.name == domain_name
            ).first()
            return domain.id if domain else None
    
    def _compute_hash(self, user_input: str, assistant_output: str) -> str:
        """Compute content hash for deduplication."""
        content = f"{user_input}|||{assistant_output}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _convert_example(
        self,
        row: Dict[str, Any],
        config: DatasetConfig,
        row_index: int,
    ) -> Optional[Dict[str, Any]]:
        """Convert a dataset row to training example format."""
        try:
            # Handle chat format (messages field)
            if config.messages_field and config.messages_field in row:
                messages = row[config.messages_field]
                if not messages or len(messages) < 2:
                    return None
                
                # Extract from messages
                system_prompt = None
                user_input = None
                assistant_output = None
                
                for msg in messages:
                    role = msg.get("role", msg.get("from", "")).lower()
                    content = msg.get("content", msg.get("value", ""))
                    
                    if role in ["system"]:
                        system_prompt = content
                    elif role in ["user", "human"]:
                        if user_input is None:
                            user_input = content
                    elif role in ["assistant", "gpt", "bot"]:
                        if assistant_output is None:
                            assistant_output = content
                
                if not user_input or not assistant_output:
                    return None
                
                return {
                    "system_prompt": system_prompt,
                    "user_input": user_input,
                    "assistant_output": assistant_output,
                    "messages": messages,
                }
            
            # Handle instruction/output format
            user_input = row.get(config.input_field, "")
            assistant_output = row.get(config.output_field, "")
            
            # Get system prompt / context if available
            system_prompt = None
            if config.system_field and config.system_field in row:
                context = row[config.system_field]
                if context:
                    system_prompt = context if len(context) > 10 else None
            
            if not user_input or not assistant_output:
                return None
            
            # Skip very short or very long examples
            if len(user_input) < 10 or len(assistant_output) < 10:
                return None
            if len(user_input) > 10000 or len(assistant_output) > 20000:
                return None
            
            return {
                "system_prompt": system_prompt,
                "user_input": user_input,
                "assistant_output": assistant_output,
                "messages": None,
            }
            
        except Exception as e:
            print(f"Error converting row {row_index}: {e}")
            return None
    
    def load_dataset(
        self,
        dataset_key: str,
        max_examples: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        batch_size: int = 100,
    ) -> Tuple[int, int]:
        """
        Load a HuggingFace dataset into the database.
        
        Args:
            dataset_key: Key from RECOMMENDED_DATASETS or full HF path
            max_examples: Maximum examples to load (None = all)
            progress_callback: Optional callback(loaded, total)
            batch_size: Number of examples to commit at once
        
        Returns:
            Tuple of (examples_loaded, examples_skipped)
        """
        if not self._datasets_available:
            raise RuntimeError("HuggingFace datasets library not installed")
        
        import datasets
        
        # Get dataset configuration
        if dataset_key in RECOMMENDED_DATASETS:
            config = RECOMMENDED_DATASETS[dataset_key]
        else:
            # Assume it's a direct HF path
            config = DatasetConfig(
                name=dataset_key,
                description=f"HuggingFace dataset: {dataset_key}",
                hf_path=dataset_key,
            )
        
        print(f"Loading dataset: {config.name} ({config.hf_path})")
        
        # Load the dataset
        try:
            if config.subset:
                hf_dataset = datasets.load_dataset(
                    config.hf_path,
                    config.subset,
                    split=config.hf_split,
                    trust_remote_code=True,
                )
            else:
                hf_dataset = datasets.load_dataset(
                    config.hf_path,
                    split=config.hf_split,
                    trust_remote_code=True,
                )
        except Exception as e:
            raise RuntimeError(f"Failed to load dataset {config.hf_path}: {e}")
        
        # Get or create data source
        source_id = self._ensure_data_source(config)
        domain_id = self._get_domain_id(config.default_domain)
        
        # Track statistics
        loaded = 0
        skipped = 0
        batch = []
        total = len(hf_dataset)
        
        if max_examples:
            total = min(total, max_examples)
        
        print(f"Processing {total} examples...")
        
        for idx, row in enumerate(hf_dataset):
            if max_examples and idx >= max_examples:
                break
            
            # Convert example
            converted = self._convert_example(row, config, idx)
            if not converted:
                skipped += 1
                continue
            
            # Compute content hash
            content_hash = self._compute_hash(
                converted["user_input"],
                converted["assistant_output"]
            )
            
            # Create training example
            example = TrainingExample(
                source_id=source_id,
                external_id=f"row_{idx}",
                system_prompt=converted.get("system_prompt"),
                user_input=converted["user_input"],
                assistant_output=converted["assistant_output"],
                messages=converted.get("messages"),
                domain_id=domain_id,
                status=ExampleStatus.PROCESSED,
                content_hash=content_hash,
                extra_data={
                    "hf_path": config.hf_path,
                    "row_index": idx,
                    "quality_tier": config.quality_tier,
                },
            )
            batch.append(example)
            loaded += 1
            
            # Batch insert
            if len(batch) >= batch_size:
                self._insert_batch(batch)
                batch = []
                
                if progress_callback:
                    progress_callback(loaded, total)
                elif loaded % 1000 == 0:
                    print(f"  Loaded {loaded}/{total} examples...")
        
        # Insert remaining batch
        if batch:
            self._insert_batch(batch)
        
        # Update source statistics
        self._update_source_stats(source_id, loaded)
        
        print(f"Completed: {loaded} loaded, {skipped} skipped")
        return loaded, skipped
    
    def _insert_batch(self, examples: List[TrainingExample]) -> None:
        """Insert a batch of examples, handling duplicates."""
        with DatabaseSession() as db:
            for example in examples:
                # Check for duplicate by content hash
                existing = db.query(TrainingExample).filter(
                    TrainingExample.content_hash == example.content_hash
                ).first()
                
                if not existing:
                    db.add(example)
    
    def _update_source_stats(self, source_id: int, count: int) -> None:
        """Update data source statistics."""
        with DatabaseSession() as db:
            source = db.query(DataSource).filter(DataSource.id == source_id).first()
            if source:
                source.total_examples = (source.total_examples or 0) + count
                source.processed_examples = (source.processed_examples or 0) + count
                source.last_sync_at = datetime.utcnow()


# =============================================================================
# Convenience Functions
# =============================================================================

def load_huggingface_dataset(
    dataset_key: str,
    max_examples: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[int, int]:
    """
    Load a HuggingFace dataset into the learning loop database.
    
    Args:
        dataset_key: Key from RECOMMENDED_DATASETS or HuggingFace path
        max_examples: Maximum examples to load
        progress_callback: Optional progress callback
    
    Returns:
        Tuple of (examples_loaded, examples_skipped)
    """
    loader = HuggingFaceLoader()
    return loader.load_dataset(dataset_key, max_examples, progress_callback)


def get_recommended_datasets() -> List[Dict[str, Any]]:
    """Get list of recommended HuggingFace datasets."""
    loader = HuggingFaceLoader()
    return loader.list_available_datasets()

