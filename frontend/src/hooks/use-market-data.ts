'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { ccxtClient, Candle, Ticker, OrderBook, Trade } from '@/lib/trading/ccxt-client'

interface UseMarketDataOptions {
  symbol: string
  timeframe?: string
  refreshInterval?: number // in milliseconds
  enableLiveUpdates?: boolean
}

interface MarketDataState {
  candles: Candle[]
  ticker: Ticker | null
  orderbook: OrderBook | null
  trades: Trade[]
  loading: boolean
  error: string | null
  lastUpdate: number | null
}

export function useMarketData({
  symbol,
  timeframe = '1h',
  refreshInterval = 10000, // 10 seconds default
  enableLiveUpdates = true,
}: UseMarketDataOptions) {
  const [state, setState] = useState<MarketDataState>({
    candles: [],
    ticker: null,
    orderbook: null,
    trades: [],
    loading: true,
    error: null,
    lastUpdate: null,
  })

  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const fetchCandles = useCallback(async () => {
    try {
      const candles = await ccxtClient.fetchOHLCV(symbol, timeframe, 100)
      setState(prev => ({
        ...prev,
        candles,
        loading: false,
        error: null,
        lastUpdate: Date.now(),
      }))
      return candles
    } catch (error: any) {
      console.error('Error fetching candles:', error)
      setState(prev => ({
        ...prev,
        loading: false,
        error: error.message,
      }))
      return []
    }
  }, [symbol, timeframe])

  const fetchTicker = useCallback(async () => {
    try {
      const ticker = await ccxtClient.fetchTicker(symbol)
      setState(prev => ({
        ...prev,
        ticker,
        error: null,
      }))
      return ticker
    } catch (error: any) {
      console.error('Error fetching ticker:', error)
      return null
    }
  }, [symbol])

  const fetchOrderBook = useCallback(async () => {
    try {
      const orderbook = await ccxtClient.fetchOrderBook(symbol)
      setState(prev => ({
        ...prev,
        orderbook,
        error: null,
      }))
      return orderbook
    } catch (error: any) {
      console.error('Error fetching orderbook:', error)
      return null
    }
  }, [symbol])

  const fetchTrades = useCallback(async () => {
    try {
      const trades = await ccxtClient.fetchTrades(symbol)
      setState(prev => ({
        ...prev,
        trades,
        error: null,
      }))
      return trades
    } catch (error: any) {
      console.error('Error fetching trades:', error)
      return []
    }
  }, [symbol])

  const fetchAll = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true }))
    await Promise.all([
      fetchCandles(),
      fetchTicker(),
      fetchOrderBook(),
      fetchTrades(),
    ])
  }, [fetchCandles, fetchTicker, fetchOrderBook, fetchTrades])

  // Initial fetch
  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  // Live updates
  useEffect(() => {
    if (!enableLiveUpdates) return

    intervalRef.current = setInterval(() => {
      fetchTicker()
      fetchOrderBook()
    }, refreshInterval)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [enableLiveUpdates, refreshInterval, fetchTicker, fetchOrderBook])

  // Refetch candles when timeframe changes
  useEffect(() => {
    fetchCandles()
  }, [timeframe, fetchCandles])

  return {
    ...state,
    refetch: fetchAll,
    refetchCandles: fetchCandles,
    refetchTicker: fetchTicker,
    refetchOrderBook: fetchOrderBook,
    refetchTrades: fetchTrades,
  }
}

