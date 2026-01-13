'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

interface LivePrice {
  symbol: string
  price: number
  change24h: number
  high24h: number
  low24h: number
  volume24h: number
}

interface UseLivePricesOptions {
  refreshInterval?: number // in milliseconds
  autoRefresh?: boolean
}

export function useLivePrices({
  refreshInterval = 10000, // 10 seconds default
  autoRefresh = true,
}: UseLivePricesOptions = {}) {
  const [prices, setPrices] = useState<Record<string, LivePrice>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<number | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const fetchPrices = useCallback(async () => {
    try {
      // Fetch from scraper data instead of CCXT/Binance direct
      const response = await fetch('/api/scraped-data?type=markets')
      if (!response.ok) throw new Error('Failed to fetch prices')
      
      const data = await response.json()
      
      if (data.error) {
        throw new Error(data.error)
      }
      
      const priceMap: Record<string, LivePrice> = {}
      for (const market of data.markets || []) {
        priceMap[market.symbol] = {
          symbol: market.symbol,
          price: market.price,
          change24h: market.change24h,
          high24h: market.high24h,
          low24h: market.low24h,
          volume24h: market.volume24h,
        }
      }
      
      setPrices(priceMap)
      setLoading(false)
      setError(null)
      setLastUpdate(data.timestamp || Date.now())
    } catch (err: any) {
      console.error('Error fetching live prices:', err)
      setError(err.message)
      setLoading(false)
    }
  }, [])

  // Initial fetch
  useEffect(() => {
    fetchPrices()
  }, [fetchPrices])

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return

    intervalRef.current = setInterval(fetchPrices, refreshInterval)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [autoRefresh, refreshInterval, fetchPrices])

  const getPrice = useCallback((symbol: string): LivePrice | null => {
    // Normalize symbol
    const normalized = symbol.replace('/', '')
    return prices[normalized] || null
  }, [prices])

  return {
    prices,
    loading,
    error,
    lastUpdate,
    refetch: fetchPrices,
    getPrice,
  }
}

