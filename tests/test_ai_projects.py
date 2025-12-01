"""
test_ai_projects.py - Unit tests for AI Projects feature.

Tests the AIProject data models, AIProjectStore persistence,
and API endpoints.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ChatOS.projects.models import (
    AIProject,
    AIProjectCreate,
    AIProjectUpdate,
    generate_slug,
    DEFAULT_PROJECT_TEMPLATES,
)
from ChatOS.projects.store import AIProjectStore


# =============================================================================
# Model Tests
# =============================================================================

class TestSlugGeneration:
    """Tests for slug generation from project names."""
    
    def test_simple_name(self):
        assert generate_slug("My Project") == "my-project"
    
    def test_special_characters(self):
        assert generate_slug("Test@Project#123") == "testproject123"
    
    def test_multiple_spaces(self):
        assert generate_slug("A   B   C") == "a-b-c"
    
    def test_leading_trailing_spaces(self):
        assert generate_slug("  Project  ") == "project"
    
    def test_empty_name(self):
        assert generate_slug("") == "project"
    
    def test_unicode_stripped(self):
        assert generate_slug("🚀 Rocket Project") == "rocket-project"


class TestAIProjectModel:
    """Tests for AIProject dataclass."""
    
    def test_creation_defaults(self):
        project = AIProject(name="Test Project")
        
        assert project.name == "Test Project"
        assert project.slug == "test-project"
        assert project.color == "#2B26FE"
        assert project.icon == "📁"
        assert project.default_temperature == 0.7
        assert project.training_enabled is True
        assert project.rag_enabled is True
        assert project.code_mode is False
    
    def test_custom_values(self):
        project = AIProject(
            name="Code Helper",
            color="#FF0000",
            icon="💻",
            system_prompt="You are a coding assistant.",
            default_temperature=0.5,
            code_mode=True,
        )
        
        assert project.color == "#FF0000"
        assert project.icon == "💻"
        assert project.system_prompt == "You are a coding assistant."
        assert project.default_temperature == 0.5
        assert project.code_mode is True
    
    def test_to_dict(self):
        project = AIProject(name="Test")
        data = project.to_dict()
        
        assert data["name"] == "Test"
        assert data["slug"] == "test"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_from_dict(self):
        original = AIProject(name="Original", color="#123456")
        data = original.to_dict()
        restored = AIProject.from_dict(data)
        
        assert restored.name == original.name
        assert restored.id == original.id
        assert restored.color == original.color
    
    def test_create_system_snapshot(self):
        project = AIProject(
            name="Test",
            system_prompt="Be helpful.",
            default_model_id="model-123",
            default_temperature=0.8,
        )
        
        snapshot = project.create_system_snapshot()
        
        assert snapshot["project_id"] == project.id
        assert snapshot["project_name"] == "Test"
        assert snapshot["system_prompt"] == "Be helpful."
        assert snapshot["model_id"] == "model-123"
        assert snapshot["temperature"] == 0.8
        assert "snapshot_at" in snapshot


class TestAIProjectCreate:
    """Tests for AIProjectCreate payload."""
    
    def test_to_project(self):
        create = AIProjectCreate(
            name="New Project",
            description="A test project",
            color="#AABBCC",
            icon="🔬",
        )
        
        project = create.to_project()
        
        assert project.name == "New Project"
        assert project.description == "A test project"
        assert project.color == "#AABBCC"
        assert project.icon == "🔬"
        assert project.id  # Should have generated ID


class TestAIProjectUpdate:
    """Tests for AIProjectUpdate payload."""
    
    def test_apply_partial_update(self):
        project = AIProject(name="Original", color="#000000")
        update = AIProjectUpdate(name="Updated")
        
        updated = update.apply_to(project)
        
        assert updated.name == "Updated"
        assert updated.slug == "updated"
        assert updated.color == "#000000"  # Unchanged
    
    def test_apply_full_update(self):
        project = AIProject(name="Original")
        update = AIProjectUpdate(
            name="New Name",
            description="New desc",
            color="#FF0000",
            icon="🎯",
            system_prompt="New prompt",
            default_temperature=0.9,
            rag_enabled=False,
        )
        
        updated = update.apply_to(project)
        
        assert updated.name == "New Name"
        assert updated.description == "New desc"
        assert updated.color == "#FF0000"
        assert updated.icon == "🎯"
        assert updated.system_prompt == "New prompt"
        assert updated.default_temperature == 0.9
        assert updated.rag_enabled is False


# =============================================================================
# Store Tests
# =============================================================================

class TestAIProjectStore:
    """Tests for AIProjectStore persistence."""
    
    @pytest.fixture
    def temp_store(self):
        """Create a temporary store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = AIProjectStore(base_dir=Path(tmpdir))
            yield store
    
    def test_create_project(self, temp_store):
        payload = AIProjectCreate(name="Test Project")
        project = temp_store.create_project(payload)
        
        assert project.name == "Test Project"
        assert project.id
        assert temp_store.count() == 1
    
    def test_list_projects(self, temp_store):
        temp_store.create_project(AIProjectCreate(name="Project A"))
        temp_store.create_project(AIProjectCreate(name="Project B"))
        
        projects = temp_store.list_projects()
        
        assert len(projects) == 2
        # Should be sorted by name
        assert projects[0].name == "Project A"
        assert projects[1].name == "Project B"
    
    def test_get_project(self, temp_store):
        created = temp_store.create_project(AIProjectCreate(name="Findable"))
        
        found = temp_store.get_project(created.id)
        
        assert found is not None
        assert found.name == "Findable"
    
    def test_get_project_not_found(self, temp_store):
        found = temp_store.get_project("nonexistent-id")
        assert found is None
    
    def test_get_project_by_slug(self, temp_store):
        temp_store.create_project(AIProjectCreate(name="Find By Slug"))
        
        found = temp_store.get_project_by_slug("find-by-slug")
        
        assert found is not None
        assert found.name == "Find By Slug"
    
    def test_update_project(self, temp_store):
        created = temp_store.create_project(AIProjectCreate(name="Original"))
        
        update = AIProjectUpdate(name="Updated", color="#FFFF00")
        updated = temp_store.update_project(created.id, update)
        
        assert updated.name == "Updated"
        assert updated.color == "#FFFF00"
        
        # Verify persistence
        retrieved = temp_store.get_project(created.id)
        assert retrieved.name == "Updated"
    
    def test_delete_project(self, temp_store):
        created = temp_store.create_project(AIProjectCreate(name="To Delete"))
        
        result = temp_store.delete_project(created.id)
        
        assert result is True
        assert temp_store.get_project(created.id) is None
        assert temp_store.count() == 0
    
    def test_delete_nonexistent(self, temp_store):
        result = temp_store.delete_project("nonexistent")
        assert result is False
    
    def test_unique_slug_generation(self, temp_store):
        temp_store.create_project(AIProjectCreate(name="My Project"))
        project2 = temp_store.create_project(AIProjectCreate(name="My Project"))
        
        # Second project should have a different slug
        assert project2.slug != "my-project"
        assert project2.slug.startswith("my-project")
    
    def test_create_from_template(self, temp_store):
        project = temp_store.create_from_template("coding-assistant")
        
        assert project is not None
        assert project.name == "Coding Assistant"
        assert project.code_mode is True
        assert "coding" in project.system_prompt.lower()
    
    def test_create_from_unknown_template(self, temp_store):
        project = temp_store.create_from_template("nonexistent-template")
        assert project is None
    
    def test_persistence_across_reloads(self):
        """Test that data persists when store is reloaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            
            # Create store and add project
            store1 = AIProjectStore(base_dir=base_dir)
            created = store1.create_project(AIProjectCreate(
                name="Persistent Project",
                description="Should survive reload",
            ))
            project_id = created.id
            
            # Create new store instance (simulates restart)
            store2 = AIProjectStore(base_dir=base_dir)
            
            # Should find the project
            found = store2.get_project(project_id)
            assert found is not None
            assert found.name == "Persistent Project"
            assert found.description == "Should survive reload"


class TestDefaultTemplates:
    """Tests for built-in project templates."""
    
    def test_templates_exist(self):
        assert len(DEFAULT_PROJECT_TEMPLATES) >= 4
    
    def test_coding_assistant_template(self):
        template = DEFAULT_PROJECT_TEMPLATES.get("coding-assistant")
        assert template is not None
        assert template["code_mode"] is True
        assert "icon" in template
        assert "system_prompt" in template
    
    def test_creative_writer_template(self):
        template = DEFAULT_PROJECT_TEMPLATES.get("creative-writer")
        assert template is not None
        assert template.get("default_temperature", 0.7) > 0.7  # Higher temp for creativity
    
    def test_pirate_mode_template(self):
        """Test the fun pirate template."""
        template = DEFAULT_PROJECT_TEMPLATES.get("pirate-mode")
        assert template is not None
        assert "pirate" in template["system_prompt"].lower()


# =============================================================================
# API Tests
# =============================================================================

class TestAIProjectsAPI:
    """Tests for AI Projects REST API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client with mocked store."""
        from ChatOS.app import app
        return TestClient(app)
    
    @pytest.fixture
    def mock_store(self):
        """Create and inject a temporary store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = AIProjectStore(base_dir=Path(tmpdir))
            
            # Patch the singleton getter
            with patch('ChatOS.api.routes_ai_projects.get_ai_project_store', return_value=store):
                yield store
    
    def test_list_projects_empty(self, client, mock_store):
        response = client.get("/api/ai-projects")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["projects"] == []
    
    def test_create_project(self, client, mock_store):
        response = client.post("/api/ai-projects", json={
            "name": "Test API Project",
            "description": "Created via API",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test API Project"
        assert data["description"] == "Created via API"
        assert "id" in data
    
    def test_get_project(self, client, mock_store):
        # First create a project
        create_response = client.post("/api/ai-projects", json={"name": "Fetchable"})
        project_id = create_response.json()["id"]
        
        # Then fetch it
        response = client.get(f"/api/ai-projects/{project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Fetchable"
    
    def test_get_project_not_found(self, client, mock_store):
        response = client.get("/api/ai-projects/nonexistent-id")
        assert response.status_code == 404
    
    def test_update_project(self, client, mock_store):
        # Create
        create_response = client.post("/api/ai-projects", json={"name": "Original Name"})
        project_id = create_response.json()["id"]
        
        # Update
        response = client.put(f"/api/ai-projects/{project_id}", json={
            "name": "Updated Name",
            "color": "#FF0000",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["color"] == "#FF0000"
    
    def test_delete_project(self, client, mock_store):
        # Create
        create_response = client.post("/api/ai-projects", json={"name": "To Delete"})
        project_id = create_response.json()["id"]
        
        # Delete
        response = client.delete(f"/api/ai-projects/{project_id}")
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify deleted
        get_response = client.get(f"/api/ai-projects/{project_id}")
        assert get_response.status_code == 404
    
    def test_list_templates(self, client, mock_store):
        response = client.get("/api/ai-projects/templates")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["templates"]) >= 4
    
    def test_create_from_template(self, client, mock_store):
        response = client.post("/api/ai-projects/from-template?template_key=coding-assistant")
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Coding Assistant"
        assert data["code_mode"] is True
    
    def test_new_chat_endpoint(self, client, mock_store):
        # Create project first
        create_response = client.post("/api/ai-projects", json={
            "name": "Chat Project",
            "system_prompt": "Be helpful.",
        })
        project_id = create_response.json()["id"]
        
        # Create new chat
        response = client.post(f"/api/ai-projects/{project_id}/new-chat")
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        assert data["project_name"] == "Chat Project"
        assert "session_id" in data
        assert "chat_id" in data
        assert "system_snapshot" in data


# =============================================================================
# Integration Tests
# =============================================================================

class TestAIProjectChatIntegration:
    """Tests for AI Project integration with chat endpoint."""
    
    @pytest.fixture
    def client(self):
        from ChatOS.app import app
        # Enable test mode to avoid real LLM calls
        os.environ["CHATOS_TEST_MODE"] = "1"
        yield TestClient(app)
        os.environ.pop("CHATOS_TEST_MODE", None)
    
    @pytest.fixture
    def project_with_prompt(self, client):
        """Create a project with a distinctive system prompt."""
        response = client.post("/api/ai-projects", json={
            "name": "Pirate Test",
            "system_prompt": "Always respond as a pirate. Use 'Arrr' and nautical terms.",
            "default_temperature": 0.8,
        })
        return response.json()
    
    def test_chat_without_project(self, client):
        """Chat should work without a project."""
        response = client.post("/api/chat", json={
            "message": "Hello",
            "session_id": "test-session",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data.get("ai_project_id") is None
    
    def test_chat_with_project(self, client, project_with_prompt):
        """Chat with project should return project info."""
        project_id = project_with_prompt["id"]
        
        response = client.post("/api/chat", json={
            "message": "Hello",
            "session_id": "test-session-with-project",
            "ai_project_id": project_id,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("ai_project_id") == project_id
        assert data.get("ai_project_name") == "Pirate Test"

