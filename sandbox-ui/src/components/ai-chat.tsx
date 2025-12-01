"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Send, Sparkles, Code2, Zap, ChevronDown, Brain, Search, Loader2, Copy, Check } from "lucide-react"
import { cn } from "@/lib/utils"
import { sendChatMessage, getModels, type ChatResponse, type ModelInfo } from "@/lib/api"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  model?: string
  isLoading?: boolean
}

interface AiChatProps {
  currentFile?: string | null
  currentFileContent?: string
  onApplyCode?: (code: string) => void
}

const COMMANDS = [
  { id: "code", label: "/code", icon: Code2, description: "Code generation" },
  { id: "swarm", label: "/swarm", icon: Zap, description: "Multi-agent coding" },
  { id: "research", label: "/research", icon: Search, description: "Deep research" },
  { id: "deepthinking", label: "/deepthinking", icon: Brain, description: "Extended reasoning" },
]

export function AiChat({ currentFile, currentFileContent, onApplyCode }: AiChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hello! I'm your AI coding assistant. Use /swarm for multi-agent coding, /code for code generation, or just ask anything about your code.",
    },
  ])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(null)
  const [showModelDropdown, setShowModelDropdown] = useState(false)
  const [sessionId] = useState(() => `session_${Math.random().toString(36).substr(2, 9)}`)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Fetch available models
  useEffect(() => {
    getModels(true)
      .then((data) => {
        // Filter to real models (not dummy)
        const realModels = data.filter((m) => m.provider !== "dummy")
        setModels(realModels)
        if (realModels.length > 0) {
          setSelectedModel(realModels[0])
        }
      })
      .catch(console.error)
  }, [])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowModelDropdown(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
    }

    // Add loading message
    const loadingMessage: Message = {
      id: `loading-${Date.now()}`,
      role: "assistant",
      content: "",
      isLoading: true,
    }

    setMessages((prev) => [...prev, userMessage, loadingMessage])
    setInput("")
    setIsLoading(true)

    try {
      // Build the message with file context if available
      let fullMessage = input
      if (currentFile && currentFileContent && !input.includes("```")) {
        fullMessage = `Current file: ${currentFile}\n\`\`\`\n${currentFileContent}\n\`\`\`\n\n${input}`
      }

      const response = await sendChatMessage({
        message: fullMessage,
        mode: "code",
        use_rag: true,
        session_id: sessionId,
        model_id: selectedModel?.id,
      })

      // Replace loading message with actual response
      setMessages((prev) => {
        const filtered = prev.filter((m) => !m.isLoading)
        return [
          ...filtered,
          {
            id: `response-${Date.now()}`,
            role: "assistant",
            content: response.answer,
            model: response.chosen_model,
          },
        ]
      })
    } catch (error) {
      // Replace loading with error
      setMessages((prev) => {
        const filtered = prev.filter((m) => !m.isLoading)
        return [
          ...filtered,
          {
            id: `error-${Date.now()}`,
            role: "assistant",
            content: `Error: ${error instanceof Error ? error.message : "Failed to get response"}`,
          },
        ]
      })
    } finally {
      setIsLoading(false)
    }
  }

  const insertCommand = (command: string) => {
    setInput(`/${command} `)
  }

  const copyToClipboard = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const extractCodeBlocks = (content: string): string[] => {
    const codeBlockRegex = /```[\w]*\n?([\s\S]*?)```/g
    const blocks: string[] = []
    let match
    while ((match = codeBlockRegex.exec(content)) !== null) {
      blocks.push(match[1].trim())
    }
    return blocks
  }

  const formatMessage = (content: string) => {
    // Simple markdown-like formatting
    let formatted = content
      // Code blocks
      .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre class="code-block bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-md p-3 my-2 overflow-x-auto"><code class="text-[var(--text-primary)] text-xs">$2</code></pre>')
      // Inline code
      .replace(/`([^`]+)`/g, '<code class="bg-[var(--bg-elevated)] px-1.5 py-0.5 rounded text-[var(--accent-primary)] text-xs">$1</code>')
      // Bold
      .replace(/\*\*([^*]+)\*\*/g, '<strong class="text-[var(--text-primary)]">$1</strong>')
      // Line breaks
      .replace(/\n/g, '<br>')

    return <span dangerouslySetInnerHTML={{ __html: formatted }} />
  }

  return (
    <div className="flex h-full flex-col bg-[var(--bg-secondary)]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border-color)] px-4 py-3 bg-gradient-to-r from-[var(--accent-primary)]/10 to-[var(--accent-secondary)]/10">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-[var(--accent-primary)]" />
          <span className="font-semibold text-[var(--text-primary)]">AI Assistant</span>
        </div>

        {/* Model Selector */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setShowModelDropdown(!showModelDropdown)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[var(--bg-elevated)] hover:bg-[var(--bg-tertiary)] text-xs text-[var(--text-secondary)] transition-colors border border-[var(--border-color)]"
          >
            <span className="text-[var(--text-primary)] font-medium max-w-[100px] truncate">
              {selectedModel?.name || "Select Model"}
            </span>
            <ChevronDown className="h-3.5 w-3.5" />
          </button>

          {showModelDropdown && (
            <div className="absolute right-0 mt-2 w-56 rounded-lg border border-[var(--border-color)] bg-[var(--bg-elevated)] shadow-lg z-50">
              <div className="p-1 max-h-64 overflow-y-auto">
                {/* Council option */}
                <button
                  onClick={() => {
                    setSelectedModel(null)
                    setShowModelDropdown(false)
                  }}
                  className={cn(
                    "w-full flex flex-col items-start gap-0.5 px-3 py-2 rounded-md text-left transition-colors",
                    !selectedModel
                      ? "bg-gradient-to-r from-[var(--accent-primary)]/20 to-[var(--accent-secondary)]/20 text-[var(--text-primary)]"
                      : "hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]"
                  )}
                >
                  <span className="text-sm font-medium">🏛️ Council Mode</span>
                  <span className="text-xs text-[var(--text-muted)]">Multi-model consensus</span>
                </button>

                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => {
                      setSelectedModel(model)
                      setShowModelDropdown(false)
                    }}
                    className={cn(
                      "w-full flex flex-col items-start gap-0.5 px-3 py-2 rounded-md text-left transition-colors",
                      selectedModel?.id === model.id
                        ? "bg-gradient-to-r from-[var(--accent-primary)]/20 to-[var(--accent-secondary)]/20 text-[var(--text-primary)]"
                        : "hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]"
                    )}
                  >
                    <span className="text-sm font-medium">{model.name}</span>
                    <span className="text-xs text-[var(--text-muted)]">{model.provider}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Quick Commands */}
      <div className="border-b border-[var(--border-color)] px-3 py-2 space-y-1.5">
        <p className="text-[10px] text-[var(--text-muted)]">Quick commands:</p>
        <div className="flex flex-wrap gap-1.5">
          {COMMANDS.map((cmd) => (
            <button
              key={cmd.id}
              onClick={() => insertCommand(cmd.id)}
              className="flex items-center gap-1 px-2 py-1 rounded-md bg-[var(--bg-tertiary)] hover:bg-[var(--bg-elevated)] text-[10px] text-[var(--text-secondary)] transition-colors border border-[var(--border-color)]"
              title={cmd.description}
            >
              <cmd.icon className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">{cmd.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-4 overflow-auto p-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn("flex gap-3", message.role === "user" ? "justify-end" : "justify-start")}
          >
            <div
              className={cn(
                "max-w-[85%] rounded-lg px-4 py-2.5 text-sm relative group",
                message.role === "user"
                  ? "bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-[var(--bg-primary)] font-medium"
                  : "bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-color)]"
              )}
            >
              {message.isLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Thinking...</span>
                </div>
              ) : (
                <>
                  {message.model && (
                    <div className="text-xs text-[var(--text-muted)] mb-1">{message.model}</div>
                  )}
                  <div className="break-words">{formatMessage(message.content)}</div>
                  
                  {/* Action buttons for code blocks */}
                  {message.role === "assistant" && extractCodeBlocks(message.content).length > 0 && (
                    <div className="mt-2 flex gap-2">
                      <button
                        onClick={() => copyToClipboard(extractCodeBlocks(message.content).join('\n\n'), message.id)}
                        className="flex items-center gap-1 px-2 py-1 text-xs bg-[var(--bg-tertiary)] hover:bg-[var(--bg-primary)] rounded border border-[var(--border-color)] transition-colors"
                      >
                        {copiedId === message.id ? (
                          <Check className="h-3 w-3 text-[var(--success)]" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                        Copy code
                      </button>
                      {onApplyCode && (
                        <button
                          onClick={() => onApplyCode(extractCodeBlocks(message.content)[0])}
                          className="flex items-center gap-1 px-2 py-1 text-xs bg-[var(--accent-primary)]/20 hover:bg-[var(--accent-primary)]/30 text-[var(--accent-primary)] rounded border border-[var(--accent-primary)]/30 transition-colors"
                        >
                          <Code2 className="h-3 w-3" />
                          Apply to file
                        </button>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-[var(--border-color)] p-4 bg-[var(--bg-tertiary)]">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything or use /commands..."
            disabled={isLoading}
            className="flex-1 bg-[var(--bg-primary)] border-[var(--border-color)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:ring-2 focus:ring-[var(--accent-primary)]"
          />
          <Button
            type="submit"
            size="icon"
            disabled={isLoading || !input.trim()}
            className="bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-[var(--bg-primary)] hover:opacity-90 disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </div>
    </div>
  )
}

