"use client"

import { useState } from "react"
import { Check, Copy, ChevronDown, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

interface CodeBlockProps {
  children: string
  language?: string
  className?: string
}

export function CodeBlock({ children, language, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  
  const code = String(children).replace(/\n$/, '')
  const lines = code.split('\n')
  const isLong = lines.length > 15

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn("relative group my-3 rounded-lg overflow-hidden border border-[var(--border-color)] bg-[#0d1117]", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-[var(--border-color)]">
        <div className="flex items-center gap-2">
          {isLong && (
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-0.5 hover:bg-[var(--bg-tertiary)] rounded"
            >
              {collapsed ? (
                <ChevronRight className="h-4 w-4 text-[var(--text-muted)]" />
              ) : (
                <ChevronDown className="h-4 w-4 text-[var(--text-muted)]" />
              )}
            </button>
          )}
          <span className="text-xs text-[var(--text-muted)] font-mono">
            {language || 'text'}
          </span>
          {isLong && (
            <span className="text-xs text-[var(--text-muted)]">
              ({lines.length} lines)
            </span>
          )}
        </div>
        <button
          onClick={copyToClipboard}
          className="flex items-center gap-1.5 px-2 py-1 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] rounded transition-colors"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-green-500" />
              <span className="text-green-500">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      
      {/* Code content */}
      <div className={cn(
        "overflow-x-auto transition-all duration-200",
        collapsed && "max-h-0 overflow-hidden"
      )}>
        <pre className="p-4 text-sm leading-relaxed">
          <code className={cn(
            "font-mono text-[#e6edf3]",
            language && `language-${language}`
          )}>
            {code}
          </code>
        </pre>
      </div>
      
      {/* Collapsed indicator */}
      {collapsed && (
        <div 
          className="px-4 py-2 text-xs text-[var(--text-muted)] cursor-pointer hover:bg-[var(--bg-tertiary)]"
          onClick={() => setCollapsed(false)}
        >
          Click to expand ({lines.length} lines)
        </div>
      )}
    </div>
  )
}

