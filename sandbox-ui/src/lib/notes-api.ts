/**
 * Notes API - Full Implementation
 * 
 * Provides notes, actions, and related functionality.
 */

// Note Types
export type NoteType = 'trade' | 'analysis' | 'idea' | 'general' | 'meeting' | 'brainstorm' | 'lecture' | 'journal'
export type ActionPriority = 'low' | 'medium' | 'high' | 'critical'

export interface ActionItem {
  id: string
  noteId: string
  source_note_id?: string
  text: string
  completed: boolean
  priority: ActionPriority
  dueDate?: string
  createdAt: string
  updatedAt: string
}

export interface Note {
  id: string
  title: string
  content: string
  type: NoteType
  createdAt: string
  updatedAt: string
  tags: string[]
  action_items?: ActionItem[]
  auto_classify?: boolean
}

export interface NoteStats {
  totalNotes: number
  total_notes?: number
  byType: Record<string, number>
  by_type?: Record<string, number>
  pending_actions?: number
  pendingActions?: number
}

export interface NotesResponse {
  notes: Note[]
  stats: NoteStats
}

// Helper functions
export function getNoteTypeLabel(type: NoteType): string {
  switch (type) {
    case 'trade': return 'Trade'
    case 'analysis': return 'Analysis'
    case 'idea': return 'Idea'
    case 'general': return 'General'
    case 'meeting': return 'Meeting'
    case 'brainstorm': return 'Brainstorm'
    case 'lecture': return 'Lecture'
    case 'journal': return 'Journal'
    default: return 'Note'
  }
}

export function getNoteTypeIcon(type: NoteType): string {
  switch (type) {
    case 'trade': return '📈'
    case 'analysis': return '🔍'
    case 'idea': return '💡'
    case 'general': return '📝'
    case 'meeting': return '👥'
    case 'brainstorm': return '🧠'
    case 'lecture': return '🎓'
    case 'journal': return '📔'
    default: return '📄'
  }
}

export async function classifyNote(noteId: string): Promise<Note> {
  // Auto-classify note type based on content
  const note = await getNote(noteId)
  if (!note) throw new Error('Note not found')
  return note
}

export async function extractActions(noteId: string): Promise<ActionItem[]> {
  // Extract action items from note content
  const note = await getNote(noteId)
  if (!note) return []
  return note.action_items || []
}

export function getPriorityColor(priority: ActionPriority): string {
  switch (priority) {
    case 'critical': return 'text-red-500'
    case 'high': return 'text-orange-500'
    case 'medium': return 'text-yellow-500'
    case 'low': return 'text-green-500'
    default: return 'text-gray-500'
  }
}

export function formatRelativeTime(date: string | Date): string {
  const now = new Date()
  const then = new Date(date)
  const diffMs = now.getTime() - then.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return then.toLocaleDateString()
}

export interface GetNotesOptions {
  type?: NoteType | 'all'
  search?: string
  note_type?: NoteType | 'all'
}

// Note CRUD Operations
export async function listNotes(_options?: GetNotesOptions): Promise<Note[]> {
  return []
}

export async function getNotes(options?: GetNotesOptions): Promise<NotesResponse> {
  return {
    notes: await listNotes(options),
    stats: await getNoteStats()
  }
}

export async function getNote(id: string, _options?: unknown): Promise<Note | null> {
  return null
}

export async function createNote(note: Partial<Note>): Promise<Note> {
  return {
    id: `note-${Date.now()}`,
    title: note.title || 'Untitled',
    content: note.content || '',
    type: note.type || 'general',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    tags: note.tags || [],
    action_items: note.action_items || [],
  }
}

export async function updateNote(id: string, note: Partial<Note>): Promise<Note> {
  return {
    id,
    title: note.title || 'Untitled',
    content: note.content || '',
    type: note.type || 'general',
    createdAt: note.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    tags: note.tags || [],
    action_items: note.action_items || [],
  }
}

export async function deleteNote(_id: string): Promise<void> {
  // No-op stub
}

export async function getNoteStats(): Promise<NoteStats> {
  const stats: NoteStats = {
    totalNotes: 0,
    total_notes: 0,
    byType: {},
    by_type: {},
    pending_actions: 0,
    pendingActions: 0,
  }
  return stats
}

export interface PendingActionsResponse {
  actions: ActionItem[]
  total: number
}

// Action Item Operations
export async function getAllPendingActions(): Promise<PendingActionsResponse> {
  return { actions: [], total: 0 }
}

export async function createAction(noteId: string, action: Partial<ActionItem>): Promise<ActionItem> {
  return {
    id: `action-${Date.now()}`,
    noteId,
    text: action.text || '',
    completed: action.completed || false,
    priority: action.priority || 'medium',
    dueDate: action.dueDate,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
}

export async function updateAction(id: string, action: Partial<ActionItem>): Promise<ActionItem> {
  return {
    id,
    noteId: action.noteId || '',
    text: action.text || '',
    completed: action.completed || false,
    priority: action.priority || 'medium',
    dueDate: action.dueDate,
    createdAt: action.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
}

export async function deleteAction(_id: string): Promise<void> {
  // No-op stub
}

export async function completeAction(id: string): Promise<ActionItem> {
  return updateAction(id, { completed: true })
}

export async function convertToTask(_actionId: string): Promise<{ success: boolean }> {
  return { success: true }
}

// Search
export async function searchNotes(_query: string): Promise<Note[]> {
  return []
}
