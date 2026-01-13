"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Plus,
  MoreVertical,
  Trash2,
  ArrowRight,
  Loader2,
  User,
  Calendar,
  Flag,
} from "lucide-react"
import {
  createAction,
  updateAction,
  deleteAction,
  completeAction,
  convertToTask,
  type Note,
  type ActionItem,
  type ActionPriority,
  getPriorityColor,
} from "@/lib/notes-api"
import { cn } from "@/lib/utils"

interface NoteActionItemsProps {
  note: Note
  onUpdate: (note: Note) => void
}

export function NoteActionItems({ note, onUpdate }: NoteActionItemsProps) {
  const [isAdding, setIsAdding] = useState(false)
  const [newDescription, setNewDescription] = useState("")
  const [loadingId, setLoadingId] = useState<string | null>(null)

  const handleAddAction = async () => {
    if (!newDescription.trim()) return

    try {
      setIsAdding(true)
      const action = await createAction(note.id, {
        text: newDescription.trim(),
      })
      onUpdate({
        ...note,
        action_items: [...(note.action_items || []), action],
      })
      setNewDescription("")
    } catch (error) {
      console.error("Failed to add action:", error)
    } finally {
      setIsAdding(false)
    }
  }

  const handleToggleComplete = async (action: ActionItem) => {
    try {
      setLoadingId(action.id)
      if (action.completed) {
        // Reopen
        const updated = await updateAction(action.id, { completed: false })
        onUpdate({
          ...note,
          action_items: (note.action_items || []).map((a) =>
            a.id === action.id ? updated : a
          ),
        })
      } else {
        // Complete
        const result = await completeAction(action.id)
        onUpdate({
          ...note,
          action_items: (note.action_items || []).map((a) =>
            a.id === action.id ? result : a
          ),
        })
      }
    } catch (error) {
      console.error("Failed to toggle action:", error)
    } finally {
      setLoadingId(null)
    }
  }

  const handleDelete = async (actionId: string) => {
    try {
      setLoadingId(actionId)
      await deleteAction(actionId)
      onUpdate({
        ...note,
        action_items: (note.action_items || []).filter((a) => a.id !== actionId),
      })
    } catch (error) {
      console.error("Failed to delete action:", error)
    } finally {
      setLoadingId(null)
    }
  }

  const handleConvertToTask = async (action: ActionItem) => {
    try {
      setLoadingId(action.id)
      const result = await convertToTask(action.id)
      if (result.success) {
        // Remove from action items list after conversion
        onUpdate({
          ...note,
          action_items: (note.action_items || []).filter((a) => a.id !== action.id),
        })
      }
    } catch (error) {
      console.error("Failed to convert to task:", error)
    } finally {
      setLoadingId(null)
    }
  }

  const handleSetPriority = async (action: ActionItem, priority: ActionPriority) => {
    try {
      setLoadingId(action.id)
      const updated = await updateAction(action.id, { priority })
      onUpdate({
        ...note,
        action_items: (note.action_items || []).map((a) =>
          a.id === action.id ? updated : a
        ),
      })
    } catch (error) {
      console.error("Failed to update priority:", error)
    } finally {
      setLoadingId(null)
    }
  }

  const pendingActions = (note.action_items || []).filter((a) => !a.completed)
  const completedActions = (note.action_items || []).filter((a) => a.completed)

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-color)]">
        <h3 className="font-semibold text-[var(--text-primary)]">Action Items</h3>
        <p className="text-xs text-[var(--text-muted)] mt-1">
          {pendingActions.length} pending, {completedActions.length} completed
        </p>
      </div>

      {/* Add New */}
      <div className="p-4 border-b border-[var(--border-color)]">
        <div className="flex gap-2">
          <Input
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAddAction()
            }}
            placeholder="Add action item..."
            className="flex-1 text-sm"
            disabled={isAdding}
          />
          <Button
            size="icon"
            onClick={handleAddAction}
            disabled={isAdding || !newDescription.trim()}
            className="bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/80"
          >
            {isAdding ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Action Items List */}
      <div className="flex-1 overflow-y-auto">
        {/* Pending */}
        {pendingActions.length > 0 && (
          <div className="p-2">
            {pendingActions.map((action) => (
              <ActionItemRow
                key={action.id}
                action={action}
                isLoading={loadingId === action.id}
                onToggle={() => handleToggleComplete(action)}
                onDelete={() => handleDelete(action.id)}
                onConvert={() => handleConvertToTask(action)}
                onSetPriority={(priority) => handleSetPriority(action, priority)}
              />
            ))}
          </div>
        )}

        {/* Completed */}
        {completedActions.length > 0 && (
          <div className="p-2 border-t border-[var(--border-color)]">
            <p className="text-xs text-[var(--text-muted)] px-2 py-1">Completed</p>
            {completedActions.map((action) => (
              <ActionItemRow
                key={action.id}
                action={action}
                isLoading={loadingId === action.id}
                onToggle={() => handleToggleComplete(action)}
                onDelete={() => handleDelete(action.id)}
                onConvert={() => handleConvertToTask(action)}
                onSetPriority={(priority) => handleSetPriority(action, priority)}
              />
            ))}
          </div>
        )}

        {(note.action_items || []).length === 0 && (
          <div className="p-8 text-center text-[var(--text-muted)]">
            <p className="text-sm">No action items yet</p>
            <p className="text-xs mt-1">
              Add items manually or use AI to extract them
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

interface ActionItemRowProps {
  action: ActionItem
  isLoading: boolean
  onToggle: () => void
  onDelete: () => void
  onConvert: () => void
  onSetPriority: (priority: ActionPriority) => void
}

function ActionItemRow({
  action,
  isLoading,
  onToggle,
  onDelete,
  onConvert,
  onSetPriority,
}: ActionItemRowProps) {
  const isCompleted = action.completed

  return (
    <div
      className={cn(
        "group flex items-start gap-2 p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors",
        isLoading && "opacity-50"
      )}
    >
      <Checkbox
        checked={isCompleted}
        onCheckedChange={onToggle}
        disabled={isLoading}
        className="mt-0.5"
      />

      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-sm",
            isCompleted
              ? "text-[var(--text-muted)] line-through"
              : "text-[var(--text-primary)]"
          )}
        >
          {action.text}
        </p>

        <div className="flex items-center gap-2 mt-1">
          {action.dueDate && (
            <span className="inline-flex items-center gap-1 text-xs text-[var(--text-muted)]">
              <Calendar className="h-3 w-3" />
              {action.dueDate}
            </span>
          )}
          <span
            className={cn(
              "inline-flex items-center gap-1 text-xs",
              getPriorityColor(action.priority)
            )}
          >
            <Flag className="h-3 w-3" />
            {action.priority}
          </span>
        </div>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 group-hover:opacity-100"
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <MoreVertical className="h-3 w-3" />
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => onSetPriority("low")}>
            <Flag className="h-4 w-4 mr-2 text-blue-500" />
            Low Priority
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => onSetPriority("medium")}>
            <Flag className="h-4 w-4 mr-2 text-yellow-500" />
            Medium Priority
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => onSetPriority("high")}>
            <Flag className="h-4 w-4 mr-2 text-red-500" />
            High Priority
          </DropdownMenuItem>
          <DropdownMenuItem onClick={onConvert}>
            <ArrowRight className="h-4 w-4 mr-2" />
            Convert to Task
          </DropdownMenuItem>
          <DropdownMenuItem onClick={onDelete} className="text-[var(--error)]">
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

