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
  Tag,
  Loader2,
  Check,
  X,
  MessageSquare,
  FileAudio,
  ListChecks,
  Copy,
  CheckCircle2,
  ListTodo,
} from "lucide-react"
import {
  updateNoteDB,
  deleteNoteDB,
  createTasksFromNote,
  getTasksForNote,
  type NoteDB,
  type TaskInfo,
  formatRelativeTimeDB,
  parseActionItems,
  parseSummary,
  isTranscriptNote,
} from "@/lib/notes-db-api"
import { cn } from "@/lib/utils"

interface NoteDBEditorProps {
  note: NoteDB
  onUpdate: (note: NoteDB) => void
  onDelete: (noteId: number) => void
  onSendToChat?: (content: string) => void
}

export function NoteDBEditor({ note, onUpdate, onDelete, onSendToChat }: NoteDBEditorProps) {
  const [title, setTitle] = useState(note.title)
  const [content, setContent] = useState(note.content)
  const [tags, setTags] = useState<string[]>(note.tags)
  const [isSaving, setIsSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [showTagInput, setShowTagInput] = useState(false)
  const [newTag, setNewTag] = useState("")
  const [copiedSummary, setCopiedSummary] = useState(false)
  
  // Task creation state
  const [isCreatingTasks, setIsCreatingTasks] = useState(false)
  const [tasks, setTasks] = useState<TaskInfo[]>([])
  const [tasksLoaded, setTasksLoaded] = useState(false)

  // Parse summary and action items for transcript notes
  const isFromTranscript = isTranscriptNote(note)
  const summary = isFromTranscript ? parseSummary(note.content) : null
  const actionItems = isFromTranscript ? parseActionItems(note.content) : []
  const hasActionItems = actionItems.length > 0

  // Reset state when note changes
  useEffect(() => {
    setTitle(note.title)
    setContent(note.content)
    setTags(note.tags)
    setHasChanges(false)
    setTasksLoaded(false)
    setTasks([])
  }, [note.id])

  // Load existing tasks for this note
  useEffect(() => {
    if (hasActionItems && !tasksLoaded) {
      getTasksForNote(note.id)
        .then((response) => {
          setTasks(response.tasks)
          setTasksLoaded(true)
        })
        .catch((error) => {
          console.error("Failed to load tasks:", error)
          setTasksLoaded(true)
        })
    }
  }, [note.id, hasActionItems, tasksLoaded])

  // Track changes
  useEffect(() => {
    const changed =
      title !== note.title ||
      content !== note.content ||
      JSON.stringify(tags) !== JSON.stringify(note.tags)
    setHasChanges(changed)
  }, [title, content, tags, note])

  // Auto-save with debounce
  const saveNote = useCallback(async () => {
    if (!hasChanges) return

    try {
      setIsSaving(true)
      const updated = await updateNoteDB(note.id, {
        title,
        content,
        tags,
      })
      onUpdate(updated)
      setHasChanges(false)
    } catch (error) {
      console.error("Failed to save note:", error)
    } finally {
      setIsSaving(false)
    }
  }, [note.id, title, content, tags, hasChanges, onUpdate])

  // Debounced auto-save
  useEffect(() => {
    if (!hasChanges) return

    const timer = setTimeout(() => {
      saveNote()
    }, 1500)

    return () => clearTimeout(timer)
  }, [hasChanges, saveNote])

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this note?")) return

    try {
      await deleteNoteDB(note.id)
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

  const handleSendToChat = () => {
    if (onSendToChat) {
      const textToSend = isFromTranscript && summary
        ? `**Summary:** ${summary}\n\n**Action Items:**\n${actionItems.map(item => `- ${item}`).join('\n')}`
        : content
      onSendToChat(textToSend)
    }
  }

  const handleCreateTasks = async () => {
    if (tasks.length > 0) {
      // Tasks already exist
      return
    }

    try {
      setIsCreatingTasks(true)
      const response = await createTasksFromNote(note.id)
      setTasks(response.tasks)
      
      if (response.tasks_created > 0) {
        // Show success feedback
        alert(`Created ${response.tasks_created} task(s) from action items!`)
      } else if (response.already_exists) {
        alert("Tasks have already been created for this note.")
      } else {
        alert("No action items found to create tasks from.")
      }
    } catch (error) {
      console.error("Failed to create tasks:", error)
      alert("Failed to create tasks. Please try again.")
    } finally {
      setIsCreatingTasks(false)
    }
  }

  const handleCopySummary = async () => {
    if (!summary) return
    
    const textToCopy = `Summary: ${summary}\n\nAction Items:\n${actionItems.map(item => `- ${item}`).join('\n')}`
    await navigator.clipboard.writeText(textToCopy)
    setCopiedSummary(true)
    setTimeout(() => setCopiedSummary(false), 2000)
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)] bg-[var(--bg-secondary)]">
        <div className="flex items-center gap-3">
          {/* Note Type Indicator */}
          <div className={cn(
            "p-2 rounded-lg",
            isFromTranscript
              ? "bg-[var(--accent-primary)]/10"
              : "bg-[var(--bg-tertiary)]"
          )}>
            {isFromTranscript ? (
              <FileAudio className="h-4 w-4 text-[var(--accent-primary)]" />
            ) : (
              <Tag className="h-4 w-4 text-[var(--text-muted)]" />
            )}
          </div>

          <span className="text-xs text-[var(--text-muted)]">
            Updated {formatRelativeTimeDB(note.updated_at)}
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
          {/* Create Tasks (for notes with action items) */}
          {hasActionItems && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCreateTasks}
              disabled={isCreatingTasks || tasks.length > 0}
              className={cn(
                "gap-2",
                tasks.length > 0
                  ? "text-green-500"
                  : "text-[var(--accent-secondary)]"
              )}
            >
              {isCreatingTasks ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : tasks.length > 0 ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <ListTodo className="h-4 w-4" />
              )}
              <span className="hidden sm:inline">
                {tasks.length > 0 ? `${tasks.length} Tasks` : "Create Tasks"}
              </span>
            </Button>
          )}

          {/* Send to Chat */}
          {onSendToChat && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSendToChat}
              className="gap-2 text-[var(--accent-primary)]"
            >
              <MessageSquare className="h-4 w-4" />
              <span className="hidden sm:inline">Send to Chat</span>
            </Button>
          )}

          {/* Copy Summary (for transcript notes) */}
          {isFromTranscript && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopySummary}
              className="gap-2"
            >
              {copiedSummary ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
              <span className="hidden sm:inline">
                {copiedSummary ? "Copied!" : "Copy"}
              </span>
            </Button>
          )}

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
                className={cn(
                  "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs",
                  tag === 'auto' || tag === 'meeting'
                    ? "bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
                    : "bg-[var(--bg-elevated)] text-[var(--text-secondary)]"
                )}
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

          {/* Summary Card (for transcript notes) */}
          {isFromTranscript && summary && (
            <div className="mt-6 p-4 rounded-xl bg-gradient-to-br from-[var(--accent-primary)]/5 to-[var(--accent-secondary)]/5 border border-[var(--accent-primary)]/20">
              <h3 className="text-sm font-semibold text-[var(--accent-primary)] mb-2 flex items-center gap-2">
                <FileAudio className="h-4 w-4" />
                AI Summary
              </h3>
              <p className="text-sm text-[var(--text-primary)] leading-relaxed">
                {summary}
              </p>
              
              {actionItems.length > 0 && (
                <div className="mt-4 pt-4 border-t border-[var(--accent-primary)]/20">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold text-[var(--accent-secondary)] flex items-center gap-2">
                      <ListChecks className="h-4 w-4" />
                      Action Items
                    </h4>
                    {tasks.length > 0 && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-500">
                        {tasks.length} tasks created
                      </span>
                    )}
                  </div>
                  <ul className="space-y-2">
                    {actionItems.map((item, index) => {
                      const matchingTask = tasks.find(t => t.title === item)
                      return (
                        <li
                          key={index}
                          className="flex items-start gap-2 text-sm text-[var(--text-primary)]"
                        >
                          <span className={cn(
                            "w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5",
                            matchingTask
                              ? "bg-green-500/20 text-green-500"
                              : "bg-[var(--accent-secondary)]/20 text-[var(--accent-secondary)]"
                          )}>
                            {matchingTask ? <Check className="h-3 w-3" /> : index + 1}
                          </span>
                          <span className={cn(matchingTask && "line-through opacity-70")}>
                            {item}
                          </span>
                          {matchingTask && (
                            <span className="text-xs text-[var(--text-muted)] ml-auto">
                              {matchingTask.status}
                            </span>
                          )}
                        </li>
                      )
                    })}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Content */}
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Start writing your note..."
            className={cn(
              "flex-1 mt-6 resize-none border-none bg-transparent p-0 focus-visible:ring-0 text-[var(--text-primary)] placeholder:text-[var(--text-muted)] leading-relaxed",
              isFromTranscript && "min-h-[100px]"
            )}
          />
        </div>
      </div>
    </div>
  )
}

