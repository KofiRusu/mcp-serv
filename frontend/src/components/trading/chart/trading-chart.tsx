'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useTradingStore } from '@/stores/trading-store'
import { useMarketData } from '@/hooks/use-market-data'
import { Loader2, Wifi, WifiOff, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { IndicatorMenu, useIndicators } from './indicator-menu'

interface TradingChartProps {
  symbol: string
  timeframe?: string
}

interface ChartState {
  scrollOffset: number
  candleWidth: number
}

// Calculate RSI (Relative Strength Index)
function calculateRSI(candles: any[], period: number = 14): number[] {
  if (candles.length < period + 1) return []
  
  const gains: number[] = []
  const losses: number[] = []
  
  for (let i = 1; i < candles.length; i++) {
    const change = candles[i].close - candles[i - 1].close
    gains.push(change > 0 ? change : 0)
    losses.push(change < 0 ? -change : 0)
  }
  
  const rsiValues: number[] = []
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period
  
  for (let i = period; i < gains.length; i++) {
    if (avgLoss === 0) {
      rsiValues.push(100)
    } else {
      const rs = avgGain / avgLoss
      const rsi = 100 - (100 / (1 + rs))
      rsiValues.push(rsi)
    }
    
    // Update averages using Wilder's smoothing
    avgGain = (avgGain * (period - 1) + gains[i]) / period
    avgLoss = (avgLoss * (period - 1) + losses[i]) / period
  }
  
  return rsiValues
}

// Calculate EMA (Exponential Moving Average)
function calculateEMA(values: number[], period: number): number[] {
  if (values.length < period) return []
  
  const multiplier = 2 / (period + 1)
  const ema: number[] = []
  
  // Start with SMA
  let sum = 0
  for (let i = 0; i < period; i++) {
    sum += values[i]
  }
  ema.push(sum / period)
  
  // Calculate EMA
  for (let i = period; i < values.length; i++) {
    ema.push((values[i] - ema[ema.length - 1]) * multiplier + ema[ema.length - 1])
  }
  
  return ema
}

// Calculate MACD (Moving Average Convergence Divergence)
function calculateMACD(candles: any[], fastPeriod: number = 12, slowPeriod: number = 26, signalPeriod: number = 9): Array<{ macd: number; signal: number; histogram: number }> {
  if (candles.length < slowPeriod + signalPeriod) return []
  
  const closes = candles.map(c => c.close)
  const fastEMA = calculateEMA(closes, fastPeriod)
  const slowEMA = calculateEMA(closes, slowPeriod)
  
  // Calculate MACD line
  const macdLine: number[] = []
  const offset = slowPeriod - fastPeriod
  for (let i = 0; i < slowEMA.length; i++) {
    macdLine.push(fastEMA[i + offset] - slowEMA[i])
  }
  
  // Calculate signal line (EMA of MACD)
  const signalLine = calculateEMA(macdLine, signalPeriod)
  
  // Calculate histogram
  const result: Array<{ macd: number; signal: number; histogram: number }> = []
  const signalOffset = macdLine.length - signalLine.length
  for (let i = 0; i < signalLine.length; i++) {
    result.push({
      macd: macdLine[i + signalOffset],
      signal: signalLine[i],
      histogram: macdLine[i + signalOffset] - signalLine[i]
    })
  }
  
  return result
}

export function TradingChart({ symbol, timeframe: propTimeframe }: TradingChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const { positions } = useTradingStore()
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 })
  const [timeframe, setTimeframe] = useState('1h')
  const [useLiveData, setUseLiveData] = useState(true)
  const [chartState, setChartState] = useState<ChartState>({ scrollOffset: 0, candleWidth: 12 })
  const [showVolume, setShowVolume] = useState(true)
  const [showRSI, setShowRSI] = useState(false)
  const [showMACD, setShowMACD] = useState(false)
  
  // Indicator menu state
  const { 
    indicators, 
    enabledIndicators,
    toggleIndicator, 
    toggleFavorite 
  } = useIndicators()

  // Use prop timeframe if provided, otherwise use internal state
  const activeTimeframe = propTimeframe || timeframe

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
    timeframe: activeTimeframe,
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

  // Handle scroll
  const handleScroll = useCallback((direction: 'left' | 'right', amount: number = 5) => {
    setChartState(prev => {
      const newOffset = direction === 'left' 
        ? Math.max(prev.scrollOffset - amount, 0)
        : prev.scrollOffset + amount
      return { ...prev, scrollOffset: newOffset }
    })
  }, [])

  // Handle wheel scroll (individual scrolling)
  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault()
    // Scroll direction: up = left, down = right
    const amount = Math.abs(e.deltaY) > 100 ? 10 : 3
    if (e.deltaY > 0) {
      handleScroll('right', amount)
    } else {
      handleScroll('left', amount)
    }
  }, [handleScroll])

  // Add wheel listener
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    canvas.addEventListener('wheel', handleWheel, { passive: false })
    return () => canvas.removeEventListener('wheel', handleWheel)
  }, [handleWheel])

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

    // Calculate price range from visible candles
    const prices = chartCandles.flatMap(c => [c.high, c.low])
    const minPrice = Math.min(...prices)
    const maxPrice = Math.max(...prices)
    const priceRange = maxPrice - minPrice
    const padding = priceRange * 0.1

    const chartMinPrice = minPrice - padding
    const chartMaxPrice = maxPrice + padding
    const chartPriceRange = chartMaxPrice - chartMinPrice

    // Chart dimensions with larger margins for axes (labels on right, volume at bottom)
    const volumeHeight = showVolume ? 80 : 0
    const chartPadding = { top: 30, right: 80, bottom: 50 + volumeHeight, left: 20 }
    const chartWidth = width - chartPadding.left - chartPadding.right
    const chartHeight = height - chartPadding.top - chartPadding.bottom - volumeHeight

    // Flexible candle sizing based on state
    const candleWidth = chartState.candleWidth
    const candleSpacing = candleWidth + 2
    const maxVisibleCandles = Math.floor(chartWidth / candleSpacing)
    
    // Calculate which candles to display based on scroll
    const startIdx = Math.min(chartState.scrollOffset, Math.max(0, chartCandles.length - maxVisibleCandles))
    const endIdx = Math.min(startIdx + maxVisibleCandles, chartCandles.length)
    const visibleCandles = chartCandles.slice(startIdx, endIdx)

    // Draw Y-axis (left side)
    ctx.strokeStyle = '#2a2a35'
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.moveTo(chartPadding.left - 10, chartPadding.top)
    ctx.lineTo(chartPadding.left - 10, height - chartPadding.bottom)
    ctx.stroke()

    // Draw X-axis (bottom)
    ctx.beginPath()
    ctx.moveTo(chartPadding.left - 10, height - chartPadding.bottom)
    ctx.lineTo(width - chartPadding.right, height - chartPadding.bottom)
    ctx.stroke()

    // Draw horizontal grid lines and Y-axis labels (on right side)
    ctx.strokeStyle = '#1a1a24'
    ctx.lineWidth = 1
    ctx.fillStyle = '#6b7280'
    ctx.font = '11px monospace'
    ctx.textAlign = 'left'

    const gridLines = 5
    for (let i = 0; i <= gridLines; i++) {
      const y = chartPadding.top + (chartHeight / gridLines) * i
      
      // Grid line
      ctx.beginPath()
      ctx.moveTo(chartPadding.left - 10, y)
      ctx.lineTo(width - chartPadding.right, y)
      ctx.stroke()

      // Price labels on Y-axis (right side)
      const price = chartMaxPrice - (chartPriceRange / gridLines) * i
      ctx.fillText(`$${price.toFixed(0)}`, width - chartPadding.right + 8, y + 4)
    }

    // Draw vertical grid lines and X-axis time labels
    ctx.strokeStyle = '#1a1a24'
    ctx.lineWidth = 0.5
      ctx.fillStyle = '#6b7280'
    ctx.font = '10px monospace'
    ctx.textAlign = 'center'

    const timeLabels = 4
    for (let i = 0; i <= timeLabels; i++) {
      const idx = Math.floor((visibleCandles.length / timeLabels) * i)
      if (idx < visibleCandles.length) {
        const candle = visibleCandles[idx]
        const x = chartPadding.left + idx * candleSpacing + candleSpacing / 2

        // Vertical grid line
        ctx.beginPath()
        ctx.moveTo(x, chartPadding.top)
        ctx.lineTo(x, height - chartPadding.bottom)
        ctx.stroke()

        // Time label - handle both timestamp and time property
        const timeValue = candle.time || Date.now()
        const date = new Date(typeof timeValue === 'number' ? timeValue : 0)
        const timeStr = isNaN(date.getTime()) 
          ? `[${i}/${timeLabels}]`
          : `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
        ctx.fillText(timeStr, x, height - chartPadding.bottom + 20)
      }
    }

    // Draw candles with better visibility
    visibleCandles.forEach((candle, i) => {
      const x = chartPadding.left + i * candleSpacing + candleSpacing / 2
      const isGreen = candle.close >= candle.open

      // Calculate y positions
      const yHigh = chartPadding.top + ((chartMaxPrice - candle.high) / chartPriceRange) * chartHeight
      const yLow = chartPadding.top + ((chartMaxPrice - candle.low) / chartPriceRange) * chartHeight
      const yOpen = chartPadding.top + ((chartMaxPrice - candle.open) / chartPriceRange) * chartHeight
      const yClose = chartPadding.top + ((chartMaxPrice - candle.close) / chartPriceRange) * chartHeight

      // Wick (thin line from high to low)
      ctx.strokeStyle = isGreen ? '#10b981' : '#ef5350'
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.moveTo(x, yHigh)
      ctx.lineTo(x, yLow)
      ctx.stroke()

      // Body (rectangle from open to close)
      const bodyTop = Math.min(yOpen, yClose)
      const bodyHeight = Math.max(Math.abs(yClose - yOpen), 2)
      
      if (isGreen) {
        // Green candle - bullish
        ctx.fillStyle = '#10b981'
        ctx.strokeStyle = '#059669'
        ctx.lineWidth = 0.5
        ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight)
        ctx.strokeRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight)
      } else {
        // Red candle - bearish
        ctx.fillStyle = '#ef5350'
        ctx.strokeStyle = '#c62828'
        ctx.lineWidth = 0.5
      ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight)
        ctx.strokeRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight)
      }
    })

    // Draw volume bars
    if (showVolume && volumeHeight > 0 && visibleCandles.length > 0) {
      const volumes = visibleCandles.map(c => c.volume || 0)
      const maxVolume = Math.max(...volumes, 1)
      const volumeY = height - chartPadding.bottom + volumeHeight
      const volumeBarHeight = volumeHeight - 20

      visibleCandles.forEach((candle, i) => {
        const x = chartPadding.left + i * candleSpacing + candleSpacing / 2
        const isGreen = candle.close >= candle.open
        const volume = candle.volume || 0
        const barHeight = (volume / maxVolume) * volumeBarHeight

        ctx.fillStyle = isGreen ? 'rgba(16, 185, 129, 0.5)' : 'rgba(239, 68, 68, 0.5)'
        ctx.fillRect(x - candleWidth / 2, volumeY - barHeight, candleWidth, barHeight)
      })
    }

    // Calculate and draw technical indicators (use full candle array for calculations)
    if (chartCandles.length > 0) {
      // Calculate RSI on full dataset, then slice to visible
      if (showRSI) {
        const allRSI = calculateRSI(chartCandles, 14)
        // RSI starts after period, so align with candles
        const rsiStartIdx = Math.max(0, startIdx - 14)
        const rsiEndIdx = Math.min(startIdx + visibleCandles.length, allRSI.length)
        const rsiValues = allRSI.slice(rsiStartIdx, rsiEndIdx)
        
        if (rsiValues.length > 0) {
          const rsiY = chartPadding.top + chartHeight / 2
          const rsiHeight = chartHeight / 4

          // Draw RSI background
          ctx.fillStyle = 'rgba(26, 26, 36, 0.8)'
          ctx.fillRect(chartPadding.left, rsiY, chartWidth, rsiHeight)

          // Draw RSI levels (30, 50, 70)
          ctx.strokeStyle = '#3a3a4a'
          ctx.lineWidth = 1
          for (const level of [30, 50, 70]) {
            const y = rsiY + rsiHeight - (level / 100) * rsiHeight
            ctx.beginPath()
            ctx.moveTo(chartPadding.left, y)
            ctx.lineTo(chartPadding.left + chartWidth, y)
            ctx.stroke()
          }

          // Draw RSI line
          ctx.strokeStyle = '#8b5cf6'
          ctx.lineWidth = 1.5
          ctx.beginPath()
          rsiValues.forEach((rsi, i) => {
            const x = chartPadding.left + i * candleSpacing + candleSpacing / 2
            const y = rsiY + rsiHeight - (rsi / 100) * rsiHeight
            if (i === 0) {
              ctx.moveTo(x, y)
            } else {
              ctx.lineTo(x, y)
            }
          })
          ctx.stroke()

          // Draw RSI labels
          ctx.fillStyle = '#8b5cf6'
          ctx.font = '9px monospace'
          ctx.textAlign = 'left'
          ctx.fillText('RSI', chartPadding.left + 4, rsiY + 12)
        }
      }

      // Calculate and draw MACD on full dataset
      if (showMACD) {
        const allMACD = calculateMACD(chartCandles, 12, 26, 9)
        // MACD starts after slowPeriod + signalPeriod
        const macdStartIdx = Math.max(0, startIdx - 35)
        const macdEndIdx = Math.min(startIdx + visibleCandles.length, allMACD.length)
        const macdData = allMACD.slice(macdStartIdx, macdEndIdx)
        
        if (macdData.length > 0) {
          const macdY = chartPadding.top + chartHeight * 0.75
          const macdHeight = chartHeight / 4

          // Draw MACD background
          ctx.fillStyle = 'rgba(26, 26, 36, 0.8)'
          ctx.fillRect(chartPadding.left, macdY, chartWidth, macdHeight)

          // Draw zero line
          ctx.strokeStyle = '#3a3a4a'
          ctx.lineWidth = 1
          const zeroY = macdY + macdHeight / 2
          ctx.beginPath()
          ctx.moveTo(chartPadding.left, zeroY)
          ctx.lineTo(chartPadding.left + chartWidth, zeroY)
          ctx.stroke()

          // Find MACD range
          const macdValues = macdData.map(d => d.macd)
          const signalValues = macdData.map(d => d.signal)
          const histogramValues = macdData.map(d => d.histogram)
          const allValues = [...macdValues, ...signalValues, ...histogramValues]
          const maxMACD = Math.max(...allValues.map(Math.abs), 0.001)
          const macdScale = macdHeight / 2 / maxMACD

          // Draw MACD line
          ctx.strokeStyle = '#3b82f6'
          ctx.lineWidth = 1.5
          ctx.beginPath()
          macdData.forEach((data, i) => {
            const x = chartPadding.left + i * candleSpacing + candleSpacing / 2
            const y = zeroY - data.macd * macdScale
            if (i === 0) {
              ctx.moveTo(x, y)
            } else {
              ctx.lineTo(x, y)
            }
          })
          ctx.stroke()

          // Draw signal line
          ctx.strokeStyle = '#f59e0b'
          ctx.lineWidth = 1.5
          ctx.beginPath()
          macdData.forEach((data, i) => {
            const x = chartPadding.left + i * candleSpacing + candleSpacing / 2
            const y = zeroY - data.signal * macdScale
            if (i === 0) {
              ctx.moveTo(x, y)
            } else {
              ctx.lineTo(x, y)
            }
          })
          ctx.stroke()

          // Draw histogram
          macdData.forEach((data, i) => {
            const x = chartPadding.left + i * candleSpacing + candleSpacing / 2
            const barHeight = Math.abs(data.histogram * macdScale)
            const barY = zeroY - (data.histogram >= 0 ? barHeight : 0)
            ctx.fillStyle = data.histogram >= 0 ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)'
            ctx.fillRect(x - candleWidth / 2, barY, candleWidth, barHeight)
          })

          // Draw MACD label
          ctx.fillStyle = '#3b82f6'
          ctx.font = '9px monospace'
          ctx.textAlign = 'left'
          ctx.fillText('MACD', chartPadding.left + 4, macdY + 12)
        }
      }
    }

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

        // Entry label (on left side to avoid price labels)
        ctx.fillStyle = '#8b5cf6'
        ctx.fillRect(chartPadding.left, yEntry - 10, 60, 20)
        ctx.fillStyle = '#fff'
        ctx.font = '10px sans-serif'
        ctx.textAlign = 'center'
        ctx.fillText(`Entry`, chartPadding.left + 30, yEntry + 4)
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
          ctx.fillRect(chartPadding.left, ySL - 10, 60, 20)
          ctx.fillStyle = '#fff'
          ctx.fillText(`SL`, chartPadding.left + 30, ySL + 4)
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
          ctx.fillRect(chartPadding.left, yTP - 10, 60, 20)
          ctx.fillStyle = '#fff'
          ctx.fillText(`TP`, chartPadding.left + 30, yTP + 4)
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

  }, [chartCandles, dimensions, positions, symbol, ticker, chartState, showVolume, showRSI, showMACD])

  return (
    <div ref={containerRef} className="w-full h-full relative flex flex-col">
      {/* Controls */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800 bg-[#0d0d14]">
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleScroll('left')}
            className="p-1.5 hover:bg-gray-800 rounded text-gray-500 hover:text-white transition-colors"
            title="Scroll left"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleScroll('right')}
            className="p-1.5 hover:bg-gray-800 rounded text-gray-500 hover:text-white transition-colors"
            title="Scroll right"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <div className="ml-4 text-xs text-gray-500">
            Candle Size: {chartState.candleWidth}px
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Indicator Menu - Full selection like aggr.trade */}
          <IndicatorMenu 
            indicators={indicators}
            onToggle={toggleIndicator}
            onFavorite={toggleFavorite}
          />
          
          {/* Quick toggles for common indicators */}
          <div className="h-4 w-px bg-gray-700 mx-1" />
          <button
            onClick={() => setShowVolume(!showVolume)}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              showVolume ? 'bg-purple-800 text-purple-200' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
            title="Toggle volume bars"
          >
            Vol
          </button>
          <button
            onClick={() => setShowRSI(!showRSI)}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              showRSI ? 'bg-purple-800 text-purple-200' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
            title="Toggle RSI indicator"
          >
            RSI
          </button>
          <button
            onClick={() => setShowMACD(!showMACD)}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              showMACD ? 'bg-purple-800 text-purple-200' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
            title="Toggle MACD indicator"
          >
            MACD
          </button>
          <button
            onClick={() => setChartState(prev => ({ ...prev, candleWidth: Math.max(prev.candleWidth - 1, 4) }))}
            className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded text-gray-400 transition-colors"
          >
            Zoom Out
          </button>
          <button
            onClick={() => setChartState(prev => ({ ...prev, candleWidth: Math.min(prev.candleWidth + 1, 30) }))}
            className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded text-gray-400 transition-colors"
          >
            Zoom In
          </button>
        </div>
      </div>

      {/* Chart Container */}
      <div className="flex-1 min-h-0 relative">
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

        <canvas 
          ref={canvasRef} 
          className="w-full h-full cursor-grab active:cursor-grabbing"
          title="Scroll with mouse wheel to navigate chart. Click zoom buttons to adjust candle size."
        />
      </div>
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
