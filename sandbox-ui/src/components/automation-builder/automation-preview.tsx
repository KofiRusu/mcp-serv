'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Play, 
  Square, 
  Code, 
  Terminal, 
  Rocket, 
  RefreshCw,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle
} from 'lucide-react'
import { cn } from '@/lib/utils'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '' // Empty = same origin

interface AutomationPreviewProps {
  automationId: string | null
  generatedCode: string | null
  status: 'draft' | 'testing' | 'deployed' | 'stopped' | 'error'
  onRun: () => Promise<void>
  onStop: () => Promise<void>
  onDeploy: () => Promise<void>
}

export function AutomationPreview({
  automationId,
  generatedCode,
  status,
  onRun,
  onStop,
  onDeploy
}: AutomationPreviewProps) {
  const [output, setOutput] = useState<string[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [isDeploying, setIsDeploying] = useState(false)
  const outputRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Auto-scroll output
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [output])

  // Connect to WebSocket for real-time output
  useEffect(() => {
    if (!automationId || status !== 'testing') return

    // Build WebSocket URL from current location or API_BASE
    let wsUrl: string
    if (typeof window !== 'undefined') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = API_BASE || window.location.host
      wsUrl = API_BASE ? API_BASE.replace(/^https?:/, protocol) : `${protocol}//${host}`
    } else {
      wsUrl = API_BASE || 'ws://localhost:8000'
    }
    const ws = new WebSocket(`${wsUrl}/api/v1/automations/${automationId}/ws/output`)
    
    ws.onmessage = (event) => {
      setOutput(prev => [...prev, event.data])
    }

    ws.onerror = () => {
      setOutput(prev => [...prev, '[WebSocket Error] Could not connect to output stream'])
    }

    wsRef.current = ws

    return () => {
      ws.close()
    }
  }, [automationId, status])

  // Fetch output periodically as fallback
  useEffect(() => {
    if (!automationId || status !== 'testing') return

    const fetchOutput = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/automations/${automationId}/output?lines=50`)
        if (res.ok) {
          const data = await res.json()
          if (data.output?.length > 0) {
            setOutput(data.output)
          }
        }
      } catch (e) {
        // Ignore
      }
    }

    const interval = setInterval(fetchOutput, 2000)
    return () => clearInterval(interval)
  }, [automationId, status])

  const handleRun = async () => {
    setIsRunning(true)
    setOutput([])
    try {
      await onRun()
    } finally {
      setIsRunning(false)
    }
  }

  const handleStop = async () => {
    try {
      await onStop()
      setOutput(prev => [...prev, '[Stopped] Automation stopped by user'])
    } catch (e) {
      // Ignore
    }
  }

  const handleDeploy = async () => {
    setIsDeploying(true)
    try {
      await onDeploy()
      setOutput(prev => [...prev, '[Deployed] Automation deployed as Docker container'])
    } finally {
      setIsDeploying(false)
    }
  }

  const getStatusBadge = () => {
    switch (status) {
      case 'testing':
        return (
          <span className="flex items-center gap-1 text-xs text-amber-400">
            <Loader2 className="w-3 h-3 animate-spin" />
            Running
          </span>
        )
      case 'deployed':
        return (
          <span className="flex items-center gap-1 text-xs text-emerald-400">
            <CheckCircle2 className="w-3 h-3" />
            Deployed
          </span>
        )
      case 'error':
        return (
          <span className="flex items-center gap-1 text-xs text-red-400">
            <XCircle className="w-3 h-3" />
            Error
          </span>
        )
      case 'stopped':
        return (
          <span className="flex items-center gap-1 text-xs text-gray-400">
            <Square className="w-3 h-3" />
            Stopped
          </span>
        )
      default:
        return (
          <span className="flex items-center gap-1 text-xs text-gray-500">
            <AlertCircle className="w-3 h-3" />
            Draft
          </span>
        )
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-900/50 border-t border-gray-800">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-white">Preview</h3>
          {getStatusBadge()}
        </div>
        <div className="flex items-center gap-2">
          {status === 'testing' ? (
            <Button size="sm" variant="destructive" onClick={handleStop}>
              <Square className="w-3 h-3 mr-1" />
              Stop
            </Button>
          ) : (
            <Button 
              size="sm" 
              onClick={handleRun}
              disabled={!generatedCode || isRunning}
              className="bg-emerald-600 hover:bg-emerald-500"
            >
              {isRunning ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <Play className="w-3 h-3 mr-1" />
              )}
              Test
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={handleDeploy}
            disabled={!generatedCode || isDeploying || status === 'testing'}
            className="border-purple-500/50 text-purple-400 hover:bg-purple-500/10"
          >
            {isDeploying ? (
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            ) : (
              <Rocket className="w-3 h-3 mr-1" />
            )}
            Deploy
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="output" className="flex-1 flex flex-col">
        <TabsList className="grid grid-cols-2 mx-3 mt-2 bg-gray-800">
          <TabsTrigger value="output" className="text-xs gap-1">
            <Terminal className="w-3 h-3" />
            Output
          </TabsTrigger>
          <TabsTrigger value="code" className="text-xs gap-1">
            <Code className="w-3 h-3" />
            Code
          </TabsTrigger>
        </TabsList>

        <TabsContent value="output" className="flex-1 m-0 p-3">
          <ScrollArea className="h-full" ref={outputRef}>
            <div className="font-mono text-xs space-y-0.5">
              {output.length === 0 ? (
                <p className="text-gray-500">
                  {generatedCode 
                    ? 'Click "Test" to run the automation and see output here.'
                    : 'Generate an automation first to see its output.'}
                </p>
              ) : (
                output.map((line, i) => (
                  <p 
                    key={i} 
                    className={cn(
                      'whitespace-pre-wrap',
                      line.includes('[Error]') || line.includes('Error:') 
                        ? 'text-red-400' 
                        : line.includes('[Stopped]') || line.includes('[Deployed]')
                        ? 'text-amber-400'
                        : 'text-gray-300'
                    )}
                  >
                    {line}
                  </p>
                ))
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="code" className="flex-1 m-0 p-3">
          <ScrollArea className="h-full">
            {generatedCode ? (
              <pre className="font-mono text-xs text-gray-300 whitespace-pre-wrap">
                {generatedCode}
              </pre>
            ) : (
              <p className="text-xs text-gray-500">
                No code generated yet. Use the AI chat to describe what you want to build.
              </p>
            )}
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default AutomationPreview

