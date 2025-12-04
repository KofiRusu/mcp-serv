"""
Tests for transcripts API.

Tests CRUD operations and session_id scoping.
"""

import os
import pytest
from fastapi.testclient import TestClient

# Use SQLite for testing
os.environ["CHATOS_USE_SQLITE"] = "true"
os.environ["CHATOS_SQLITE_PATH"] = "/tmp/chatos_test_transcripts.db"

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


class TestTranscriptsEndpoints:
    """Tests for /api/transcripts endpoints."""

    def test_create_transcript(self, client):
        """Create a transcript returns 201 with status=pending."""
        response = client.post(
            "/api/transcripts",
            json={
                "session_id": "transcript-test-1",
                "audio_path": "/tmp/test-audio.wav",
                "language": "en",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["audio_path"] == "/tmp/test-audio.wav"
        assert data["language"] == "en"
        assert data["status"] == "pending"
        assert data["session_id"] == "transcript-test-1"
        assert "id" in data
        assert data["transcript_text"] is None

    def test_list_transcripts(self, client):
        """List transcripts returns transcripts for the session."""
        # Create a transcript first
        client.post(
            "/api/transcripts",
            json={
                "session_id": "transcript-test-2",
                "audio_path": "/tmp/list-test.wav",
            },
        )
        
        # List transcripts
        response = client.get("/api/transcripts?session_id=transcript-test-2")
        assert response.status_code == 200
        data = response.json()
        assert "transcripts" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_get_transcript(self, client):
        """Get a specific transcript by ID."""
        # Create a transcript first
        create_response = client.post(
            "/api/transcripts",
            json={
                "session_id": "transcript-test-3",
                "audio_path": "/tmp/get-test.wav",
            },
        )
        transcript_id = create_response.json()["id"]
        
        # Get the transcript
        response = client.get(f"/api/transcripts/{transcript_id}?session_id=transcript-test-3")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == transcript_id
        assert data["audio_path"] == "/tmp/get-test.wav"

    def test_session_scoping(self, client):
        """User A cannot see User B's transcripts."""
        # Create transcript for user A
        create_response = client.post(
            "/api/transcripts",
            json={
                "session_id": "user-a-transcript",
                "audio_path": "/tmp/user-a.wav",
            },
        )
        transcript_id = create_response.json()["id"]
        
        # User B tries to access
        response = client.get(f"/api/transcripts/{transcript_id}?session_id=user-b-transcript")
        assert response.status_code == 403

    def test_list_transcripts_with_status_filter(self, client):
        """List transcripts filtered by status."""
        # Create transcripts
        client.post(
            "/api/transcripts",
            json={
                "session_id": "status-filter-test",
                "audio_path": "/tmp/pending1.wav",
            },
        )
        client.post(
            "/api/transcripts",
            json={
                "session_id": "status-filter-test",
                "audio_path": "/tmp/pending2.wav",
            },
        )
        
        # Filter by pending status
        response = client.get("/api/transcripts?session_id=status-filter-test&status=pending")
        assert response.status_code == 200
        data = response.json()
        assert all(t["status"] == "pending" for t in data["transcripts"])

    def test_create_transcript_without_session_id(self, client):
        """Create transcript without session_id fails validation."""
        response = client.post(
            "/api/transcripts",
            json={
                "audio_path": "/tmp/no-session.wav",
            },
        )
        assert response.status_code == 422  # Validation error

    def test_create_transcript_without_audio_path(self, client):
        """Create transcript without audio_path fails validation."""
        response = client.post(
            "/api/transcripts",
            json={
                "session_id": "missing-path-test",
            },
        )
        assert response.status_code == 422  # Validation error

    def test_get_nonexistent_transcript(self, client):
        """Get nonexistent transcript returns 404."""
        response = client.get("/api/transcripts/99999?session_id=test-session")
        assert response.status_code == 404

