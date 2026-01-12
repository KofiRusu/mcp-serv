"""
store.py - Persistence layer for AI Projects.

Handles saving/loading AI Projects from JSON files under ~/ChatOS-Memory/ai_projects/.
Uses atomic writes to prevent corruption during concurrent access.
Supports file uploads for project-specific knowledge bases.
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from chatos_backend.projects.models import (
    AIProject,
    AIProjectCreate,
    AIProjectUpdate,
    DEFAULT_PROJECT_TEMPLATES,
)

# Allowed file extensions for knowledge base
ALLOWED_EXTENSIONS = {
    '.txt', '.md', '.pdf', '.docx', '.doc',
    '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css',
    '.json', '.yaml', '.yml', '.xml', '.csv',
    '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb',
    '.sh', '.bash', '.zsh', '.sql',
}


class AIProjectStore:
    """
    Manages persistence of AI Projects to JSON files.
    
    Storage location: ~/ChatOS-Memory/ai_projects/projects.json
    
    Uses atomic write pattern (temp file + rename) for safe concurrent access.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the store.
        
        Args:
            base_dir: Base directory for storage. Defaults to ~/ChatOS-Memory/ai_projects/
        """
        if base_dir is None:
            base_dir = Path.home() / "ChatOS-Memory" / "ai_projects"
        
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.projects_file = self.base_dir / "projects.json"
        self._projects: Dict[str, AIProject] = {}
        
        # Load existing projects
        self._load()
    
    def _load(self) -> None:
        """Load projects from disk."""
        if not self.projects_file.exists():
            self._projects = {}
            return
        
        try:
            data = json.loads(self.projects_file.read_text(encoding="utf-8"))
            self._projects = {}
            
            for project_data in data.get("projects", []):
                try:
                    project = AIProject.from_dict(project_data)
                    self._projects[project.id] = project
                except Exception as e:
                    print(f"Warning: Failed to load project: {e}")
                    
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse projects.json: {e}")
            self._projects = {}
        except Exception as e:
            print(f"Warning: Failed to load projects: {e}")
            self._projects = {}
    
    def _save(self) -> None:
        """
        Save projects to disk using atomic write pattern.
        
        Writes to a temp file first, then renames to prevent corruption.
        """
        data = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "projects": [p.to_dict() for p in self._projects.values()],
        }
        
        # Atomic write: write to temp file, then rename
        fd, temp_path = tempfile.mkstemp(
            suffix=".json",
            prefix="projects_",
            dir=self.base_dir,
        )
        
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.replace(temp_path, self.projects_file)
            
        except Exception:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    def list_projects(self) -> List[AIProject]:
        """
        List all AI projects.
        
        Returns:
            List of AIProject instances, sorted by name.
        """
        return sorted(self._projects.values(), key=lambda p: p.name.lower())
    
    def get_project(self, project_id: str) -> Optional[AIProject]:
        """
        Get a project by ID.
        
        Args:
            project_id: The project ID to look up.
            
        Returns:
            AIProject if found, None otherwise.
        """
        return self._projects.get(project_id)
    
    def get_project_by_slug(self, slug: str) -> Optional[AIProject]:
        """
        Get a project by its URL-friendly slug.
        
        Args:
            slug: The project slug to look up.
            
        Returns:
            AIProject if found, None otherwise.
        """
        for project in self._projects.values():
            if project.slug == slug:
                return project
        return None
    
    def create_project(self, payload: AIProjectCreate) -> AIProject:
        """
        Create a new AI project.
        
        Args:
            payload: AIProjectCreate with project details.
            
        Returns:
            The newly created AIProject.
        """
        project = payload.to_project()
        
        # Ensure unique slug
        base_slug = project.slug
        counter = 1
        while self.get_project_by_slug(project.slug):
            project.slug = f"{base_slug}-{counter}"
            counter += 1
        
        self._projects[project.id] = project
        self._save()
        
        return project
    
    def update_project(
        self,
        project_id: str,
        payload: AIProjectUpdate,
    ) -> Optional[AIProject]:
        """
        Update an existing project.
        
        Args:
            project_id: ID of the project to update.
            payload: AIProjectUpdate with fields to change.
            
        Returns:
            Updated AIProject if found, None otherwise.
        """
        project = self._projects.get(project_id)
        if not project:
            return None
        
        # Apply updates
        project = payload.apply_to(project)
        
        # Ensure unique slug if name changed
        if payload.name is not None:
            base_slug = project.slug
            counter = 1
            while True:
                existing = self.get_project_by_slug(project.slug)
                if existing is None or existing.id == project_id:
                    break
                project.slug = f"{base_slug}-{counter}"
                counter += 1
        
        self._projects[project_id] = project
        self._save()
        
        return project
    
    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project.
        
        Args:
            project_id: ID of the project to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        if project_id not in self._projects:
            return False
        
        del self._projects[project_id]
        self._save()
        
        return True
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_default_project(self) -> Optional[AIProject]:
        """
        Get the most recently updated project as a "default" option.
        
        Returns:
            Most recently updated AIProject, or None if no projects exist.
        """
        if not self._projects:
            return None
        
        return max(self._projects.values(), key=lambda p: p.updated_at)
    
    def create_from_template(self, template_key: str) -> Optional[AIProject]:
        """
        Create a new project from a built-in template.
        
        Args:
            template_key: Key from DEFAULT_PROJECT_TEMPLATES.
            
        Returns:
            New AIProject if template exists, None otherwise.
        """
        template = DEFAULT_PROJECT_TEMPLATES.get(template_key)
        if not template:
            return None
        
        payload = AIProjectCreate(
            name=template.get("name", "New Project"),
            description=template.get("description"),
            color=template.get("color", "#2B26FE"),
            icon=template.get("icon", "📁"),
            system_prompt=template.get("system_prompt", ""),
            default_model_id=template.get("default_model_id"),
            default_temperature=template.get("default_temperature", 0.7),
            training_enabled=template.get("training_enabled", True),
            rag_enabled=template.get("rag_enabled", True),
            code_mode=template.get("code_mode", False),
        )
        
        return self.create_project(payload)
    
    def get_templates(self) -> Dict[str, dict]:
        """
        Get available project templates.
        
        Returns:
            Dictionary of template_key -> template_data.
        """
        return DEFAULT_PROJECT_TEMPLATES.copy()
    
    def count(self) -> int:
        """Return the number of projects."""
        return len(self._projects)
    
    # =========================================================================
    # File Management
    # =========================================================================
    
    def get_project_files_dir(self, project_id: str) -> Path:
        """
        Get the directory for a project's knowledge base files.
        
        Args:
            project_id: The project ID.
            
        Returns:
            Path to the project's files directory.
        """
        files_dir = self.base_dir / project_id / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        return files_dir
    
    def add_file_to_project(
        self,
        project_id: str,
        filename: str,
        content: bytes,
    ) -> Tuple[bool, str]:
        """
        Add a file to a project's knowledge base.
        
        Args:
            project_id: The project ID.
            filename: Original filename.
            content: File content as bytes.
            
        Returns:
            Tuple of (success, message or saved_filename).
        """
        project = self._projects.get(project_id)
        if not project:
            return False, "Project not found"
        
        # Validate extension
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"File type {ext} not allowed"
        
        # Sanitize filename
        safe_name = "".join(c for c in filename if c.isalnum() or c in '._-')
        if not safe_name:
            safe_name = f"file{ext}"
        
        # Ensure unique filename
        files_dir = self.get_project_files_dir(project_id)
        base_name = Path(safe_name).stem
        final_name = safe_name
        counter = 1
        while (files_dir / final_name).exists():
            final_name = f"{base_name}_{counter}{ext}"
            counter += 1
        
        # Save file
        file_path = files_dir / final_name
        file_path.write_bytes(content)
        
        # Update project
        if final_name not in project.files:
            project.files.append(final_name)
            project.updated_at = datetime.now()
            self._save()
        
        return True, final_name
    
    def remove_file_from_project(
        self,
        project_id: str,
        filename: str,
    ) -> bool:
        """
        Remove a file from a project's knowledge base.
        
        Args:
            project_id: The project ID.
            filename: The filename to remove.
            
        Returns:
            True if removed, False otherwise.
        """
        project = self._projects.get(project_id)
        if not project:
            return False
        
        # Remove from disk
        files_dir = self.get_project_files_dir(project_id)
        file_path = files_dir / filename
        if file_path.exists():
            file_path.unlink()
        
        # Update project
        if filename in project.files:
            project.files.remove(filename)
            project.updated_at = datetime.now()
            self._save()
        
        return True
    
    def list_project_files(self, project_id: str) -> List[Dict[str, any]]:
        """
        List all files in a project's knowledge base.
        
        Args:
            project_id: The project ID.
            
        Returns:
            List of file info dictionaries.
        """
        project = self._projects.get(project_id)
        if not project:
            return []
        
        files_dir = self.get_project_files_dir(project_id)
        result = []
        
        for filename in project.files:
            file_path = files_dir / filename
            if file_path.exists():
                stat = file_path.stat()
                result.append({
                    "name": filename,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "extension": file_path.suffix.lower(),
                })
        
        return result
    
    def get_file_content(self, project_id: str, filename: str) -> Optional[bytes]:
        """
        Get the content of a file from a project.
        
        Args:
            project_id: The project ID.
            filename: The filename to read.
            
        Returns:
            File content as bytes, or None if not found.
        """
        project = self._projects.get(project_id)
        if not project or filename not in project.files:
            return None
        
        files_dir = self.get_project_files_dir(project_id)
        file_path = files_dir / filename
        
        if not file_path.exists():
            return None
        
        return file_path.read_bytes()
    
    # =========================================================================
    # Chat Association
    # =========================================================================
    
    def add_chat_to_project(self, project_id: str, chat_id: str) -> bool:
        """
        Associate a chat with a project.
        
        Args:
            project_id: The project ID.
            chat_id: The conversation/chat ID.
            
        Returns:
            True if added, False if project not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return False
        
        if chat_id not in project.chat_ids:
            project.chat_ids.append(chat_id)
            project.updated_at = datetime.now()
            self._save()
        
        return True
    
    def remove_chat_from_project(self, project_id: str, chat_id: str) -> bool:
        """
        Remove a chat association from a project.
        
        Args:
            project_id: The project ID.
            chat_id: The conversation/chat ID.
            
        Returns:
            True if removed, False otherwise.
        """
        project = self._projects.get(project_id)
        if not project:
            return False
        
        if chat_id in project.chat_ids:
            project.chat_ids.remove(chat_id)
            project.updated_at = datetime.now()
            self._save()
        
        return True
    
    def get_project_for_chat(self, chat_id: str) -> Optional[AIProject]:
        """
        Find which project a chat belongs to.
        
        Args:
            chat_id: The conversation/chat ID.
            
        Returns:
            AIProject if found, None otherwise.
        """
        for project in self._projects.values():
            if chat_id in project.chat_ids:
                return project
        return None


# =============================================================================
# Singleton Instance
# =============================================================================

_store: Optional[AIProjectStore] = None


def get_ai_project_store() -> AIProjectStore:
    """
    Get the singleton AIProjectStore instance.
    
    Returns:
        The global AIProjectStore instance.
    """
    global _store
    if _store is None:
        _store = AIProjectStore()
    return _store

