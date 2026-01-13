'use client'

/**
 * Paper Trading Panel Component
 * 
 * Controls and displays paper trading sessions on live data.
 */

import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Play,
  Square,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Activity,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  BarChart3,
} from 'lucide-react'
import { useTradingStore } from '@/stores/trading-store'

interface PaperSession {
  id: string
  startedAt: string
  isRunning: boolean
  portfolio: {
    balance: number
    equity: number
    totalPnl: number
    totalPnlPercent: number
    maxDrawdown: number
    positions: any[]
  }
  trades: any[]
}

interface PaperConfig {
  initialBalance: number
  maxPositionSize: number
  maxConcurrentPositions: number
  riskPerTrade: number
  stopLossPercent: number
  takeProfitPercent: number
}

const DEFAULT_CONFIG: PaperConfig = {
  initialBalance: 100000,
  maxPositionSize: 0.1,
  maxConcurrentPositions: 3,
  riskPerTrade: 0.02,
  stopLossPercent: 0.02,
  takeProfitPercent: 0.04,
}

export function PaperTradingPanel() {
  const { currentSymbol, backtestHistory } = useTradingStore()
  const [session, setSession] = useState<PaperSession | null>(null)
  const [config, setConfig] = useState<PaperConfig>(DEFAULT_CONFIG)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch current session status
  const fetchSession = useCallback(async () => {
    try {
      const response = await fetch('/api/paper-trading?action=list')
      if (response.ok) {
        const data = await response.json()
        const runningSession = data.sessions?.find((s: any) => s.isRunning)
        if (runningSession) {
          // Get full session details
          const detailsResponse = await fetch(`/api/paper-trading?action=status&sessionId=${runningSession.id}`)
          if (detailsResponse.ok) {
            const details = await detailsResponse.json()
            setSession(details.session)
          }
        } else {
          setSession(null)
        }
      }
    } catch (err) {
      console.error('Failed to fetch session:', err)
    }
  }, [])

  // Poll for updates when session is running
  useEffect(() => {
    fetchSession()
    
    const interval = setInterval(() => {
      if (session?.isRunning) {
        fetchSession()
      }
    }, 5000)
    
    return () => clearInterval(interval)
  }, [fetchSession, session?.isRunning])

  // Start paper trading
  const startPaperTrading = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/paper-trading', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'start',
          config: {
            ...config,
            symbols: [currentSymbol, 'BTCUSDT', 'ETHUSDT', 'SOLUSDT'].filter((s, i, arr) => arr.indexOf(s) === i),
          },
        }),
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to start paper trading')
      }
      
      const data = await response.json()
      setSession({
        id: data.sessionId,
        startedAt: new Date().toISOString(),
        isRunning: true,
        portfolio: {
          balance: config.initialBalance,
          equity: config.initialBalance,
          totalPnl: 0,
          totalPnlPercent: 0,
          maxDrawdown: 0,
          positions: [],
        },
        trades: [],
      })
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Stop paper trading
  const stopPaperTrading = async () => {
    if (!session) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/paper-trading', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'stop',
          sessionId: session.id,
        }),
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to stop paper trading')
      }
      
      setSession(prev => prev ? { ...prev, isRunning: false } : null)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Get latest backtest for comparison
  const latestBacktest = backtestHistory.length > 0 
    ? backtestHistory[backtestHistory.length - 1] 
    : null

  return (
    <div className="flex flex-col h-full p-4 bg-[#0d0d14] text-gray-100 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <Activity className="w-5 h-5 text-purple-400" />
          Paper Trading
        </h2>
        <Badge 
          variant="outline" 
          className={session?.isRunning 
            ? 'bg-green-500/10 text-green-400 border-green-500/30' 
            : 'bg-gray-800 text-gray-400 border-gray-700'
          }
        >
          {session?.isRunning ? 'Running' : 'Stopped'}
        </Badge>
      </div>

      {error && (
        <div className="mb-4 p-2 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Session Status */}
      {session?.isRunning ? (
        <div className="space-y-4">
          {/* Portfolio Summary */}
          <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-500">Portfolio Value</span>
              <span className="text-sm font-bold text-amber-400">
                ${session.portfolio.equity.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-500">Total P&L</span>
              <span className={`text-sm font-medium ${session.portfolio.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {session.portfolio.totalPnl >= 0 ? '+' : ''}${session.portfolio.totalPnl.toFixed(2)}
                <span className="text-xs ml-1">
                  ({session.portfolio.totalPnlPercent >= 0 ? '+' : ''}{(session.portfolio.totalPnlPercent * 100).toFixed(2)}%)
                </span>
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Max Drawdown</span>
              <span className="text-sm text-red-400">
                {(session.portfolio.maxDrawdown * 100).toFixed(2)}%
              </span>
            </div>
          </div>

          {/* Positions */}
          <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
            <h3 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              Open Positions ({session.portfolio.positions.length})
            </h3>
            {session.portfolio.positions.length === 0 ? (
              <p className="text-xs text-gray-500">No open positions</p>
            ) : (
              <div className="space-y-1">
                {session.portfolio.positions.slice(0, 5).map((pos, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1">
                      <Badge 
                        variant="outline" 
                        className={`text-[9px] px-1 ${pos.side === 'long' ? 'text-green-400' : 'text-red-400'}`}
                      >
                        {pos.side.toUpperCase()}
                      </Badge>
                      <span className="text-gray-300">{pos.symbol}</span>
                    </div>
                    <span className={pos.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                      {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Trades */}
          <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
            <h3 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1">
              <BarChart3 className="w-3 h-3" />
              Recent Trades ({session.trades.length})
            </h3>
            {session.trades.length === 0 ? (
              <p className="text-xs text-gray-500">No trades yet</p>
            ) : (
              <div className="space-y-1">
                {session.trades.slice(-5).reverse().map((trade, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1">
                      <span className="text-gray-400">{trade.symbol}</span>
                      <Badge 
                        variant="outline" 
                        className={`text-[9px] px-1 ${trade.side === 'long' ? 'text-green-400' : 'text-red-400'}`}
                      >
                        {trade.side}
                      </Badge>
                    </div>
                    <span className={trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                      {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Comparison to Backtest */}
          {latestBacktest?.metrics && (
            <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
              <h3 className="text-xs font-medium text-gray-400 mb-2">vs. Backtest</h3>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">BT Return</span>
                  <p className={latestBacktest.metrics.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {(latestBacktest.metrics.totalReturn * 100).toFixed(2)}%
                  </p>
                </div>
                <div>
                  <span className="text-gray-500">Paper Return</span>
                  <p className={session.portfolio.totalPnlPercent >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {(session.portfolio.totalPnlPercent * 100).toFixed(2)}%
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Stop Button */}
          <Button
            onClick={stopPaperTrading}
            disabled={loading}
            className="w-full bg-red-600 hover:bg-red-700 text-white"
          >
            {loading ? (
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Square className="w-4 h-4 mr-2" />
            )}
            Stop Paper Trading
          </Button>
        </div>
      ) : (
        /* Configuration */
        <div className="space-y-4">
          <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800 space-y-3">
            <div>
              <Label className="text-xs text-gray-400">Initial Balance</Label>
              <Input
                type="number"
                value={config.initialBalance}
                onChange={(e) => setConfig(prev => ({ ...prev, initialBalance: parseFloat(e.target.value) || 0 }))}
                className="mt-1 bg-gray-900 border-gray-700 text-sm"
              />
            </div>
            <div>
              <Label className="text-xs text-gray-400">Risk Per Trade (%)</Label>
              <Input
                type="number"
                step="0.01"
                value={(config.riskPerTrade * 100).toFixed(1)}
                onChange={(e) => setConfig(prev => ({ ...prev, riskPerTrade: parseFloat(e.target.value) / 100 || 0 }))}
                className="mt-1 bg-gray-900 border-gray-700 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs text-gray-400">Stop Loss (%)</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={(config.stopLossPercent * 100).toFixed(1)}
                  onChange={(e) => setConfig(prev => ({ ...prev, stopLossPercent: parseFloat(e.target.value) / 100 || 0 }))}
                  className="mt-1 bg-gray-900 border-gray-700 text-sm"
                />
              </div>
              <div>
                <Label className="text-xs text-gray-400">Take Profit (%)</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={(config.takeProfitPercent * 100).toFixed(1)}
                  onChange={(e) => setConfig(prev => ({ ...prev, takeProfitPercent: parseFloat(e.target.value) / 100 || 0 }))}
                  className="mt-1 bg-gray-900 border-gray-700 text-sm"
                />
              </div>
            </div>
          </div>

          {/* Info */}
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-xs text-blue-300">
            <p className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              Paper trading uses live market data with simulated execution to validate strategy performance before using real funds.
            </p>
          </div>

          {/* Start Button */}
          <Button
            onClick={startPaperTrading}
            disabled={loading}
            className="w-full bg-green-600 hover:bg-green-700 text-white"
          >
            {loading ? (
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Play className="w-4 h-4 mr-2" />
            )}
            Start Paper Trading
          </Button>
        </div>
      )}
    </div>
  )
}

