"use client"

import { useState, useCallback, useEffect } from "react"
import { FileTree } from "./file-tree"
import { CodeEditor } from "./code-editor"
import { AiChat } from "./ai-chat"
import { OutputPanel } from "./output-panel"
import { Button } from "@/components/ui/button"
import { 
  PanelLeftClose, 
  PanelLeftOpen, 
  Play, 
  Save,
  Loader2,
  X,
  FileCode,
  Zap,
  Sparkles,
  PanelRightClose,
  PanelRightOpen,
  GripVertical
} from "lucide-react"
import { readFile, writeFile, executeCode, checkHealth, type ExecutionResult } from "@/lib/api"
import { cn } from "@/lib/utils"

interface OpenFile {
  path: string
  content: string
  originalContent: string
  isDirty: boolean
}

// Minimum panel widths
const MIN_SIDEBAR_WIDTH = 180
const MAX_SIDEBAR_WIDTH = 400
const MIN_CHAT_WIDTH = 280
const MAX_CHAT_WIDTH = 500
const DEFAULT_SIDEBAR_WIDTH = 256
const DEFAULT_CHAT_WIDTH = 360

export function EditorInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [chatOpen, setChatOpen] = useState(true)
  const [outputPanelHeight, setOutputPanelHeight] = useState(200)
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_SIDEBAR_WIDTH)
  const [chatWidth, setChatWidth] = useState(DEFAULT_CHAT_WIDTH)
  const [openFiles, setOpenFiles] = useState<Map<string, OpenFile>>(new Map())
  const [activeFile, setActiveFile] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null)
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking")
  
  // Resizing state
  const [isResizingSidebar, setIsResizingSidebar] = useState(false)
  const [isResizingChat, setIsResizingChat] = useState(false)
  const [isResizingOutput, setIsResizingOutput] = useState(false)

  // Check API status on mount
  useEffect(() => {
    checkHealth()
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"))
  }, [])

  // Handle responsive behavior
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      // Auto-collapse sidebars on small screens
      if (width < 768) {
        setSidebarOpen(false)
        setChatOpen(false)
      } else if (width < 1024) {
        // On medium screens, keep one sidebar open
        setChatOpen(false)
      }
    }
    
    handleResize() // Check on mount
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Handle sidebar resize
  useEffect(() => {
    if (!isResizingSidebar) return

    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, e.clientX))
      setSidebarWidth(newWidth)
    }

    const handleMouseUp = () => {
      setIsResizingSidebar(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizingSidebar])

  // Handle chat resize
  useEffect(() => {
    if (!isResizingChat) return

    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = Math.min(MAX_CHAT_WIDTH, Math.max(MIN_CHAT_WIDTH, window.innerWidth - e.clientX))
      setChatWidth(newWidth)
    }

    const handleMouseUp = () => {
      setIsResizingChat(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizingChat])

  // Handle output panel resize
  useEffect(() => {
    if (!isResizingOutput) return

    const handleMouseMove = (e: MouseEvent) => {
      const container = document.querySelector('.editor-container')
      if (!container) return
      const rect = container.getBoundingClientRect()
      const newHeight = Math.min(400, Math.max(100, rect.bottom - e.clientY))
      setOutputPanelHeight(newHeight)
    }

    const handleMouseUp = () => {
      setIsResizingOutput(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizingOutput])

  // Get active file content
  const activeFileData = activeFile ? openFiles.get(activeFile) : null

  // Handle file selection from tree
  const handleSelectFile = useCallback(async (path: string) => {
    if (!path) {
      setActiveFile(null)
      return
    }

    // Check if already open
    if (openFiles.has(path)) {
      setActiveFile(path)
      return
    }

    // Load file from API
    setIsLoading(true)
    try {
      const data = await readFile(path)
      setOpenFiles((prev) => {
        const next = new Map(prev)
        next.set(path, {
          path,
          content: data.content,
          originalContent: data.content,
          isDirty: false,
        })
        return next
      })
      setActiveFile(path)
    } catch (error) {
      console.error("Failed to load file:", error)
      alert(error instanceof Error ? error.message : "Failed to load file")
    } finally {
      setIsLoading(false)
    }
  }, [openFiles])

  // Handle content change
  const handleContentChange = useCallback((content: string) => {
    if (!activeFile) return
    setOpenFiles((prev) => {
      const next = new Map(prev)
      const file = next.get(activeFile)
      if (file) {
        next.set(activeFile, {
          ...file,
          content,
          isDirty: content !== file.originalContent,
        })
      }
      return next
    })
  }, [activeFile])

  // Handle save
  const handleSave = useCallback(async () => {
    if (!activeFile || !activeFileData) return
    
    setIsSaving(true)
    try {
      await writeFile(activeFile, activeFileData.content)
      setOpenFiles((prev) => {
        const next = new Map(prev)
        const file = next.get(activeFile)
        if (file) {
          next.set(activeFile, {
            ...file,
            originalContent: file.content,
            isDirty: false,
          })
        }
        return next
      })
    } catch (error) {
      console.error("Failed to save:", error)
      alert(error instanceof Error ? error.message : "Failed to save file")
    } finally {
      setIsSaving(false)
    }
  }, [activeFile, activeFileData])

  // Handle run
  const handleRun = useCallback(async () => {
    if (!activeFile) return
    
    // Save first if dirty
    if (activeFileData?.isDirty) {
      await handleSave()
    }

    setIsExecuting(true)
    setExecutionResult(null)
    try {
      const result = await executeCode({ file_path: activeFile })
      setExecutionResult(result)
    } catch (error) {
      console.error("Failed to execute:", error)
      const errorMessage = error instanceof Error ? error.message : "Execution failed"
      setExecutionResult({
        success: false,
        output: errorMessage,
        stdout: "",
        stderr: errorMessage,
        exit_code: -1,
        execution_time: 0,
      })
    } finally {
      setIsExecuting(false)
    }
  }, [activeFile, activeFileData, handleSave])

  // Handle close tab
  const handleCloseTab = useCallback((path: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const file = openFiles.get(path)
    
    if (file?.isDirty) {
      if (!confirm(`${path} has unsaved changes. Close anyway?`)) {
        return
      }
    }

    setOpenFiles((prev) => {
      const next = new Map(prev)
      next.delete(path)
      return next
    })

    if (activeFile === path) {
      const remaining = Array.from(openFiles.keys()).filter((p) => p !== path)
      setActiveFile(remaining.length > 0 ? remaining[remaining.length - 1] : null)
    }
  }, [openFiles, activeFile])

  // Handle apply code from AI
  const handleApplyCode = useCallback((code: string) => {
    if (!activeFile) return
    handleContentChange(code)
  }, [activeFile, handleContentChange])

  // Check if file is Python
  const isPythonFile = activeFile?.endsWith(".py")

  return (
    <div className={cn(
      "flex h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] overflow-hidden",
      (isResizingSidebar || isResizingChat || isResizingOutput) && "select-none cursor-col-resize"
    )}>
      {/* File Explorer Sidebar */}
      {sidebarOpen && (
        <>
          <div 
            className="border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex flex-col flex-shrink-0"
            style={{ width: sidebarWidth }}
          >
            <div className="flex h-12 items-center justify-between border-b border-[var(--border-color)] px-3">
              <span className="text-sm font-semibold text-[var(--text-primary)] truncate">Explorer</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-[var(--text-secondary)] hover:text-[var(--accent-primary)] hover:bg-[var(--bg-tertiary)] flex-shrink-0"
                onClick={() => setSidebarOpen(false)}
              >
                <PanelLeftClose className="h-4 w-4" />
              </Button>
            </div>
            <FileTree 
              selectedFile={activeFile} 
              onSelectFile={handleSelectFile} 
            />
          </div>
          
          {/* Sidebar Resize Handle */}
          <div
            className="w-1 bg-transparent hover:bg-[var(--accent-primary)]/50 cursor-col-resize flex-shrink-0 group relative"
            onMouseDown={() => setIsResizingSidebar(true)}
          >
            <div className="absolute inset-y-0 -left-1 -right-1" />
          </div>
        </>
      )}

      {/* Main Editor Area */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Header Bar */}
        <div className="flex h-12 items-center justify-between border-b border-[var(--border-color)] bg-[var(--bg-secondary)] px-4 flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            {!sidebarOpen && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-[var(--text-secondary)] hover:text-[var(--accent-primary)] hover:bg-[var(--bg-tertiary)] flex-shrink-0"
                onClick={() => setSidebarOpen(true)}
              >
                <PanelLeftOpen className="h-4 w-4" />
              </Button>
            )}
            
            {/* Logo */}
            <div className="flex items-center gap-2 flex-shrink-0">
              <Zap className="h-5 w-5 text-[var(--accent-primary)]" />
              <span className="font-bold bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] bg-clip-text text-transparent hidden sm:inline">
                ChatOS
              </span>
            </div>
            
            {/* Status indicator */}
            <div className="flex items-center gap-1.5 text-xs flex-shrink-0">
              <span className={cn(
                "w-2 h-2 rounded-full",
                apiStatus === "online" && "bg-[var(--success)]",
                apiStatus === "offline" && "bg-[var(--error)]",
                apiStatus === "checking" && "bg-[var(--warning)] animate-pulse"
              )} />
              <span className="text-[var(--text-muted)] hidden md:inline">
                {apiStatus === "online" ? "Connected" : apiStatus === "offline" ? "Offline" : "..."}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Save Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSave}
              disabled={!activeFileData?.isDirty || isSaving}
              className="h-8 gap-1.5 text-[var(--text-secondary)] hover:text-[var(--accent-primary)] hover:bg-[var(--bg-tertiary)] disabled:opacity-50"
            >
              {isSaving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              <span className="hidden sm:inline">Save</span>
            </Button>

            {/* Run Button (Python only) */}
            <Button
              size="sm"
              onClick={handleRun}
              disabled={!isPythonFile || isExecuting}
              className="h-8 gap-1.5 bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-[var(--bg-primary)] hover:opacity-90 font-medium disabled:opacity-50"
            >
              {isExecuting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
              <span className="hidden sm:inline">Run</span>
            </Button>

            <div className="w-px h-6 bg-[var(--border-color)] mx-1 hidden sm:block" />

            {/* AI Toggle */}
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
              <span className="hidden sm:inline">AI</span>
            </Button>
          </div>
        </div>

        {/* Tabs */}
        {openFiles.size > 0 && (
          <div className="flex items-center border-b border-[var(--border-color)] bg-[var(--bg-tertiary)] px-2 overflow-x-auto flex-shrink-0">
            {Array.from(openFiles.entries()).map(([path, file]) => (
              <button
                key={path}
                onClick={() => setActiveFile(path)}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 text-xs border-b-2 transition-colors whitespace-nowrap flex-shrink-0",
                  activeFile === path
                    ? "text-[var(--accent-primary)] border-[var(--accent-primary)] bg-[var(--bg-secondary)]"
                    : "text-[var(--text-secondary)] border-transparent hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]"
                )}
              >
                <FileCode className="h-3.5 w-3.5" />
                <span className="max-w-[120px] truncate">{path.split("/").pop()}</span>
                {file.isDirty && <span className="text-[var(--accent-primary)]">•</span>}
                <button
                  onClick={(e) => handleCloseTab(path, e)}
                  className="ml-1 p-0.5 hover:bg-[var(--bg-elevated)] rounded"
                >
                  <X className="h-3 w-3" />
                </button>
              </button>
            ))}
          </div>
        )}

        {/* Editor and Chat Container */}
        <div className="flex flex-1 overflow-hidden editor-container">
          <div className="flex flex-col flex-1 min-w-0">
            {/* Code Editor */}
            <div className="flex-1 overflow-hidden min-h-0">
              {isLoading ? (
                <div className="flex items-center justify-center h-full bg-[var(--bg-primary)]">
                  <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-primary)]" />
                </div>
              ) : (
                <CodeEditor
                  file={activeFile}
                  content={activeFileData?.content || ""}
                  onChange={handleContentChange}
                  onSave={handleSave}
                />
              )}
            </div>

            {/* Output Panel Resize Handle */}
            <div
              className="h-1 bg-transparent hover:bg-[var(--accent-primary)]/50 cursor-row-resize flex-shrink-0 relative"
              onMouseDown={() => setIsResizingOutput(true)}
            >
              <div className="absolute -top-1 -bottom-1 inset-x-0" />
            </div>

            {/* Output Panel */}
            <OutputPanel
              height={outputPanelHeight}
              executionResult={executionResult}
              isExecuting={isExecuting}
              onClear={() => setExecutionResult(null)}
            />
          </div>

          {/* AI Chat Panel */}
          {chatOpen && (
            <>
              {/* Chat Resize Handle */}
              <div
                className="w-1 bg-transparent hover:bg-[var(--accent-primary)]/50 cursor-col-resize flex-shrink-0 relative"
                onMouseDown={() => setIsResizingChat(true)}
              >
                <div className="absolute inset-y-0 -left-1 -right-1" />
              </div>
              
              <div 
                className="border-l border-[var(--border-color)] bg-[var(--bg-secondary)] flex-shrink-0"
                style={{ width: chatWidth }}
              >
                <AiChat
                  currentFile={activeFile}
                  currentFileContent={activeFileData?.content}
                  onApplyCode={handleApplyCode}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
