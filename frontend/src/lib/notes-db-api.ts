/**
 * Notes Database API
 * API client for managing notes stored in the database
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"

// =============================================================================
// Types
// =============================================================================

export interface NoteDB {
  id: number
  title: string
  content: string
  tags: string[]
  source_type: "text" | "voice" | "import"
  transcript_id?: number
  created_at: string
  updated_at: string
  summary?: string
  action_items?: string[]
}

export interface TranscriptDB {
  id: number
  audio_path: string
  text?: string
  status: TranscriptStatus
  created_at: string
  completed_at?: string
  error?: string
  note_id?: number
}

export type TranscriptStatus = "pending" | "processing" | "completed" | "failed"

export interface TaskInfo {
  id: number
  content: string
  completed: boolean
  note_id: number
  created_at: string
}

export interface SearchResult {
  id: number | string
  title: string
  content: string
  snippet: string
  score: number
  type: "note" | "transcript" | "memory" | "chat_history"
  created_at: string
  note_id?: number  // Optional note_id for transcripts
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  query: string
  by_type: {
    notes: SearchResult[]
    transcripts: SearchResult[]
    memory: SearchResult[]
    chat_history: SearchResult[]
  }
}

export interface ListNotesDBResponse {
  notes: NoteDB[]
  total: number
  offset: number
  limit: number
}

// =============================================================================
// Note Operations
// =============================================================================

/**
 * List notes from the database
 */
export async function listNotesDB(options?: {
  search?: string
  tags?: string[]
  source_type?: string
  limit?: number
  offset?: number
}): Promise<ListNotesDBResponse> {
  const url = new URL(`${API_BASE}/api/notes-db`)
  if (options?.search) url.searchParams.set("search", options.search)
  if (options?.tags?.length) url.searchParams.set("tags", options.tags.join(","))
  if (options?.source_type) url.searchParams.set("source_type", options.source_type)
  if (options?.limit) url.searchParams.set("limit", String(options.limit))
  if (options?.offset) url.searchParams.set("offset", String(options.offset))

  try {
    const response = await fetch(url.toString())
    if (!response.ok) {
      console.warn(`Notes DB API unavailable: ${response.statusText}`)
      return { notes: [], total: 0, offset: 0, limit: 50 }
    }
    return response.json()
  } catch (error) {
    console.warn("Notes DB API unavailable:", error)
    return { notes: [], total: 0, offset: 0, limit: 50 }
  }
}

/**
 * Get a single note by ID
 */
export async function getNoteDB(id: number): Promise<NoteDB | null> {
  try {
    const response = await fetch(`${API_BASE}/api/notes-db/${id}`)
    if (!response.ok) {
      return null
    }
    return response.json()
  } catch (error) {
    console.warn("Failed to get note:", error)
    return null
  }
}

/**
 * Create a new note
 */
export async function createNoteDB(data: {
  title: string
  content: string
  tags?: string[]
  source_type?: "text" | "voice" | "import"
  transcript_id?: number
}): Promise<NoteDB | null> {
  try {
    const response = await fetch(`${API_BASE}/api/notes-db`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: data.title,
        content: data.content,
        tags: data.tags || [],
        source_type: data.source_type || "text",
        transcript_id: data.transcript_id,
      }),
    })
    if (!response.ok) {
      throw new Error(`Failed to create note: ${response.statusText}`)
    }
    return response.json()
  } catch (error) {
    console.error("Failed to create note:", error)
    return null
  }
}

/**
 * Update an existing note
 */
export async function updateNoteDB(
  id: number,
  data: Partial<{
    title: string
    content: string
    tags: string[]
  }>
): Promise<NoteDB | null> {
  try {
    const response = await fetch(`${API_BASE}/api/notes-db/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      throw new Error(`Failed to update note: ${response.statusText}`)
    }
    return response.json()
  } catch (error) {
    console.error("Failed to update note:", error)
    return null
  }
}

/**
 * Delete a note
 */
export async function deleteNoteDB(id: number): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/notes-db/${id}`, {
      method: "DELETE",
    })
    return response.ok
  } catch (error) {
    console.error("Failed to delete note:", error)
    return false
  }
}

// =============================================================================
// Search
// =============================================================================

/**
 * Search all notes and transcripts
 */
export async function searchAll(query: string): Promise<SearchResponse> {
  try {
    const url = new URL(`${API_BASE}/api/notes-db/search`)
    url.searchParams.set("q", query)
    const response = await fetch(url.toString())
    if (!response.ok) {
      return { results: [], total: 0, query, by_type: { notes: [], transcripts: [], memory: [], chat_history: [] } }
    }
    return response.json()
  } catch (error) {
    console.warn("Search failed:", error)
    return { results: [], total: 0, query, by_type: { notes: [], transcripts: [], memory: [], chat_history: [] } }
  }
}

// =============================================================================
// Transcript Operations
// =============================================================================

/**
 * Create a new transcript from audio
 */
export async function createTranscript(audioPath: string): Promise<TranscriptDB | null> {
  try {
    const response = await fetch(`${API_BASE}/api/transcripts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio_path: audioPath }),
    })
    if (!response.ok) {
      throw new Error(`Failed to create transcript: ${response.statusText}`)
    }
    return response.json()
  } catch (error) {
    console.error("Failed to create transcript:", error)
    return null
  }
}

/**
 * Wait for a transcript to complete
 */
export async function waitForTranscript(
  transcriptId: number,
  options?: { maxWaitMs?: number; pollIntervalMs?: number }
): Promise<TranscriptDB | null> {
  const maxWait = options?.maxWaitMs || 120000 // 2 minutes
  const pollInterval = options?.pollIntervalMs || 2000 // 2 seconds
  const startTime = Date.now()

  while (Date.now() - startTime < maxWait) {
    try {
      const response = await fetch(`${API_BASE}/api/transcripts/${transcriptId}`)
      if (!response.ok) {
        return null
      }
      const transcript: TranscriptDB = await response.json()
      
      if (transcript.status === "completed" || transcript.status === "failed") {
        return transcript
      }
      
      await new Promise(resolve => setTimeout(resolve, pollInterval))
    } catch (error) {
      console.error("Error polling transcript:", error)
      await new Promise(resolve => setTimeout(resolve, pollInterval))
    }
  }
  
  return null // Timed out
}

/**
 * Upload an audio file for transcription
 */
export async function uploadAudioFile(file: File): Promise<{ audio_path: string } | null> {
  try {
    const formData = new FormData()
    formData.append("file", file)
    
    const response = await fetch(`${API_BASE}/api/uploads/audio`, {
      method: "POST",
      body: formData,
    })
    
    if (!response.ok) {
      throw new Error(`Failed to upload audio: ${response.statusText}`)
    }
    
    return response.json()
  } catch (error) {
    console.error("Failed to upload audio:", error)
    return null
  }
}

// =============================================================================
// Task Operations
// =============================================================================

/**
 * Get tasks associated with a note
 */
export async function getTasksForNote(noteId: number): Promise<TaskInfo[]> {
  try {
    const response = await fetch(`${API_BASE}/api/notes-db/${noteId}/tasks`)
    if (!response.ok) {
      return []
    }
    return response.json()
  } catch (error) {
    console.warn("Failed to get tasks:", error)
    return []
  }
}

/**
 * Create tasks from note content
 */
export async function createTasksFromNote(noteId: number): Promise<TaskInfo[]> {
  try {
    const response = await fetch(`${API_BASE}/api/notes-db/${noteId}/tasks`, {
      method: "POST",
    })
    if (!response.ok) {
      return []
    }
    return response.json()
  } catch (error) {
    console.error("Failed to create tasks:", error)
    return []
  }
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format a relative time string (e.g., "2 hours ago")
 */
export function formatRelativeTimeDB(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return "just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return date.toLocaleDateString()
}

/**
 * Check if a note is from a voice transcript
 */
export function isTranscriptNote(note: NoteDB): boolean {
  return note.source_type === "voice" && note.transcript_id !== undefined
}

/**
 * Parse action items from note content
 */
export function parseActionItems(content: string): string[] {
  const items: string[] = []
  const lines = content.split("\n")
  
  for (const line of lines) {
    // Match common action item patterns
    const trimmed = line.trim()
    if (
      trimmed.startsWith("- [ ]") ||
      trimmed.startsWith("* [ ]") ||
      trimmed.match(/^(?:TODO|ACTION|TASK):/i) ||
      trimmed.match(/^\d+\.\s+\[?\s*\]/)
    ) {
      items.push(trimmed.replace(/^[-*]\s*\[\s*\]\s*/, "").replace(/^(?:TODO|ACTION|TASK):\s*/i, ""))
    }
  }
  
  return items
}

/**
 * Parse summary from note content
 */
export function parseSummary(content: string, maxLength: number = 200): string {
  // Try to find a summary section
  const summaryMatch = content.match(/(?:^|\n)(?:Summary|SUMMARY|TL;DR):\s*(.+?)(?:\n\n|\n#|$)/i)
  if (summaryMatch) {
    return summaryMatch[1].trim().slice(0, maxLength)
  }
  
  // Fall back to first paragraph
  const firstPara = content.split(/\n\n/)[0]
  if (firstPara.length <= maxLength) {
    return firstPara
  }
  
  return firstPara.slice(0, maxLength - 3) + "..."
}

/**
 * Get human-readable label for transcript status
 */
export function getTranscriptStatusLabel(status: TranscriptStatus): string {
  switch (status) {
    case "pending":
      return "Waiting..."
    case "processing":
      return "Transcribing..."
    case "completed":
      return "Complete"
    case "failed":
      return "Failed"
    default:
      return status
  }
}

/**
 * Get color class for transcript status
 */
export function getTranscriptStatusColor(status: TranscriptStatus): string {
  switch (status) {
    case "pending":
      return "text-yellow-500"
    case "processing":
      return "text-blue-500"
    case "completed":
      return "text-green-500"
    case "failed":
      return "text-red-500"
    default:
      return "text-gray-500"
  }
}

