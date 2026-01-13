---
name: User Pages Beta Testing Plan
overview: Create a comprehensive manual beta testing plan for all user-dedicated pages (non-admin) to ensure functionality, UI responsiveness, and integration work correctly from a human user perspective.
todos:
  - id: test-chat-page
    content: Test main chat interface (/) - messaging, commands, streaming, context integration
    status: pending
  - id: test-trading-dashboard
    content: Test trading dashboard (/trading) - market data, portfolio, navigation, exchange connection
    status: pending
  - id: test-automations
    content: Test trading automations (/trading/automations) - list, create, start/stop, edit, delete, real-time updates
    status: pending
  - id: test-journal
    content: Test trading journal (/trading/journal) - entries, create/edit/delete, filters, auto-creation from trades
    status: pending
  - id: test-lab
    content: Test backtesting lab (/trading/lab) - configure, run, view results, history, export
    status: pending
  - id: test-diary
    content: Test diary (/diary) - notes, audio upload/transcription, search, send to chat, tags
    status: pending
  - id: test-notes
    content: Test notes (/notes) - list, create, filter by type, search, action items
    status: pending
  - id: test-editor
    content: Test automation editor (/editor) - create automation, add blocks, configure, connect, save, run, AI builder
    status: pending
  - id: test-sandbox
    content: Test code sandbox (/sandbox) - write code, run, file management, save/load
    status: pending
  - id: test-training
    content: Test training page (/training) - model selection, configure, start, monitor, view results
    status: pending
  - id: test-integration
    content: Test cross-page integration - navigation, data persistence, shared state, real-time updates
    status: pending
  - id: test-errors
    content: Test error scenarios - network failure, invalid input, server errors, recovery
    status: pending
  - id: test-performance
    content: Test performance - page load times, large datasets, real-time update smoothness
    status: pending
  - id: test-browsers
    content: Test browser compatibility - Chrome, Firefox, Safari/Edge
    status: pending
  - id: compile-report
    content: Compile test results report with bugs, issues, and recommendations
    status: pending
---

# User Pages Beta Testing Plan

## Overview

This plan provides a systematic approach for beta testing all user-facing pages in ChatOS, excluding admin pages. The focus is on validating functionality, user experience, and integration between pages.

## Pages to Test

### Core User Pages

1. `/` - Main Chat Interface
2. `/trading` - Trading Dashboard
3. `/trading/automations` - Trading Automations
4. `/trading/journal` - Trading Journal
5. `/trading/lab` - Backtesting Lab
6. `/diary` - Diary/Notes with Transcription
7. `/notes` - Notes Management
8. `/editor` - Automation Builder/Editor
9. `/sandbox` - Code Sandbox
10. `/training` - Model Training Interface

---

## Testing Framework

### Test Environment Setup

**Prerequisites:**

- ChatOS running at `http://192.168.0.249` (or localhost)
- Browser with DevTools open (F12)
- Network tab monitoring enabled
- Console tab open for error checking

**Test Browser:**

- Primary: Chrome/Firefox (latest)
- Secondary: Safari/Edge (if available)

---

## Page-by-Page Test Scenarios

### 1. Main Chat Interface (`/`)

**Test Cases:**

**TC-CHAT-001: Page Load**

- Navigate to `/`
- Verify page loads without errors
- Check console for JavaScript errors
- Verify chat input is visible and focused
- Verify sidebar navigation is visible

**TC-CHAT-002: Send Message**

- Type a message in chat input
- Click Send button (or press Enter)
- Verify message appears in chat history
- Verify loading indicator shows
- Verify response appears from backend
- Check Network tab for API call to `/api/chat`

**TC-CHAT-003: Command Buttons**

- Click `/code` button
- Verify command is inserted into input
- Repeat for `/research`, `/deepthinking`, `/swarm`
- Verify each command inserts correctly

**TC-CHAT-004: Context from Other Pages**

- Open `/diary` page in another tab
- Create a note and click "Send to Chat"
- Return to `/` tab
- Verify note content appears as context message
- Verify source label shows correctly

**TC-CHAT-005: Streaming Response**

- Send a message that triggers streaming
- Verify tokens appear incrementally
- Verify no duplicate messages
- Verify final message is complete

**TC-CHAT-006: Error Handling**

- Stop backend server
- Try to send a message
- Verify error message displays
- Restart backend
- Verify recovery works

---

### 2. Trading Dashboard (`/trading`)

**Test Cases:**

**TC-TRADING-001: Page Load**

- Navigate to `/trading`
- Verify page loads without errors
- Verify market data displays
- Check for live price updates

**TC-TRADING-002: Market Data Display**

- Verify symbols show (BTC, ETH, etc.)
- Verify prices update in real-time
- Verify 24h change percentages show
- Verify volume data displays
- Check WebSocket connection in Network tab

**TC-TRADING-003: Symbol Selection**

- Click on a symbol (e.g., BTCUSDT)
- Verify chart updates
- Verify order book updates (if shown)
- Verify position data updates

**TC-TRADING-004: Portfolio Display**

- Verify portfolio stats show
- Verify total value calculates correctly
- Verify PnL displays
- Verify win rate shows

**TC-TRADING-005: Navigation Tabs**

- Click "Markets" tab
- Click "Portfolio" tab
- Click "Journal" tab
- Verify each tab loads correctly
- Verify data persists when switching tabs

**TC-TRADING-006: Exchange Connection**

- Click "Connect Exchange" (if available)
- Verify connection modal opens
- Test with paper trading account
- Verify connection status updates

---

### 3. Trading Automations (`/trading/automations`)

**Test Cases:**

**TC-AUTO-001: Page Load**

- Navigate to `/trading/automations`
- Verify page loads without errors
- Verify automation list displays
- Check for empty state if no automations

**TC-AUTO-002: Automation List**

- Verify automations show status (running/stopped)
- Verify automation names display
- Verify last run time shows
- Verify performance metrics display

**TC-TRADING-003: Create Automation**

- Click "Create Automation" or "+" button
- Verify creation modal/form opens
- Fill in automation details
- Submit form
- Verify new automation appears in list

**TC-AUTO-004: Start/Stop Automation**

- Find a stopped automation
- Click "Start" button
- Verify status changes to "Running"
- Verify start time updates
- Click "Stop" button
- Verify status changes back

**TC-AUTO-005: Edit Automation**

- Click edit icon on an automation
- Verify edit form opens with current values
- Modify settings
- Save changes
- Verify updates reflect in list

**TC-AUTO-006: Delete Automation**

- Click delete icon
- Verify confirmation dialog
- Confirm deletion
- Verify automation removed from list

**TC-AUTO-007: Real-time Updates**

- Start an automation
- Verify WebSocket updates show
- Verify execution logs update
- Verify performance metrics update live

---

### 4. Trading Journal (`/trading/journal`)

**Test Cases:**

**TC-JOURNAL-001: Page Load**

- Navigate to `/trading/journal`
- Verify page loads without errors
- Verify journal entries display
- Check for empty state if no entries

**TC-JOURNAL-002: Entry List**

- Verify entries show in chronological order
- Verify entry types display (trade/note/analysis)
- Verify timestamps show correctly
- Verify symbols/tags display

**TC-JOURNAL-003: Create Entry**

- Click "New Entry" or "+" button
- Select entry type (trade/note/analysis)
- Fill in title and content
- Add symbols/tags
- Save entry
- Verify entry appears in list

**TC-JOURNAL-004: View Entry**

- Click on a journal entry
- Verify entry details display
- Verify all fields show correctly
- Verify edit/delete options available

**TC-JOURNAL-005: Edit Entry**

- Open an entry
- Click edit button
- Modify content
- Save changes
- Verify updates reflect

**TC-JOURNAL-006: Delete Entry**

- Open an entry
- Click delete button
- Confirm deletion
- Verify entry removed

**TC-JOURNAL-007: Filter/Search**

- Use search box to filter entries
- Verify results update in real-time
- Use type filter (trade/note/analysis)
- Verify filtering works correctly

**TC-JOURNAL-008: Auto-Entry Creation**

- Execute a trade in trading dashboard
- Navigate to journal
- Verify trade entry auto-created
- Verify trade details populated correctly

---

### 5. Backtesting Lab (`/trading/lab`)

**Test Cases:**

**TC-LAB-001: Page Load**

- Navigate to `/trading/lab`
- Verify page loads without errors
- Verify backtest form displays
- Verify backtest history shows (if any)

**TC-LAB-002: Configure Backtest**

- Select symbols (multiple)
- Set timeframe (1m/5m/15m)
- Set initial balance
- Set days/hours to test
- Set risk parameters
- Verify all fields accept input

**TC-LAB-003: Run Backtest**

- Fill in all required fields
- Click "Run Backtest" button
- Verify progress indicator shows
- Verify progress updates
- Wait for completion
- Verify results display

**TC-LAB-004: View Results**

- After backtest completes
- Verify metrics display (win rate, PnL, etc.)
- Verify equity curve chart shows
- Verify trade list displays
- Verify individual trades clickable

**TC-LAB-005: Backtest History**

- Verify previous backtests listed
- Click on a previous backtest
- Verify results load correctly
- Verify can compare multiple backtests

**TC-LAB-006: Export Results**

- Complete a backtest
- Click export button (if available)
- Verify export downloads
- Verify file format correct

---

### 6. Diary (`/diary`)

**Test Cases:**

**TC-DIARY-001: Page Load**

- Navigate to `/diary`
- Verify page loads without errors
- Verify note list displays in sidebar
- Verify editor area shows

**TC-DIARY-002: Create Note**

- Click "+" button in sidebar
- Verify new note created
- Type title and content
- Verify auto-save indicator shows
- Verify note appears in sidebar

**TC-DIARY-003: Edit Note**

- Click on a note in sidebar
- Modify content
- Verify auto-save works
- Verify "Saving..." indicator shows
- Verify changes persist after refresh

**TC-DIARY-004: Delete Note**

- Open a note
- Click menu (⋮) button
- Select "Delete"
- Confirm deletion
- Verify note removed

**TC-DIARY-005: Audio Upload**

- Click "Upload Audio" button
- Select an audio file (MP3/WAV)
- Verify upload progress shows
- Verify status: Uploading → Processing → Done
- Verify note created with transcription

**TC-DIARY-006: Search Notes**

- Type in sidebar search box
- Verify notes filter in real-time
- Clear search
- Verify all notes show again

**TC-DIARY-007: Global Search**

- Click "Search All" button
- Enter search term
- Verify results show (notes/transcripts/memory)
- Click on a result
- Verify correct note opens

**TC-DIARY-008: Send to Chat**

- Open a note with content
- Click "Send to Chat" button
- Verify navigation to `/`
- Verify note content appears in chat
- Verify can continue conversation

**TC-DIARY-009: Tags**

- Create/edit a note
- Add tags
- Verify tags save
- Verify tags display in note
- Filter by tag (if available)

---

### 7. Notes (`/notes`)

**Test Cases:**

**TC-NOTES-001: Page Load**

- Navigate to `/notes`
- Verify page loads without errors
- Verify note list displays
- Verify stats panel shows

**TC-NOTES-002: Note List**

- Verify notes display correctly
- Verify note types show (meeting/brainstorm/etc.)
- Verify timestamps display
- Verify tags display

**TC-NOTES-003: Create Note**

- Click "New Note" button
- Select note type
- Fill in title and content
- Add tags
- Save note
- Verify appears in list

**TC-NOTES-004: Filter by Type**

- Click type filter (Meetings/Brainstorms/etc.)
- Verify list filters correctly
- Select "All Notes"
- Verify all notes show

**TC-NOTES-005: Search**

- Type in search box
- Verify notes filter in real-time
- Verify search works across title and content

**TC-NOTES-006: Action Items**

- Open a note with action items
- Verify action items panel shows
- Verify can create tasks from action items
- Verify task status updates

---

### 8. Automation Editor (`/editor`)

**Test Cases:**

**TC-EDITOR-001: Page Load**

- Navigate to `/editor`
- Verify page loads without errors
- Verify canvas/workspace displays
- Verify block palette shows

**TC-EDITOR-002: Create Automation**

- Click "New Automation"
- Enter name and description
- Verify canvas is empty
- Verify block palette available

**TC-EDITOR-003: Add Blocks**

- Drag blocks from palette to canvas
- Verify blocks connect correctly
- Verify connection lines draw
- Verify block properties editable

**TC-EDITOR-004: Configure Blocks**

- Click on a block
- Verify properties panel opens
- Modify block settings
- Verify changes save
- Verify block updates visually

**TC-EDITOR-005: Connect Blocks**

- Add multiple blocks
- Connect output of one to input of another
- Verify connection validates
- Verify invalid connections rejected

**TC-EDITOR-006: Save Automation**

- Create/edit automation
- Click Save button
- Verify save success message
- Verify automation persists

**TC-EDITOR-007: Run Automation**

- Create a simple automation
- Click "Run" or "Test" button
- Verify execution starts
- Verify output displays
- Verify logs show execution steps

**TC-EDITOR-008: AI Builder**

- Click "AI Builder" mode
- Enter description of automation
- Verify AI generates blocks
- Verify can edit AI-generated automation

---

### 9. Code Sandbox (`/sandbox`)

**Test Cases:**

**TC-SANDBOX-001: Page Load**

- Navigate to `/sandbox`
- Verify page loads without errors
- Verify code editor displays
- Verify run button visible

**TC-SANDBOX-002: Write Code**

- Type code in editor
- Verify syntax highlighting works
- Verify code auto-saves
- Verify can write multiple languages

**TC-SANDBOX-003: Run Code**

- Write simple code (e.g., print("Hello"))
- Click "Run" button
- Verify execution starts
- Verify output displays
- Verify errors display if code fails

**TC-SANDBOX-004: File Management**

- Create new file
- Verify file appears in file tree
- Switch between files
- Verify code persists per file

**TC-SANDBOX-005: Save/Load**

- Write code
- Click Save
- Refresh page
- Verify code loads correctly

---

### 10. Training (`/training`)

**Test Cases:**

**TC-TRAIN-001: Page Load**

- Navigate to `/training`
- Verify page loads without errors
- Verify training interface displays
- Verify model selection available

**TC-TRAIN-002: Select Model**

- Choose a model from dropdown
- Verify model details display
- Verify training options show

**TC-TRAIN-003: Configure Training**

- Set training parameters
- Upload training data (if applicable)
- Verify configuration validates
- Verify can start training

**TC-TRAIN-004: Start Training**

- Configure training job
- Click "Start Training"
- Verify training starts
- Verify progress indicator shows
- Verify logs display

**TC-TRAIN-005: Monitor Training**

- During training, verify progress updates
- Verify metrics display (loss, accuracy, etc.)
- Verify can pause/resume (if available)
- Verify can stop training

**TC-TRAIN-006: View Results**

- After training completes
- Verify results display
- Verify model metrics show
- Verify can download model (if available)

---

## Cross-Page Integration Tests

**TC-INTEG-001: Navigation**

- Test navigation between all pages
- Verify sidebar links work
- Verify browser back/forward works
- Verify URLs update correctly

**TC-INTEG-002: Data Persistence**

- Create data on one page
- Navigate to another page
- Return to first page
- Verify data persists

**TC-INTEG-003: Shared State**

- Update settings/preferences
- Navigate to different pages
- Verify settings apply across pages

**TC-INTEG-004: Real-time Updates**

- Open trading page
- Verify WebSocket connects
- Open another tab with same page
- Verify both tabs update simultaneously

---

## Error Scenarios

**TC-ERROR-001: Network Failure**

- Disconnect network
- Try to perform actions
- Verify error messages display
- Reconnect network
- Verify recovery works

**TC-ERROR-002: Invalid Input**

- Enter invalid data in forms
- Verify validation errors show
- Verify form doesn't submit
- Fix errors
- Verify submission works

**TC-ERROR-003: Server Error**

- Stop backend server
- Try to load pages
- Verify error handling
- Restart server
- Verify pages recover

---

## Performance Tests

**TC-PERF-001: Page Load Time**

- Measure load time for each page
- Target: < 3 seconds initial load
- Verify subsequent navigations faster

**TC-PERF-002: Large Data Sets**

- Create 50+ journal entries
- Verify page still responsive
- Verify search/filter still fast
- Verify scrolling smooth

**TC-PERF-003: Real-time Updates**

- Open trading page with live data
- Verify updates don't freeze UI
- Verify smooth animations
- Verify no memory leaks

---

## Browser Compatibility

**TC-BROWSER-001: Chrome**

- Test all pages in Chrome
- Verify all features work
- Verify no console errors

**TC-BROWSER-002: Firefox**

- Test all pages in Firefox
- Verify all features work
- Verify no console errors

**TC-BROWSER-003: Safari/Edge**

- Test critical pages
- Verify core functionality works

---

## Mobile Responsiveness (Optional)

**TC-MOBILE-001: Mobile View**

- Resize browser to mobile size
- Test key pages
- Verify layout adapts
- Verify touch interactions work

---

## Test Execution Checklist

Create a spreadsheet or document with:

- Test Case ID
- Page/Feature
- Steps
- Expected Result
- Actual Result
- Pass/Fail
- Notes/Comments
- Screenshots (for failures)

---

## Success Criteria

- All pages load without JavaScript errors
- All core functionality works as expected
- Real-time updates function correctly
- Navigation between pages smooth
- Data persists correctly
- Error handling graceful
- Performance acceptable (< 3s load time)
- No critical bugs blocking user workflows

---

## Reporting

After testing, compile:

1. Test execution summary (pass/fail counts)
2. List of bugs found (with severity)
3. List of usability issues
4. Performance observations
5. Browser compatibility notes
6. Recommendations for improvements