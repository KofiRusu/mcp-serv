'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useTradingStore } from '@/stores/trading-store'
import { useMarketData } from '@/hooks/use-market-data'
import { Loader2, Wifi, WifiOff, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface TradingChartProps {
  symbol: string
}

export function TradingChart({ symbol }: TradingChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const { positions } = useTradingStore()
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 })
  const [timeframe, setTimeframe] = useState('1h')
  const [useLiveData, setUseLiveData] = useState(true)

  // Use CCXT data hook
  const { 
    candles, 
    ticker, 
    loading, 
    error, 
    lastUpdate,
    refetchCandles 
  } = useMarketData({
    symbol,
    timeframe,
    refreshInterval: 10000,
    enableLiveUpdates: useLiveData,
  })

  // Fallback to mock data if CCXT fails
  const chartCandles = candles.length > 0 ? candles : generateMockCandles(symbol)

  // Handle resize
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const resizeObserver = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      setDimensions({ width, height })
    })

    resizeObserver.observe(container)
    return () => resizeObserver.disconnect()
  }, [])

  // Draw chart
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || chartCandles.length === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const { width, height } = dimensions
    const dpr = window.devicePixelRatio || 1

    // Set canvas size with DPR
    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    ctx.scale(dpr, dpr)

    // Clear canvas
    ctx.fillStyle = '#0a0a0f'
    ctx.fillRect(0, 0, width, height)

    // Calculate price range
    const prices = chartCandles.flatMap(c => [c.high, c.low])
    const minPrice = Math.min(...prices)
    const maxPrice = Math.max(...prices)
    const priceRange = maxPrice - minPrice
    const padding = priceRange * 0.1

    const chartMinPrice = minPrice - padding
    const chartMaxPrice = maxPrice + padding
    const chartPriceRange = chartMaxPrice - chartMinPrice

    // Chart dimensions
    const chartPadding = { top: 20, right: 80, bottom: 30, left: 20 }
    const chartWidth = width - chartPadding.left - chartPadding.right
    const chartHeight = height - chartPadding.top - chartPadding.bottom

    const candleWidth = Math.max(chartWidth / chartCandles.length * 0.7, 2)
    const candleSpacing = chartWidth / chartCandles.length

    // Draw grid
    ctx.strokeStyle = '#1a1a24'
    ctx.lineWidth = 1

    // Horizontal grid lines
    const gridLines = 5
    for (let i = 0; i <= gridLines; i++) {
      const y = chartPadding.top + (chartHeight / gridLines) * i
      ctx.beginPath()
      ctx.moveTo(chartPadding.left, y)
      ctx.lineTo(width - chartPadding.right, y)
      ctx.stroke()

      // Price labels
      const price = chartMaxPrice - (chartPriceRange / gridLines) * i
      ctx.fillStyle = '#6b7280'
      ctx.font = '11px monospace'
      ctx.textAlign = 'left'
      ctx.fillText(`$${price.toFixed(2)}`, width - chartPadding.right + 8, y + 4)
    }

    // Draw candles
    chartCandles.forEach((candle, i) => {
      const x = chartPadding.left + i * candleSpacing + candleSpacing / 2
      const isGreen = candle.close >= candle.open

      // Calculate y positions
      const yHigh = chartPadding.top + ((chartMaxPrice - candle.high) / chartPriceRange) * chartHeight
      const yLow = chartPadding.top + ((chartMaxPrice - candle.low) / chartPriceRange) * chartHeight
      const yOpen = chartPadding.top + ((chartMaxPrice - candle.open) / chartPriceRange) * chartHeight
      const yClose = chartPadding.top + ((chartMaxPrice - candle.close) / chartPriceRange) * chartHeight

      // Wick
      ctx.strokeStyle = isGreen ? '#22c55e' : '#ef4444'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(x, yHigh)
      ctx.lineTo(x, yLow)
      ctx.stroke()

      // Body
      ctx.fillStyle = isGreen ? '#22c55e' : '#ef4444'
      const bodyTop = Math.min(yOpen, yClose)
      const bodyHeight = Math.max(Math.abs(yClose - yOpen), 1)
      ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight)
    })

    // Draw position markers
    const currentPosition = positions.find(p => p.symbol === symbol)
    if (currentPosition) {
      // Entry line
      const yEntry = chartPadding.top + ((chartMaxPrice - currentPosition.entryPrice) / chartPriceRange) * chartHeight
      if (yEntry > chartPadding.top && yEntry < height - chartPadding.bottom) {
        ctx.strokeStyle = '#8b5cf6'
        ctx.setLineDash([5, 5])
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(chartPadding.left, yEntry)
        ctx.lineTo(width - chartPadding.right, yEntry)
        ctx.stroke()
        ctx.setLineDash([])

        // Entry label
        ctx.fillStyle = '#8b5cf6'
        ctx.fillRect(width - chartPadding.right - 60, yEntry - 10, 60, 20)
        ctx.fillStyle = '#fff'
        ctx.font = '10px sans-serif'
        ctx.textAlign = 'center'
        ctx.fillText(`Entry`, width - chartPadding.right - 30, yEntry + 4)
      }

      // Stop loss line
      if (currentPosition.stopLoss) {
        const ySL = chartPadding.top + ((chartMaxPrice - currentPosition.stopLoss) / chartPriceRange) * chartHeight
        if (ySL > chartPadding.top && ySL < height - chartPadding.bottom) {
          ctx.strokeStyle = '#ef4444'
          ctx.setLineDash([3, 3])
          ctx.beginPath()
          ctx.moveTo(chartPadding.left, ySL)
          ctx.lineTo(width - chartPadding.right, ySL)
          ctx.stroke()
          ctx.setLineDash([])

          ctx.fillStyle = '#ef4444'
          ctx.fillRect(width - chartPadding.right - 60, ySL - 10, 60, 20)
          ctx.fillStyle = '#fff'
          ctx.fillText(`SL`, width - chartPadding.right - 30, ySL + 4)
        }
      }

      // Take profit line
      if (currentPosition.takeProfit) {
        const yTP = chartPadding.top + ((chartMaxPrice - currentPosition.takeProfit) / chartPriceRange) * chartHeight
        if (yTP > chartPadding.top && yTP < height - chartPadding.bottom) {
          ctx.strokeStyle = '#22c55e'
          ctx.setLineDash([3, 3])
          ctx.beginPath()
          ctx.moveTo(chartPadding.left, yTP)
          ctx.lineTo(width - chartPadding.right, yTP)
          ctx.stroke()
          ctx.setLineDash([])

          ctx.fillStyle = '#22c55e'
          ctx.fillRect(width - chartPadding.right - 60, yTP - 10, 60, 20)
          ctx.fillStyle = '#fff'
          ctx.fillText(`TP`, width - chartPadding.right - 30, yTP + 4)
        }
      }
    }

    // Current price line (from ticker or last candle)
    const currentPrice = ticker?.last || chartCandles[chartCandles.length - 1]?.close || 0
    const yCurrentPrice = chartPadding.top + ((chartMaxPrice - currentPrice) / chartPriceRange) * chartHeight
    
    if (yCurrentPrice > chartPadding.top && yCurrentPrice < height - chartPadding.bottom) {
      ctx.strokeStyle = '#f59e0b'
      ctx.lineWidth = 1
      ctx.setLineDash([2, 2])
      ctx.beginPath()
      ctx.moveTo(chartPadding.left, yCurrentPrice)
      ctx.lineTo(width - chartPadding.right, yCurrentPrice)
      ctx.stroke()
      ctx.setLineDash([])

      // Current price label
      ctx.fillStyle = '#f59e0b'
      ctx.fillRect(width - chartPadding.right, yCurrentPrice - 10, 80, 20)
      ctx.fillStyle = '#000'
      ctx.font = 'bold 11px monospace'
      ctx.textAlign = 'left'
      ctx.fillText(`$${currentPrice.toFixed(2)}`, width - chartPadding.right + 4, yCurrentPrice + 4)
    }

  }, [chartCandles, dimensions, positions, symbol, ticker])

  return (
    <div ref={containerRef} className="w-full h-full relative">
      {/* Loading overlay */}
      {loading && candles.length === 0 && (
        <div className="absolute inset-0 bg-[#0a0a0f]/80 flex items-center justify-center z-10">
          <div className="flex items-center gap-2 text-gray-400">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Loading market data...</span>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="absolute top-2 left-2 bg-red-500/20 border border-red-500/30 rounded-lg px-3 py-1.5 text-xs text-red-400 z-10">
          Using mock data: {error}
        </div>
      )}

      {/* Connection status */}
      <div className="absolute top-2 right-2 flex items-center gap-2 z-10">
        <button
          onClick={() => setUseLiveData(!useLiveData)}
          className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs ${
            useLiveData && !error
              ? 'bg-green-500/20 text-green-400'
              : 'bg-gray-800 text-gray-500'
          }`}
        >
          {useLiveData && !error ? (
            <Wifi className="w-3 h-3" />
          ) : (
            <WifiOff className="w-3 h-3" />
          )}
          {useLiveData ? 'Live' : 'Paused'}
        </button>
        <Button
          size="icon"
          variant="ghost"
          className="h-6 w-6 text-gray-500 hover:text-white"
          onClick={() => refetchCandles()}
        >
          <RefreshCw className="w-3 h-3" />
        </Button>
      </div>

      {/* Last update */}
      {lastUpdate && (
        <div className="absolute bottom-2 left-2 text-[10px] text-gray-600 z-10">
          Updated: {new Date(lastUpdate).toLocaleTimeString()}
        </div>
      )}

      <canvas ref={canvasRef} className="w-full h-full" />
    </div>
  )
}

// Fallback mock data generator
function generateMockCandles(symbol: string, count: number = 100) {
  const basePrice = symbol.includes('BTC') ? 67000 : 
                    symbol.includes('ETH') ? 3400 : 
                    symbol.includes('SOL') ? 175 : 100
  
  const data = []
  let price = basePrice
  const now = Date.now()

  for (let i = count; i >= 0; i--) {
    const volatility = basePrice * 0.02
    const change = (Math.random() - 0.5) * volatility
    const open = price
    const close = price + change
    const high = Math.max(open, close) + Math.random() * volatility * 0.5
    const low = Math.min(open, close) - Math.random() * volatility * 0.5
    const volume = Math.random() * 1000000

    data.push({
      time: now - i * 3600000,
      open,
      high,
      low,
      close,
      volume,
    })

    price = close
  }

  return data
}
