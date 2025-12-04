"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  ListTodo,
  MoreVertical,
  ArrowRight,
  Loader2,
  Flag,
  FileText,
  RefreshCw,
} from "lucide-react"
import {
  getAllPendingActions,
  completeAction,
  convertToTask,
  getNote,
  type ActionItem,
  type Note,
  getPriorityColor,
  formatRelativeTime,
} from "@/lib/notes-api"
import { cn } from "@/lib/utils"

interface ActionItemsPanelProps {
  onNoteSelect: (note: Note) => void
}

export function ActionItemsPanel({ onNoteSelect }: ActionItemsPanelProps) {
  const [actions, setActions] = useState<ActionItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadingId, setLoadingId] = useState<string | null>(null)

  const fetchActions = async () => {
    try {
      setIsLoading(true)
      const response = await getAllPendingActions()
      setActions(response.actions)
    } catch (error) {
      console.error("Failed to fetch actions:", error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchActions()
  }, [])

  const handleComplete = async (action: ActionItem) => {
    try {
      setLoadingId(action.id)
      await completeAction(action.source_note_id, action.id)
      setActions((prev) => prev.filter((a) => a.id !== action.id))
    } catch (error) {
      console.error("Failed to complete action:", error)
    } finally {
      setLoadingId(null)
    }
  }

  const handleConvert = async (action: ActionItem) => {
    try {
      setLoadingId(action.id)
      const result = await convertToTask(action.source_note_id, action.id)
      if (result.success) {
        setActions((prev) =>
          prev.map((a) => (a.id === action.id ? result.action : a))
        )
      }
    } catch (error) {
      console.error("Failed to convert to task:", error)
    } finally {
      setLoadingId(null)
    }
  }

  const handleOpenNote = async (action: ActionItem) => {
    try {
      const note = await getNote(action.source_note_id)
      onNoteSelect(note)
    } catch (error) {
      console.error("Failed to fetch note:", error)
    }
  }

  // Group actions by priority
  const highPriority = actions.filter((a) => a.priority === "high")
  const mediumPriority = actions.filter((a) => a.priority === "medium")
  const lowPriority = actions.filter((a) => a.priority === "low")

  return (
    <div className="flex-1 flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-[var(--border-color)] bg-[var(--bg-secondary)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-br from-[var(--accent-secondary)]/20 to-[var(--accent-primary)]/20">
              <ListTodo className="h-5 w-5 text-[var(--accent-secondary)]" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-[var(--text-primary)]">
                All Action Items
              </h2>
              <p className="text-sm text-[var(--text-muted)]">
                {actions.length} pending across all notes
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={fetchActions}
            disabled={isLoading}
          >
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-primary)]" />
          </div>
        ) : actions.length === 0 ? (
          <div className="text-center py-12">
            <div className="mx-auto w-16 h-16 rounded-2xl bg-[var(--bg-elevated)] flex items-center justify-center mb-4">
              <ListTodo className="h-8 w-8 text-[var(--text-muted)]" />
            </div>
            <h3 className="text-lg font-medium text-[var(--text-primary)]">
              All caught up!
            </h3>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              No pending action items across your notes
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* High Priority */}
            {highPriority.length > 0 && (
              <PrioritySection
                title="High Priority"
                icon={<Flag className="h-4 w-4 text-red-500" />}
                actions={highPriority}
                loadingId={loadingId}
                onComplete={handleComplete}
                onConvert={handleConvert}
                onOpenNote={handleOpenNote}
              />
            )}

            {/* Medium Priority */}
            {mediumPriority.length > 0 && (
              <PrioritySection
                title="Medium Priority"
                icon={<Flag className="h-4 w-4 text-yellow-500" />}
                actions={mediumPriority}
                loadingId={loadingId}
                onComplete={handleComplete}
                onConvert={handleConvert}
                onOpenNote={handleOpenNote}
              />
            )}

            {/* Low Priority */}
            {lowPriority.length > 0 && (
              <PrioritySection
                title="Low Priority"
                icon={<Flag className="h-4 w-4 text-blue-500" />}
                actions={lowPriority}
                loadingId={loadingId}
                onComplete={handleComplete}
                onConvert={handleConvert}
                onOpenNote={handleOpenNote}
              />
            )}
          </div>
        )}
      </div>
    </div>
  )
}

interface PrioritySectionProps {
  title: string
  icon: React.ReactNode
  actions: ActionItem[]
  loadingId: string | null
  onComplete: (action: ActionItem) => void
  onConvert: (action: ActionItem) => void
  onOpenNote: (action: ActionItem) => void
}

function PrioritySection({
  title,
  icon,
  actions,
  loadingId,
  onComplete,
  onConvert,
  onOpenNote,
}: PrioritySectionProps) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h3 className="text-sm font-medium text-[var(--text-secondary)]">
          {title}
        </h3>
        <span className="text-xs text-[var(--text-muted)]">({actions.length})</span>
      </div>
      <div className="space-y-2">
        {actions.map((action) => (
          <GlobalActionItem
            key={action.id}
            action={action}
            isLoading={loadingId === action.id}
            onComplete={() => onComplete(action)}
            onConvert={() => onConvert(action)}
            onOpenNote={() => onOpenNote(action)}
          />
        ))}
      </div>
    </div>
  )
}

interface GlobalActionItemProps {
  action: ActionItem
  isLoading: boolean
  onComplete: () => void
  onConvert: () => void
  onOpenNote: () => void
}

function GlobalActionItem({
  action,
  isLoading,
  onComplete,
  onConvert,
  onOpenNote,
}: GlobalActionItemProps) {
  return (
    <div
      className={cn(
        "group flex items-start gap-3 p-3 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] hover:border-[var(--accent-primary)]/30 transition-colors",
        isLoading && "opacity-50"
      )}
    >
      <Checkbox
        checked={false}
        onCheckedChange={onComplete}
        disabled={isLoading}
        className="mt-0.5"
      />

      <div className="flex-1 min-w-0">
        <p className="text-sm text-[var(--text-primary)]">{action.description}</p>
        <div className="flex items-center gap-3 mt-2">
          <button
            onClick={onOpenNote}
            className="inline-flex items-center gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--accent-primary)]"
          >
            <FileText className="h-3 w-3" />
            Open note
          </button>
          {action.assignee && (
            <span className="text-xs text-[var(--text-muted)]">
              @{action.assignee}
            </span>
          )}
          {action.due_date && (
            <span className="text-xs text-[var(--text-muted)]">
              Due: {action.due_date}
            </span>
          )}
          <span className="text-xs text-[var(--text-muted)]">
            {formatRelativeTime(action.created_at)}
          </span>
        </div>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 opacity-0 group-hover:opacity-100"
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <MoreVertical className="h-4 w-4" />
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={onOpenNote}>
            <FileText className="h-4 w-4 mr-2" />
            Open Note
          </DropdownMenuItem>
          {!action.linked_task_id && (
            <DropdownMenuItem onClick={onConvert}>
              <ArrowRight className="h-4 w-4 mr-2" />
              Convert to Task
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

