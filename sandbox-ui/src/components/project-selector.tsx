"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import {
  Folder,
  GitBranch,
  Play,
  Square,
  Loader2,
  RefreshCw,
  AlertCircle,
} from "lucide-react"
import {
  getProjects,
  getVSCodeStatus,
  startVSCode,
  stopVSCode,
  type ProjectInfo,
  type VSCodeStatus,
} from "@/lib/api"
import { cn } from "@/lib/utils"

interface ProjectSelectorProps {
  onStatusChange?: (status: VSCodeStatus) => void
  onError?: (error: string) => void
}

export function ProjectSelector({ onStatusChange, onError }: ProjectSelectorProps) {
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [selectedProject, setSelectedProject] = useState<string | null>(null)
  const [status, setStatus] = useState<VSCodeStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch projects and status on mount
  useEffect(() => {
    async function fetchData() {
      setIsLoading(true)
      setError(null)
      
      try {
        const [projectsData, statusData] = await Promise.all([
          getProjects(),
          getVSCodeStatus(),
        ])
        
        setProjects(Array.isArray(projectsData) ? projectsData : [])
        setStatus(statusData || { running: false })
        onStatusChange?.(statusData)
        
        // Set selected project based on current workspace or first project
        if (statusData.workspace) {
          setSelectedProject(statusData.workspace)
        } else if (projectsData.length > 0) {
          setSelectedProject(projectsData[0].path)
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to load projects'
        setError(msg)
        onError?.(msg)
      } finally {
        setIsLoading(false)
      }
    }
    
    fetchData()
  }, [onStatusChange, onError])

  // Handle start VSCode
  const handleStart = async () => {
    if (!selectedProject) return
    
    setIsStarting(true)
    setError(null)
    
    try {
      const newStatus = await startVSCode({ workspace: selectedProject })
      setStatus(newStatus)
      onStatusChange?.(newStatus)
      
      if (newStatus.error) {
        setError(newStatus.error)
        onError?.(newStatus.error)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to start VSCode'
      setError(msg)
      onError?.(msg)
    } finally {
      setIsStarting(false)
    }
  }

  // Handle stop VSCode
  const handleStop = async () => {
    setIsStopping(true)
    setError(null)
    
    try {
      await stopVSCode()
      const newStatus = await getVSCodeStatus()
      setStatus(newStatus)
      onStatusChange?.(newStatus)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to stop VSCode'
      setError(msg)
      onError?.(msg)
    } finally {
      setIsStopping(false)
    }
  }

  // Refresh status
  const handleRefresh = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const [projectsData, statusData] = await Promise.all([
        getProjects(),
        getVSCodeStatus(),
      ])
      
      setProjects(projectsData)
      setStatus(statusData)
      onStatusChange?.(statusData)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to refresh'
      setError(msg)
      onError?.(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const isRunning = status?.running ?? false

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Project Selector */}
      <div className="flex items-center gap-2">
        <Folder className="h-4 w-4 text-[var(--text-muted)]" />
        <Select
          value={selectedProject || ""}
          onValueChange={setSelectedProject}
          disabled={isLoading || isRunning}
        >
          <SelectTrigger className="w-[240px] bg-[var(--bg-tertiary)] border-[var(--border-color)]">
            <SelectValue placeholder="Select project..." />
          </SelectTrigger>
          <SelectContent className="bg-[var(--bg-secondary)] border-[var(--border-color)]">
            {(projects || []).map((project) => (
              <SelectItem
                key={project.path}
                value={project.path}
                className="cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <span className="truncate max-w-[180px]">{project.name}</span>
                  {project.is_git && (
                    <GitBranch className="h-3 w-3 text-[var(--accent-primary)]" />
                  )}
                  {!project.exists && (
                    <Badge variant="outline" className="text-[10px] px-1 py-0 text-[var(--warning)]">
                      new
                    </Badge>
                  )}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Status Badge */}
      <Badge
        variant={isRunning ? "default" : "outline"}
        className={cn(
          "font-normal",
          isRunning
            ? "bg-[var(--success)]/20 text-[var(--success)] border-[var(--success)]/50"
            : "text-[var(--text-muted)]"
        )}
      >
        <span
          className={cn(
            "w-2 h-2 rounded-full mr-1.5",
            isRunning ? "bg-[var(--success)]" : "bg-[var(--text-muted)]"
          )}
        />
        {isRunning ? "Running" : "Stopped"}
      </Badge>

      {/* Control Buttons */}
      <div className="flex items-center gap-1">
        {!isRunning ? (
          <Button
            size="sm"
            onClick={handleStart}
            disabled={!selectedProject || isLoading || isStarting}
            className="bg-[var(--accent-primary)] text-[var(--bg-primary)] hover:bg-[var(--accent-primary)]/90"
          >
            {isStarting ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Play className="h-4 w-4 mr-1" />
            )}
            Start
          </Button>
        ) : (
          <Button
            size="sm"
            variant="outline"
            onClick={handleStop}
            disabled={isStopping}
            className="border-[var(--error)] text-[var(--error)] hover:bg-[var(--error)]/10"
          >
            {isStopping ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Square className="h-4 w-4 mr-1" />
            )}
            Stop
          </Button>
        )}

        <Button
          size="icon"
          variant="ghost"
          onClick={handleRefresh}
          disabled={isLoading}
          className="h-8 w-8 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
        </Button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="flex items-center gap-1 text-[var(--error)] text-xs">
          <AlertCircle className="h-3 w-3" />
          <span className="max-w-[200px] truncate">{error}</span>
        </div>
      )}
    </div>
  )
}

