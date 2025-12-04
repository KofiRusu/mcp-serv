'use client'

import { useMemo } from 'react'
import { useTradingStore } from '@/stores/trading-store'

interface OrderBookProps {
  symbol: string
}

// Generate mock order book data
function generateOrderBook(basePrice: number, depth: number = 15) {
  const asks = []
  const bids = []
  
  let askPrice = basePrice + 10
  let bidPrice = basePrice - 10

  for (let i = 0; i < depth; i++) {
    const askSize = Math.random() * 5 + 0.5
    const bidSize = Math.random() * 5 + 0.5

    asks.push({ price: askPrice, size: askSize, total: 0 })
    bids.push({ price: bidPrice, size: bidSize, total: 0 })

    askPrice += Math.random() * 20 + 5
    bidPrice -= Math.random() * 20 + 5
  }

  // Calculate totals
  let askTotal = 0
  let bidTotal = 0
  asks.forEach(a => { askTotal += a.size; a.total = askTotal })
  bids.forEach(b => { bidTotal += b.size; b.total = bidTotal })

  return { asks: asks.reverse(), bids }
}

export function OrderBook({ symbol }: OrderBookProps) {
  const { markets } = useTradingStore()
  const currentMarket = markets.find(m => m.symbol === symbol)
  const basePrice = currentMarket?.price || 67500

  const { asks, bids } = useMemo(() => generateOrderBook(basePrice), [basePrice])
  
  const maxTotal = Math.max(
    asks[asks.length - 1]?.total || 0,
    bids[bids.length - 1]?.total || 0
  )

  return (
    <div className="h-full flex flex-col text-xs">
      {/* Header */}
      <div className="flex justify-between px-3 py-2 text-gray-500 font-medium border-b border-gray-800">
        <span>Price (USDT)</span>
        <span>Size</span>
        <span>Total</span>
      </div>

      {/* Asks (Sells) */}
      <div className="flex-1 overflow-hidden flex flex-col justify-end">
        {asks.map((ask, i) => (
          <div key={i} className="relative flex justify-between px-3 py-0.5 hover:bg-gray-800/50">
            <div 
              className="absolute inset-0 bg-red-500/10" 
              style={{ width: `${(ask.total / maxTotal) * 100}%`, right: 0, left: 'auto' }}
            />
            <span className="relative text-red-400 font-mono">${ask.price.toFixed(2)}</span>
            <span className="relative text-gray-400 font-mono">{ask.size.toFixed(4)}</span>
            <span className="relative text-gray-500 font-mono">{ask.total.toFixed(4)}</span>
          </div>
        ))}
      </div>

      {/* Spread */}
      <div className="px-3 py-2 bg-gray-900/50 border-y border-gray-800 text-center">
        <span className="font-mono font-bold text-lg text-white">${basePrice.toLocaleString()}</span>
        <span className="ml-2 text-gray-500">Spread: ${((asks[asks.length - 1]?.price || 0) - (bids[0]?.price || 0)).toFixed(2)}</span>
      </div>

      {/* Bids (Buys) */}
      <div className="flex-1 overflow-hidden">
        {bids.map((bid, i) => (
          <div key={i} className="relative flex justify-between px-3 py-0.5 hover:bg-gray-800/50">
            <div 
              className="absolute inset-0 bg-green-500/10" 
              style={{ width: `${(bid.total / maxTotal) * 100}%`, right: 0, left: 'auto' }}
            />
            <span className="relative text-green-400 font-mono">${bid.price.toFixed(2)}</span>
            <span className="relative text-gray-400 font-mono">{bid.size.toFixed(4)}</span>
            <span className="relative text-gray-500 font-mono">{bid.total.toFixed(4)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

