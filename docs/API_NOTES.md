# ChatOS Notes & Diary API Documentation

This document describes the API endpoints for the Notes/Diary module in ChatOS v0.2.

## Base URL

All endpoints are relative to: `http://localhost:8000`

## Authentication

Currently, all endpoints use `session_id` for user scoping. Pass this as a query parameter.

---

## Notes API

### Create Note

```http
POST /api/notes/db
Content-Type: application/json

{
  "session_id": "user123",
  "title": "Meeting Notes",
  "content": "Discussion about Q4 goals...",
  "tags": ["meeting", "q4"]
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "session_id": "user123",
  "title": "Meeting Notes",
  "content": "Discussion about Q4 goals...",
  "tags": ["meeting", "q4"],
  "source_conversation_id": null,
  "source_attachment_id": null,
  "created_at": "2025-12-02T10:30:00",
  "updated_at": "2025-12-02T10:30:00"
}
```

### List Notes

```http
GET /api/notes/db?session_id=user123&query=meeting&tag=q4
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| session_id | string | Yes | User session ID |
| query | string | No | Search in title and content |
| tag | string | No | Filter by tag |

**Response (200 OK):**
```json
{
  "notes": [
    {
      "id": 1,
      "session_id": "user123",
      "title": "Meeting Notes",
      "content": "Discussion about Q4 goals...",
      "tags": ["meeting", "q4"],
      "created_at": "2025-12-02T10:30:00",
      "updated_at": "2025-12-02T10:30:00"
    }
  ],
  "total": 1
}
```

### Get Note

```http
GET /api/notes/db/{note_id}?session_id=user123
```

**Response (200 OK):**
```json
{
  "id": 1,
  "session_id": "user123",
  "title": "Meeting Notes",
  "content": "Discussion about Q4 goals...",
  "tags": ["meeting", "q4"],
  "created_at": "2025-12-02T10:30:00",
  "updated_at": "2025-12-02T10:30:00"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Note not found"
}
```

### Update Note

```http
PUT /api/notes/db/{note_id}?session_id=user123
Content-Type: application/json

{
  "title": "Updated Meeting Notes",
  "content": "New content...",
  "tags": ["meeting", "q4", "updated"]
}
```

**Response (200 OK):** Returns the updated note object.

### Delete Note

```http
DELETE /api/notes/db/{note_id}?session_id=user123
```

**Response (200 OK):**
```json
{
  "success": true
}
```

---

## Transcripts API

### Create Transcript

Creates a transcript record and starts background processing.

```http
POST /api/transcripts
Content-Type: application/json

{
  "session_id": "user123",
  "audio_path": "/path/to/audio.wav",
  "language": "en"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "session_id": "user123",
  "audio_path": "/path/to/audio.wav",
  "transcript_text": null,
  "language": "en",
  "speaker_info": null,
  "status": "pending",
  "error_message": null,
  "created_at": "2025-12-02T10:30:00",
  "updated_at": "2025-12-02T10:30:00"
}
```

**Status Values:**
- `pending` - Waiting to be processed
- `processing` - Currently being transcribed
- `done` - Transcription complete, note created
- `error` - Transcription failed

### Get Transcript

Poll this endpoint to check transcription status.

```http
GET /api/transcripts/{transcript_id}?session_id=user123
```

**Response (200 OK):**
```json
{
  "id": 1,
  "session_id": "user123",
  "audio_path": "/path/to/audio.wav",
  "transcript_text": "Hello, this is the transcribed text...",
  "language": "en",
  "status": "done",
  "created_at": "2025-12-02T10:30:00",
  "updated_at": "2025-12-02T10:31:00"
}
```

### List Transcripts

```http
GET /api/transcripts?session_id=user123&status=done
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| session_id | string | Yes | User session ID |
| status | string | No | Filter by status |

---

## File Upload API

### Upload Audio File

```http
POST /api/uploads
Content-Type: multipart/form-data

file: <binary audio data>
session_id: user123
```

**Response (200 OK):**
```json
{
  "id": "upload_abc123def456",
  "original_filename": "meeting.wav",
  "stored_path": "/home/user/ChatOS-Memory/uploads/user123/upload_abc123def456.wav",
  "mime_type": "audio/wav",
  "size": 1234567,
  "session_id": "user123",
  "created_at": "2025-12-02T10:30:00"
}
```

**Supported Formats:** MP3, WAV, M4A, OGG, FLAC, WebM, AAC  
**Maximum Size:** 100MB

### List Uploads

```http
GET /api/uploads?session_id=user123
```

### Delete Upload

```http
DELETE /api/uploads/{file_id}?session_id=user123
```

### Get Allowed Types

```http
GET /api/uploads/info/allowed-types
```

**Response:**
```json
{
  "allowed_extensions": [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".aac"],
  "max_size_bytes": 104857600,
  "max_size_mb": 100
}
```

---

## Tasks API

### Create Tasks from Note

Extracts action items from a note and creates AGI tasks.

```http
POST /api/notes/db/{note_id}/create_tasks?session_id=user123
```

**Response (200 OK):**
```json
{
  "success": true,
  "note_id": 1,
  "tasks_created": 3,
  "tasks": [
    {
      "id": "task_abc123",
      "title": "Follow up with John",
      "description": "Action item from note: Meeting Notes",
      "status": "pending",
      "priority": "medium",
      "tags": ["note:1", "from-note", "action-item"],
      "created_at": 1733134200,
      "metadata": {
        "source_note_id": 1,
        "source_note_title": "Meeting Notes",
        "session_id": "user123"
      }
    }
  ],
  "message": "Created 3 tasks from action items.",
  "already_exists": false
}
```

### Get Tasks for Note

```http
GET /api/notes/db/{note_id}/tasks?session_id=user123
```

**Response (200 OK):**
```json
{
  "tasks": [
    {
      "id": "task_abc123",
      "title": "Follow up with John",
      "status": "pending",
      "priority": "medium"
    }
  ],
  "total": 1
}
```

---

## Unified Search API

### Search All

Search across notes, transcripts, AGI memory, and chat history.

```http
GET /api/search?session_id=user123&query=meeting&limit=10
```

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| session_id | string | Yes | - | User session ID |
| query | string | Yes | - | Search query (min 2 chars) |
| limit | int | No | 10 | Max results (1-50) |
| include_notes | bool | No | true | Include notes |
| include_transcripts | bool | No | true | Include transcripts |
| include_memory | bool | No | true | Include AGI memory |
| include_chat_history | bool | No | true | Include chat history |

**Response (200 OK):**
```json
{
  "query": "meeting",
  "results": [
    {
      "type": "note",
      "id": 1,
      "title": "Meeting Notes",
      "snippet": "Discussion about Q4 goals...",
      "score": 1.0,
      "created_at": "2025-12-02T10:30:00",
      "tags": ["meeting", "q4"]
    },
    {
      "type": "memory",
      "id": "mem_xyz",
      "title": "Meeting Summary",
      "snippet": "Memory: Key decisions from the meeting...",
      "score": 0.9,
      "source": "note",
      "note_id": 1
    }
  ],
  "by_type": {
    "notes": [...],
    "transcripts": [...],
    "memory": [...],
    "chat_history": [...]
  },
  "total": 2
}
```

### Search Notes Only

```http
GET /api/search/notes?session_id=user123&query=meeting
```

### Search Transcripts Only

```http
GET /api/search/transcripts?session_id=user123&query=meeting
```

### Search Memory Only

```http
GET /api/search/memory?session_id=user123&query=meeting
```

---

## Error Responses

All endpoints return standard error responses:

**400 Bad Request:**
```json
{
  "detail": "Invalid request parameters"
}
```

**404 Not Found:**
```json
{
  "detail": "Resource not found"
}
```

**422 Unprocessable Entity:**
```json
{
  "detail": [
    {
      "loc": ["query", "session_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limits

Currently no rate limits are enforced. This may change in future versions.

---

## Webhooks

Not yet implemented. Future versions may support webhooks for:
- Transcript completion
- Task status changes
- Note updates

---

## Versioning

This API is currently v1 (implicit). Future versions will use explicit versioning:
- `/api/v1/notes/db`
- `/api/v2/notes/db`

