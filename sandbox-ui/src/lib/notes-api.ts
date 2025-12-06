/**
 * Notes API
 * 
 * API client for notes functionality.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"

export interface Note {
  id: string
  title: string
  content: string
  note_type: NoteType
  created_at: string
  updated_at: string
  tags: string[]
  action_items: ActionItem[]
}

export interface ActionItem {
  id: string
  content: string
  completed: boolean
  priority?: ActionPriority
  note_id?: string
}

export type ActionPriority = 'high' | 'medium' | 'low'

export type NoteType = 'trade' | 'analysis' | 'idea' | 'research' | 'meeting' | 'general'

export interface NoteStats {
  total_notes: number
  pending_actions: number
  by_type: Record<string, number>
}

export interface ListNotesResponse {
  notes: Note[]
  stats: NoteStats
}

// Note type icons
const NOTE_TYPE_ICONS: Record<NoteType, string> = {
  trade: '📈',
  analysis: '📊',
  idea: '💡',
  research: '🔬',
  meeting: '👥',
  general: '📝',
}

// Note type labels
const NOTE_TYPE_LABELS: Record<NoteType, string> = {
  trade: 'Trade',
  analysis: 'Analysis',
  idea: 'Idea',
  research: 'Research',
  meeting: 'Meeting',
  general: 'General',
}

export function getNoteTypeIcon(type: NoteType): string {
  return NOTE_TYPE_ICONS[type] || NOTE_TYPE_ICONS.general
}

export function getNoteTypeLabel(type: NoteType): string {
  return NOTE_TYPE_LABELS[type] || NOTE_TYPE_LABELS.general
}

export function formatRelativeTime(dateString: string): string {
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

export async function listNotes(options?: {
  search?: string
  note_type?: NoteType
  limit?: number
  offset?: number
}): Promise<ListNotesResponse> {
  const url = new URL(`${API_BASE}/api/notes`)
  if (options?.search) url.searchParams.set("search", options.search)
  if (options?.note_type) url.searchParams.set("note_type", options.note_type)
  if (options?.limit) url.searchParams.set("limit", String(options.limit))
  if (options?.offset) url.searchParams.set("offset", String(options.offset))

  try {
    const response = await fetch(url.toString())
    if (!response.ok) {
      console.warn(`Notes API unavailable: ${response.statusText}`)
      return { notes: [], stats: { total_notes: 0, pending_actions: 0, by_type: {} } }
    }
    return response.json()
  } catch (error) {
    console.warn("Notes API unavailable:", error)
    return { notes: [], stats: { total_notes: 0, pending_actions: 0, by_type: {} } }
  }
}

export async function getNote(id: string): Promise<Note | null> {
  try {
    const response = await fetch(`${API_BASE}/api/notes/${id}`)
    if (!response.ok) return null
    return response.json()
  } catch (error) {
    console.warn("Failed to get note:", error)
    return null
  }
}

export async function createNote(note: Partial<Note>): Promise<Note> {
  try {
    const response = await fetch(`${API_BASE}/api/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: note.title || 'Untitled',
        content: note.content || '',
        note_type: note.note_type || 'general',
        tags: note.tags || [],
      }),
    })
    if (!response.ok) {
      throw new Error(`Failed to create note: ${response.statusText}`)
    }
    return response.json()
  } catch (error) {
    console.error("Failed to create note:", error)
    // Return a stub note on error
    return {
      id: `note-${Date.now()}`,
      title: note.title || 'Untitled',
      content: note.content || '',
      note_type: note.note_type || 'general',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      tags: note.tags || [],
      action_items: [],
    }
  }
}

export async function updateNote(id: string, note: Partial<Note>): Promise<Note> {
  try {
    const response = await fetch(`${API_BASE}/api/notes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(note),
    })
    if (!response.ok) {
      throw new Error(`Failed to update note: ${response.statusText}`)
    }
    return response.json()
  } catch (error) {
    console.error("Failed to update note:", error)
    // Return input as-is on error
    return {
      id,
      title: note.title || 'Untitled',
      content: note.content || '',
      note_type: note.note_type || 'general',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      tags: note.tags || [],
      action_items: note.action_items || [],
    }
  }
}

export async function deleteNote(id: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/notes/${id}`, {
      method: "DELETE",
    })
  } catch (error) {
    console.error("Failed to delete note:", error)
  }
}

export async function classifyNote(id: string): Promise<{ classified_type: NoteType }> {
  try {
    const response = await fetch(`${API_BASE}/api/notes/${id}/classify`, {
      method: "POST",
    })
    if (!response.ok) {
      return { classified_type: 'general' }
    }
    return response.json()
  } catch (error) {
    console.warn("Failed to classify note:", error)
    return { classified_type: 'general' }
  }
}

export async function extractActions(id: string): Promise<{ added_count: number; actions: ActionItem[] }> {
  try {
    const response = await fetch(`${API_BASE}/api/notes/${id}/extract-actions`, {
      method: "POST",
    })
    if (!response.ok) {
      return { added_count: 0, actions: [] }
    }
    return response.json()
  } catch (error) {
    console.warn("Failed to extract actions:", error)
    return { added_count: 0, actions: [] }
  }
}

export async function getNoteStats(): Promise<NoteStats> {
  try {
    const response = await fetch(`${API_BASE}/api/notes/stats`)
    if (!response.ok) {
      return { total_notes: 0, pending_actions: 0, by_type: {} }
    }
    return response.json()
  } catch (error) {
    console.warn("Failed to get note stats:", error)
    return { total_notes: 0, pending_actions: 0, by_type: {} }
  }
}

// Priority colors for action items
export function getPriorityColor(priority?: string): string {
  switch (priority) {
    case 'high':
      return 'text-red-500'
    case 'medium':
      return 'text-yellow-500'
    case 'low':
      return 'text-green-500'
    default:
      return 'text-gray-500'
  }
}

export async function getAllPendingActions(): Promise<ActionItem[]> {
  try {
    const response = await fetch(`${API_BASE}/api/notes/actions/pending`)
    if (!response.ok) {
      return []
    }
    return response.json()
  } catch (error) {
    console.warn("Failed to get pending actions:", error)
    return []
  }
}

export async function completeAction(noteId: string, actionId: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/notes/${noteId}/actions/${actionId}/complete`, {
      method: "POST",
    })
  } catch (error) {
    console.error("Failed to complete action:", error)
  }
}

export async function convertToTask(noteId: string, actionId: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/notes/${noteId}/actions/${actionId}/convert-to-task`, {
      method: "POST",
    })
  } catch (error) {
    console.error("Failed to convert to task:", error)
  }
}

export async function createAction(noteId: string, action: Partial<ActionItem>): Promise<ActionItem | null> {
  try {
    const response = await fetch(`${API_BASE}/api/notes/${noteId}/actions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(action),
    })
    if (!response.ok) {
      return null
    }
    return response.json()
  } catch (error) {
    console.error("Failed to create action:", error)
    return null
  }
}

export async function updateAction(noteId: string, actionId: string, action: Partial<ActionItem>): Promise<ActionItem | null> {
  try {
    const response = await fetch(`${API_BASE}/api/notes/${noteId}/actions/${actionId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(action),
    })
    if (!response.ok) {
      return null
    }
    return response.json()
  } catch (error) {
    console.error("Failed to update action:", error)
    return null
  }
}

export async function deleteAction(noteId: string, actionId: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/notes/${noteId}/actions/${actionId}`, {
      method: "DELETE",
    })
  } catch (error) {
    console.error("Failed to delete action:", error)
  }
}

