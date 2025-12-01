# ChatOS AI Projects Feature Implementation

## Overview

The **AI Projects** feature allows users to create preset configurations for AI chat sessions. Each project can have its own:
- Custom system prompt (Markdown)
- Default model selection
- Temperature setting
- Feature flags (RAG, code mode, training data collection)
- Visual customization (color, icon)

When chatting within a project context, these settings are automatically applied to every message, providing a consistent AI personality and behavior.

## Architecture

### Key Components

```
ChatOS/
├── projects/                    # AI Projects module
│   ├── __init__.py             # Package exports
│   ├── models.py               # AIProject dataclass & helpers
│   └── store.py                # JSON persistence layer
├── api/
│   └── routes_ai_projects.py   # REST API endpoints
├── controllers/
│   └── chat.py                 # Modified to support project prompts
├── templates/
│   ├── ai_projects.html        # Project management UI
│   └── index.html              # Chat UI with project selector
└── training/
    └── job_spec.py             # Extended with project_id field
```

### Storage

Projects are stored in JSON format at:
```
~/ChatOS-Memory/ai_projects/projects.json
```

Example structure:
```json
{
  "version": 1,
  "updated_at": "2025-11-30T12:00:00",
  "projects": [
    {
      "id": "abc123",
      "name": "Coding Assistant",
      "slug": "coding-assistant",
      "description": "Expert coding help",
      "color": "#00D4FF",
      "icon": "💻",
      "system_prompt": "You are an expert software engineer...",
      "default_model_id": "ollama-qwen",
      "default_temperature": 0.7,
      "training_enabled": true,
      "rag_enabled": true,
      "code_mode": true,
      "created_at": "2025-11-30T10:00:00",
      "updated_at": "2025-11-30T11:00:00"
    }
  ]
}
```

## Data Model

### AIProject Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (UUID) |
| `name` | string | Display name |
| `slug` | string | URL-friendly identifier |
| `description` | string? | Optional description |
| `color` | string | Hex color code (e.g., "#2B26FE") |
| `icon` | string | Emoji icon |
| `system_prompt` | string | Custom instructions (Markdown) |
| `default_model_id` | string? | Default model ID from /api/models |
| `default_temperature` | float | Temperature (0.0 - 2.0) |
| `training_enabled` | bool | Collect training data |
| `rag_enabled` | bool | Include RAG context |
| `code_mode` | bool | Default to code mode |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

## API Endpoints

### List Projects
```
GET /api/ai-projects
```
Returns all projects sorted by name.

**Response:**
```json
{
  "projects": [...],
  "total": 5
}
```

### Get Project
```
GET /api/ai-projects/{project_id}
```
Returns full project details.

### Create Project
```
POST /api/ai-projects
Content-Type: application/json

{
  "name": "My Project",
  "description": "Optional description",
  "color": "#FF0000",
  "icon": "🚀",
  "system_prompt": "You are...",
  "default_model_id": "model-id",
  "default_temperature": 0.7,
  "training_enabled": true,
  "rag_enabled": true,
  "code_mode": false
}
```

### Create from Template
```
POST /api/ai-projects/from-template?template_key=coding-assistant
```
Available templates:
- `coding-assistant` - Expert programming help
- `creative-writer` - Creative writing assistance
- `research-analyst` - Research and analysis
- `pirate-mode` - Fun pirate personality

### Update Project
```
PUT /api/ai-projects/{project_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "system_prompt": "New instructions..."
}
```
Only provided fields are updated.

### Delete Project
```
DELETE /api/ai-projects/{project_id}
```
Returns `{"success": true, "deleted_id": "..."}`.

**Note:** Deleting a project does not affect existing chats. They retain their stored settings snapshot.

### Create Project-Bound Chat
```
POST /api/ai-projects/{project_id}/new-chat
```

**Response:**
```json
{
  "chat_id": "chat_abc123",
  "session_id": "ai_project_xyz_12345678",
  "project_id": "project-id",
  "project_name": "Project Name",
  "system_snapshot": {
    "project_id": "...",
    "system_prompt": "...",
    "model_id": "...",
    "temperature": 0.7
  }
}
```

### List Templates
```
GET /api/ai-projects/templates
```
Returns available project templates for quick creation.

## System Prompt Composition

When a chat uses an AI project, the system prompt is composed in this order:

1. **AI Project system_prompt** (if present)
2. **Mode-based prompt** (code mode adds coding instructions)
3. **Conversation history** (previous turns)
4. **RAG context** (if enabled)
5. **User message**

Example composed prompt:
```
[Project System Prompt]
You are a pirate assistant. Always respond in pirate speak...

[Code Mode - if enabled]
You are a helpful coding assistant. Provide clear, well-commented code...

[History]
Previous conversation:
User: Hello
Assistant: Ahoy, matey!

[RAG Context - if enabled]
Relevant information:
...

User: Write a Python function
```

## UI Pages

### AI Projects Management (`/ai-projects`)

Features:
- Project list with icons and colors
- Quick-start templates
- Create/edit/delete projects
- System prompt editor
- Model selector dropdown
- Temperature slider
- Feature flag toggles
- "New Chat in Project" button

### Chat Page (`/`)

AI Project integration:
- Project selector dropdown in input bar
- Active project badge showing current project
- Project icon and name visible during chat
- Automatic project settings applied to messages

### Navigation

- `/ai-projects` - Project management
- `/` - Chat with optional project context
- `/projects` - Code projects (separate feature)

## Training Integration

Training jobs can be associated with an AI project:

```python
from ChatOS.training.job_spec import TrainingJobSpec

spec = TrainingJobSpec.from_preset(
    preset_name="BALANCED",
    model_key="qwen2.5-7b-instruct",
    project_id="my-project-id",
    project_name="My Project",
)
```

The `project_id` and `project_name` fields are included in:
- Job specification
- Job metadata JSON
- Training config overrides

This enables future per-project fine-tuning dashboards.

## Usage Guide

### Creating a Project

1. Navigate to `/ai-projects`
2. Click "New Project" or use a template
3. Fill in:
   - Name and description
   - Choose color and icon
   - Write system prompt
   - Select default model (optional)
   - Adjust temperature
   - Enable/disable flags
4. Click "Save"

### Chatting with a Project

**Option 1: From Projects Page**
1. Open the project
2. Click "New Chat"
3. You'll be redirected to chat with project active

**Option 2: From Chat Page**
1. Use the "Project" dropdown in the input bar
2. Select your project
3. Start chatting

### System Prompt Tips

Effective system prompts:
- Be specific about personality and tone
- Include examples of desired behavior
- Specify formatting preferences
- Define boundaries and limitations

Example:
```markdown
You are an expert Python developer specializing in FastAPI.

When providing code:
- Always include type hints
- Add docstrings to functions
- Use async/await where appropriate
- Include error handling

When explaining:
- Start with a brief overview
- Use bullet points for steps
- Provide code examples

Never:
- Suggest deprecated patterns
- Skip error handling
- Use global state
```

## Backward Compatibility

- Existing chats without `ai_project_id` continue to work unchanged
- The `project_id` field in ChatRequest is for coding projects (separate feature)
- The new `ai_project_id` field is for AI preset projects
- No database migrations needed (JSON storage)

## Testing

Run AI Projects tests:
```bash
cd ~/ChatOS-0.1
python -m pytest tests/test_ai_projects.py -v
```

Test categories:
- Model tests: Slug generation, dataclass behavior
- Store tests: CRUD operations, persistence
- API tests: Endpoint responses
- Integration tests: Chat with project context

## Limitations & Future Work

### Current Limitations
- No project sharing/export
- Single user (no permissions system)
- No version history for projects
- Templates are hardcoded

### Future Enhancements
- Project import/export (JSON)
- Project templates from existing projects
- Project-specific conversation history
- Per-project analytics dashboard
- Project sharing via URL

## Files Changed

### New Files
- `ChatOS/projects/__init__.py`
- `ChatOS/projects/models.py`
- `ChatOS/projects/store.py`
- `ChatOS/api/routes_ai_projects.py`
- `ChatOS/templates/ai_projects.html`
- `tests/test_ai_projects.py`
- `PROJECTS_FEATURE_IMPLEMENTATION.md`

### Modified Files
- `ChatOS/app.py` - Router registration, HTML route
- `ChatOS/schemas.py` - New Pydantic models
- `ChatOS/controllers/chat.py` - Project system prompt integration
- `ChatOS/templates/index.html` - Project selector UI
- `ChatOS/static/style.css` - Project badge styles
- `ChatOS/training/job_spec.py` - project_id field

## Troubleshooting

### Project not saving
- Check write permissions on `~/ChatOS-Memory/ai_projects/`
- Look for JSON parsing errors in server logs

### System prompt not applied
- Verify project is selected in chat UI
- Check that `ai_project_id` is passed in request
- Review server logs for project loading errors

### Model not switching
- Ensure `default_model_id` matches an enabled model
- Check `/api/models?enabled_only=true` response

---

*Implementation completed: November 30, 2025*

