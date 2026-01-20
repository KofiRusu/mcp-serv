'use client'

import { useEffect, useCallback, useState } from 'react'
import { Play, Square, RefreshCw, Wifi, WifiOff, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { 
  useThoughtNetworkStore, 
  fetchDAGManifest, 
  executeCycle,
  type DAGNode,
  type ExecutionLogEntry 
} from './thought-network-store'

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']

function StatusBadge({ status }: { status: DAGNode['status'] }) {
  const styles = {
    idle: 'bg-gray-700 text-gray-300',
    running: 'bg-blue-600 text-white animate-pulse',
    passed: 'bg-green-600 text-white',
    warned: 'bg-yellow-600 text-white',
    blocked: 'bg-red-600 text-white',
    error: 'bg-red-800 text-white',
  }
  return (
    <span className={cn('px-2 py-0.5 rounded text-xs font-medium', styles[status])}>
      {status.toUpperCase()}
    </span>
  )
}

function NodeCard({ node }: { node: DAGNode }) {
  const typeStyles = {
    input: 'border-blue-500/50 bg-blue-950/30',
    thought: 'border-purple-500/50 bg-purple-950/30',
    filter: 'border-yellow-500/50 bg-yellow-950/30',
    arbiter: 'border-cyan-500/50 bg-cyan-950/30',
    risk: 'border-orange-500/50 bg-orange-950/30',
    execution: 'border-green-500/50 bg-green-950/30',
    audit: 'border-gray-500/50 bg-gray-950/30',
  }

  return (
    <div className={cn(
      'p-2 rounded border min-w-[120px] text-center',
      typeStyles[node.type]
    )}>
      <div className="text-xs text-gray-400 mb-1">{node.type}</div>
      <div className="text-sm font-medium text-white mb-1">{node.label}</div>
      <StatusBadge status={node.status} />
    </div>
  )
}

function ExecutionLog({ entries }: { entries: ExecutionLogEntry[] }) {
  const getIcon = (type: ExecutionLogEntry['type']) => {
    switch (type) {
      case 'thought': return <div className="w-2 h-2 rounded-full bg-purple-500" />
      case 'filter': return <AlertTriangle className="w-3 h-3 text-yellow-500" />
      case 'decision': return <CheckCircle className="w-3 h-3 text-cyan-500" />
      case 'risk': return <AlertTriangle className="w-3 h-3 text-orange-500" />
      case 'execution': return <CheckCircle className="w-3 h-3 text-green-500" />
      case 'error': return <XCircle className="w-3 h-3 text-red-500" />
      default: return <div className="w-2 h-2 rounded-full bg-gray-500" />
    }
  }

  return (
    <div className="h-full overflow-y-auto p-2 space-y-1">
      {entries.length === 0 ? (
        <div className="text-gray-500 text-sm text-center py-4">
          No activity yet. Click Execute to run a cycle.
        </div>
      ) : (
        entries.map((entry) => (
          <div key={entry.id} className="flex items-start gap-2 text-xs py-1 border-b border-gray-800">
            {getIcon(entry.type)}
            <div className="flex-1">
              <span className="text-gray-400">{entry.timestamp}</span>
              <span className="text-gray-300 ml-2">{entry.message}</span>
            </div>
          </div>
        ))
      )}
    </div>
  )
}

function DAGVisualization({ nodes }: { nodes: DAGNode[] }) {
  const nodesByType: Record<string, DAGNode[]> = {}
  nodes.forEach(node => {
    if (!nodesByType[node.type]) nodesByType[node.type] = []
    nodesByType[node.type].push(node)
  })

  const columns = ['input', 'thought', 'filter', 'arbiter', 'risk', 'execution', 'audit']

  return (
    <div className="h-full flex items-center justify-around p-4 overflow-x-auto">
      {columns.map((type, colIdx) => (
        <div key={type} className="flex flex-col gap-2 items-center">
          {nodesByType[type]?.map((node) => (
            <NodeCard key={node.id} node={node} />
          ))}
          {colIdx < columns.length - 1 && (
            <div className="absolute" style={{ left: `${(colIdx + 1) * (100 / columns.length)}%` }}>
              <div className="w-8 h-0.5 bg-gray-700" />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export function ThoughtNetworkPanel() {
  const {
    nodes,
    edges,
    executionLog,
    isConnected,
    isExecuting,
    lastCycleResult,
    selectedSymbol,
    tradingMode,
    setNodes,
    setEdges,
    addLogEntry,
    clearLog,
    setConnected,
    setExecuting,
    setLastCycleResult,
    setSelectedSymbol,
    setTradingMode,
    updateNodeStatus,
    resetNodeStatuses,
  } = useThoughtNetworkStore()

  const [wsRef, setWsRef] = useState<WebSocket | null>(null)

  useEffect(() => {
    fetchDAGManifest().then(({ nodes, edges }) => {
      setNodes(nodes)
      setEdges(edges)
    })
  }, [setNodes, setEdges])

  const connectWebSocket = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/thought-lines/ws/status`)
    
    ws.onopen = () => {
      setConnected(true)
      addLogEntry({
        id: Date.now().toString(),
        timestamp: new Date().toLocaleTimeString(),
        type: 'info',
        message: 'Connected to thought-lines WebSocket',
      })
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'event') {
          const eventType = data.event_type as string
          
          if (eventType.startsWith('thought.')) {
            const thoughtId = data.payload?.thought_id
            if (eventType === 'thought.started') {
              updateNodeStatus('thought_trend', 'running')
            } else if (eventType === 'thought.completed') {
              updateNodeStatus('thought_trend', data.payload?.status === 'passed' ? 'passed' : 'warned')
            } else if (eventType === 'thought.blocked') {
              updateNodeStatus('thought_trend', 'blocked')
            }
          }
          
          addLogEntry({
            id: Date.now().toString(),
            timestamp: new Date().toLocaleTimeString(),
            type: eventType.split('.')[0] as ExecutionLogEntry['type'],
            message: `${eventType}: ${JSON.stringify(data.payload).slice(0, 100)}`,
            details: data.payload,
          })
        }
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }

    ws.onclose = () => {
      setConnected(false)
      addLogEntry({
        id: Date.now().toString(),
        timestamp: new Date().toLocaleTimeString(),
        type: 'info',
        message: 'WebSocket disconnected',
      })
    }

    ws.onerror = () => {
      setConnected(false)
    }

    setWsRef(ws)
    return ws
  }, [setConnected, addLogEntry, updateNodeStatus])

  useEffect(() => {
    const ws = connectWebSocket()
    return () => {
      ws.close()
    }
  }, [connectWebSocket])

  const handleExecute = async () => {
    if (isExecuting) return
    
    setExecuting(true)
    resetNodeStatuses()
    
    updateNodeStatus('live_feed', 'running')
    addLogEntry({
      id: Date.now().toString(),
      timestamp: new Date().toLocaleTimeString(),
      type: 'info',
      message: `Executing cycle for ${selectedSymbol} in ${tradingMode} mode...`,
    })

    const result = await executeCycle(selectedSymbol, tradingMode)
    
    if (result) {
      setLastCycleResult(result)
      updateNodeStatus('live_feed', 'passed')
      updateNodeStatus('arbiter', result.arbiterDecision.action === 'HOLD' ? 'passed' : 'passed')
      updateNodeStatus('risk', result.riskResult.approved ? 'passed' : 'blocked')
      updateNodeStatus('execution', result.executionResult?.success ? 'passed' : 'idle')
      updateNodeStatus('audit', 'passed')
      
      addLogEntry({
        id: Date.now().toString(),
        timestamp: new Date().toLocaleTimeString(),
        type: 'decision',
        message: `Cycle complete: ${result.arbiterDecision.action} (${result.durationMs.toFixed(0)}ms)`,
        details: result,
      })
    } else {
      addLogEntry({
        id: Date.now().toString(),
        timestamp: new Date().toLocaleTimeString(),
        type: 'error',
        message: 'Cycle execution failed',
      })
    }

    setExecuting(false)
  }

  return (
    <div className="h-[280px] bg-[#0a0a0f] border-t border-gray-800 flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-900/50">
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-semibold text-gray-200">Chat Model Data Processing</h3>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Wifi className="w-4 h-4 text-green-500" />
            ) : (
              <WifiOff className="w-4 h-4 text-red-500" />
            )}
            <span className="text-xs text-gray-500">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
            <SelectTrigger className="w-[120px] h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SYMBOLS.map(s => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Select value={tradingMode} onValueChange={(v) => setTradingMode(v as 'paper' | 'live')}>
            <SelectTrigger className="w-[90px] h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="paper">Paper</SelectItem>
              <SelectItem value="live">Live</SelectItem>
            </SelectContent>
          </Select>

          <Button
            size="sm"
            variant="outline"
            onClick={clearLog}
            className="h-8"
          >
            <RefreshCw className="w-3 h-3 mr-1" />
            Clear
          </Button>

          <Button
            size="sm"
            onClick={handleExecute}
            disabled={isExecuting}
            className={cn(
              "h-8",
              isExecuting && "animate-pulse"
            )}
          >
            {isExecuting ? (
              <>
                <Square className="w-3 h-3 mr-1" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-3 h-3 mr-1" />
                Execute
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-[70%] border-r border-gray-800 relative">
          <DAGVisualization nodes={nodes} />
        </div>
        <div className="w-[30%]">
          <ExecutionLog entries={executionLog} />
        </div>
      </div>

      {lastCycleResult && (
        <div className="px-4 py-1 border-t border-gray-800 bg-gray-900/30 flex items-center gap-4 text-xs">
          <Badge variant="outline" className="text-xs">
            {lastCycleResult.arbiterDecision.action as string}
          </Badge>
          <span className="text-gray-500">
            Confidence: {((lastCycleResult.arbiterDecision.confidence as number) * 100).toFixed(0)}%
          </span>
          <span className="text-gray-500">
            Duration: {lastCycleResult.durationMs.toFixed(0)}ms
          </span>
          <span className="text-gray-500">
            Thoughts: {lastCycleResult.thoughts.length}
          </span>
        </div>
      )}
    </div>
  )
}
