"use client"

import { useState, lazy, Suspense } from "react"
import { Terminal as TerminalIcon, AlertCircle, CheckCircle2, X, Loader2, Play } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ExecutionResult } from "@/lib/api"

// Lazy load the terminal to avoid SSR issues
const Terminal = lazy(() => import("./terminal").then(mod => ({ default: mod.Terminal })))

interface OutputPanelProps {
  height: number
  executionResult: ExecutionResult | null
  isExecuting: boolean
  onClear: () => void
}

type TabType = "output" | "problems" | "terminal"

interface Problem {
  type: "error" | "warning"
  file: string
  line: number
  message: string
}

export function OutputPanel({ height, executionResult, isExecuting, onClear }: OutputPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>("output")
  const [terminalReady, setTerminalReady] = useState(false)

  // Parse problems from stderr
  const parseProblems = (stderr: string): Problem[] => {
    const problems: Problem[] = []
    const lines = stderr.split('\n').filter(Boolean)
    
    for (const line of lines) {
      // Try to parse Python traceback style errors
      const fileMatch = line.match(/File "([^"]+)", line (\d+)/)
      if (fileMatch) {
        problems.push({
          type: "error",
          file: fileMatch[1],
          line: parseInt(fileMatch[2]),
          message: line,
        })
      } else if (line.toLowerCase().includes('warning')) {
        problems.push({
          type: "warning",
          file: "",
          line: 0,
          message: line,
        })
      } else if (line.toLowerCase().includes('error') || line.includes('Error:')) {
        problems.push({
          type: "error",
          file: "",
          line: 0,
          message: line,
        })
      }
    }
    
    return problems
  }

  const problems = executionResult?.stderr ? parseProblems(executionResult.stderr) : []

  return (
    <div
      className="border-t border-[var(--border-color)] bg-[var(--bg-secondary)] flex flex-col"
      style={{ height: `${height}px` }}
    >
      {/* Tabs */}
      <div className="flex items-center justify-between border-b border-[var(--border-color)] px-2 bg-[var(--bg-tertiary)] flex-shrink-0">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab("output")}
            className={cn(
              "flex items-center gap-2 px-3 py-2 text-xs font-medium transition-colors",
              activeTab === "output"
                ? "text-[var(--accent-primary)] border-b-2 border-[var(--accent-primary)]"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            )}
          >
            <Play className="h-3.5 w-3.5" />
            Output
            {isExecuting && <Loader2 className="h-3 w-3 animate-spin" />}
          </button>
          <button
            onClick={() => setActiveTab("problems")}
            className={cn(
              "flex items-center gap-2 px-3 py-2 text-xs font-medium transition-colors",
              activeTab === "problems"
                ? "text-[var(--accent-primary)] border-b-2 border-[var(--accent-primary)]"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            )}
          >
            <AlertCircle className="h-3.5 w-3.5" />
            Problems
            {problems.length > 0 && (
              <span className="px-1.5 py-0.5 rounded text-[10px] bg-[var(--error)] text-[var(--bg-primary)]">
                {problems.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab("terminal")}
            className={cn(
              "flex items-center gap-2 px-3 py-2 text-xs font-medium transition-colors",
              activeTab === "terminal"
                ? "text-[var(--accent-primary)] border-b-2 border-[var(--accent-primary)]"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            )}
          >
            <TerminalIcon className="h-3.5 w-3.5" />
            Terminal
            {activeTab === "terminal" && terminalReady && (
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)]" />
            )}
          </button>
        </div>
        
        <button
          onClick={onClear}
          className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] rounded transition-colors"
          title="Clear output"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden min-h-0">
        {activeTab === "output" && (
          <div className="h-full overflow-auto p-3 font-mono text-xs">
            <div className="space-y-1">
              {isExecuting ? (
                <div className="flex items-center gap-2 text-[var(--accent-primary)]">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Running...</span>
                </div>
              ) : executionResult ? (
                <>
                  {/* Success/Error Status */}
                  <div className="flex items-start gap-2 mb-2">
                    {executionResult.success ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-[var(--success)] mt-0.5 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="h-3.5 w-3.5 text-[var(--error)] mt-0.5 flex-shrink-0" />
                    )}
                    <span className={executionResult.success ? "text-[var(--success)]" : "text-[var(--error)]"}>
                      {executionResult.success ? "Execution completed" : "Execution failed"}
                    </span>
                  </div>

                  {/* Stdout */}
                  {executionResult.stdout && (
                    <pre className="whitespace-pre-wrap text-[var(--text-primary)] bg-[var(--bg-primary)] p-2 rounded border border-[var(--border-color)]">
                      {executionResult.stdout}
                    </pre>
                  )}

                  {/* Stderr */}
                  {executionResult.stderr && (
                    <pre className="whitespace-pre-wrap text-[var(--error)] bg-[var(--bg-primary)] p-2 rounded border border-[var(--error)]/30 mt-2">
                      {executionResult.stderr}
                    </pre>
                  )}

                  {/* Execution Info */}
                  <div className="text-[var(--text-muted)] mt-2 flex items-center gap-4">
                    <span>⏱️ {(executionResult.execution_time ?? 0).toFixed(3)}s</span>
                    <span>Exit code: {executionResult.exit_code}</span>
                  </div>
                </>
              ) : (
                <div className="text-[var(--text-muted)]">
                  Run a file to see output here...
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "problems" && (
          <div className="h-full overflow-auto p-3 font-mono text-xs">
            <div className="space-y-2">
              {problems.length === 0 ? (
                <div className="flex items-center gap-2 text-[var(--success)]">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>No problems detected</span>
                </div>
              ) : (
                problems.map((problem, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <AlertCircle
                      className={cn(
                        "h-3.5 w-3.5 mt-0.5 flex-shrink-0",
                        problem.type === "error" ? "text-[var(--error)]" : "text-[var(--warning)]"
                      )}
                    />
                    <div>
                      {problem.file && (
                        <div className="text-[var(--accent-primary)]">
                          {problem.file}:{problem.line}
                        </div>
                      )}
                      <div className="text-[var(--text-primary)]">{problem.message}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === "terminal" && (
          <Suspense fallback={
            <div className="h-full flex items-center justify-center text-[var(--text-muted)]">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              Loading terminal...
            </div>
          }>
            <Terminal 
              sessionId="sandbox-main"
              onReady={() => setTerminalReady(true)}
            />
          </Suspense>
        )}
      </div>
    </div>
  )
}
