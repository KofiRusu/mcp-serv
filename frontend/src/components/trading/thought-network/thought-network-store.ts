import { create } from 'zustand'

export interface DAGNode {
  id: string
  type: 'input' | 'thought' | 'filter' | 'arbiter' | 'risk' | 'execution' | 'audit'
  label: string
  status: 'idle' | 'running' | 'passed' | 'warned' | 'blocked' | 'error'
  x: number
  y: number
}

export interface DAGEdge {
  id: string
  source: string
  target: string
  animated: boolean
}

export interface ExecutionLogEntry {
  id: string
  timestamp: string
  type: 'thought' | 'filter' | 'decision' | 'risk' | 'execution' | 'info' | 'error'
  message: string
  details?: Record<string, unknown>
}

export interface CycleResult {
  cycleId: string
  symbol: string
  thoughts: unknown[]
  arbiterDecision: Record<string, unknown>
  riskResult: Record<string, unknown>
  executionResult?: Record<string, unknown>
  durationMs: number
}

interface ThoughtNetworkState {
  nodes: DAGNode[]
  edges: DAGEdge[]
  executionLog: ExecutionLogEntry[]
  isConnected: boolean
  isExecuting: boolean
  lastCycleResult: CycleResult | null
  selectedSymbol: string
  tradingMode: 'paper' | 'live'
  
  setNodes: (nodes: DAGNode[]) => void
  setEdges: (edges: DAGEdge[]) => void
  updateNodeStatus: (nodeId: string, status: DAGNode['status']) => void
  addLogEntry: (entry: ExecutionLogEntry) => void
  clearLog: () => void
  setConnected: (connected: boolean) => void
  setExecuting: (executing: boolean) => void
  setLastCycleResult: (result: CycleResult | null) => void
  setSelectedSymbol: (symbol: string) => void
  setTradingMode: (mode: 'paper' | 'live') => void
  resetNodeStatuses: () => void
}

export const useThoughtNetworkStore = create<ThoughtNetworkState>((set, get) => ({
  nodes: [],
  edges: [],
  executionLog: [],
  isConnected: false,
  isExecuting: false,
  lastCycleResult: null,
  selectedSymbol: 'BTCUSDT',
  tradingMode: 'paper',

  setNodes: (nodes) => set({ nodes }),
  
  setEdges: (edges) => set({ edges }),
  
  updateNodeStatus: (nodeId, status) => set((state) => ({
    nodes: state.nodes.map(node => 
      node.id === nodeId ? { ...node, status } : node
    )
  })),
  
  addLogEntry: (entry) => set((state) => ({
    executionLog: [entry, ...state.executionLog].slice(0, 100)
  })),
  
  clearLog: () => set({ executionLog: [] }),
  
  setConnected: (connected) => set({ isConnected: connected }),
  
  setExecuting: (executing) => set({ isExecuting: executing }),
  
  setLastCycleResult: (result) => set({ lastCycleResult: result }),
  
  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
  
  setTradingMode: (mode) => set({ tradingMode: mode }),
  
  resetNodeStatuses: () => set((state) => ({
    nodes: state.nodes.map(node => ({ ...node, status: 'idle' as const }))
  })),
}))

export async function fetchDAGManifest(): Promise<{ nodes: DAGNode[], edges: DAGEdge[] }> {
  try {
    const response = await fetch('/api/thought-lines/dag')
    if (!response.ok) throw new Error('Failed to fetch DAG')
    const data = await response.json()
    return {
      nodes: data.nodes.map((n: DAGNode) => ({ ...n, status: 'idle' })),
      edges: data.edges.map((e: DAGEdge) => ({ ...e, animated: false })),
    }
  } catch (error) {
    console.error('Error fetching DAG:', error)
    return { nodes: [], edges: [] }
  }
}

export async function executeCycle(symbol: string, mode: 'paper' | 'live'): Promise<CycleResult | null> {
  try {
    const response = await fetch('/api/thought-lines/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, mode }),
    })
    if (!response.ok) throw new Error('Execution failed')
    const data = await response.json()
    return {
      cycleId: data.cycle_id,
      symbol: data.symbol,
      thoughts: data.thoughts,
      arbiterDecision: data.arbiter_decision,
      riskResult: data.risk_result,
      executionResult: data.execution_result,
      durationMs: data.duration_ms,
    }
  } catch (error) {
    console.error('Execution error:', error)
    return null
  }
}
