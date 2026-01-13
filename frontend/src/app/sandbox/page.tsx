"use client"

import { useState, useCallback } from "react"
import { ProjectSelector } from "@/components/project-selector"
import { VSCodeSandbox } from "@/components/vscode-sandbox"
import { AiChat } from "@/components/ai-chat"
import { Button } from "@/components/ui/button"
import {
  Zap,
  Sparkles,
  PanelRightClose,
  PanelRightOpen,
  Home,
  Terminal,
  Code2,
} from "lucide-react"
import { type VSCodeStatus, getVSCodeStatus } from "@/lib/api"
import { cn } from "@/lib/utils"
import Link from "next/link"

export default function SandboxPage() {
  const [status, setStatus] = useState<VSCodeStatus | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Handle status changes from project selector
  const handleStatusChange = useCallback((newStatus: VSCodeStatus) => {
    setStatus(newStatus)
    setError(null)
  }, [])

  // Handle errors
  const handleError = useCallback((msg: string) => {
    setError(msg)
  }, [])

  // Refresh status
  const handleRefresh = useCallback(async () => {
    try {
      const newStatus = await getVSCodeStatus()
      setStatus(newStatus)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh")
    }
  }, [])

  return (
    <div className="flex h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] overflow-hidden">
      {/* Main Content */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <header className="flex h-14 items-center justify-between border-b border-[var(--border-color)] bg-[var(--bg-secondary)] px-4 flex-shrink-0">
          <div className="flex items-center gap-4">
            {/* Logo and Navigation */}
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--accent-primary)] transition-colors"
              >
                <Home className="h-4 w-4" />
              </Link>
              <div className="w-px h-5 bg-[var(--border-color)]" />
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-[var(--accent-primary)]" />
                <span className="font-bold bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] bg-clip-text text-transparent">
                  ChatOS
                </span>
                <span className="text-[var(--text-muted)] text-sm">/</span>
                <div className="flex items-center gap-1.5 text-[var(--text-primary)]">
                  <Code2 className="h-4 w-4" />
                  <span className="font-medium">Sandbox</span>
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className="w-px h-5 bg-[var(--border-color)] hidden md:block" />

            {/* Project Selector */}
            <div className="hidden md:block">
              <ProjectSelector
                onStatusChange={handleStatusChange}
                onError={handleError}
              />
            </div>
          </div>

          {/* Right Side Controls */}
          <div className="flex items-center gap-2">
            {/* Quick Links */}
            <Link href="/">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-1.5 text-[var(--text-secondary)] hover:text-[var(--accent-primary)]"
              >
                <Terminal className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Editor</span>
              </Button>
            </Link>

            <div className="w-px h-6 bg-[var(--border-color)] mx-1" />

            {/* AI Chat Toggle */}
            <Button
              variant={chatOpen ? "default" : "ghost"}
              size="sm"
              onClick={() => setChatOpen(!chatOpen)}
              className={cn(
                "h-8 gap-1.5",
                chatOpen
                  ? "bg-[var(--accent-primary)] text-[var(--bg-primary)] hover:bg-[var(--accent-primary)]/90"
                  : "text-[var(--text-secondary)] hover:text-[var(--accent-primary)] hover:bg-[var(--bg-tertiary)]"
              )}
            >
              {chatOpen ? (
                <PanelRightClose className="h-3.5 w-3.5" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              <span className="hidden sm:inline">AI Assist</span>
            </Button>
          </div>
        </header>

        {/* Mobile Project Selector */}
        <div className="md:hidden border-b border-[var(--border-color)] bg-[var(--bg-secondary)] px-4 py-2">
          <ProjectSelector
            onStatusChange={handleStatusChange}
            onError={handleError}
          />
        </div>

        {/* Main Area */}
        <div className="flex flex-1 overflow-hidden">
          {/* VSCode Sandbox */}
          <div className="flex-1 min-w-0">
            <VSCodeSandbox
              status={status}
              onRefresh={handleRefresh}
              className="h-full"
            />
          </div>

          {/* AI Chat Panel */}
          {chatOpen && (
            <div className="w-[360px] border-l border-[var(--border-color)] bg-[var(--bg-secondary)] flex-shrink-0">
              <AiChat
                currentFile={status?.workspace ? `${status.workspace}/...` : undefined}
                currentFileContent={undefined}
                onApplyCode={() => {
                  // In VSCode mode, code is applied manually
                  // Could add clipboard copy functionality here
                }}
              />
            </div>
          )}
        </div>

        {/* Error Banner */}
        {error && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-[var(--error)]/90 text-white px-4 py-2 rounded-lg shadow-lg text-sm flex items-center gap-2">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="hover:bg-white/20 rounded p-1"
            >
              ×
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

