"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { CodeBlock } from "./code-block"
import { cn } from "@/lib/utils"

interface MarkdownRendererProps {
  content: string
  className?: string
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn("prose prose-invert prose-sm max-w-none", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
        // Code blocks
        code(props) {
          const { className, children, node, ...rest } = props
          const match = /language-(\w+)/.exec(className || '')
          const language = match ? match[1] : undefined
          
          // Check if this is an inline code block (no language class and short content)
          const isInline = !className && typeof children === 'string' && !children.includes('\n')
          
          if (isInline) {
            return (
              <code 
                className="px-1.5 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--accent-primary)] font-mono text-[0.9em]"
                {...rest}
              >
                {children}
              </code>
            )
          }
          
          return (
            <CodeBlock language={language}>
              {String(children)}
            </CodeBlock>
          )
        },
        
        // Paragraphs
        p({ children }) {
          return <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>
        },
        
        // Headers
        h1({ children }) {
          return <h1 className="text-xl font-bold mb-3 mt-4 first:mt-0 text-[var(--text-primary)]">{children}</h1>
        },
        h2({ children }) {
          return <h2 className="text-lg font-bold mb-2 mt-4 first:mt-0 text-[var(--text-primary)]">{children}</h2>
        },
        h3({ children }) {
          return <h3 className="text-base font-bold mb-2 mt-3 first:mt-0 text-[var(--text-primary)]">{children}</h3>
        },
        h4({ children }) {
          return <h4 className="text-sm font-bold mb-2 mt-3 first:mt-0 text-[var(--text-primary)]">{children}</h4>
        },
        
        // Lists
        ul({ children }) {
          return <ul className="list-disc list-inside mb-3 space-y-1 ml-2">{children}</ul>
        },
        ol({ children }) {
          return <ol className="list-decimal list-inside mb-3 space-y-1 ml-2">{children}</ol>
        },
        li({ children }) {
          return <li className="text-[var(--text-secondary)]">{children}</li>
        },
        
        // Links
        a({ href, children }) {
          return (
            <a 
              href={href} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-[var(--accent-primary)] hover:underline"
            >
              {children}
            </a>
          )
        },
        
        // Blockquotes
        blockquote({ children }) {
          return (
            <blockquote className="border-l-4 border-[var(--accent-primary)] pl-4 my-3 italic text-[var(--text-muted)]">
              {children}
            </blockquote>
          )
        },
        
        // Tables
        table({ children }) {
          return (
            <div className="overflow-x-auto my-3">
              <table className="min-w-full border border-[var(--border-color)] rounded">
                {children}
              </table>
            </div>
          )
        },
        thead({ children }) {
          return <thead className="bg-[var(--bg-tertiary)]">{children}</thead>
        },
        th({ children }) {
          return <th className="px-3 py-2 text-left text-sm font-semibold border-b border-[var(--border-color)]">{children}</th>
        },
        td({ children }) {
          return <td className="px-3 py-2 text-sm border-b border-[var(--border-color)]">{children}</td>
        },
        
        // Horizontal rule
        hr() {
          return <hr className="my-4 border-[var(--border-color)]" />
        },
        
        // Strong/Bold
        strong({ children }) {
          return <strong className="font-semibold text-[var(--text-primary)]">{children}</strong>
        },
        
        // Emphasis/Italic
        em({ children }) {
          return <em className="italic">{children}</em>
        },
        
        // Strikethrough
        del({ children }) {
          return <del className="line-through text-[var(--text-muted)]">{children}</del>
        },
        
        // Pre (wrapper for code blocks)
        pre({ children }) {
          // Let the code component handle everything
          return <>{children}</>
        },
      }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

