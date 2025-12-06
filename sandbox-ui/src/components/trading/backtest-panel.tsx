'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { DatePicker } from '@/components/ui/date-picker'
import { BacktestQueue, BacktestJobSummary } from './backtest-queue'
import {
  Play,
  Square,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  Percent,
  BarChart3,
  Zap,
  Brain,
  History,
  Trash2,
  ChevronRight,
  ChevronLeft,
  CalendarDays,
  Plus,
  Bot,
} from 'lucide-react'

// Available PersRM model versions for backtesting
// Add new versions here after training with persrm_trading_cycle.sh
const MODEL_OPTIONS = [
  { value: 'persrm-trading', label: 'persrm-trading (default)' },
  { value: 'persrm-trading-v1', label: 'persrm-trading-v1' },
  { value: 'persrm-trading-v2', label: 'persrm-trading-v2' },
]
import { useTradingStore, BacktestConfig, BacktestResult } from '@/stores/trading-store'

type ViewMode = 'queue' | 'config' | 'running' | 'results'

export function BacktestPanel() {
  const {
    backtestHistory,
    currentBacktestId,
    isBacktesting,
    backtestProgress,
    addBacktestResult,
    setCurrentBacktestId,
    setIsBacktesting,
    setBacktestProgress,
    loadBacktestHistory,
    getBacktestById,
  } = useTradingStore()

  const [viewMode, setViewMode] = useState<ViewMode>('queue')
  const [backtestId, setBacktestId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedJob, setSelectedJob] = useState<BacktestJobSummary | null>(null)
  
  // Configuration state with date range and model selection
  const [config, setConfig] = useState<BacktestConfig & { startDate?: Date; endDate?: Date; modelName?: string }>({
    symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
    timeframe: '5m',
    initialBalance: 100000,
    days: 7,
    maxPositionSize: 0.1,
    riskPerTrade: 0.02,
    stopLossPercent: 0.02,
    takeProfitPercent: 0.04,
    startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
    endDate: new Date(),
    modelName: 'persrm-trading', // Default model version
  })
  
  // Get current result from store
  const currentResult = currentBacktestId ? getBacktestById(currentBacktestId) : null
  
  // Load history on mount
  useEffect(() => {
    loadBacktestHistory()
  }, [loadBacktestHistory])
  
  // Update days when date range changes
  useEffect(() => {
    if (config.startDate && config.endDate) {
      const diffMs = config.endDate.getTime() - config.startDate.getTime()
      const days = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
      if (days !== config.days && days > 0) {
        setConfig(prev => ({ ...prev, days }))
      }
    }
  }, [config.startDate, config.endDate, config.days])

  // Date preset handlers
  const setDatePreset = (preset: 'last7d' | 'last30d' | 'last90d' | 'ytd') => {
    const now = new Date()
    let startDate: Date
    
    switch (preset) {
      case 'last7d':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        break
      case 'last30d':
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
        break
      case 'last90d':
        startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)
        break
      case 'ytd':
        startDate = new Date(now.getFullYear(), 0, 1)
        break
    }
    
    setConfig(prev => ({
      ...prev,
      startDate,
      endDate: now,
    }))
  }
  
  // Start backtest
  const startBacktest = async () => {
    setIsBacktesting(true)
    setBacktestProgress(0)
    setError(null)
    setViewMode('running')
    
    try {
      const response = await fetch('/api/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...config,
          startDate: config.startDate?.toISOString(),
          endDate: config.endDate?.toISOString(),
          modelName: config.modelName || 'persrm-trading',
        }),
      })
      
      if (!response.ok) {
        throw new Error('Failed to start backtest')
      }
      
      const data = await response.json()
      setBacktestId(data.backtestId)
      
      // Start listening for updates
      pollBacktestStatus(data.backtestId)
      
    } catch (err: any) {
      setError(err.message)
      setIsBacktesting(false)
      setViewMode('config')
    }
  }
  
  // Poll for backtest status
  const pollBacktestStatus = useCallback(async (id: string) => {
    const poll = async () => {
      try {
        const response = await fetch(`/api/backtest?id=${id}`)
        const data = await response.json()
        
        setBacktestProgress(data.progress || 0)
        
        if (data.status === 'completed') {
          const result: BacktestResult = {
            id,
            config,
            metrics: data.result.metrics,
            trades: data.result.trades || [],
            equityCurve: data.result.equityCurve || [],
            duration: data.result.duration || 0,
            startTime: data.result.startTime || new Date().toISOString(),
            endTime: data.result.endTime || new Date().toISOString(),
            status: 'completed',
          }
          
          addBacktestResult(result)
          setIsBacktesting(false)
          setViewMode('results')
          
        } else if (data.status === 'error' || data.status === 'failed') {
          setError(data.error || 'Backtest failed')
          setIsBacktesting(false)
          setViewMode('config')
        } else if (data.status === 'running' || data.status === 'queued') {
          setTimeout(poll, 500)
        }
      } catch (err) {
        console.error('Polling error:', err)
        setTimeout(poll, 1000)
      }
    }
    
    poll()
  }, [config, addBacktestResult, setIsBacktesting, setBacktestProgress])
  
  // Stop backtest
  const stopBacktest = async () => {
    if (backtestId) {
      try {
        await fetch(`/api/backtest?id=${backtestId}`, { method: 'DELETE' })
      } catch (e) {
        console.error('Failed to stop backtest:', e)
      }
    }
    setIsBacktesting(false)
    setViewMode('queue')
  }
  
  // Go to new backtest config
  const goToNewBacktest = () => {
    setError(null)
    setBacktestProgress(0)
    setViewMode('config')
    setBacktestId(null)
    setSelectedJob(null)
  }

  // Handle job selection from queue
  const handleSelectJob = (job: BacktestJobSummary) => {
    setSelectedJob(job)
    if (job.status === 'completed' && job.result) {
      // Show results view
      setViewMode('results')
    } else if (job.status === 'running') {
      setBacktestId(job.id)
      setIsBacktesting(true)
      setViewMode('running')
      pollBacktestStatus(job.id)
    }
  }
  
  // Format percentage
  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : ''
    return `${sign}${(value * 100).toFixed(2)}%`
  }
  
  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  // Get display result (from selected job or current result)
  const displayResult = selectedJob?.status === 'completed' && selectedJob.result?.metrics
    ? {
        config: {
          ...selectedJob.config,
          riskPerTrade: 0.02,
          stopLossPercent: 0.02,
          takeProfitPercent: 0.04,
          maxPositionSize: 0.1,
        },
        metrics: selectedJob.result.metrics,
        duration: 0,
      }
    : currentResult
  
  return (
    <div className="flex flex-col h-full bg-[#0d0d14] text-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-400" />
          <span className="font-semibold">PersRM Backtesting</span>
        </div>
        <div className="flex items-center gap-2">
          {viewMode !== 'queue' && (
          <Button
            size="sm"
            variant="ghost"
              onClick={() => setViewMode('queue')}
            className="text-gray-400 hover:text-white"
          >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Queue
            </Button>
          )}
          {(viewMode === 'results' || viewMode === 'queue') && (
            <Button
              size="sm"
              variant="ghost"
              onClick={goToNewBacktest}
              className="text-purple-400 hover:text-purple-300"
            >
              <Plus className="w-4 h-4 mr-1" />
            New Test
          </Button>
        )}
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {/* Queue View */}
        {viewMode === 'queue' && (
          <BacktestQueue
            onSelectJob={handleSelectJob}
            selectedJobId={selectedJob?.id}
            onNewBacktest={goToNewBacktest}
            className="h-full"
          />
        )}
        
        {/* Configuration View */}
        {viewMode === 'config' && !isBacktesting && (
          <div className="p-3 space-y-4">
            <h3 className="text-sm font-medium text-gray-400">New Backtest Configuration</h3>
            
            {/* Date Range Section */}
            <div className="space-y-3 bg-gray-900/50 rounded-lg p-3 border border-gray-800">
              <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                <CalendarDays className="w-4 h-4" />
                <span>Date Range</span>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs text-gray-500">Start Date</label>
                  <DatePicker
                    value={config.startDate}
                    onChange={(date) => date && setConfig(prev => ({ ...prev, startDate: date }))}
                    maxDate={config.endDate}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-gray-500">End Date</label>
                  <DatePicker
                    value={config.endDate}
                    onChange={(date) => date && setConfig(prev => ({ ...prev, endDate: date }))}
                    minDate={config.startDate}
                    maxDate={new Date()}
                  />
                </div>
              </div>
              
              {/* Date Presets */}
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setDatePreset('last7d')}
                  className="px-2 py-1 text-xs rounded bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white transition-colors"
                >
                  Last 7d
                </button>
                <button
                  onClick={() => setDatePreset('last30d')}
                  className="px-2 py-1 text-xs rounded bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white transition-colors"
                >
                  Last 30d
                </button>
                <button
                  onClick={() => setDatePreset('last90d')}
                  className="px-2 py-1 text-xs rounded bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white transition-colors"
                >
                  Last 90d
                </button>
                <button
                  onClick={() => setDatePreset('ytd')}
                  className="px-2 py-1 text-xs rounded bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white transition-colors"
                >
                  YTD
                </button>
              </div>
              
              <div className="text-xs text-gray-500">
                Duration: {config.days} days
              </div>
            </div>
            
            {/* Model Selection */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <Bot className="w-4 h-4" />
                <span>Model</span>
              </div>
              <select
                value={config.modelName || 'persrm-trading'}
                onChange={(e) => setConfig(prev => ({ ...prev, modelName: e.target.value }))}
                className="w-full h-9 px-3 text-sm rounded-md bg-gray-900 border border-gray-700 text-white focus:border-purple-500 focus:outline-none"
              >
                {MODEL_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <p className="text-[10px] text-gray-600">
                Choose which PersRM version to test. Add new versions after training.
              </p>
            </div>
            
            {/* Symbols */}
            <div className="space-y-2">
              <label className="text-xs text-gray-500">Trading Pairs</label>
              <div className="flex flex-wrap gap-2">
                {['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'].map(symbol => (
                  <button
                    key={symbol}
                    onClick={() => {
                      setConfig(prev => ({
                        ...prev,
                        symbols: prev.symbols.includes(symbol)
                          ? prev.symbols.filter(s => s !== symbol)
                          : [...prev.symbols, symbol],
                      }))
                    }}
                    className={`px-2 py-1 text-xs rounded-md transition-colors ${
                      config.symbols.includes(symbol)
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}
                  >
                    {symbol.replace('USDT', '')}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Timeframe */}
            <div className="space-y-2">
              <label className="text-xs text-gray-500">Timeframe</label>
              <div className="flex gap-2">
                {['1m', '5m', '15m'].map(tf => (
                  <button
                    key={tf}
                    onClick={() => setConfig(prev => ({ ...prev, timeframe: tf as any }))}
                    className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                      config.timeframe === tf
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Balance */}
            <div className="space-y-2">
              <label className="text-xs text-gray-500">Initial Balance</label>
              <div className="flex gap-2">
                {[10000, 50000, 100000, 250000].map(balance => (
                  <button
                    key={balance}
                    onClick={() => setConfig(prev => ({ ...prev, initialBalance: balance }))}
                    className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                      config.initialBalance === balance
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}
                  >
                    ${(balance / 1000).toFixed(0)}k
                  </button>
                ))}
              </div>
            </div>
            
            {/* Risk Settings */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-gray-500">Risk per Trade</label>
                <Input
                  type="number"
                  value={(config.riskPerTrade * 100).toFixed(1)}
                  onChange={e => setConfig(prev => ({ ...prev, riskPerTrade: parseFloat(e.target.value) / 100 }))}
                  className="h-8 bg-gray-900 border-gray-700 text-sm"
                  step="0.5"
                  min="0.5"
                  max="5"
                />
                <span className="text-[10px] text-gray-600">% of equity</span>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-500">Stop Loss</label>
                <Input
                  type="number"
                  value={(config.stopLossPercent * 100).toFixed(1)}
                  onChange={e => setConfig(prev => ({ ...prev, stopLossPercent: parseFloat(e.target.value) / 100 }))}
                  className="h-8 bg-gray-900 border-gray-700 text-sm"
                  step="0.5"
                  min="0.5"
                  max="10"
                />
                <span className="text-[10px] text-gray-600">% from entry</span>
              </div>
            </div>
            
            {/* Start Button */}
            <Button
              onClick={startBacktest}
              className="w-full bg-purple-600 hover:bg-purple-700"
              disabled={config.symbols.length === 0}
            >
              <Play className="w-4 h-4 mr-2" />
              Start Backtest
            </Button>
          </div>
        )}
        
        {/* Running State */}
        {viewMode === 'running' && isBacktesting && (
          <div className="p-3 space-y-4">
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-purple-600/20 mb-4">
                <Activity className="w-8 h-8 text-purple-400 animate-pulse" />
              </div>
              <h3 className="font-medium mb-2">Running Backtest</h3>
              <p className="text-sm text-gray-400 mb-4">
                Testing strategy on {config.symbols.length} pairs
                {config.startDate && config.endDate && (
                  <>
                    <br />
                    <span className="text-xs">
                      {config.startDate.toLocaleDateString()} - {config.endDate.toLocaleDateString()}
                    </span>
                  </>
                )}
              </p>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-gray-400">
                <span>Progress</span>
                <span>{backtestProgress.toFixed(0)}%</span>
              </div>
              <Progress value={backtestProgress} className="h-2" />
            </div>
            
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-gray-900 rounded-lg p-3">
                <div className="text-gray-500 mb-1">Timeframe</div>
                <div className="font-medium">{config.timeframe}</div>
              </div>
              <div className="bg-gray-900 rounded-lg p-3">
                <div className="text-gray-500 mb-1">Pairs</div>
                <div className="font-medium">{config.symbols.length}</div>
              </div>
            </div>
            
            <Button
              onClick={stopBacktest}
              variant="outline"
              className="w-full border-red-600 text-red-400 hover:bg-red-600/10"
            >
              <Square className="w-4 h-4 mr-2" />
              Stop Backtest
            </Button>
          </div>
        )}
        
        {/* Error State */}
        {error && (
          <div className="p-3">
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <div>
                <h4 className="font-medium text-red-400">Backtest Failed</h4>
                <p className="text-sm text-gray-400 mt-1">{error}</p>
              </div>
            </div>
            <Button
                onClick={goToNewBacktest}
              variant="outline"
              size="sm"
              className="mt-3"
            >
              Try Again
            </Button>
            </div>
          </div>
        )}
        
        {/* Results */}
        {viewMode === 'results' && displayResult && !isBacktesting && (
          <div className="p-3 space-y-4">
            {/* Summary */}
            <div className={`rounded-lg p-4 ${
              displayResult.metrics.totalReturn >= 0 
                ? 'bg-green-500/10 border border-green-500/30' 
                : 'bg-red-500/10 border border-red-500/30'
            }`}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  {displayResult.metrics.totalReturn >= 0 
                    ? <TrendingUp className="w-5 h-5 text-green-400" />
                    : <TrendingDown className="w-5 h-5 text-red-400" />
                  }
                  <span className="font-medium">
                    {displayResult.metrics.totalReturn >= 0 ? 'Profitable' : 'Loss'}
                  </span>
                </div>
                <Badge variant="outline" className={
                  displayResult.metrics.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'
                }>
                  {formatPercent(displayResult.metrics.totalReturn)}
                </Badge>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-500">Final Balance</div>
                  <div className="text-lg font-bold">
                    {formatCurrency(displayResult.config.initialBalance * (1 + displayResult.metrics.totalReturn))}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Total P&L</div>
                  <div className={`text-lg font-bold ${
                    displayResult.metrics.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {formatCurrency(displayResult.config.initialBalance * displayResult.metrics.totalReturn)}
                  </div>
                </div>
              </div>
            </div>
            
            {/* Key Metrics */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-400">Performance Metrics</h4>
              <div className="grid grid-cols-2 gap-2">
                <MetricCard
                  icon={<Target className="w-4 h-4" />}
                  label="Win Rate"
                  value={formatPercent(displayResult.metrics.winRate)}
                  good={displayResult.metrics.winRate >= 0.5}
                />
                <MetricCard
                  icon={<BarChart3 className="w-4 h-4" />}
                  label="Sharpe Ratio"
                  value={displayResult.metrics.sharpeRatio.toFixed(2)}
                  good={displayResult.metrics.sharpeRatio >= 1.5}
                />
                <MetricCard
                  icon={<AlertTriangle className="w-4 h-4" />}
                  label="Max Drawdown"
                  value={formatPercent(-displayResult.metrics.maxDrawdown)}
                  good={displayResult.metrics.maxDrawdown <= 0.1}
                  inverted
                />
                <MetricCard
                  icon={<Zap className="w-4 h-4" />}
                  label="Total Trades"
                  value={displayResult.metrics.totalTrades.toString()}
                  good={displayResult.metrics.totalTrades >= 10}
                />
              </div>
            </div>
            
            {/* Trade Stats */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-400">Trade Statistics</h4>
              <div className="bg-gray-900 rounded-lg p-3 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Total Trades</span>
                  <span>{displayResult.metrics.totalTrades}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Winning</span>
                  <span className="text-green-400">{displayResult.metrics.winningTrades ?? Math.round(displayResult.metrics.totalTrades * displayResult.metrics.winRate)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Losing</span>
                  <span className="text-red-400">{displayResult.metrics.losingTrades ?? Math.round(displayResult.metrics.totalTrades * (1 - displayResult.metrics.winRate))}</span>
                </div>
              </div>
            </div>
            
            {/* Run Another Button */}
            <Button
              onClick={goToNewBacktest}
              variant="outline"
              className="w-full border-purple-600 text-purple-400 hover:bg-purple-600/10"
            >
              <Plus className="w-4 h-4 mr-2" />
              Run Another Backtest
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

// Metric Card Component
function MetricCard({ 
  icon, 
  label, 
  value, 
  good,
  inverted = false,
}: { 
  icon: React.ReactNode
  label: string
  value: string
  good: boolean
  inverted?: boolean
}) {
  const colorClass = inverted
    ? (good ? 'text-green-400' : 'text-red-400')
    : (good ? 'text-green-400' : 'text-yellow-400')
  
  return (
    <div className="bg-gray-900 rounded-lg p-3">
      <div className="flex items-center gap-2 text-gray-500 mb-1">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <div className={`text-lg font-bold ${colorClass}`}>
        {value}
      </div>
    </div>
  )
}
