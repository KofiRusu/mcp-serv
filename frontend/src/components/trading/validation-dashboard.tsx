'use client'

/**
 * Validation Dashboard Component
 * 
 * Compares backtest, paper trading, and live trading results
 * to ensure strategy consistency across modes.
 */

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Activity,
  RefreshCw,
  ChevronRight,
} from 'lucide-react'
import { useTradingStore } from '@/stores/trading-store'

interface ValidationCriteria {
  name: string
  status: 'pass' | 'warning' | 'fail'
  expected: number
  actual: number
  threshold: number
  message: string
}

interface ComparisonData {
  backtest?: {
    totalReturn: number
    winRate: number
    sharpeRatio: number
    totalTrades: number
    maxDrawdown: number
  }
  paper?: {
    totalReturn: number
    winRate: number
    totalTrades: number
    maxDrawdown: number
  }
  validation?: {
    overall: 'pass' | 'warning' | 'fail'
    criteria: ValidationCriteria[]
    recommendations: string[]
  }
}

export function ValidationDashboard() {
  const { backtestHistory } = useTradingStore()
  const [comparison, setComparison] = useState<ComparisonData | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedBacktest, setSelectedBacktest] = useState<string | null>(null)

  // Get latest backtest
  const latestBacktest = backtestHistory.length > 0 
    ? backtestHistory[backtestHistory.length - 1] 
    : null

  // Fetch comparison data
  const fetchComparison = async () => {
    if (!latestBacktest?.id) return

    setLoading(true)
    try {
      // Get paper trading comparison
      const response = await fetch(`/api/paper-trading?action=comparison&sessionId=${selectedBacktest || 'latest'}&backtestId=${latestBacktest.id}`)
      
      if (response.ok) {
        const data = await response.json()
        
        // Build comparison data
        const comparisonData: ComparisonData = {
          backtest: latestBacktest.metrics ? {
            totalReturn: latestBacktest.metrics.totalReturn,
            winRate: latestBacktest.metrics.winRate,
            sharpeRatio: latestBacktest.metrics.sharpeRatio,
            totalTrades: latestBacktest.metrics.totalTrades,
            maxDrawdown: latestBacktest.metrics.maxDrawdown,
          } : undefined,
          paper: data.session?.portfolio ? {
            totalReturn: data.session.portfolio.totalPnlPercent,
            winRate: data.session.trades?.length > 0
              ? data.session.trades.filter((t: any) => t.pnl > 0).length / data.session.trades.length
              : 0,
            totalTrades: data.session.trades?.length || 0,
            maxDrawdown: data.session.portfolio.maxDrawdown,
          } : undefined,
        }

        // Generate validation criteria
        if (comparisonData.backtest && comparisonData.paper) {
          const returnDiff = Math.abs(comparisonData.paper.totalReturn - comparisonData.backtest.totalReturn)
          const winRateDiff = Math.abs(comparisonData.paper.winRate - comparisonData.backtest.winRate)
          
          const criteria: ValidationCriteria[] = [
            {
              name: 'Return Consistency',
              status: returnDiff <= 0.2 ? 'pass' : returnDiff <= 0.3 ? 'warning' : 'fail',
              expected: comparisonData.backtest.totalReturn,
              actual: comparisonData.paper.totalReturn,
              threshold: 0.2,
              message: `Return difference: ${(returnDiff * 100).toFixed(2)}%`,
            },
            {
              name: 'Win Rate Consistency',
              status: winRateDiff <= 0.1 ? 'pass' : winRateDiff <= 0.15 ? 'warning' : 'fail',
              expected: comparisonData.backtest.winRate,
              actual: comparisonData.paper.winRate,
              threshold: 0.1,
              message: `Win rate difference: ${(winRateDiff * 100).toFixed(2)}%`,
            },
            {
              name: 'Drawdown Check',
              status: comparisonData.paper.maxDrawdown <= comparisonData.backtest.maxDrawdown * 1.5 
                ? 'pass' 
                : comparisonData.paper.maxDrawdown <= comparisonData.backtest.maxDrawdown * 2 
                ? 'warning' 
                : 'fail',
              expected: comparisonData.backtest.maxDrawdown,
              actual: comparisonData.paper.maxDrawdown,
              threshold: 1.5,
              message: `Drawdown ratio: ${(comparisonData.paper.maxDrawdown / comparisonData.backtest.maxDrawdown).toFixed(2)}x`,
            },
          ]

          const failCount = criteria.filter(c => c.status === 'fail').length
          const warnCount = criteria.filter(c => c.status === 'warning').length

          comparisonData.validation = {
            overall: failCount > 0 ? 'fail' : warnCount > 0 ? 'warning' : 'pass',
            criteria,
            recommendations: failCount > 0 
              ? ['Do not proceed to live trading until issues are resolved.']
              : warnCount > 0
              ? ['Monitor closely and consider adjustments before increasing position sizes.']
              : ['Strategy validation passed. Consider starting with micro positions in live trading.'],
          }
        }

        setComparison(comparisonData)
      }
    } catch (error) {
      console.error('Failed to fetch comparison:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (latestBacktest) {
      fetchComparison()
    }
  }, [latestBacktest?.id])

  const getStatusIcon = (status: 'pass' | 'warning' | 'fail') => {
    switch (status) {
      case 'pass':
        return <CheckCircle className="w-4 h-4 text-green-400" />
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />
      case 'fail':
        return <XCircle className="w-4 h-4 text-red-400" />
    }
  }

  const getStatusColor = (status: 'pass' | 'warning' | 'fail') => {
    switch (status) {
      case 'pass':
        return 'text-green-400 bg-green-400/10 border-green-400/30'
      case 'warning':
        return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30'
      case 'fail':
        return 'text-red-400 bg-red-400/10 border-red-400/30'
    }
  }

  return (
    <div className="flex flex-col h-full p-4 bg-[#0d0d14] text-gray-100 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <Activity className="w-5 h-5 text-purple-400" />
          Strategy Validation
        </h2>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchComparison}
          disabled={loading || !latestBacktest}
          className="text-xs"
        >
          <RefreshCw className={`w-3 h-3 mr-1 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {!latestBacktest ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center text-gray-500">
          <BarChart3 className="w-12 h-12 mb-3 opacity-50" />
          <p className="text-sm mb-1">No backtest data available</p>
          <p className="text-xs">Run a backtest first to enable validation</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Overall Status */}
          {comparison?.validation && (
            <div className={`p-3 rounded-lg border ${getStatusColor(comparison.validation.overall)}`}>
              <div className="flex items-center gap-2 mb-2">
                {getStatusIcon(comparison.validation.overall)}
                <span className="font-semibold">
                  {comparison.validation.overall === 'pass' && 'Validation Passed'}
                  {comparison.validation.overall === 'warning' && 'Validation Warning'}
                  {comparison.validation.overall === 'fail' && 'Validation Failed'}
                </span>
              </div>
              {comparison.validation.recommendations.map((rec, i) => (
                <p key={i} className="text-xs opacity-80">{rec}</p>
              ))}
            </div>
          )}

          {/* Comparison Table */}
          <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
            <h3 className="text-sm font-medium mb-3 text-gray-300">Performance Comparison</h3>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="text-gray-500">Metric</div>
              <div className="text-gray-500 text-center">Backtest</div>
              <div className="text-gray-500 text-center">Paper</div>

              {/* Total Return */}
              <div className="text-gray-300">Total Return</div>
              <div className="text-center">
                <span className={comparison?.backtest?.totalReturn && comparison.backtest.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {comparison?.backtest?.totalReturn 
                    ? `${(comparison.backtest.totalReturn * 100).toFixed(2)}%`
                    : '-'}
                </span>
              </div>
              <div className="text-center">
                <span className={comparison?.paper?.totalReturn && comparison.paper.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {comparison?.paper?.totalReturn !== undefined
                    ? `${(comparison.paper.totalReturn * 100).toFixed(2)}%`
                    : '-'}
                </span>
              </div>

              {/* Win Rate */}
              <div className="text-gray-300">Win Rate</div>
              <div className="text-center text-gray-200">
                {comparison?.backtest?.winRate 
                  ? `${(comparison.backtest.winRate * 100).toFixed(1)}%`
                  : '-'}
              </div>
              <div className="text-center text-gray-200">
                {comparison?.paper?.winRate !== undefined
                  ? `${(comparison.paper.winRate * 100).toFixed(1)}%`
                  : '-'}
              </div>

              {/* Total Trades */}
              <div className="text-gray-300">Total Trades</div>
              <div className="text-center text-gray-200">
                {comparison?.backtest?.totalTrades || '-'}
              </div>
              <div className="text-center text-gray-200">
                {comparison?.paper?.totalTrades || '-'}
              </div>

              {/* Max Drawdown */}
              <div className="text-gray-300">Max Drawdown</div>
              <div className="text-center text-red-400">
                {comparison?.backtest?.maxDrawdown
                  ? `${(comparison.backtest.maxDrawdown * 100).toFixed(2)}%`
                  : '-'}
              </div>
              <div className="text-center text-red-400">
                {comparison?.paper?.maxDrawdown !== undefined
                  ? `${(comparison.paper.maxDrawdown * 100).toFixed(2)}%`
                  : '-'}
              </div>
            </div>
          </div>

          {/* Validation Criteria */}
          {comparison?.validation?.criteria && (
            <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
              <h3 className="text-sm font-medium mb-3 text-gray-300">Validation Criteria</h3>
              <div className="space-y-2">
                {comparison.validation.criteria.map((criterion, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(criterion.status)}
                      <span className="text-gray-300">{criterion.name}</span>
                    </div>
                    <span className="text-gray-500">{criterion.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Workflow Steps */}
          <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
            <h3 className="text-sm font-medium mb-3 text-gray-300">Validation Workflow</h3>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center ${latestBacktest ? 'bg-green-500' : 'bg-gray-700'}`}>
                  {latestBacktest ? <CheckCircle className="w-3 h-3" /> : '1'}
                </div>
                <span className={latestBacktest ? 'text-gray-300' : 'text-gray-500'}>
                  Run backtest on historical data
                </span>
                <ChevronRight className="w-3 h-3 text-gray-600 ml-auto" />
              </div>
              <div className="flex items-center gap-2 text-xs">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center ${comparison?.paper ? 'bg-green-500' : 'bg-gray-700'}`}>
                  {comparison?.paper ? <CheckCircle className="w-3 h-3" /> : '2'}
                </div>
                <span className={comparison?.paper ? 'text-gray-300' : 'text-gray-500'}>
                  Paper trade for 1-2 weeks
                </span>
                <ChevronRight className="w-3 h-3 text-gray-600 ml-auto" />
              </div>
              <div className="flex items-center gap-2 text-xs">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center ${comparison?.validation?.overall === 'pass' ? 'bg-green-500' : 'bg-gray-700'}`}>
                  {comparison?.validation?.overall === 'pass' ? <CheckCircle className="w-3 h-3" /> : '3'}
                </div>
                <span className={comparison?.validation?.overall === 'pass' ? 'text-gray-300' : 'text-gray-500'}>
                  Validate results match
                </span>
                <ChevronRight className="w-3 h-3 text-gray-600 ml-auto" />
              </div>
              <div className="flex items-center gap-2 text-xs">
                <div className="w-5 h-5 rounded-full bg-gray-700 flex items-center justify-center">
                  4
                </div>
                <span className="text-gray-500">
                  Start live with micro positions
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

