"""
Tests for SQLModel-based notes API.

Tests CRUD operations and session_id scoping.
"""

import os
import pytest
from fastapi.testclient import TestClient

# Use SQLite for testing
os.environ["CHATOS_USE_SQLITE"] = "true"
os.environ["CHATOS_SQLITE_PATH"] = "/tmp/chatos_test_notes.db"

from ChatOS.app import app
from ChatOS.database.connection import init_database, get_engine


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Initialize the database tables before tests."""
    # Import models to register them with Base
    from ChatOS.database.notes_models import NoteDB, TranscriptDB
    init_database()
    yield
    # Cleanup after all tests
    engine = get_engine()
    engine.dispose()


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestNotesDBEndpoints:
    """Tests for /api/notes/db endpoints."""

    def test_create_note(self, client):
        """Create a note returns 201 and note data."""
        response = client.post(
            "/api/notes/db",
            json={
                "session_id": "test-session-1",
                "title": "Test Note",
                "content": "Hello, world!",
                "tags": ["test", "example"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Note"
        assert data["content"] == "Hello, world!"
        assert data["tags"] == ["test", "example"]
        assert data["session_id"] == "test-session-1"
        assert "id" in data
        assert "created_at" in data

    def test_list_notes(self, client):
        """List notes returns notes for the session."""
        # Create a note first
        client.post(
            "/api/notes/db",
            json={
                "session_id": "test-session-2",
                "title": "List Test Note",
                "content": "Content for list test",
            },
        )
        
        # List notes
        response = client.get("/api/notes/db?session_id=test-session-2")
        assert response.status_code == 200
        data = response.json()
        assert "notes" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_get_note(self, client):
        """Get a specific note by ID."""
        # Create a note first
        create_response = client.post(
            "/api/notes/db",
            json={
                "session_id": "test-session-3",
                "title": "Get Test Note",
                "content": "Content for get test",
            },
        )
        note_id = create_response.json()["id"]
        
        # Get the note
        response = client.get(f"/api/notes/db/{note_id}?session_id=test-session-3")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == note_id
        assert data["title"] == "Get Test Note"

    def test_update_note(self, client):
        """Update a note's title and content."""
        # Create a note first
        create_response = client.post(
            "/api/notes/db",
            json={
                "session_id": "test-session-4",
                "title": "Original Title",
                "content": "Original content",
            },
        )
        note_id = create_response.json()["id"]
        
        # Update the note
        response = client.put(
            f"/api/notes/db/{note_id}?session_id=test-session-4",
            json={
                "title": "Updated Title",
                "content": "Updated content",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content"] == "Updated content"

    def test_delete_note(self, client):
        """Delete a note."""
        # Create a note first
        create_response = client.post(
            "/api/notes/db",
            json={
                "session_id": "test-session-5",
                "title": "Delete Test Note",
                "content": "To be deleted",
            },
        )
        note_id = create_response.json()["id"]
        
        # Delete the note
        response = client.delete(f"/api/notes/db/{note_id}?session_id=test-session-5")
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify it's gone
        get_response = client.get(f"/api/notes/db/{note_id}?session_id=test-session-5")
        assert get_response.status_code == 404

    def test_session_scoping(self, client):
        """User A cannot see User B's notes."""
        # Create note for user A
        create_response = client.post(
            "/api/notes/db",
            json={
                "session_id": "user-a-session",
                "title": "User A Note",
                "content": "Private content",
            },
        )
        note_id = create_response.json()["id"]
        
        # User B tries to access
        response = client.get(f"/api/notes/db/{note_id}?session_id=user-b-session")
        assert response.status_code == 403

    def test_list_notes_with_search(self, client):
        """List notes with search query."""
        # Create notes
        client.post(
            "/api/notes/db",
            json={
                "session_id": "search-test-session",
                "title": "Python Tutorial",
                "content": "Learn Python basics",
            },
        )
        client.post(
            "/api/notes/db",
            json={
                "session_id": "search-test-session",
                "title": "JavaScript Guide",
                "content": "Learn JavaScript",
            },
        )
        
        # Search for Python
        response = client.get("/api/notes/db?session_id=search-test-session&query=Python")
        assert response.status_code == 200
        data = response.json()
        assert any("Python" in n["title"] for n in data["notes"])

    def test_create_note_without_session_id(self, client):
        """Create note without session_id fails validation."""
        response = client.post(
            "/api/notes/db",
            json={
                "title": "No Session",
                "content": "Should fail",
            },
        )
        assert response.status_code == 422  # Validation error

