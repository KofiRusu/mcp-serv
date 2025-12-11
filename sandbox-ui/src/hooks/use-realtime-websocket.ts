"use client"

import { useState, useEffect, useCallback, useRef } from 'react'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface NewsItem {
  id: string
  title: string
  content?: string
  source: string
  url?: string
  timestamp: string
  symbols?: string[]
  sentiment?: 'bullish' | 'bearish' | 'neutral'
}

export interface SentimentData {
  value: number
  label: string
  timestamp: string
}

export interface RealtimeData {
  type: string
  data: unknown
  timestamp: number
}

export interface UseRealtimeWebSocketOptions {
  url?: string
  reconnectInterval?: number
  maxReconnectAttempts?: number
  onMessage?: (data: RealtimeData) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
}

export interface UseRealtimeWebSocketReturn {
  status: ConnectionStatus
  lastMessage: RealtimeData | null
  send: (data: unknown) => void
  connect: () => void
  disconnect: () => void
  isConnected: boolean
  news: NewsItem[]
  sentiment: SentimentData | null
  lastUpdate: Date | null
  refresh: () => void
}

const DEFAULT_WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/realtime'

export function useRealtimeWebSocket(
  _channel: string | UseRealtimeWebSocketOptions = {}
): UseRealtimeWebSocketReturn {
  // Handle both string channel and options object
  const options: UseRealtimeWebSocketOptions = typeof _channel === 'string' ? {} : _channel
  
  const {
    url = DEFAULT_WS_URL,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
  } = options

  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const [lastMessage, setLastMessage] = useState<RealtimeData | null>(null)
  const [news, setNews] = useState<NewsItem[]>([])
  const [sentiment, setSentiment] = useState<SentimentData | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
  }, [])

  const disconnect = useCallback(() => {
    clearReconnectTimeout()
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setStatus('disconnected')
  }, [clearReconnectTimeout])

  const connect = useCallback(() => {
    // Don't connect if already connected or connecting
    if (wsRef.current?.readyState === WebSocket.OPEN || 
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }

    setStatus('connecting')

    try {
      const ws = new WebSocket(url)

      ws.onopen = () => {
        setStatus('connected')
        reconnectAttemptsRef.current = 0
        onConnect?.()
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as RealtimeData
          setLastMessage(data)
          setLastUpdate(new Date())
          
          // Handle different message types
          if (data.type === 'news' && Array.isArray(data.data)) {
            setNews(data.data as NewsItem[])
          } else if (data.type === 'sentiment' && data.data) {
            setSentiment(data.data as SentimentData)
          }
          
          onMessage?.(data)
        } catch {
          // Handle non-JSON messages
          const data: RealtimeData = {
            type: 'raw',
            data: event.data,
            timestamp: Date.now(),
          }
          setLastMessage(data)
          onMessage?.(data)
        }
      }

      ws.onclose = () => {
        setStatus('disconnected')
        wsRef.current = null
        onDisconnect?.()

        // Attempt to reconnect
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        }
      }

      ws.onerror = (error) => {
        setStatus('error')
        onError?.(error)
      }

      wsRef.current = ws
    } catch {
      setStatus('error')
    }
  }, [url, reconnectInterval, maxReconnectAttempts, onMessage, onConnect, onDisconnect, onError])

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }, [])

  const refresh = useCallback(() => {
    disconnect()
    connect()
  }, [disconnect, connect])

  // Auto-connect on mount (disabled by default - call connect() manually)
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    status,
    lastMessage,
    send,
    connect,
    disconnect,
    isConnected: status === 'connected',
    news,
    sentiment,
    lastUpdate,
    refresh,
  }
}

export default useRealtimeWebSocket

