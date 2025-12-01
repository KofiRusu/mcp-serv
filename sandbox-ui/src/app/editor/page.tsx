"use client"

import { EditorInterface } from "@/components/editor-interface"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { MessageSquare, Home } from "lucide-react"

export default function EditorPage() {
  return (
    <div className="h-screen flex flex-col">
      {/* Quick nav back to chat */}
      <div className="absolute top-2 left-2 z-50">
        <Link href="/">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-2 bg-[var(--bg-secondary)]/80 backdrop-blur-sm hover:bg-[var(--bg-tertiary)]"
          >
            <Home className="h-4 w-4" />
            <MessageSquare className="h-4 w-4" />
            Back to Chat
          </Button>
        </Link>
      </div>
      <EditorInterface />
    </div>
  )
}
