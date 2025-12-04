"use client"

import { cn } from "@/lib/utils"

interface TypingIndicatorProps {
  className?: string
}

export function TypingIndicator({ className }: TypingIndicatorProps) {
  return (
    <div className={cn("flex items-center gap-1", className)}>
      <span className="w-2 h-2 rounded-full bg-[var(--accent-primary)] animate-bounce [animation-delay:-0.3s]" />
      <span className="w-2 h-2 rounded-full bg-[var(--accent-primary)] animate-bounce [animation-delay:-0.15s]" />
      <span className="w-2 h-2 rounded-full bg-[var(--accent-primary)] animate-bounce" />
    </div>
  )
}

