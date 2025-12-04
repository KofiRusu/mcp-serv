"""
Tests for the transcript processing pipeline.

Tests the end-to-end flow: create transcript -> transcribe -> summarise -> create note.
"""

import asyncio
import os
import time

import pytest
from fastapi.testclient import TestClient

# Use SQLite for testing
os.environ["CHATOS_USE_SQLITE"] = "true"
os.environ["CHATOS_SQLITE_PATH"] = "/tmp/chatos_test_pipeline.db"

from ChatOS.app import app
from ChatOS.database.connection import init_database, get_engine


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Initialize the database tables before tests."""
    from ChatOS.database.notes_models import NoteDB, TranscriptDB
    init_database()
    yield
    engine = get_engine()
    engine.dispose()


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def wait_for_transcript_status(
    client: TestClient,
    transcript_id: int,
    session_id: str,
    target_status: str,
    timeout: float = 5.0,
    poll_interval: float = 0.1,
) -> dict:
    """
    Poll transcript endpoint until status matches target or timeout.
    
    Args:
        client: Test client
        transcript_id: Transcript ID to poll
        session_id: User session ID
        target_status: Status to wait for (e.g., "done", "error")
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds
        
    Returns:
        Final transcript data
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = client.get(
            f"/api/transcripts/{transcript_id}?session_id={session_id}"
        )
        if response.status_code == 200:
            data = response.json()
            if data["status"] == target_status:
                return data
        time.sleep(poll_interval)
    
    # Return last response even if timeout
    response = client.get(f"/api/transcripts/{transcript_id}?session_id={session_id}")
    return response.json() if response.status_code == 200 else {}


class TestTranscriptPipeline:
    """Tests for the transcript processing pipeline."""

    def test_create_transcript_returns_pending(self, client):
        """Creating a transcript should return immediately with status='pending'."""
        response = client.post(
            "/api/transcripts",
            json={
                "session_id": "pipeline-test-1",
                "audio_path": "/tmp/test-audio.wav",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["transcript_text"] is None

    def test_transcript_processing_success(self, client):
        """Transcript should be processed and status should become 'done'."""
        # Create transcript
        response = client.post(
            "/api/transcripts",
            json={
                "session_id": "pipeline-test-2",
                "audio_path": "/tmp/pipeline-test.wav",
            },
        )
        assert response.status_code == 201
        transcript_id = response.json()["id"]
        
        # Wait for processing to complete
        data = wait_for_transcript_status(
            client,
            transcript_id,
            "pipeline-test-2",
            "done",
            timeout=5.0,
        )
        
        assert data["status"] == "done"
        assert data["transcript_text"] == "Transcribed text of /tmp/pipeline-test.wav"
        assert data["error_message"] is None

    def test_note_created_after_processing(self, client):
        """A note should be created with summary after transcript processing."""
        session_id = "pipeline-test-3"
        audio_path = "/tmp/note-creation-test.wav"
        
        # Create transcript
        response = client.post(
            "/api/transcripts",
            json={
                "session_id": session_id,
                "audio_path": audio_path,
            },
        )
        assert response.status_code == 201
        transcript_id = response.json()["id"]
        
        # Wait for processing to complete
        data = wait_for_transcript_status(
            client,
            transcript_id,
            session_id,
            "done",
            timeout=5.0,
        )
        assert data["status"] == "done"
        
        # Check that a note was created
        notes_response = client.get(f"/api/notes/db?session_id={session_id}")
        assert notes_response.status_code == 200
        notes_data = notes_response.json()
        
        # Find the note with expected title
        expected_title = f"Summary of {audio_path}"
        matching_notes = [n for n in notes_data["notes"] if n["title"] == expected_title]
        assert len(matching_notes) >= 1, f"Expected note with title '{expected_title}'"
        
        note = matching_notes[0]
        
        # Verify note content contains action items
        assert "Action Items:" in note["content"]
        assert "Follow up on key points" in note["content"]
        assert "Schedule next meeting" in note["content"]
        
        # Verify tags
        assert "meeting" in note["tags"]
        assert "auto" in note["tags"]

    def test_transcript_text_matches_stub(self, client):
        """Transcript text should match the stub output format."""
        session_id = "pipeline-test-4"
        audio_path = "/tmp/specific-path-test.wav"
        
        response = client.post(
            "/api/transcripts",
            json={
                "session_id": session_id,
                "audio_path": audio_path,
            },
        )
        transcript_id = response.json()["id"]
        
        # Wait for processing
        data = wait_for_transcript_status(
            client,
            transcript_id,
            session_id,
            "done",
            timeout=5.0,
        )
        
        # Verify exact stub output
        expected_text = f"Transcribed text of {audio_path}"
        assert data["transcript_text"] == expected_text

    def test_multiple_transcripts_independent(self, client):
        """Multiple transcripts for same session should be processed independently."""
        session_id = "pipeline-test-5"
        
        # Create two transcripts
        response1 = client.post(
            "/api/transcripts",
            json={
                "session_id": session_id,
                "audio_path": "/tmp/audio1.wav",
            },
        )
        response2 = client.post(
            "/api/transcripts",
            json={
                "session_id": session_id,
                "audio_path": "/tmp/audio2.wav",
            },
        )
        
        id1 = response1.json()["id"]
        id2 = response2.json()["id"]
        
        # Wait for both to complete
        data1 = wait_for_transcript_status(client, id1, session_id, "done", timeout=5.0)
        data2 = wait_for_transcript_status(client, id2, session_id, "done", timeout=5.0)
        
        # Both should be done with correct text
        assert data1["status"] == "done"
        assert data2["status"] == "done"
        assert data1["transcript_text"] == "Transcribed text of /tmp/audio1.wav"
        assert data2["transcript_text"] == "Transcribed text of /tmp/audio2.wav"

    def test_transcript_with_language(self, client):
        """Transcript with language parameter should process correctly."""
        session_id = "pipeline-test-6"
        
        response = client.post(
            "/api/transcripts",
            json={
                "session_id": session_id,
                "audio_path": "/tmp/spanish-audio.wav",
                "language": "es",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["language"] == "es"
        
        transcript_id = data["id"]
        
        # Wait for processing
        final_data = wait_for_transcript_status(
            client,
            transcript_id,
            session_id,
            "done",
            timeout=5.0,
        )
        
        assert final_data["status"] == "done"
        assert final_data["language"] == "es"


class TestTranscriptErrorHandling:
    """Tests for error handling in the pipeline."""

    def test_session_scoping_in_pipeline(self, client):
        """User should not be able to access another user's transcript."""
        # Create transcript for user A
        response = client.post(
            "/api/transcripts",
            json={
                "session_id": "user-a-pipeline",
                "audio_path": "/tmp/user-a-audio.wav",
            },
        )
        transcript_id = response.json()["id"]
        
        # User B tries to access
        response = client.get(
            f"/api/transcripts/{transcript_id}?session_id=user-b-pipeline"
        )
        assert response.status_code == 403


class TestPhase1TestsStillPass:
    """Verify that Phase 1 tests still work."""

    def test_create_transcript_basic(self, client):
        """Basic transcript creation still works."""
        response = client.post(
            "/api/transcripts",
            json={
                "session_id": "phase1-compat-test",
                "audio_path": "/tmp/compat.wav",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["session_id"] == "phase1-compat-test"
        assert data["audio_path"] == "/tmp/compat.wav"

    def test_list_transcripts_basic(self, client):
        """List transcripts still works."""
        session_id = "phase1-list-test"
        
        # Create a transcript
        client.post(
            "/api/transcripts",
            json={
                "session_id": session_id,
                "audio_path": "/tmp/list-test.wav",
            },
        )
        
        # List transcripts
        response = client.get(f"/api/transcripts?session_id={session_id}")
        assert response.status_code == 200
        data = response.json()
        assert "transcripts" in data
        assert "total" in data

