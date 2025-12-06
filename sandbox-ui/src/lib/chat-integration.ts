/**
 * Chat Integration Utilities
 * 
 * Handles cross-page chat message integration.
 */

const PENDING_MESSAGE_KEY = 'pending_chat_message'

export interface PendingChatMessage {
  content: string
  sourceType?: 'note' | 'search' | 'diary' | 'general'
  sourceId?: string | number
}

/**
 * Store a pending chat message for another page to consume
 */
export function setPendingChatMessage(message: string): void {
  if (typeof window !== 'undefined') {
    sessionStorage.setItem(PENDING_MESSAGE_KEY, message)
  }
}

/**
 * Queue a chat message with metadata
 */
export function queueChatMessage(message: PendingChatMessage): void {
  if (typeof window !== 'undefined') {
    sessionStorage.setItem(PENDING_MESSAGE_KEY, JSON.stringify(message))
  }
}

/**
 * Consume a pending chat message (removes it after reading)
 */
export function consumePendingChatMessage(): string | null {
  if (typeof window === 'undefined') return null
  
  const message = sessionStorage.getItem(PENDING_MESSAGE_KEY)
  if (message) {
    sessionStorage.removeItem(PENDING_MESSAGE_KEY)
  }
  
  // Try to parse as JSON, fall back to raw string
  if (message) {
    try {
      const parsed = JSON.parse(message) as PendingChatMessage
      return parsed.content
    } catch {
      return message
    }
  }
  return null
}

/**
 * Check if there's a pending chat message without consuming it
 */
export function hasPendingChatMessage(): boolean {
  if (typeof window === 'undefined') return false
  return sessionStorage.getItem(PENDING_MESSAGE_KEY) !== null
}

/**
 * Format a note for sending to chat
 */
export function formatNoteForChat(note: {
  title: string
  content: string
  tags?: string[]
}): string {
  const tagsStr = note.tags?.length ? `\nTags: ${note.tags.join(', ')}` : ''
  return `**Note: ${note.title}**\n\n${note.content}${tagsStr}`
}

/**
 * Format a search result for sending to chat
 */
export function formatSearchResultForChat(result: {
  title: string
  snippet: string
  type: string
}): string {
  return `**${result.type.toUpperCase()}: ${result.title}**\n\n${result.snippet}`
}

