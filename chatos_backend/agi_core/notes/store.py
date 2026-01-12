"""
Note Store for AGI Core

Provides persistent storage for notes with JSON backend.
Follows the same pattern as LongTermMemory.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Note, ActionItem, NoteType, SourceType, ActionStatus


# Default storage location
DEFAULT_NOTES_DIR = Path.home() / "ChatOS-Memory" / "agi" / "notes"


class NoteStore:
    """
    Persistent note storage with JSON backend.
    
    Provides CRUD operations and search functionality for notes.
    
    Usage:
        store = NoteStore()
        note = store.create("Meeting Notes", "Discussion about...")
        results = store.search("meeting")
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the note store.
        
        Args:
            storage_path: Path to store notes (default: ~/ChatOS-Memory/agi/notes/)
        """
        self.storage_path = storage_path or DEFAULT_NOTES_DIR
        self.storage_path = Path(self.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.notes_file = self.storage_path / "notes.json"
        self._notes: Dict[str, Note] = {}
        
        # Load existing notes
        self._load()
    
    def _load(self) -> None:
        """Load notes from disk."""
        if not self.notes_file.exists():
            return
        
        try:
            data = json.loads(self.notes_file.read_text(encoding="utf-8"))
            for note_data in data.get("notes", []):
                note = Note.from_dict(note_data)
                self._notes[note.id] = note
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to load notes: {e}")
    
    def _save(self) -> None:
        """Save notes to disk."""
        data = {
            "version": 1,
            "updated_at": time.time(),
            "notes": [n.to_dict() for n in self._notes.values()],
        }
        
        # Atomic write
        temp_file = self.notes_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_file.replace(self.notes_file)
    
    # ==========================================================================
    # CRUD Operations
    # ==========================================================================
    
    def create(
        self,
        title: str,
        content: str = "",
        note_type: NoteType = NoteType.GENERAL,
        source_type: SourceType = SourceType.TEXT,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Note:
        """
        Create a new note.
        
        Args:
            title: Note title
            content: Note content
            note_type: Type of note
            source_type: How the note was created
            tags: Tags for categorization
            metadata: Additional data
            
        Returns:
            The created note
        """
        note = Note(
            title=title,
            content=content,
            note_type=note_type,
            source_type=source_type,
            tags=tags or [],
            metadata=metadata or {},
        )
        
        self._notes[note.id] = note
        self._save()
        return note
    
    def get(self, note_id: str) -> Optional[Note]:
        """Get a note by ID."""
        return self._notes.get(note_id)
    
    def update(
        self,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        note_type: Optional[NoteType] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Note]:
        """
        Update a note's properties.
        
        Args:
            note_id: ID of the note to update
            title: New title (if provided)
            content: New content (if provided)
            note_type: New type (if provided)
            tags: New tags (if provided)
            metadata: Metadata to merge (if provided)
            
        Returns:
            The updated note, or None if not found
        """
        note = self._notes.get(note_id)
        if not note:
            return None
        
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if note_type is not None:
            note.note_type = note_type
        if tags is not None:
            note.tags = tags
        if metadata is not None:
            note.metadata.update(metadata)
        
        note.updated_at = time.time()
        self._save()
        return note
    
    def delete(self, note_id: str) -> bool:
        """
        Delete a note by ID.
        
        Args:
            note_id: ID of the note to delete
            
        Returns:
            True if deleted, False if not found
        """
        if note_id in self._notes:
            # Remove links from other notes
            for note in self._notes.values():
                if note_id in note.linked_note_ids:
                    note.linked_note_ids.remove(note_id)
            
            del self._notes[note_id]
            self._save()
            return True
        return False
    
    def all(self) -> List[Note]:
        """Return all notes."""
        return list(self._notes.values())
    
    def count(self) -> int:
        """Return the number of notes."""
        return len(self._notes)
    
    # ==========================================================================
    # Search & Query
    # ==========================================================================
    
    def search(self, query: str, k: int = 10) -> List[Note]:
        """
        Search notes by keyword matching.
        
        Args:
            query: Search query
            k: Maximum number of results
            
        Returns:
            List of matching notes, sorted by relevance
        """
        query_lower = query.lower()
        keywords = query_lower.split()
        
        scored = []
        for note in self._notes.values():
            score = 0
            
            # Title matching (higher weight)
            title_lower = note.title.lower()
            for kw in keywords:
                if kw in title_lower:
                    score += 3
            
            # Content matching
            content_lower = note.content.lower()
            for kw in keywords:
                if kw in content_lower:
                    score += 1
            
            # Tag matching
            for tag in note.tags:
                if any(kw in tag.lower() for kw in keywords):
                    score += 2
            
            if score > 0:
                scored.append((note, score))
        
        # Sort by score descending, then by updated_at descending
        scored.sort(key=lambda x: (x[1], x[0].updated_at), reverse=True)
        return [n for n, _ in scored[:k]]
    
    def list_by_type(self, note_type: NoteType) -> List[Note]:
        """List notes of a specific type."""
        return [n for n in self._notes.values() if n.note_type == note_type]
    
    def list_by_tag(self, tag: str) -> List[Note]:
        """List notes with a specific tag."""
        return [n for n in self._notes.values() if tag in n.tags]
    
    def list_with_pending_actions(self) -> List[Note]:
        """List notes that have pending action items."""
        return [n for n in self._notes.values() if n.pending_actions_count() > 0]
    
    def recent(self, hours: float = 24, k: int = 10) -> List[Note]:
        """
        Get recently updated notes.
        
        Args:
            hours: Time window in hours
            k: Maximum number of results
            
        Returns:
            List of recent notes, sorted by update time
        """
        cutoff = time.time() - (hours * 3600)
        recent_notes = [n for n in self._notes.values() if n.updated_at >= cutoff]
        recent_notes.sort(key=lambda n: n.updated_at, reverse=True)
        return recent_notes[:k]
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags across all notes."""
        tags = set()
        for note in self._notes.values():
            tags.update(note.tags)
        return sorted(tags)
    
    # ==========================================================================
    # Action Item Operations
    # ==========================================================================
    
    def add_action_item(self, note_id: str, action: ActionItem) -> Optional[Note]:
        """
        Add an action item to a note.
        
        Args:
            note_id: ID of the note
            action: Action item to add
            
        Returns:
            The updated note, or None if not found
        """
        note = self._notes.get(note_id)
        if not note:
            return None
        
        note.add_action_item(action)
        self._save()
        return note
    
    def update_action_item(
        self,
        note_id: str,
        action_id: str,
        status: Optional[ActionStatus] = None,
        linked_task_id: Optional[str] = None,
    ) -> Optional[ActionItem]:
        """
        Update an action item.
        
        Args:
            note_id: ID of the note
            action_id: ID of the action item
            status: New status (if provided)
            linked_task_id: ID of linked task (if provided)
            
        Returns:
            The updated action item, or None if not found
        """
        note = self._notes.get(note_id)
        if not note:
            return None
        
        action = note.get_action_item(action_id)
        if not action:
            return None
        
        if status is not None:
            action.status = status
            if status == ActionStatus.COMPLETED:
                action.completed_at = time.time()
        
        if linked_task_id is not None:
            action.linked_task_id = linked_task_id
        
        note.updated_at = time.time()
        self._save()
        return action
    
    def get_all_pending_actions(self) -> List[ActionItem]:
        """Get all pending action items across all notes."""
        actions = []
        for note in self._notes.values():
            for action in note.action_items:
                if action.status == ActionStatus.PENDING:
                    actions.append(action)
        return actions
    
    # ==========================================================================
    # Note Linking
    # ==========================================================================
    
    def link_notes(self, note_id_1: str, note_id_2: str) -> bool:
        """
        Create a bidirectional link between two notes.
        
        Args:
            note_id_1: First note ID
            note_id_2: Second note ID
            
        Returns:
            True if linked, False if either note not found
        """
        note1 = self._notes.get(note_id_1)
        note2 = self._notes.get(note_id_2)
        
        if not note1 or not note2:
            return False
        
        note1.link_note(note_id_2)
        note2.link_note(note_id_1)
        self._save()
        return True
    
    def unlink_notes(self, note_id_1: str, note_id_2: str) -> bool:
        """
        Remove a bidirectional link between two notes.
        
        Args:
            note_id_1: First note ID
            note_id_2: Second note ID
            
        Returns:
            True if unlinked, False if either note not found
        """
        note1 = self._notes.get(note_id_1)
        note2 = self._notes.get(note_id_2)
        
        if not note1 or not note2:
            return False
        
        note1.unlink_note(note_id_2)
        note2.unlink_note(note_id_1)
        self._save()
        return True
    
    def get_linked_notes(self, note_id: str) -> List[Note]:
        """Get all notes linked to a given note."""
        note = self._notes.get(note_id)
        if not note:
            return []
        
        return [
            self._notes[linked_id]
            for linked_id in note.linked_note_ids
            if linked_id in self._notes
        ]
    
    # ==========================================================================
    # Statistics & Export
    # ==========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored notes."""
        type_counts = {t.value: 0 for t in NoteType}
        total_actions = 0
        pending_actions = 0
        completed_actions = 0
        total_words = 0
        
        for note in self._notes.values():
            type_counts[note.note_type.value] += 1
            total_actions += len(note.action_items)
            pending_actions += note.pending_actions_count()
            completed_actions += note.completed_actions_count()
            total_words += note.word_count()
        
        return {
            "total_notes": len(self._notes),
            "by_type": type_counts,
            "total_actions": total_actions,
            "pending_actions": pending_actions,
            "completed_actions": completed_actions,
            "total_words": total_words,
            "unique_tags": len(self.get_all_tags()),
        }
    
    def export(self, output_path: Path) -> int:
        """
        Export all notes to a JSON file.
        
        Args:
            output_path: Path to write the export
            
        Returns:
            Number of notes exported
        """
        data = {
            "exported_at": time.time(),
            "notes": [n.to_dict() for n in self._notes.values()],
        }
        
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return len(self._notes)
    
    def import_notes(self, input_path: Path) -> int:
        """
        Import notes from a JSON file.
        
        Args:
            input_path: Path to the import file
            
        Returns:
            Number of notes imported
        """
        data = json.loads(input_path.read_text(encoding="utf-8"))
        count = 0
        
        for note_data in data.get("notes", []):
            note = Note.from_dict(note_data)
            if note.id not in self._notes:
                self._notes[note.id] = note
                count += 1
        
        if count > 0:
            self._save()
        
        return count
    
    def clear(self) -> int:
        """
        Clear all notes.
        
        Returns:
            Number of notes cleared
        """
        count = len(self._notes)
        self._notes.clear()
        self._save()
        return count

