"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import Link from "next/link"
import {
  Send,
  Sparkles,
  Code2,
  Zap,
  ChevronDown,
  Brain,
  Search,
  Loader2,
  Copy,
  Check,
  MessageSquare,
  Menu,
  X,
  FileText,
  Mic,
  Square,
  RotateCcw,
  RefreshCw,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { 
  streamChatMessage, 
  sendChatMessage,
  getModels, 
  type ChatResponse, 
  type ModelInfo,
  type StreamEvent,
} from "@/lib/api"
import { consumePendingChatMessage } from "@/lib/chat-integration"
import { MarkdownRenderer } from "@/components/chat/markdown-renderer"
import { TypingIndicator } from "@/components/chat/typing-indicator"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  model?: string
  isLoading?: boolean
  isStreaming?: boolean
  isError?: boolean
  responses?: Array<{ model: string; text: string }>
}

const COMMANDS = [
  { id: "code", label: "/code", icon: Code2, description: "Code generation" },
  { id: "swarm", label: "/swarm", icon: Zap, description: "Multi-agent coding" },
  { id: "research", label: "/research", icon: Search, description: "Deep research" },
  { id: "deepthinking", label: "/deepthinking", icon: Brain, description: "Extended reasoning" },
]

const NAV_ITEMS = [
  { href: "/", label: "Chat", icon: MessageSquare },
  { href: "/notes", label: "Notes", icon: FileText },
  { href: "/diary", label: "Diary", icon: Mic },
  { href: "/editor", label: "Editor", icon: Code2 },
  { href: "/sandbox", label: "VSCode", icon: Code2 },
]

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Welcome to ChatOS! I'm your AI assistant powered by local LLMs. Try these commands:\n\n- **/code** - Generate code snippets\n- **/swarm** - Multi-agent collaboration\n- **/research** - Deep research mode\n- **/deepthinking** - Extended reasoning\n\nOr just ask me anything!",
    },
  ])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(null)
  const [showModelDropdown, setShowModelDropdown] = useState(false)
  const [sessionId] = useState(() => `chat_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [abortController, setAbortController] = useState<AbortController | null>(null)
  const [lastUserMessage, setLastUserMessage] = useState<string>("")
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Fetch available models
  useEffect(() => {
    getModels(true)
      .then((data) => {
        // Include all models (filter dummy only if real models exist)
        const realModels = data.filter((m) => m.provider !== "dummy")
        const modelsToUse = realModels.length > 0 ? realModels : data
        setModels(modelsToUse)
        // Always select first model by default (council mode is opt-in)
        if (modelsToUse.length > 0 && !selectedModel) {
          setSelectedModel(modelsToUse[0])
        }
      })
      .catch(console.error)
  }, [selectedModel])

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

  // Focus input on load
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Check for pending chat messages from other pages (Notes, Diary)
  useEffect(() => {
    const pendingMessage = consumePendingChatMessage()
    if (pendingMessage) {
      const sourceLabel = {
        note: '📝 Note',
        diary: '🎙️ Diary',
        search: '🔍 Search',
        other: '📄 Content',
      }[pendingMessage.source] || '📄 Content'
      
      const contextMessage: Message = {
        id: `context-${Date.now()}`,
        role: "assistant",
        content: `**${sourceLabel}${pendingMessage.sourceTitle ? `: ${pendingMessage.sourceTitle}` : ''}**\n\n${pendingMessage.content}\n\n---\n*How can I help you with this?*`,
      }
      
      setMessages((prev) => [...prev, contextMessage])
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [])

  // Handle streaming chat
  const handleSendStreaming = useCallback(async (messageText: string) => {
    if (!messageText.trim() || isLoading) return

    const controller = new AbortController()
    setAbortController(controller)
    setLastUserMessage(messageText)

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: messageText,
    }

    const streamingMessage: Message = {
      id: `streaming-${Date.now()}`,
      role: "assistant",
      content: "",
      isStreaming: true,
    }

    setMessages((prev) => [...prev, userMessage, streamingMessage])
    setInput("")
    setIsLoading(true)

    let fullContent = ""
    let modelName = ""

    try {
      await streamChatMessage(
        {
          message: messageText,
          session_id: sessionId,
          model_id: selectedModel?.id,
        },
        (event) => {
          if (event.type === "metadata") {
            modelName = event.model
          } else if (event.type === "token") {
            fullContent += event.text
            setMessages((prev) =>
              prev.map((msg) =>
                msg.isStreaming
                  ? { ...msg, content: fullContent, model: modelName }
                  : msg
              )
            )
          } else if (event.type === "done") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.isStreaming
                  ? {
                      ...msg,
                      content: event.answer || fullContent,
                      model: event.chosen_model || modelName,
                      isStreaming: false,
                    }
                  : msg
              )
            )
          } else if (event.type === "error") {
            throw new Error(event.message)
          }
        },
        controller.signal
      )

      // Ensure streaming is marked complete
      setMessages((prev) =>
        prev.map((msg) =>
          msg.isStreaming
            ? { ...msg, isStreaming: false, content: fullContent || "No response received." }
            : msg
        )
      )
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        // User cancelled - mark as stopped
        setMessages((prev) =>
          prev.map((msg) =>
            msg.isStreaming
              ? { ...msg, isStreaming: false, content: msg.content + "\n\n*[Generation stopped]*" }
              : msg
          )
        )
      } else {
        // Replace streaming message with error
        setMessages((prev) =>
          prev.map((msg) =>
            msg.isStreaming
              ? {
                  ...msg,
                  isStreaming: false,
                  isError: true,
                  content: `**Error:** ${error instanceof Error ? error.message : "Failed to get response"}`,
                }
              : msg
          )
        )
      }
    } finally {
      setIsLoading(false)
      setAbortController(null)
    }
  }, [isLoading, sessionId, selectedModel])

  const handleSend = async () => {
    await handleSendStreaming(input)
  }

  const handleStop = () => {
    if (abortController) {
      abortController.abort()
    }
  }

  const handleRegenerate = async () => {
    if (lastUserMessage && !isLoading) {
      // Remove the last assistant message
      setMessages((prev) => {
        const lastUserIdx = prev.findLastIndex((m) => m.role === "user")
        if (lastUserIdx >= 0) {
          return prev.slice(0, lastUserIdx + 1)
        }
        return prev
      })
      
      // Regenerate
      await handleSendStreaming(lastUserMessage)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const copyToClipboard = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const insertCommand = (command: string) => {
    setInput(command + " ")
    inputRef.current?.focus()
  }

  const clearChat = () => {
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        content: "Chat cleared. How can I help you?",
      },
    ])
    setLastUserMessage("")
  }

  return (
    <div className="flex h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      {/* Sidebar */}
      <div
        className={cn(
          "flex flex-col border-r border-[var(--border-color)] bg-[var(--bg-secondary)] transition-all duration-300",
          sidebarOpen ? "w-64" : "w-0 overflow-hidden"
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center gap-2 border-b border-[var(--border-color)] px-4">
          <Zap className="h-6 w-6 text-[var(--accent-primary)]" />
          <span className="font-bold text-lg bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] bg-clip-text text-transparent">
            ChatOS
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1">
          {NAV_ITEMS.map((item) => (
            <Link key={item.href} href={item.href}>
              <Button
                variant="ghost"
                className={cn(
                  "w-full justify-start gap-3 h-10",
                  item.href === "/"
                    ? "bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Button>
            </Link>
          ))}
        </nav>

        {/* Commands Section */}
        <div className="border-t border-[var(--border-color)] p-3">
          <p className="text-xs text-[var(--text-muted)] mb-2 px-2">Quick Commands</p>
          <div className="space-y-1">
            {COMMANDS.map((cmd) => (
              <Button
                key={cmd.id}
                variant="ghost"
                size="sm"
                onClick={() => insertCommand(cmd.label)}
                className="w-full justify-start gap-2 h-8 text-xs text-[var(--text-secondary)] hover:text-[var(--accent-primary)] hover:bg-[var(--bg-tertiary)]"
              >
                <cmd.icon className="h-3.5 w-3.5" />
                {cmd.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Model Selector */}
        <div className="border-t border-[var(--border-color)] p-3">
          <p className="text-xs text-[var(--text-muted)] mb-2 px-2">Model</p>
          <div className="relative" ref={dropdownRef}>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowModelDropdown(!showModelDropdown)}
              className="w-full justify-between h-9 text-xs bg-[var(--bg-tertiary)] border-[var(--border-color)]"
            >
              <span className="truncate">{selectedModel?.name || "Select model..."}</span>
              <ChevronDown className="h-3.5 w-3.5 ml-2 flex-shrink-0" />
            </Button>
            {showModelDropdown && (
              <div className="absolute bottom-full left-0 right-0 mb-1 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-md shadow-lg max-h-48 overflow-y-auto z-50">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => {
                      setSelectedModel(model)
                      setShowModelDropdown(false)
                    }}
                    className={cn(
                      "w-full px-3 py-2 text-left text-xs hover:bg-[var(--bg-tertiary)] transition-colors",
                      selectedModel?.id === model.id && "bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
                    )}
                  >
                    <div className="font-medium">{model.name}</div>
                    <div className="text-[var(--text-muted)] text-[10px]">{model.provider}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex h-14 items-center justify-between border-b border-[var(--border-color)] bg-[var(--bg-secondary)] px-4">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="h-8 w-8"
            >
              {sidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </Button>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-[var(--accent-primary)]" />
              <span className="font-semibold">AI Chat</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {lastUserMessage && !isLoading && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRegenerate}
                className="h-8 text-xs text-[var(--text-secondary)] gap-1.5"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Regenerate
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={clearChat}
              className="h-8 text-xs text-[var(--text-secondary)]"
            >
              Clear Chat
            </Button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex gap-3 max-w-4xl mx-auto",
                message.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              {message.role === "assistant" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
              )}
              <div
                className={cn(
                  "rounded-2xl px-4 py-3 max-w-[80%]",
                  message.role === "user"
                    ? "bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-white"
                    : "bg-[var(--bg-secondary)] border border-[var(--border-color)]",
                  message.isError && "border-red-500/50"
                )}
              >
                {message.isStreaming && !message.content ? (
                  <div className="flex items-center gap-2 py-1">
                    <TypingIndicator />
                    <span className="text-sm text-[var(--text-muted)]">Thinking...</span>
                  </div>
                ) : (
                  <>
                    {message.role === "assistant" ? (
                      <MarkdownRenderer 
                        content={message.content} 
                        className="text-sm"
                      />
                    ) : (
                      <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                    )}
                    
                    {/* Streaming indicator */}
                    {message.isStreaming && message.content && (
                      <div className="mt-2 flex items-center gap-2">
                        <TypingIndicator />
                      </div>
                    )}
                    
                    {/* Message footer */}
                    {message.model && !message.isStreaming && (
                      <div className="mt-3 pt-2 border-t border-[var(--border-color)] flex items-center justify-between">
                        <span className="text-xs text-[var(--text-muted)]">{message.model}</span>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => copyToClipboard(message.content, message.id)}
                          >
                            {copiedId === message.id ? (
                              <Check className="h-3 w-3 text-green-500" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
              {message.role === "user" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
                  <span className="text-xs font-medium">You</span>
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything or use /commands..."
                  disabled={isLoading}
                  className="h-12 bg-[var(--bg-tertiary)] border-[var(--border-color)] pr-12 text-base"
                />
              </div>
              {isLoading ? (
                <Button
                  onClick={handleStop}
                  className="h-12 px-6 bg-red-500 hover:bg-red-600"
                >
                  <Square className="h-5 w-5" />
                </Button>
              ) : (
                <Button
                  onClick={handleSend}
                  disabled={!input.trim()}
                  className="h-12 px-6 bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] hover:opacity-90"
                >
                  <Send className="h-5 w-5" />
                </Button>
              )}
            </div>
            <p className="mt-2 text-xs text-[var(--text-muted)] text-center">
              Press Enter to send • {isLoading ? "Click Stop to cancel" : "Shift+Enter for new line"}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
