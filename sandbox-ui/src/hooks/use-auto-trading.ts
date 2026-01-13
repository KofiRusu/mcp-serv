/**
 * use-auto-trading.ts - SSE Hook for Auto-Trading Activity Stream
 * 
 * Connects to the auto-trading activity stream and provides:
 * - Real-time activity updates
 * - Connection state management
 * - Auto-reconnection on disconnect
 * - Activity history
 */

import { useState, useEffect, useCallback, useRef } from 'react'

// =============================================================================
// Types
// =============================================================================

export type ActivityType = 'analyzing' | 'signal' | 'executed' | 'error' | 'info'

export type TradingSignal = 'LONG' | 'SHORT' | 'CLOSE' | 'HOLD'

export interface ActivityEntry {
  id: string
  timestamp: string
  type: ActivityType
  symbol: string
  message: string
  signal?: TradingSignal
  reasoning?: string
  entry_price?: number
  stop_loss?: number
  take_profit?: number
  size?: number
  pnl?: number
}

export interface Position {
  id: string
  symbol: string
  side: 'long' | 'short'
  size: number
  entry_price: number
  current_price: number
  pnl: number
  pnl_percent: number
  stop_loss?: number
  take_profit?: number
  opened_at: string
}

export interface AutoTradingStatus {
  running: boolean
  mode: 'paper' | 'live'
  started_at?: string
  cycles_completed: number
  total_trades: number
  winning_trades: number
  current_pnl: number
  positions: Position[]
  config: {
    mode: 'paper' | 'live'
    interval_seconds: number
    symbols: string[]
    risk_per_trade: number
    max_positions: number
  }
}

export interface UseAutoTradingOptions {
  apiBaseUrl?: string
  autoConnect?: boolean
  maxActivities?: number
}

export interface UseAutoTradingReturn {
  // State
  connected: boolean
  connecting: boolean
  status: AutoTradingStatus | null
  activities: ActivityEntry[]
  error: string | null
  
  // Actions
  connect: () => void
  disconnect: () => void
  start: (options?: StartOptions) => Promise<boolean>
  stop: () => Promise<boolean>
  reset: () => Promise<boolean>
  refreshStatus: () => Promise<void>
  clearActivities: () => void
}

interface StartOptions {
  mode?: 'paper' | 'live'
  interval_seconds?: number
  symbols?: string[]
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_API_BASE = process.env.NEXT_PUBLIC_API_URL || '' // Empty = same origin
const MAX_ACTIVITIES = 100
const RECONNECT_DELAY = 3000

// =============================================================================
// Hook
// =============================================================================

export function useAutoTrading(options: UseAutoTradingOptions = {}): UseAutoTradingReturn {
  const {
    apiBaseUrl = DEFAULT_API_BASE,
    autoConnect = false,
    maxActivities = MAX_ACTIVITIES,
  } = options

  // State
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [status, setStatus] = useState<AutoTradingStatus | null>(null)
  const [activities, setActivities] = useState<ActivityEntry[]>([])
  const [error, setError] = useState<string | null>(null)

  // Refs
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // ==========================================================================
  // Activity Management
  // ==========================================================================

  const addActivity = useCallback((entry: ActivityEntry) => {
    setActivities((prev) => {
      const updated = [...prev, entry]
      // Keep only the last maxActivities
      if (updated.length > maxActivities) {
        return updated.slice(-maxActivities)
      }
      return updated
    })
  }, [maxActivities])

  const clearActivities = useCallback(() => {
    setActivities([])
  }, [])

  // ==========================================================================
  // SSE Connection
  // ==========================================================================

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    setConnected(false)
    setConnecting(false)
  }, [])

  const connect = useCallback(() => {
    // Clean up existing connection
    disconnect()
    
    setConnecting(true)
    setError(null)

    try {
      const eventSource = new EventSource(`${apiBaseUrl}/api/auto-trading/activity`)
      eventSourceRef.current = eventSource

      eventSource.onopen = () => {
        setConnected(true)
        setConnecting(false)
        setError(null)
      }

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          // Handle different message types
          if (data.type === 'connected' || data.type === 'keepalive') {
            // Connection/keepalive messages, ignore
            return
          }
          
          // Activity entry
          if (data.id && data.timestamp) {
            addActivity(data as ActivityEntry)
          }
        } catch (e) {
          console.error('Failed to parse SSE message:', e)
        }
      }

      eventSource.onerror = () => {
        setConnected(false)
        setConnecting(false)
        
        // Attempt reconnect
        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null
            connect()
          }, RECONNECT_DELAY)
        }
      }
    } catch (e) {
      setConnecting(false)
      setError(`Failed to connect: ${e}`)
    }
  }, [apiBaseUrl, disconnect, addActivity])

  // ==========================================================================
  // API Actions
  // ==========================================================================

  const refreshStatus = useCallback(async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/auto-trading/status`)
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
      }
    } catch (e) {
      console.error('Failed to fetch status:', e)
    }
  }, [apiBaseUrl])

  const start = useCallback(async (opts: StartOptions = {}): Promise<boolean> => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/auto-trading/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: opts.mode || 'paper',
          interval_seconds: opts.interval_seconds || 15,
          symbols: opts.symbols || ['BTCUSDT'],
        }),
      })

      if (response.ok) {
        await refreshStatus()
        return true
      } else {
        const error = await response.json()
        setError(error.detail || 'Failed to start')
        return false
      }
    } catch (e) {
      setError(`Failed to start: ${e}`)
      return false
    }
  }, [apiBaseUrl, refreshStatus])

  const stop = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/auto-trading/stop`, {
        method: 'POST',
      })

      if (response.ok) {
        await refreshStatus()
        return true
      } else {
        const error = await response.json()
        setError(error.detail || 'Failed to stop')
        return false
      }
    } catch (e) {
      setError(`Failed to stop: ${e}`)
      return false
    }
  }, [apiBaseUrl, refreshStatus])

  const reset = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/auto-trading/reset`, {
        method: 'POST',
      })

      if (response.ok) {
        clearActivities()
        await refreshStatus()
        return true
      } else {
        const error = await response.json()
        setError(error.detail || 'Failed to reset')
        return false
      }
    } catch (e) {
      setError(`Failed to reset: ${e}`)
      return false
    }
  }, [apiBaseUrl, clearActivities, refreshStatus])

  // ==========================================================================
  // Effects
  // ==========================================================================

  // Auto-connect on mount if requested
  useEffect(() => {
    if (autoConnect) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [autoConnect, connect, disconnect])

  // Fetch initial status
  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  // Poll status while running
  useEffect(() => {
    if (status?.running) {
      const interval = setInterval(refreshStatus, 5000)
      return () => clearInterval(interval)
    }
  }, [status?.running, refreshStatus])

  return {
    connected,
    connecting,
    status,
    activities,
    error,
    connect,
    disconnect,
    start,
    stop,
    reset,
    refreshStatus,
    clearActivities,
  }
}

// =============================================================================
// Export Types
// =============================================================================

export type { UseAutoTradingOptions, UseAutoTradingReturn, StartOptions }

