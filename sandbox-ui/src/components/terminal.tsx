"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import { Terminal as XTerminal } from "@xterm/xterm"
import { FitAddon } from "@xterm/addon-fit"
import { WebLinksAddon } from "@xterm/addon-web-links"
import "@xterm/xterm/css/xterm.css"

interface TerminalProps {
  sessionId?: string
  onReady?: () => void
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function Terminal({ sessionId = "default", onReady }: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<XTerminal | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const wsUrl = API_URL.replace("http", "ws")
    const ws = new WebSocket(`${wsUrl}/api/terminal/ws/${sessionId}`)
    
    ws.onopen = () => {
      setConnected(true)
      setError(null)
      
      // Send initial resize
      if (xtermRef.current && fitAddonRef.current) {
        fitAddonRef.current.fit()
        ws.send(JSON.stringify({
          type: "resize",
          rows: xtermRef.current.rows,
          cols: xtermRef.current.cols
        }))
      }
      
      onReady?.()
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === "output" && xtermRef.current) {
          xtermRef.current.write(data.data)
        }
      } catch (e) {
        // Raw data
        if (xtermRef.current) {
          xtermRef.current.write(event.data)
        }
      }
    }
    
    ws.onerror = () => {
      setError("Connection error")
      setConnected(false)
    }
    
    ws.onclose = () => {
      setConnected(false)
    }
    
    wsRef.current = ws
  }, [sessionId, onReady])

  useEffect(() => {
    if (!terminalRef.current) return

    // Create terminal
    const term = new XTerminal({
      theme: {
        background: "#0a0a12",
        foreground: "#e0e0e0",
        cursor: "#00d4ff",
        cursorAccent: "#0a0a12",
        selectionBackground: "#00d4ff33",
        black: "#0a0a12",
        red: "#ff4757",
        green: "#00ff88",
        yellow: "#ffa502",
        blue: "#00d4ff",
        magenta: "#ff00ff",
        cyan: "#00d4ff",
        white: "#e0e0e0",
        brightBlack: "#6c7086",
        brightRed: "#ff6b7a",
        brightGreen: "#00ff9d",
        brightYellow: "#ffb830",
        brightBlue: "#00e5ff",
        brightMagenta: "#ff33ff",
        brightCyan: "#00e5ff",
        brightWhite: "#ffffff",
      },
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
      fontSize: 13,
      lineHeight: 1.4,
      cursorBlink: true,
      cursorStyle: "bar",
      scrollback: 5000,
    })

    const fitAddon = new FitAddon()
    const webLinksAddon = new WebLinksAddon()
    
    term.loadAddon(fitAddon)
    term.loadAddon(webLinksAddon)
    
    term.open(terminalRef.current)
    fitAddon.fit()
    
    xtermRef.current = term
    fitAddonRef.current = fitAddon

    // Handle input
    term.onData((data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: "input",
          data: data
        }))
      }
    })

    // Handle resize
    const handleResize = () => {
      fitAddon.fit()
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: "resize",
          rows: term.rows,
          cols: term.cols
        }))
      }
    }

    window.addEventListener("resize", handleResize)
    
    // Connect to WebSocket
    connect()

    // Initial message
    term.writeln("\x1b[36m╔══════════════════════════════════════╗\x1b[0m")
    term.writeln("\x1b[36m║\x1b[0m     \x1b[1;32mChatOS Terminal\x1b[0m                \x1b[36m║\x1b[0m")
    term.writeln("\x1b[36m╚══════════════════════════════════════╝\x1b[0m")
    term.writeln("")

    return () => {
      window.removeEventListener("resize", handleResize)
      wsRef.current?.close()
      term.dispose()
    }
  }, [connect])

  // Reconnect button handler
  const handleReconnect = () => {
    wsRef.current?.close()
    setError(null)
    setTimeout(connect, 100)
  }

  return (
    <div className="h-full flex flex-col bg-[var(--bg-primary)]">
      {/* Status bar */}
      <div className="flex items-center justify-between px-3 py-1 text-xs border-b border-[var(--border-color)] bg-[var(--bg-secondary)]">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-[var(--success)]" : "bg-[var(--error)]"}`} />
          <span className="text-[var(--text-muted)]">
            {connected ? "Connected" : error || "Disconnected"}
          </span>
        </div>
        {!connected && (
          <button
            onClick={handleReconnect}
            className="text-[var(--accent-primary)] hover:underline"
          >
            Reconnect
          </button>
        )}
      </div>
      
      {/* Terminal container */}
      <div 
        ref={terminalRef} 
        className="flex-1 p-2 overflow-hidden"
        style={{ minHeight: 0 }}
      />
    </div>
  )
}

