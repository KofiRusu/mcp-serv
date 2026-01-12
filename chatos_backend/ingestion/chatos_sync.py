"""
chatos_sync.py - Sync existing ChatOS and PersRM data into the learning loop database.

Imports data from:
- ~/ChatOS-Memory/training_data/ (ChatOS conversations)
- ~/PersRM-V0.2/data/ (PersRM reasoning data)
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from chatos_backend.config.settings import settings
from chatos_backend.database.connection import DatabaseSession
from chatos_backend.database.models import (
    DataSource,
    DifficultyLevel,
    ExampleStatus,
    KnowledgeDomain,
    SourceType,
    TrainingExample,
)


# =============================================================================
# ChatOS Sync
# =============================================================================

class ChatOSSync:
    """
    Sync ChatOS conversation data into the learning loop database.
    """
    
    def __init__(self):
        """Initialize the sync utility."""
        self.training_data_dir = settings.training_data_dir
        self.persrm_data_dir = Path.home() / "PersRM-V0.2" / "data"
    
    def _ensure_source(self, name: str, description: str, config: Dict) -> int:
        """Get or create a data source."""
        with DatabaseSession() as db:
            source = db.query(DataSource).filter(DataSource.name == name).first()
            
            if not source:
                source = DataSource(
                    name=name,
                    source_type=SourceType.INTERNAL,
                    description=description,
                    config=config,
                    is_active=True,
                )
                db.add(source)
                db.flush()
            
            return source.id
    
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
    
    def sync_conversations(
        self,
        min_score: int = 0,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[int, int]:
        """
        Sync ChatOS conversations to the database.
        
        Args:
            min_score: Minimum feedback score (-1, 0, 1)
            progress_callback: Optional progress callback
        
        Returns:
            Tuple of (synced, skipped)
        """
        if not self.training_data_dir.exists():
            print(f"Training data directory not found: {self.training_data_dir}")
            return 0, 0
        
        source_id = self._ensure_source(
            "chatos_conversations",
            "ChatOS conversation logs",
            {"path": str(self.training_data_dir)},
        )
        domain_id = self._get_domain_id("conversation")
        
        synced = 0
        skipped = 0
        
        # Process JSONL files
        jsonl_files = list(self.training_data_dir.glob("*.jsonl"))
        json_files = list(self.training_data_dir.glob("*.json"))
        all_files = jsonl_files + json_files
        
        print(f"Found {len(all_files)} data files")
        
        for file_idx, data_file in enumerate(all_files):
            try:
                if data_file.suffix == ".jsonl":
                    with open(data_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                result = self._process_conversation(
                                    data, source_id, domain_id, min_score
                                )
                                if result:
                                    synced += 1
                                else:
                                    skipped += 1
                            except json.JSONDecodeError:
                                skipped += 1
                else:
                    with open(data_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    result = self._process_conversation(
                        data, source_id, domain_id, min_score
                    )
                    if result:
                        synced += 1
                    else:
                        skipped += 1
            except Exception as e:
                print(f"Error processing {data_file}: {e}")
                skipped += 1
            
            if progress_callback:
                progress_callback(file_idx + 1, len(all_files))
        
        # Update source stats
        self._update_source_stats(source_id, synced)
        
        print(f"ChatOS sync complete: {synced} synced, {skipped} skipped")
        return synced, skipped
    
    def _process_conversation(
        self,
        data: Dict[str, Any],
        source_id: int,
        domain_id: Optional[int],
        min_score: int,
    ) -> bool:
        """Process a single conversation record."""
        messages = data.get("messages", [])
        metadata = data.get("metadata", {})
        
        if len(messages) < 2:
            return False
        
        # Calculate feedback score
        thumbs_up = metadata.get("thumbs_up")
        quality = metadata.get("quality", "unrated")
        
        if thumbs_up is True:
            score = 1
        elif thumbs_up is False:
            score = -1
        else:
            quality_scores = {
                "excellent": 1, "good": 1, "acceptable": 0,
                "unrated": 0, "poor": -1, "failed": -1
            }
            score = quality_scores.get(quality, 0)
        
        if score < min_score:
            return False
        
        # Extract user/assistant messages
        user_input = None
        assistant_output = None
        system_prompt = None
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                system_prompt = content
            elif role == "user" and user_input is None:
                user_input = content
            elif role == "assistant" and assistant_output is None:
                assistant_output = content
        
        if not user_input or not assistant_output:
            return False
        
        # Compute hash and create example
        content_hash = self._compute_hash(user_input, assistant_output)
        conv_id = metadata.get("conversation_id", data.get("id", ""))
        
        with DatabaseSession() as db:
            # Check for existing
            existing = db.query(TrainingExample).filter(
                TrainingExample.content_hash == content_hash
            ).first()
            
            if existing:
                return False
            
            example = TrainingExample(
                source_id=source_id,
                external_id=conv_id,
                system_prompt=system_prompt,
                user_input=user_input,
                assistant_output=assistant_output,
                messages=messages,
                domain_id=domain_id,
                quality_score=0.5 + (score * 0.3),  # Map -1..1 to 0.2..0.8
                user_rating=score,
                status=ExampleStatus.PROCESSED,
                content_hash=content_hash,
                extra_data={
                    "mode": metadata.get("mode", "normal"),
                    "model": metadata.get("model"),
                    "quality": quality,
                    "source_file": str(conv_id),
                },
            )
            db.add(example)
        
        return True
    
    def sync_persrm_data(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[int, int]:
        """
        Sync PersRM reasoning data to the database.
        
        Returns:
            Tuple of (synced, skipped)
        """
        if not self.persrm_data_dir.exists():
            print(f"PersRM data directory not found: {self.persrm_data_dir}")
            return 0, 0
        
        source_id = self._ensure_source(
            "persrm_data",
            "PersRM UI/UX reasoning data",
            {"path": str(self.persrm_data_dir)},
        )
        
        synced = 0
        skipped = 0
        
        # Load reasoning.jsonl
        reasoning_file = self.persrm_data_dir / "reasoning.jsonl"
        if reasoning_file.exists():
            count, skip = self._load_persrm_file(
                reasoning_file, source_id, "reasoning", "ui_components"
            )
            synced += count
            skipped += skip
        
        # Load reasoning_instruction.jsonl
        instruction_file = self.persrm_data_dir / "reasoning_instruction.jsonl"
        if instruction_file.exists():
            count, skip = self._load_persrm_file(
                instruction_file, source_id, "instruction", "ui_components"
            )
            synced += count
            skipped += skip
        
        # Update source stats
        self._update_source_stats(source_id, synced)
        
        print(f"PersRM sync complete: {synced} synced, {skipped} skipped")
        return synced, skipped
    
    def _load_persrm_file(
        self,
        file_path: Path,
        source_id: int,
        data_type: str,
        domain_name: str,
    ) -> Tuple[int, int]:
        """Load a PersRM JSONL file."""
        domain_id = self._get_domain_id(domain_name)
        synced = 0
        skipped = 0
        
        # PersRM system prompt
        system_prompt = (
            "You are an expert UI/UX designer and developer. Provide detailed, "
            "structured reasoning about design decisions, component architecture, "
            "and user experience considerations."
        )
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # Handle different formats
                    if data_type == "reasoning":
                        user_input = data.get("input", "")
                        assistant_output = data.get("expected_reasoning", "")
                    else:
                        user_input = data.get("instruction", "")
                        assistant_output = data.get("output", "")
                    
                    if not user_input or not assistant_output:
                        skipped += 1
                        continue
                    
                    content_hash = self._compute_hash(user_input, assistant_output)
                    
                    with DatabaseSession() as db:
                        existing = db.query(TrainingExample).filter(
                            TrainingExample.content_hash == content_hash
                        ).first()
                        
                        if existing:
                            skipped += 1
                            continue
                        
                        example = TrainingExample(
                            source_id=source_id,
                            external_id=f"{data_type}_{line_num}",
                            system_prompt=system_prompt,
                            user_input=user_input,
                            assistant_output=assistant_output,
                            domain_id=domain_id,
                            difficulty=DifficultyLevel.INTERMEDIATE,
                            quality_score=0.8,  # PersRM data is curated
                            status=ExampleStatus.PROCESSED,
                            content_hash=content_hash,
                            extra_data={
                                "data_type": data_type,
                                "source_file": file_path.name,
                                "line_number": line_num,
                            },
                        )
                        db.add(example)
                    
                    synced += 1
                    
                except json.JSONDecodeError:
                    skipped += 1
                except Exception as e:
                    print(f"Error at line {line_num}: {e}")
                    skipped += 1
        
        return synced, skipped
    
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

def sync_chatos_conversations(
    min_score: int = 0,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[int, int]:
    """
    Sync ChatOS conversations to the learning loop database.
    
    Args:
        min_score: Minimum feedback score to include
        progress_callback: Optional progress callback
    
    Returns:
        Tuple of (synced, skipped)
    """
    sync = ChatOSSync()
    return sync.sync_conversations(min_score, progress_callback)


def sync_persrm_data(
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[int, int]:
    """
    Sync PersRM data to the learning loop database.
    
    Returns:
        Tuple of (synced, skipped)
    """
    sync = ChatOSSync()
    return sync.sync_persrm_data(progress_callback)


def sync_all_internal_data(min_score: int = 0) -> Dict[str, Tuple[int, int]]:
    """
    Sync all internal data sources.
    
    Returns:
        Dict mapping source name to (synced, skipped) counts
    """
    sync = ChatOSSync()
    
    results = {}
    results["chatos"] = sync.sync_conversations(min_score)
    results["persrm"] = sync.sync_persrm_data()
    
    return results

