# ChatOS Diary - User Guide

The Diary module in ChatOS lets you capture voice recordings, transcribe them automatically, and turn them into actionable notes with AI-powered summaries.

## Getting Started

### Accessing the Diary

1. Open ChatOS in your browser (default: `http://localhost:3000`)
2. Click **Diary** in the sidebar navigation (🎙️ icon)

### The Diary Interface

The Diary page has three main areas:

- **Sidebar** (left): List of all your notes, search, and quick actions
- **Main Area** (center): Note editor or audio uploader
- **Header**: Navigation and global search

---

## Recording & Transcribing Audio

### Uploading Audio Files

1. Click the **Upload Audio** button in the sidebar
2. Either:
   - **Drag and drop** audio files onto the upload area
   - **Click** the area to browse and select files
3. Supported formats: MP3, WAV, M4A, OGG, FLAC, WebM, AAC
4. Maximum file size: 100MB

### Transcription Process

After uploading, the system automatically:

1. **Uploads** the file to secure storage
2. **Transcribes** the audio using AI (Whisper)
3. **Summarizes** the content and extracts action items
4. **Creates a note** with the summary

You'll see status indicators:
- 🔄 **Uploading** - File being uploaded
- ⏳ **Pending** - Waiting for processing
- ⚙️ **Processing** - Transcription in progress
- ✅ **Done** - Note created successfully
- ❌ **Error** - Something went wrong

### Viewing Results

When transcription completes:
- A new note appears in your notes list
- The note contains:
  - **AI Summary** - Key points from the recording
  - **Action Items** - Tasks extracted from the content
  - **Raw Transcript** - Full transcribed text (expandable)

---

## Working with Notes

### Creating Notes Manually

1. Click the **+** button in the sidebar header
2. Enter a title and content
3. Add tags for organization
4. Notes auto-save as you type

### Editing Notes

1. Click a note in the sidebar to open it
2. Edit the title, content, or tags
3. Changes save automatically (1.5 second delay)
4. Look for "Saving..." indicator in the header

### Organizing with Tags

- Add tags by clicking the **+** button next to existing tags
- Remove tags by clicking the **×** on a tag
- Filter notes by tag using the search box

### Deleting Notes

1. Open the note you want to delete
2. Click the **⋮** (more) menu in the header
3. Select **Delete**
4. Confirm the deletion

---

## AI Features

### Understanding Summaries

For notes created from audio transcripts:

- **Summary**: A 2-4 sentence overview of the key points
- **Action Items**: Tasks mentioned in the recording
- **Topics**: Main subjects discussed

### Creating Tasks from Action Items

1. Open a note with action items
2. Click **Create Tasks** button in the header
3. Tasks are created in the AGI task system
4. The button shows ✅ when tasks exist

### Send to Chat

Share note content with the AI chat:

1. Open a note
2. Click **Send to Chat** (💬 icon)
3. You'll be redirected to the Chat page
4. The note content appears as context
5. Ask follow-up questions about the content

---

## Search

### Quick Search (Notes Only)

Use the search box in the sidebar to filter notes by:
- Title
- Content
- Tags

### Global Search (All Content)

Click **Search All** button for comprehensive search across:
- 📝 **Notes** - All your notes
- 🎙️ **Transcripts** - Audio transcriptions
- 🧠 **Memory** - AGI long-term memory
- 💬 **Chat History** - Past conversations

#### Using Global Search

1. Click **Search All (Notes, Transcripts, Memory)** button
2. Enter your search query (minimum 2 characters)
3. Results are grouped by type
4. Click a result to:
   - Open notes directly
   - Navigate to associated notes for transcripts
   - Send memory/chat results to Chat for context

---

## Tips & Best Practices

### For Better Transcriptions

- **Speak clearly** and at a moderate pace
- **Minimize background noise** when recording
- **Use a quality microphone** for best results
- **Specify language** if not English (future feature)

### For Better Summaries

- **Structure your recordings** with clear topics
- **State action items explicitly** (e.g., "I need to...")
- **Summarize key decisions** at the end

### Organizing Your Notes

- Use **consistent tags** (e.g., "meeting", "personal", "project-x")
- **Review and edit** auto-generated summaries
- **Create tasks** from action items to track follow-ups

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + N` | Create new note (when in Diary) |
| `Ctrl/Cmd + S` | Force save current note |
| `Escape` | Close dialogs/modals |

---

## Troubleshooting

### Upload Failed

- Check file format is supported
- Ensure file is under 100MB
- Try a different browser if issues persist

### Transcription Stuck

- Refresh the page and check status
- Large files may take several minutes
- Check server logs if consistently failing

### Summary Not Helpful

- The AI works best with clear, structured audio
- Edit the summary manually if needed
- Provide feedback for future improvements

### Notes Not Appearing

- Check you're using the correct session
- Refresh the page
- Clear browser cache if issues persist

---

## Privacy & Data

- **Audio files** are stored locally in `~/ChatOS-Memory/uploads/`
- **Notes** are stored in the local SQLite database
- **Transcription** happens locally (no cloud services)
- **Session isolation** ensures your data is private

---

## Getting Help

- Check the [API Documentation](./API_NOTES.md) for technical details
- Report issues on the project repository
- Join the community chat for support

