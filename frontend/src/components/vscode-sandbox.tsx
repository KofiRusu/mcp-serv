"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import {
  Loader2,
  RefreshCw,
  ExternalLink,
  AlertCircle,
  Maximize2,
  Minimize2,
} from "lucide-react"
import { type VSCodeStatus, checkVSCodeHealth } from "@/lib/api"
import { cn } from "@/lib/utils"

interface VSCodeSandboxProps {
  status: VSCodeStatus | null
  onRefresh?: () => void
  className?: string
}

export function VSCodeSandbox({ status, onRefresh, className }: VSCodeSandboxProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isHealthy, setIsHealthy] = useState(false)

  // Check health when status changes
  useEffect(() => {
    async function checkHealth() {
      if (!status?.running || !status?.url) {
        setIsHealthy(false)
        setIsLoading(false)
        return
      }

      setIsLoading(true)
      setLoadError(null)

      // Give code-server a moment to be ready
      await new Promise((resolve) => setTimeout(resolve, 1000))

      try {
        const result = await checkVSCodeHealth()
        setIsHealthy(result.healthy)
        
        if (!result.healthy) {
          setLoadError("code-server is not responding")
        }
      } catch {
        // Health check might fail, but iframe might still load
        setIsHealthy(true)
      } finally {
        setIsLoading(false)
      }
    }

    checkHealth()
  }, [status?.running, status?.url])

  // Handle iframe load
  const handleIframeLoad = useCallback(() => {
    setIsLoading(false)
    setLoadError(null)
  }, [])

  // Handle iframe error
  const handleIframeError = useCallback(() => {
    setIsLoading(false)
    setLoadError("Failed to load VSCode. Make sure code-server is running.")
  }, [])

  // Toggle fullscreen
  const toggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev)
  }, [])

  // Open in new tab
  const openInNewTab = useCallback(() => {
    if (status?.url) {
      window.open(status.url, "_blank")
    }
  }, [status?.url])

  // Not running state
  if (!status?.running) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center h-full bg-[var(--bg-primary)] text-center p-8",
          className
        )}
      >
        <div className="text-6xl mb-6 opacity-50">
          <svg
            viewBox="0 0 100 100"
            className="w-24 h-24"
            fill="currentColor"
          >
            <path d="M97.2 50L75 72.2V27.8L97.2 50zM2.8 50L25 27.8v44.4L2.8 50zM50 2.8l22.2 22.2H27.8L50 2.8zM50 97.2L27.8 75h44.4L50 97.2z" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-2">
          VSCode Sandbox
        </h2>
        <p className="text-[var(--text-secondary)] max-w-md mb-6">
          Select a project and click Start to launch the VSCode editor.
          You'll get a full IDE experience with file explorer, terminal, and extensions.
        </p>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={onRefresh}
            className="border-[var(--border-color)]"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh Status
          </Button>
        </div>
      </div>
    )
  }

  // Loading state
  if (isLoading) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center h-full bg-[var(--bg-primary)]",
          className
        )}
      >
        <Loader2 className="h-12 w-12 animate-spin text-[var(--accent-primary)] mb-4" />
        <p className="text-[var(--text-secondary)]">Starting VSCode...</p>
        <p className="text-[var(--text-muted)] text-sm mt-2">
          This may take a few seconds
        </p>
      </div>
    )
  }

  // Error state
  if (loadError) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center h-full bg-[var(--bg-primary)] text-center p-8",
          className
        )}
      >
        <AlertCircle className="h-12 w-12 text-[var(--error)] mb-4" />
        <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
          Connection Error
        </h3>
        <p className="text-[var(--text-secondary)] max-w-md mb-6">{loadError}</p>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={onRefresh}
            className="border-[var(--border-color)]"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
          {status?.url && (
            <Button variant="outline" onClick={openInNewTab}>
              <ExternalLink className="h-4 w-4 mr-2" />
              Open in New Tab
            </Button>
          )}
        </div>
      </div>
    )
  }

  // VSCode running - show launch UI since iframe embedding has limitations
  return (
    <div
      className={cn(
        "relative h-full w-full bg-[var(--bg-primary)]",
        isFullscreen && "fixed inset-0 z-50",
        className
      )}
    >
      {/* Toolbar */}
      <div className="absolute top-2 right-2 z-10 flex gap-1">
        <Button
          size="icon"
          variant="ghost"
          onClick={toggleFullscreen}
          className="h-8 w-8 bg-[var(--bg-secondary)]/80 backdrop-blur-sm hover:bg-[var(--bg-tertiary)]"
          title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
        >
          {isFullscreen ? (
            <Minimize2 className="h-4 w-4" />
          ) : (
            <Maximize2 className="h-4 w-4" />
          )}
        </Button>
        <Button
          size="icon"
          variant="ghost"
          onClick={openInNewTab}
          className="h-8 w-8 bg-[var(--bg-secondary)]/80 backdrop-blur-sm hover:bg-[var(--bg-tertiary)]"
          title="Open in new tab"
        >
          <ExternalLink className="h-4 w-4" />
        </Button>
        <Button
          size="icon"
          variant="ghost"
          onClick={onRefresh}
          className="h-8 w-8 bg-[var(--bg-secondary)]/80 backdrop-blur-sm hover:bg-[var(--bg-tertiary)]"
          title="Refresh"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Workspace indicator */}
      {status?.workspace && (
        <div className="absolute bottom-2 left-2 z-10 px-2 py-1 text-xs bg-[var(--bg-secondary)]/80 backdrop-blur-sm rounded text-[var(--text-muted)]">
          {status.workspace}
        </div>
      )}

      {/* VSCode launch panel - more reliable than iframe embedding */}
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="w-20 h-20 mb-6 rounded-2xl bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] flex items-center justify-center">
          <svg viewBox="0 0 100 100" className="w-12 h-12" fill="white">
            <path d="M97.2 50L75 72.2V27.8L97.2 50zM2.8 50L25 27.8v44.4L2.8 50zM50 2.8l22.2 22.2H27.8L50 2.8zM50 97.2L27.8 75h44.4L50 97.2z" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-2">
          VSCode is Ready
        </h2>
        <p className="text-[var(--text-secondary)] max-w-md mb-6">
          code-server is running on port {status.port}. Click below to open the full VSCode experience in a new tab.
        </p>
        <div className="flex gap-3 mb-4">
          <Button
            onClick={openInNewTab}
            className="bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-white hover:opacity-90"
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Open VSCode
          </Button>
          <Button
            variant="outline"
            onClick={onRefresh}
            className="border-[var(--border-color)]"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
        <p className="text-[var(--text-muted)] text-xs">
          Workspace: {status.workspace}
        </p>
      </div>
    </div>
  )
}

