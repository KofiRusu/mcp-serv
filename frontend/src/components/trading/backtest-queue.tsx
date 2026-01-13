'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  Play,
  Trash2,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  ChevronRight,
  Loader2,
} from 'lucide-react'

export interface BacktestJobSummary {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  config: {
    symbols: string[]
    timeframe: string
    startDate?: string
    endDate?: string
    days: number
    initialBalance: number
    modelName?: string // PersRM model version used
  }
  result?: {
    metrics?: {
      totalReturn: number
      winRate: number
      totalTrades: number
      winningTrades?: number
      losingTrades?: number
      sharpeRatio: number
      maxDrawdown: number
      profitFactor?: number
      sortinoRatio?: number
      averageTradeReturn?: number
      expectancy?: number
      annualizedReturn?: number
    }
  }
  error?: string
  createdAt: string
  completedAt?: string
}

interface BacktestQueueProps {
  onSelectJob?: (job: BacktestJobSummary) => void
  selectedJobId?: string
  onNewBacktest?: () => void
  className?: string
}

export function BacktestQueue({
  onSelectJob,
  selectedJobId,
  onNewBacktest,
  className,
}: BacktestQueueProps) {
  const [jobs, setJobs] = useState<BacktestJobSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchJobs = useCallback(async () => {
    try {
      const response = await fetch('/api/backtest?list=true')
      if (response.ok) {
        const data = await response.json()
        setJobs(data.jobs || [])
      }
    } catch (error) {
      console.error('Failed to fetch backtests:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    fetchJobs()
    
    // Poll for updates while there are running jobs
    const interval = setInterval(() => {
      const hasRunning = jobs.some(j => j.status === 'running' || j.status === 'queued')
      if (hasRunning) {
        fetchJobs()
      }
    }, 2000)
    
    return () => clearInterval(interval)
  }, [fetchJobs, jobs])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchJobs()
  }

  const handleDelete = async (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await fetch(`/api/backtest?id=${jobId}`, { method: 'DELETE' })
      setJobs(jobs.filter(j => j.id !== jobId))
    } catch (error) {
      console.error('Failed to delete backtest:', error)
    }
  }

  const formatDateRange = (job: BacktestJobSummary) => {
    if (job.config.startDate && job.config.endDate) {
      const start = new Date(job.config.startDate)
      const end = new Date(job.config.endDate)
      return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${end.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })}`
    }
    return `${job.config.days}d`
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
      case 'queued':
        return <Clock className="h-4 w-4 text-amber-400" />
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-400" />
      case 'cancelled':
        return <AlertCircle className="h-4 w-4 text-gray-500" />
      default:
        return null
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      running: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      queued: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      completed: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      failed: 'bg-red-500/20 text-red-400 border-red-500/30',
      cancelled: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    }
    return variants[status] || ''
  }

  const formatPnL = (value: number) => {
    const formatted = (value * 100).toFixed(1)
    return value >= 0 ? `+${formatted}%` : `${formatted}%`
  }

  if (loading) {
    return (
      <div className={cn('flex items-center justify-center py-8', className)}>
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white">Backtest Queue</span>
          <Badge variant="outline" className="text-xs bg-gray-800/50 text-gray-400 border-gray-700">
            {jobs.length}
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            className="h-7 w-7 p-0 text-gray-400 hover:text-white"
          >
            <RefreshCw className={cn('h-4 w-4', refreshing && 'animate-spin')} />
          </Button>
          {onNewBacktest && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onNewBacktest}
              className="h-7 px-2 text-xs text-purple-400 hover:text-purple-300 hover:bg-purple-500/10"
            >
              <Play className="h-3 w-3 mr-1" />
              New
            </Button>
          )}
        </div>
      </div>

      {/* Job list */}
      <div className="flex-1 overflow-y-auto">
        {jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <Clock className="h-8 w-8 mb-2 opacity-50" />
            <p className="text-sm">No backtests yet</p>
            {onNewBacktest && (
              <Button
                variant="outline"
                size="sm"
                onClick={onNewBacktest}
                className="mt-3 text-xs"
              >
                Start your first backtest
              </Button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-gray-800/50">
            {jobs.map((job) => (
              <div
                key={job.id}
                onClick={() => onSelectJob?.(job)}
                className={cn(
                  'px-3 py-3 cursor-pointer transition-colors hover:bg-gray-800/30',
                  selectedJobId === job.id && 'bg-purple-500/10 border-l-2 border-purple-500'
                )}
              >
                {/* Top row: symbols, status, date range */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(job.status)}
                    <span className="text-sm font-medium text-white">
                      {job.config.symbols.slice(0, 2).map(s => s.replace('USDT', '')).join(', ')}
                      {job.config.symbols.length > 2 && ` +${job.config.symbols.length - 2}`}
                    </span>
                    <Badge 
                      variant="outline" 
                      className={cn('text-[10px] px-1.5 py-0', getStatusBadge(job.status))}
                    >
                      {job.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-gray-500">
                      {formatDateRange(job)}
                    </span>
                    <ChevronRight className="h-4 w-4 text-gray-600" />
                  </div>
                </div>

                {/* Progress bar for running jobs */}
                {job.status === 'running' && (
                  <div className="mb-2">
                    <Progress value={job.progress} className="h-1" />
                    <span className="text-[10px] text-gray-500 mt-0.5">
                      {job.progress.toFixed(0)}% complete
                    </span>
                  </div>
                )}

                {/* Queued indicator */}
                {job.status === 'queued' && (
                  <div className="text-xs text-amber-400/70 mb-2">
                    Waiting in queue...
                  </div>
                )}

                {/* Results for completed jobs */}
                {job.status === 'completed' && job.result?.metrics && (
                  <div className="flex items-center gap-3 text-xs">
                    <span className={cn(
                      'font-medium',
                      job.result.metrics.totalReturn >= 0 ? 'text-emerald-400' : 'text-red-400'
                    )}>
                      {formatPnL(job.result.metrics.totalReturn)}
                    </span>
                    <span className="text-gray-500">
                      {job.result.metrics.totalTrades} trades
                    </span>
                    <span className="text-gray-500">
                      {(job.result.metrics.winRate * 100).toFixed(0)}% win
                    </span>
                    <span className="text-gray-500">
                      SR {job.result.metrics.sharpeRatio.toFixed(1)}
                    </span>
                  </div>
                )}

                {/* Error for failed jobs */}
                {job.status === 'failed' && job.error && (
                  <div className="text-xs text-red-400/80 truncate">
                    {job.error}
                  </div>
                )}

                {/* Bottom row: model, timeframe, timestamp, delete */}
                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center gap-2 text-[10px] text-gray-600">
                    {job.config.modelName && (
                      <>
                        <span className="text-purple-400/80">{job.config.modelName}</span>
                        <span>•</span>
                      </>
                    )}
                    <span>{job.config.timeframe}</span>
                    <span>•</span>
                    <span>${(job.config.initialBalance / 1000).toFixed(0)}k</span>
                    <span>•</span>
                    <span>
                      {new Date(job.createdAt).toLocaleTimeString('en-US', {
                        hour: 'numeric',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => handleDelete(job.id, e)}
                    className="h-6 w-6 p-0 text-gray-600 hover:text-red-400 hover:bg-red-500/10"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Summary footer */}
      {jobs.length > 0 && (
        <div className="px-3 py-2 border-t border-gray-800 text-[10px] text-gray-500 flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            {jobs.filter(j => j.status === 'running').length} running
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            {jobs.filter(j => j.status === 'queued').length} queued
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            {jobs.filter(j => j.status === 'completed').length} done
          </span>
        </div>
      )}
    </div>
  )
}

