"use client"

import { useEffect, useRef, useState } from "react"
import Editor, { OnMount, BeforeMount } from "@monaco-editor/react"
import type { editor } from "monaco-editor"
import { getLanguageFromPath } from "@/lib/api"
import { Loader2 } from "lucide-react"

interface CodeEditorProps {
  file: string | null
  content: string
  onChange: (content: string) => void
  onSave?: () => void
}

// ChatOS custom theme definition
const chatosTheme: editor.IStandaloneThemeData = {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "comment", foreground: "606070", fontStyle: "italic" },
    { token: "keyword", foreground: "00d4ff" },
    { token: "string", foreground: "00ff88" },
    { token: "number", foreground: "ff00aa" },
    { token: "type", foreground: "00d4ff" },
    { token: "class", foreground: "00d4ff" },
    { token: "function", foreground: "f0f0f5" },
    { token: "variable", foreground: "f0f0f5" },
    { token: "operator", foreground: "a0a0b0" },
    { token: "delimiter", foreground: "a0a0b0" },
    { token: "tag", foreground: "00d4ff" },
    { token: "attribute.name", foreground: "ff00aa" },
    { token: "attribute.value", foreground: "00ff88" },
  ],
  colors: {
    "editor.background": "#0a0a0f",
    "editor.foreground": "#f0f0f5",
    "editor.lineHighlightBackground": "#12121a",
    "editor.selectionBackground": "#2a2a40",
    "editor.inactiveSelectionBackground": "#1a1a25",
    "editorCursor.foreground": "#00d4ff",
    "editorLineNumber.foreground": "#606070",
    "editorLineNumber.activeForeground": "#00d4ff",
    "editorIndentGuide.background": "#1a1a25",
    "editorIndentGuide.activeBackground": "#2a2a40",
    "editor.selectionHighlightBackground": "#00d4ff20",
    "editorBracketMatch.background": "#00d4ff30",
    "editorBracketMatch.border": "#00d4ff",
    "editorGutter.background": "#0a0a0f",
    "editorWidget.background": "#12121a",
    "editorWidget.border": "#ffffff14",
    "editorSuggestWidget.background": "#12121a",
    "editorSuggestWidget.border": "#ffffff14",
    "editorSuggestWidget.selectedBackground": "#1a1a25",
    "editorHoverWidget.background": "#12121a",
    "editorHoverWidget.border": "#ffffff14",
    "scrollbarSlider.background": "#22223060",
    "scrollbarSlider.hoverBackground": "#22223080",
    "scrollbarSlider.activeBackground": "#222230a0",
    "minimap.background": "#0a0a0f",
  },
}

export function CodeEditor({ file, content, onChange, onSave }: CodeEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)
  const [isReady, setIsReady] = useState(false)

  const handleBeforeMount: BeforeMount = (monaco) => {
    // Define custom theme
    monaco.editor.defineTheme("chatos-dark", chatosTheme)
  }

  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor
    setIsReady(true)

    // Set up keyboard shortcuts
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      onSave?.()
    })

    // Focus the editor
    editor.focus()
  }

  const handleChange = (value: string | undefined) => {
    onChange(value || "")
  }

  // Get language from file path
  const language = file ? getLanguageFromPath(file) : "plaintext"

  if (!file) {
    return (
      <div className="flex h-full items-center justify-center bg-[var(--bg-primary)]">
        <div className="text-center">
          <div className="text-5xl mb-4">💻</div>
          <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-2">
            ChatOS Sandbox
          </h2>
          <p className="text-[var(--text-secondary)] max-w-md">
            Select a file from the explorer to start editing, or create a new file.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full w-full relative">
      {!isReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-[var(--bg-primary)] z-10">
          <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-primary)]" />
        </div>
      )}
      <Editor
        height="100%"
        language={language}
        theme="chatos-dark"
        value={content}
        onChange={handleChange}
        beforeMount={handleBeforeMount}
        onMount={handleEditorMount}
        loading={
          <div className="flex items-center justify-center h-full bg-[var(--bg-primary)]">
            <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-primary)]" />
          </div>
        }
        options={{
          fontSize: 14,
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontLigatures: true,
          minimap: {
            enabled: true,
            scale: 1,
            showSlider: "mouseover",
          },
          scrollBeyondLastLine: false,
          wordWrap: "on",
          automaticLayout: true,
          tabSize: 2,
          insertSpaces: true,
          renderWhitespace: "selection",
          cursorBlinking: "smooth",
          cursorSmoothCaretAnimation: "on",
          smoothScrolling: true,
          padding: { top: 16, bottom: 16 },
          lineNumbers: "on",
          glyphMargin: true,
          folding: true,
          bracketPairColorization: {
            enabled: true,
          },
          guides: {
            bracketPairs: true,
            indentation: true,
          },
          suggest: {
            showKeywords: true,
            showSnippets: true,
          },
          quickSuggestions: {
            other: true,
            comments: false,
            strings: false,
          },
        }}
      />
    </div>
  )
}

