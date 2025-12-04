# ChatOS Diary - User Acceptance Test Cases

This document contains manual test cases for validating the Diary module functionality.

## Prerequisites

- ChatOS backend running (`uvicorn ChatOS.app:app --port 8000`)
- ChatOS frontend running (`npm run dev` in sandbox-ui)
- Sample audio files for testing (MP3, WAV)
- Browser with developer tools available

---

## Test Suite 1: Note Management

### TC1.1: Create Note Manually

**Objective:** Verify manual note creation works correctly.

**Steps:**
1. Navigate to `/diary`
2. Click the **+** button in the sidebar header
3. Observe a new note is created with default title
4. Enter title: "Test Note 1"
5. Enter content: "This is test content"
6. Add tag: "test"
7. Wait 2 seconds for auto-save

**Expected Results:**
- [ ] New note appears in sidebar list
- [ ] Title updates in sidebar as typed
- [ ] "Saving..." indicator appears briefly
- [ ] Note persists after page refresh

---

### TC1.2: Edit Existing Note

**Objective:** Verify note editing and auto-save.

**Steps:**
1. Open an existing note
2. Modify the title
3. Modify the content
4. Add a new tag
5. Remove an existing tag
6. Wait for auto-save

**Expected Results:**
- [ ] Changes save automatically
- [ ] "Unsaved changes" indicator shows before save
- [ ] "Saving..." indicator shows during save
- [ ] Changes persist after refresh

---

### TC1.3: Delete Note

**Objective:** Verify note deletion.

**Steps:**
1. Open an existing note
2. Click the **⋮** menu
3. Select "Delete"
4. Confirm deletion

**Expected Results:**
- [ ] Confirmation dialog appears
- [ ] Note is removed from sidebar
- [ ] Note is no longer accessible
- [ ] Deletion persists after refresh

---

### TC1.4: Session Isolation

**Objective:** Verify users cannot see other users' notes.

**Steps:**
1. Create a note in session A
2. Open browser incognito/private mode (new session)
3. Navigate to `/diary`
4. Check if note from session A is visible

**Expected Results:**
- [ ] Note from session A is NOT visible in session B
- [ ] Each session has independent notes

---

## Test Suite 2: Audio Upload & Transcription

### TC2.1: Upload Audio File

**Objective:** Verify audio file upload works.

**Steps:**
1. Navigate to `/diary`
2. Click "Upload Audio" button
3. Select a valid audio file (MP3 or WAV, < 100MB)
4. Observe upload progress

**Expected Results:**
- [ ] File picker opens
- [ ] Upload progress indicator shows
- [ ] Status changes: Uploading → Pending → Processing → Done
- [ ] New note appears in sidebar when done

---

### TC2.2: Drag and Drop Upload

**Objective:** Verify drag-and-drop upload works.

**Steps:**
1. Navigate to `/diary`
2. Click "Upload Audio" to show drop zone
3. Drag an audio file from file explorer
4. Drop on the upload area

**Expected Results:**
- [ ] Drop zone highlights when dragging over
- [ ] File is accepted and processing starts
- [ ] Same result as click-to-upload

---

### TC2.3: Invalid File Type Rejection

**Objective:** Verify non-audio files are rejected.

**Steps:**
1. Try to upload a .txt file
2. Try to upload a .jpg file
3. Try to upload a .pdf file

**Expected Results:**
- [ ] Files are rejected
- [ ] Error message shows allowed formats
- [ ] No processing starts

---

### TC2.4: Large File Rejection

**Objective:** Verify files over 100MB are rejected.

**Steps:**
1. Attempt to upload a file larger than 100MB

**Expected Results:**
- [ ] File is rejected before upload
- [ ] Error message shows size limit

---

### TC2.5: Transcription Result

**Objective:** Verify transcription produces expected output.

**Steps:**
1. Upload a clear audio recording with speech
2. Wait for processing to complete
3. Open the created note

**Expected Results:**
- [ ] Note has auto-generated title
- [ ] Note contains AI summary
- [ ] Note contains action items (if mentioned in audio)
- [ ] Note has "meeting" and "auto" tags
- [ ] Raw transcript is visible (expandable)

---

## Test Suite 3: Task Creation

### TC3.1: Create Tasks from Action Items

**Objective:** Verify tasks can be created from note action items.

**Steps:**
1. Create or open a note with action items
2. Click "Create Tasks" button
3. Observe task creation

**Expected Results:**
- [ ] Button shows "Creating..." during process
- [ ] Success message shows number of tasks created
- [ ] Button changes to show "X Tasks" with checkmark
- [ ] Tasks are created in AGI task system

---

### TC3.2: Idempotent Task Creation

**Objective:** Verify duplicate tasks are not created.

**Steps:**
1. Open a note that already has tasks created
2. Click "Create Tasks" button again

**Expected Results:**
- [ ] Message indicates tasks already exist
- [ ] No duplicate tasks created
- [ ] Button remains in "tasks exist" state

---

### TC3.3: View Tasks for Note

**Objective:** Verify tasks associated with a note are displayed.

**Steps:**
1. Open a note with created tasks
2. Observe the action items section

**Expected Results:**
- [ ] Tasks are loaded automatically
- [ ] Task status is shown next to each action item
- [ ] Completed tasks show checkmark

---

## Test Suite 4: Search Functionality

### TC4.1: Quick Search (Notes Filter)

**Objective:** Verify sidebar search filters notes.

**Steps:**
1. Create multiple notes with different titles
2. Type a search term in the sidebar search box
3. Observe the notes list

**Expected Results:**
- [ ] Notes list filters in real-time
- [ ] Only matching notes are shown
- [ ] Clearing search shows all notes

---

### TC4.2: Global Search - Notes

**Objective:** Verify global search finds notes.

**Steps:**
1. Click "Search All" button
2. Enter a search term that matches a note
3. Click Search

**Expected Results:**
- [ ] Search results modal appears
- [ ] Notes section shows matching notes
- [ ] Clicking a note opens it

---

### TC4.3: Global Search - Transcripts

**Objective:** Verify global search finds transcripts.

**Steps:**
1. Upload and transcribe an audio file
2. Use global search to find text from the transcript

**Expected Results:**
- [ ] Transcripts section shows matching results
- [ ] Clicking a transcript opens associated note

---

### TC4.4: Global Search - Memory

**Objective:** Verify global search finds AGI memory items.

**Steps:**
1. Create notes that are stored in memory
2. Search for content from those notes

**Expected Results:**
- [ ] Memory section shows matching results
- [ ] Results include source information
- [ ] Clicking sends to chat as context

---

### TC4.5: Search Session Isolation

**Objective:** Verify search only returns current user's data.

**Steps:**
1. Create searchable content in session A
2. Open new session (incognito)
3. Search for the same content

**Expected Results:**
- [ ] No results from session A appear in session B

---

## Test Suite 5: Send to Chat Integration

### TC5.1: Send Note to Chat

**Objective:** Verify Send to Chat navigates and provides context.

**Steps:**
1. Open a note with content
2. Click "Send to Chat" button
3. Observe navigation and chat page

**Expected Results:**
- [ ] User is redirected to Chat page
- [ ] Note content appears as context message
- [ ] Chat input is focused for follow-up

---

### TC5.2: Send Summary to Chat

**Objective:** Verify transcript summary is sent correctly.

**Steps:**
1. Open a note created from transcript
2. Click "Send to Chat" button
3. Check the context message in chat

**Expected Results:**
- [ ] Summary and action items are included
- [ ] Format is readable
- [ ] Source note title is mentioned

---

### TC5.3: Send Search Result to Chat

**Objective:** Verify memory/chat search results send to chat.

**Steps:**
1. Perform global search
2. Click on a memory or chat_history result
3. Observe navigation

**Expected Results:**
- [ ] User is redirected to Chat page
- [ ] Search result content appears as context

---

## Test Suite 6: Error Handling

### TC6.1: Network Error Recovery

**Objective:** Verify graceful handling of network errors.

**Steps:**
1. Start an upload
2. Disconnect network mid-upload
3. Reconnect network

**Expected Results:**
- [ ] Error message is displayed
- [ ] User can retry the upload
- [ ] No data corruption occurs

---

### TC6.2: Server Error Handling

**Objective:** Verify server errors are handled gracefully.

**Steps:**
1. Stop the backend server
2. Try to create a note
3. Restart the server

**Expected Results:**
- [ ] Error message is displayed
- [ ] UI remains functional
- [ ] Operations work after server restart

---

### TC6.3: Invalid Note ID

**Objective:** Verify handling of invalid note access.

**Steps:**
1. Manually navigate to `/api/notes/db/99999?session_id=test`

**Expected Results:**
- [ ] 404 error is returned
- [ ] Error message is clear

---

## Test Suite 7: Performance

### TC7.1: Large Note List

**Objective:** Verify performance with many notes.

**Steps:**
1. Create 50+ notes
2. Navigate to Diary page
3. Scroll through the list
4. Use search functionality

**Expected Results:**
- [ ] Page loads in < 3 seconds
- [ ] Scrolling is smooth
- [ ] Search is responsive

---

### TC7.2: Long Note Content

**Objective:** Verify handling of large note content.

**Steps:**
1. Create a note with 10,000+ characters
2. Edit the note
3. Save the note

**Expected Results:**
- [ ] Note saves successfully
- [ ] Editor remains responsive
- [ ] No truncation occurs

---

## Test Execution Log

| Test Case | Date | Tester | Result | Notes |
|-----------|------|--------|--------|-------|
| TC1.1 | | | | |
| TC1.2 | | | | |
| TC1.3 | | | | |
| TC1.4 | | | | |
| TC2.1 | | | | |
| TC2.2 | | | | |
| TC2.3 | | | | |
| TC2.4 | | | | |
| TC2.5 | | | | |
| TC3.1 | | | | |
| TC3.2 | | | | |
| TC3.3 | | | | |
| TC4.1 | | | | |
| TC4.2 | | | | |
| TC4.3 | | | | |
| TC4.4 | | | | |
| TC4.5 | | | | |
| TC5.1 | | | | |
| TC5.2 | | | | |
| TC5.3 | | | | |
| TC6.1 | | | | |
| TC6.2 | | | | |
| TC6.3 | | | | |
| TC7.1 | | | | |
| TC7.2 | | | | |

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| QA | | | |
| Product Owner | | | |

