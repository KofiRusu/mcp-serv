"use client"

import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Save,
  Trash2,
  MoreVertical,
  Sparkles,
  ListTodo,
  Tag,
  Link2,
  Calendar,
  Lightbulb,
  BookOpen,
  NotebookPen,
  FileText,
  Loader2,
  Check,
  X,
} from "lucide-react"
import {
  updateNote,
  deleteNote,
  classifyNote,
  extractActions,
  type Note,
  type NoteType,
  getNoteTypeIcon,
  getNoteTypeLabel,
  formatRelativeTime,
} from "@/lib/notes-api"
import { cn } from "@/lib/utils"
import { NoteActionItems } from "./note-action-items"

interface NoteEditorProps {
  note: Note
  onUpdate: (note: Note) => void
  onDelete: (noteId: string) => void
}

const NOTE_TYPES: { value: NoteType; label: string; icon: React.ReactNode }[] = [
  { value: "general", label: "General", icon: <FileText className="h-4 w-4" /> },
  { value: "meeting", label: "Meeting", icon: <Calendar className="h-4 w-4" /> },
  { value: "brainstorm", label: "Brainstorm", icon: <Lightbulb className="h-4 w-4" /> },
  { value: "lecture", label: "Lecture", icon: <BookOpen className="h-4 w-4" /> },
  { value: "journal", label: "Journal", icon: <NotebookPen className="h-4 w-4" /> },
]

export function NoteEditor({ note, onUpdate, onDelete }: NoteEditorProps) {
  const [title, setTitle] = useState(note.title)
  const [content, setContent] = useState(note.content)
  const [tags, setTags] = useState<string[]>(note.tags)
  const [noteType, setNoteType] = useState<NoteType>(note.note_type)
  const [isSaving, setIsSaving] = useState(false)
  const [isClassifying, setIsClassifying] = useState(false)
  const [isExtracting, setIsExtracting] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [showTagInput, setShowTagInput] = useState(false)
  const [newTag, setNewTag] = useState("")
  const [showActions, setShowActions] = useState(note.action_items.length > 0)

  // Reset state when note changes
  useEffect(() => {
    setTitle(note.title)
    setContent(note.content)
    setTags(note.tags)
    setNoteType(note.note_type)
    setHasChanges(false)
    setShowActions(note.action_items.length > 0)
  }, [note.id])

  // Track changes
  useEffect(() => {
    const changed =
      title !== note.title ||
      content !== note.content ||
      JSON.stringify(tags) !== JSON.stringify(note.tags) ||
      noteType !== note.note_type
    setHasChanges(changed)
  }, [title, content, tags, noteType, note])

  // Auto-save with debounce
  const saveNote = useCallback(async () => {
    if (!hasChanges) return

    try {
      setIsSaving(true)
      const updated = await updateNote(note.id, {
        title,
        content,
        tags,
        note_type: noteType,
      })
      onUpdate(updated)
      setHasChanges(false)
    } catch (error) {
      console.error("Failed to save note:", error)
    } finally {
      setIsSaving(false)
    }
  }, [note.id, title, content, tags, noteType, hasChanges, onUpdate])

  // Debounced auto-save
  useEffect(() => {
    if (!hasChanges) return

    const timer = setTimeout(() => {
      saveNote()
    }, 1500)

    return () => clearTimeout(timer)
  }, [hasChanges, saveNote])

  const handleClassify = async () => {
    try {
      setIsClassifying(true)
      const result = await classifyNote(note.id)
      setNoteType(result.classified_type)
      // Refetch note to get updated data
      const updated = await updateNote(note.id, { note_type: result.classified_type })
      onUpdate(updated)
    } catch (error) {
      console.error("Failed to classify note:", error)
    } finally {
      setIsClassifying(false)
    }
  }

  const handleExtractActions = async () => {
    try {
      setIsExtracting(true)
      const result = await extractActions(note.id)
      if (result.added_count > 0) {
        // Refetch note to get updated action items
        const updated = { ...note, action_items: [...note.action_items, ...result.actions] }
        onUpdate(updated)
        setShowActions(true)
      }
    } catch (error) {
      console.error("Failed to extract actions:", error)
    } finally {
      setIsExtracting(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this note?")) return

    try {
      await deleteNote(note.id)
      onDelete(note.id)
    } catch (error) {
      console.error("Failed to delete note:", error)
    }
  }

  const handleAddTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()])
      setNewTag("")
    }
    setShowTagInput(false)
  }

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter((t) => t !== tagToRemove))
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)] bg-[var(--bg-secondary)]">
        <div className="flex items-center gap-3">
          {/* Note Type Selector */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              >
                <span className="text-lg">{getNoteTypeIcon(noteType)}</span>
                <span className="text-sm">{getNoteTypeLabel(noteType)}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              {NOTE_TYPES.map((type) => (
                <DropdownMenuItem
                  key={type.value}
                  onClick={() => setNoteType(type.value)}
                  className={cn(
                    noteType === type.value && "bg-[var(--accent-primary)]/10"
                  )}
                >
                  {type.icon}
                  <span className="ml-2">{type.label}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <span className="text-xs text-[var(--text-muted)]">
            Updated {formatRelativeTime(note.updated_at)}
          </span>

          {hasChanges && (
            <span className="text-xs text-[var(--warning)]">Unsaved changes</span>
          )}
          {isSaving && (
            <span className="text-xs text-[var(--accent-primary)] flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              Saving...
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* AI Actions */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClassify}
            disabled={isClassifying}
            className="gap-2 text-[var(--accent-primary)]"
          >
            {isClassifying ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            <span className="hidden sm:inline">Classify</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleExtractActions}
            disabled={isExtracting}
            className="gap-2 text-[var(--accent-secondary)]"
          >
            {isExtracting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ListTodo className="h-4 w-4" />
            )}
            <span className="hidden sm:inline">Extract Tasks</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowActions(!showActions)}
            className={cn(
              "gap-2",
              showActions && "bg-[var(--accent-secondary)]/10 text-[var(--accent-secondary)]"
            )}
          >
            <ListTodo className="h-4 w-4" />
            <span className="hidden sm:inline">
              {note.action_items.length > 0 ? `${note.action_items.length} Tasks` : "Tasks"}
            </span>
          </Button>

          {/* More Actions */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setShowTagInput(true)}>
                <Tag className="h-4 w-4 mr-2" />
                Add Tag
              </DropdownMenuItem>
              <DropdownMenuItem disabled>
                <Link2 className="h-4 w-4 mr-2" />
                Link Notes
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleDelete}
                className="text-[var(--error)]"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Note
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Editor */}
        <div className="flex-1 flex flex-col p-6 overflow-y-auto">
          {/* Title */}
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Note title..."
            className="text-2xl font-semibold border-none bg-transparent p-0 h-auto focus-visible:ring-0 text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
          />

          {/* Tags */}
          <div className="flex flex-wrap items-center gap-2 mt-4">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-[var(--bg-elevated)] text-[var(--text-secondary)]"
              >
                #{tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="hover:text-[var(--error)]"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            {showTagInput ? (
              <div className="flex items-center gap-1">
                <Input
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleAddTag()
                    if (e.key === "Escape") setShowTagInput(false)
                  }}
                  placeholder="Tag name..."
                  className="h-6 w-24 text-xs"
                  autoFocus
                />
                <Button size="icon" variant="ghost" className="h-6 w-6" onClick={handleAddTag}>
                  <Check className="h-3 w-3" />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-6 w-6"
                  onClick={() => setShowTagInput(false)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ) : (
              <button
                onClick={() => setShowTagInput(true)}
                className="text-xs text-[var(--text-muted)] hover:text-[var(--accent-primary)]"
              >
                + Add tag
              </button>
            )}
          </div>

          {/* Content */}
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Start writing your note..."
            className="flex-1 mt-6 resize-none border-none bg-transparent p-0 focus-visible:ring-0 text-[var(--text-primary)] placeholder:text-[var(--text-muted)] leading-relaxed"
          />
        </div>

        {/* Action Items Panel */}
        {showActions && (
          <div className="w-80 border-l border-[var(--border-color)] bg-[var(--bg-secondary)] overflow-y-auto">
            <NoteActionItems
              note={note}
              onUpdate={onUpdate}
            />
          </div>
        )}
      </div>
    </div>
  )
}

