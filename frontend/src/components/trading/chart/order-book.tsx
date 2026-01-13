'use client'

import { useEffect, useState, useCallback } from 'react'
import { RefreshCw } from 'lucide-react'

interface OrderBookProps {
  symbol: string
}

interface OrderEntry {
  price: number
  size: number
  total: number
}

interface OrderBookData {
  bids: OrderEntry[]
  asks: OrderEntry[]
  spread: number
  midPrice: number
  }

// Max rows to display per side (asks/bids)
const MAX_ROWS = 10

export function OrderBook({ symbol }: OrderBookProps) {
  const [data, setData] = useState<OrderBookData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchOrderBook = useCallback(async () => {
    try {
      const response = await fetch(`/api/market?action=orderbook&symbol=${symbol}&limit=${MAX_ROWS}`)
      if (!response.ok) throw new Error('Failed to fetch order book')
      
      const result = await response.json()
      
      // Process bids - calculate cumulative totals (limit to MAX_ROWS)
      let bidTotal = 0
      const bids: OrderEntry[] = result.bids.slice(0, MAX_ROWS).map((b: any) => {
        bidTotal += b.size
        return { price: b.price, size: b.size, total: bidTotal }
      })
      
      // Process asks - calculate cumulative totals (limit to MAX_ROWS)
      let askTotal = 0
      const asks: OrderEntry[] = result.asks.slice(0, MAX_ROWS).map((a: any) => {
        askTotal += a.size
        return { price: a.price, size: a.size, total: askTotal }
      }).reverse() // Reverse so lowest ask is at bottom
      
      // Calculate spread and mid price
      const lowestAsk = result.asks[0]?.price || 0
      const highestBid = result.bids[0]?.price || 0
      const spread = lowestAsk - highestBid
      const midPrice = (lowestAsk + highestBid) / 2
      
      setData({ bids, asks, spread, midPrice })
      setLoading(false)
      setError(null)
    } catch (err: any) {
      console.error('Error fetching order book:', err)
      setError(err.message)
      setLoading(false)
    }
  }, [symbol])

  // Initial fetch and refresh every 5 seconds
  useEffect(() => {
    fetchOrderBook()
    const interval = setInterval(fetchOrderBook, 5000)
    return () => clearInterval(interval)
  }, [fetchOrderBook])

  if (loading && !data) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <RefreshCw className="w-5 h-5 animate-spin" />
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="h-full flex items-center justify-center text-red-400 text-xs p-4 text-center">
        {error}
      </div>
    )
  }

  if (!data) return null
  
  const maxTotal = Math.max(
    data.asks[0]?.total || 0,
    data.bids[data.bids.length - 1]?.total || 0
  )

  return (
    <div className="h-full flex flex-col text-[11px] overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 grid grid-cols-3 px-2 py-1.5 text-gray-500 font-medium border-b border-gray-800 text-[10px]">
        <span>Price (USDT)</span>
        <span className="text-right">Size</span>
        <span className="text-right">Total</span>
      </div>

      {/* Asks (Sells) - displayed top to bottom, highest to lowest */}
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col justify-end">
        {data.asks.map((ask, i) => (
          <div key={i} className="flex-shrink-0 relative grid grid-cols-3 px-2 py-0.5 hover:bg-gray-800/50">
            <div 
              className="absolute inset-0 bg-red-500/10" 
              style={{ width: `${(ask.total / maxTotal) * 100}%`, right: 0, left: 'auto' }}
            />
            <span className="relative text-red-400 font-mono">
              {ask.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className="relative text-gray-400 font-mono text-right">{ask.size.toFixed(4)}</span>
            <span className="relative text-gray-500 font-mono text-right">{ask.total.toFixed(4)}</span>
          </div>
        ))}
      </div>

      {/* Spread / Current Price */}
      <div className="flex-shrink-0 px-2 py-1.5 bg-gray-900/50 border-y border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-sm text-white">
            ${data.midPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          {loading && <RefreshCw className="w-3 h-3 animate-spin text-gray-500" />}
        </div>
        <span className="text-[10px] text-gray-500">
          Spread: ${data.spread.toFixed(2)}
        </span>
      </div>

      {/* Bids (Buys) - displayed top to bottom, highest to lowest */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {data.bids.map((bid, i) => (
          <div key={i} className="flex-shrink-0 relative grid grid-cols-3 px-2 py-0.5 hover:bg-gray-800/50">
            <div 
              className="absolute inset-0 bg-green-500/10" 
              style={{ width: `${(bid.total / maxTotal) * 100}%`, right: 0, left: 'auto' }}
            />
            <span className="relative text-green-400 font-mono">
              {bid.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className="relative text-gray-400 font-mono text-right">{bid.size.toFixed(4)}</span>
            <span className="relative text-gray-500 font-mono text-right">{bid.total.toFixed(4)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
