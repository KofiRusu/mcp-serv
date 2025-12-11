"use client"

import { useState, useEffect, useCallback } from 'react'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error' | 'fallback'

export interface TradingDataReturn {
  balance: number
  currency: string
  isLiveMode: boolean
  isExchangeConnected: boolean
  exchangeName: string | null
  loading: boolean
  error: string | null
  connectionStatus: ConnectionStatus
  isFallingBackToPaper: boolean
  retry: () => void
}

const DEFAULT_PAPER_BALANCE = 100000 // $100,000 paper trading balance

export function useTradingData(): TradingDataReturn {
  const [balance, setBalance] = useState(DEFAULT_PAPER_BALANCE)
  const [currency, setCurrency] = useState('USD')
  const [isLiveMode, setIsLiveMode] = useState(false)
  const [isExchangeConnected, setIsExchangeConnected] = useState(false)
  const [exchangeName, setExchangeName] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting')
  const [isFallingBackToPaper, setIsFallingBackToPaper] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    setConnectionStatus('connecting')

    try {
      // Try to connect to the trading API
      const response = await fetch('/api/market?action=ticker&symbol=BTCUSDT')
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }

      setConnectionStatus('connected')
      setIsFallingBackToPaper(false)
      setIsExchangeConnected(true)
      setExchangeName('Binance')
      setCurrency('USD')
      // In a real implementation, fetch actual balance from exchange
      setBalance(DEFAULT_PAPER_BALANCE)
    } catch (err) {
      console.warn('Trading data connection failed, falling back to paper mode')
      setConnectionStatus('disconnected')
      setIsFallingBackToPaper(true)
      setIsExchangeConnected(false)
      setExchangeName(null)
      setIsLiveMode(false)
      setBalance(DEFAULT_PAPER_BALANCE)
      setError(err instanceof Error ? err.message : 'Connection failed')
    } finally {
      setLoading(false)
    }
  }, [])

  const retry = useCallback(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    fetchData()
    
    // Poll for connection status every 30 seconds
    const interval = setInterval(() => {
      if (connectionStatus === 'disconnected' || connectionStatus === 'error') {
        fetchData()
      }
    }, 30000)

    return () => clearInterval(interval)
  }, [fetchData, connectionStatus])

  return {
    balance,
    currency,
    isLiveMode,
    isExchangeConnected,
    exchangeName,
    loading,
    error,
    connectionStatus,
    isFallingBackToPaper,
    retry,
  }
}

export default useTradingData

