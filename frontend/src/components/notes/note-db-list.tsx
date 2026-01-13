"use client"

import { cn } from "@/lib/utils"
import {
  type NoteDB,
  formatRelativeTimeDB,
  isTranscriptNote,
} from "@/lib/notes-db-api"
import { Skeleton } from "@/components/ui/skeleton"
import { FileAudio, FileText, Tag } from "lucide-react"

interface NoteDBListProps {
  notes: NoteDB[]
  selectedId?: number
  onSelect: (note: NoteDB) => void
  isLoading?: boolean
}

export function NoteDBList({ notes, selectedId, onSelect, isLoading }: NoteDBListProps) {
  if (isLoading) {
    return (
      <div className="p-2 space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="p-3 rounded-lg bg-[var(--bg-tertiary)]">
            <Skeleton className="h-4 w-3/4 mb-2" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    )
  }

  if (notes.length === 0) {
    return (
      <div className="p-4 text-center text-[var(--text-muted)]">
        <p className="text-sm">No notes found</p>
      </div>
    )
  }

  return (
    <div className="p-2 space-y-1">
      {notes.map((note) => {
        const isFromTranscript = isTranscriptNote(note)
        
        return (
          <button
            key={note.id}
            onClick={() => onSelect(note)}
            className={cn(
              "w-full text-left p-3 rounded-lg transition-all duration-200",
              "hover:bg-[var(--bg-tertiary)]",
              selectedId === note.id
                ? "bg-gradient-to-r from-[var(--accent-primary)]/10 to-[var(--accent-secondary)]/10 border border-[var(--accent-primary)]/20"
                : "border border-transparent"
            )}
          >
            <div className="flex items-start gap-2">
              <span className={cn(
                "flex-shrink-0 p-1.5 rounded-lg",
                isFromTranscript
                  ? "bg-[var(--accent-primary)]/10"
                  : "bg-[var(--bg-elevated)]"
              )}>
                {isFromTranscript ? (
                  <FileAudio className="h-4 w-4 text-[var(--accent-primary)]" />
                ) : (
                  <FileText className="h-4 w-4 text-[var(--text-muted)]" />
                )}
              </span>
              <div className="flex-1 min-w-0">
                <h3
                  className={cn(
                    "font-medium truncate",
                    selectedId === note.id
                      ? "text-[var(--accent-primary)]"
                      : "text-[var(--text-primary)]"
                  )}
                >
                  {note.title || "Untitled"}
                </h3>
                <p className="text-xs text-[var(--text-muted)] truncate mt-0.5">
                  {note.content.slice(0, 60) || "No content"}
                  {note.content.length > 60 ? "..." : ""}
                </p>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-xs text-[var(--text-muted)]">
                    {formatRelativeTimeDB(note.updated_at)}
                  </span>
                  {note.tags.length > 0 && (
                    <span className={cn(
                      "text-xs px-1.5 py-0.5 rounded",
                      isFromTranscript
                        ? "bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
                        : "bg-[var(--bg-elevated)] text-[var(--text-muted)]"
                    )}>
                      {note.tags[0]}
                      {note.tags.length > 1 && ` +${note.tags.length - 1}`}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}

