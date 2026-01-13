"use client"

import { useState, useEffect, useCallback } from "react"
import { NoteList } from "@/components/notes/note-list"
import { NoteEditor } from "@/components/notes/note-editor"
import { ActionItemsPanel } from "@/components/notes/action-items-panel"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Plus,
  Search,
  FileText,
  Calendar,
  Lightbulb,
  BookOpen,
  NotebookPen,
  ListTodo,
  ArrowLeft,
  Sparkles,
  Home,
} from "lucide-react"
import Link from "next/link"
import {
  getNotes,
  createNote,
  type Note,
  type NoteType,
  type NoteStats,
} from "@/lib/notes-api"
import { cn } from "@/lib/utils"

const NOTE_TYPE_FILTERS: { value: NoteType | "all"; label: string; icon: React.ReactNode }[] = [
  { value: "all", label: "All Notes", icon: <FileText className="h-4 w-4" /> },
  { value: "meeting", label: "Meetings", icon: <Calendar className="h-4 w-4" /> },
  { value: "brainstorm", label: "Brainstorms", icon: <Lightbulb className="h-4 w-4" /> },
  { value: "lecture", label: "Lectures", icon: <BookOpen className="h-4 w-4" /> },
  { value: "journal", label: "Journal", icon: <NotebookPen className="h-4 w-4" /> },
]

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([])
  const [stats, setStats] = useState<NoteStats | null>(null)
  const [selectedNote, setSelectedNote] = useState<Note | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [typeFilter, setTypeFilter] = useState<NoteType | "all">("all")
  const [showActionPanel, setShowActionPanel] = useState(false)
  const [isCreating, setIsCreating] = useState(false)

  const fetchNotes = useCallback(async () => {
    try {
      setIsLoading(true)
      const options: Parameters<typeof getNotes>[0] = {}
      if (searchQuery) options.search = searchQuery
      if (typeFilter !== "all") options.note_type = typeFilter

      const response = await getNotes(options)
      setNotes(response.notes)
      setStats(response.stats)
    } catch (error) {
      console.error("Failed to fetch notes:", error)
    } finally {
      setIsLoading(false)
    }
  }, [searchQuery, typeFilter])

  useEffect(() => {
    fetchNotes()
  }, [fetchNotes])

  const handleCreateNote = async () => {
    try {
      setIsCreating(true)
      const note = await createNote({
        title: "Untitled Note",
        content: "",
        auto_classify: false,
      })
      setNotes((prev) => [note, ...prev])
      setSelectedNote(note)
    } catch (error) {
      console.error("Failed to create note:", error)
    } finally {
      setIsCreating(false)
    }
  }

  const handleNoteSelect = (note: Note) => {
    setSelectedNote(note)
  }

  const handleNoteUpdate = (updatedNote: Note) => {
    setNotes((prev) =>
      prev.map((n) => (n.id === updatedNote.id ? updatedNote : n))
    )
    setSelectedNote(updatedNote)
  }

  const handleNoteDelete = (noteId: string) => {
    setNotes((prev) => prev.filter((n) => n.id !== noteId))
    if (selectedNote?.id === noteId) {
      setSelectedNote(null)
    }
  }

  const handleBack = () => {
    setSelectedNote(null)
  }

  return (
    <div className="flex h-screen bg-[var(--bg-primary)]">
      {/* Sidebar */}
      <aside className="w-72 border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-[var(--border-color)]">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Link
                href="/"
                className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors"
                title="Go to Home"
              >
                <Home className="h-5 w-5 text-[var(--text-muted)] hover:text-[var(--accent-primary)]" />
              </Link>
              <div className="p-2 rounded-lg bg-gradient-to-br from-[var(--accent-primary)]/20 to-[var(--accent-secondary)]/20">
                <Sparkles className="h-5 w-5 text-[var(--accent-primary)]" />
              </div>
              <div>
                <h1 className="font-semibold text-[var(--text-primary)]">Notes</h1>
                <p className="text-xs text-[var(--text-muted)]">
                  {stats?.total_notes ?? 0} notes
                </p>
              </div>
            </div>
            <Button
              size="icon"
              variant="ghost"
              onClick={handleCreateNote}
              disabled={isCreating}
              className="hover:bg-[var(--bg-tertiary)]"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)]" />
            <Input
              placeholder="Search notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-[var(--bg-tertiary)] border-[var(--border-color)]"
            />
          </div>
        </div>

        {/* Type Filters */}
        <div className="p-2 border-b border-[var(--border-color)]">
          {NOTE_TYPE_FILTERS.map((filter) => (
            <button
              key={filter.value}
              onClick={() => setTypeFilter(filter.value)}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors",
                typeFilter === filter.value
                  ? "bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
              )}
            >
              {filter.icon}
              <span>{filter.label}</span>
              {filter.value !== "all" && stats?.by_type && (
                <span className="ml-auto text-xs text-[var(--text-muted)]">
                  {stats.by_type[filter.value] ?? 0}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Actions Summary */}
        <button
          onClick={() => setShowActionPanel(!showActionPanel)}
          className={cn(
            "mx-2 mt-2 flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors",
            showActionPanel
              ? "bg-[var(--accent-secondary)]/10 text-[var(--accent-secondary)]"
              : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
          )}
        >
          <ListTodo className="h-4 w-4" />
          <span>Action Items</span>
          {stats && (stats.pending_actions ?? 0) > 0 && (
            <span className="ml-auto px-2 py-0.5 rounded-full text-xs bg-[var(--accent-secondary)]/20 text-[var(--accent-secondary)]">
              {stats.pending_actions}
            </span>
          )}
        </button>

        {/* Notes List */}
        <div className="flex-1 overflow-y-auto">
          <NoteList
            notes={notes}
            selectedId={selectedNote?.id}
            onSelect={handleNoteSelect}
            isLoading={isLoading}
          />
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        {selectedNote ? (
          <>
            {/* Back button for mobile */}
            <div className="md:hidden p-2 border-b border-[var(--border-color)]">
              <Button variant="ghost" size="sm" onClick={handleBack}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to list
              </Button>
            </div>
            <NoteEditor
              note={selectedNote}
              onUpdate={handleNoteUpdate}
              onDelete={handleNoteDelete}
            />
          </>
        ) : showActionPanel ? (
          <ActionItemsPanel onNoteSelect={handleNoteSelect} />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4">
              <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--accent-primary)]/20 to-[var(--accent-secondary)]/20 flex items-center justify-center">
                <FileText className="h-8 w-8 text-[var(--accent-primary)]" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-[var(--text-primary)]">
                  Select a note
                </h2>
                <p className="text-sm text-[var(--text-muted)] mt-1">
                  Choose a note from the sidebar or create a new one
                </p>
              </div>
              <Button
                onClick={handleCreateNote}
                disabled={isCreating}
                className="bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-[var(--bg-primary)]"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create New Note
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

