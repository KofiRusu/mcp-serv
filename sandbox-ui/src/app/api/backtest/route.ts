/**
 * Backtesting API Endpoints
 * 
 * POST /api/backtest - Start a new backtest
 * GET /api/backtest - Get backtest status/list (SSE stream)
 * DELETE /api/backtest - Cancel/remove a backtest
 */

import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'
import { BacktestEngine, BacktestConfig } from '@/lib/trading/backtest-engine'

// Backtest job interface
export interface BacktestJob {
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
    maxPositionSize: number
    maxConcurrentPositions: number
    tradingFee: number
    slippage: number
    maxDrawdownLimit: number
    riskPerTrade: number
    stopLossPercent: number
    takeProfitPercent: number
    modelName?: string // PersRM model version used for this backtest
  }
  result?: any
  error?: string
  createdAt: string
  startedAt?: string
  completedAt?: string
}

// In-memory store for backtests
const backtestJobs = new Map<string, BacktestJob>()

// Track running jobs for concurrency control
const MAX_CONCURRENT_JOBS = 3
let runningJobCount = 0

/**
 * Load persisted backtests on startup
 */
async function loadPersistedBacktests() {
  try {
    const dataDir = path.join(process.cwd(), 'data', 'backtests')
    const indexPath = path.join(dataDir, 'index.json')
    
    const exists = await fs.stat(indexPath).catch(() => null)
    if (exists) {
      const data = await fs.readFile(indexPath, 'utf-8')
      const jobs = JSON.parse(data) as BacktestJob[]
      // Only load completed/failed jobs, reset running/queued
      jobs.forEach(job => {
        if (job.status === 'running' || job.status === 'queued') {
          job.status = 'cancelled'
        }
        backtestJobs.set(job.id, job)
      })
      console.log(`Loaded ${jobs.length} persisted backtests`)
    }
  } catch (error) {
    console.error('Failed to load persisted backtests:', error)
  }
}

// Load on module init
loadPersistedBacktests()

/**
 * Persist backtest index
 */
async function persistBacktestIndex() {
  try {
    const dataDir = path.join(process.cwd(), 'data', 'backtests')
    await fs.mkdir(dataDir, { recursive: true })
    
    const jobs = Array.from(backtestJobs.values())
    const recentJobs = jobs.slice(-50) // Keep last 50
    
    const indexPath = path.join(dataDir, 'index.json')
    await fs.writeFile(indexPath, JSON.stringify(recentJobs, null, 2))
  } catch (error) {
    console.error('Failed to persist backtest index:', error)
  }
}

/**
 * POST /api/backtest - Start a new backtest
 */
export async function POST(request: NextRequest) {
  try {
    const config = await request.json()
    
    const backtestId = `bt-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    
    // Parse dates if provided
    let startDate: Date | undefined
    let endDate: Date | undefined
    let days = config.days || 7
    
    if (config.startDate) {
      startDate = new Date(config.startDate)
    }
    if (config.endDate) {
      endDate = new Date(config.endDate)
    }
    
    // Calculate days from date range
    if (startDate && endDate) {
      const diffMs = endDate.getTime() - startDate.getTime()
      days = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
    }
    
    const validatedConfig = {
      symbols: config.symbols || ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
      timeframe: config.timeframe || '5m',
      startDate: startDate?.toISOString(),
      endDate: endDate?.toISOString(),
      days,
      initialBalance: config.initialBalance || 100000,
      maxPositionSize: config.maxPositionSize || 0.1,
      maxConcurrentPositions: config.maxConcurrentPositions || 3,
      tradingFee: config.tradingFee || 0.001,
      slippage: config.slippage || 0.0005,
      maxDrawdownLimit: config.maxDrawdownLimit || 0.15,
      riskPerTrade: config.riskPerTrade || 0.02,
      stopLossPercent: config.stopLossPercent || 0.02,
      takeProfitPercent: config.takeProfitPercent || 0.04,
      modelName: config.modelName || 'persrm-trading', // Default model version
    }
    
    console.log(`[Backtest API] Starting backtest with model: ${validatedConfig.modelName}`)
    
    // Create job
    const job: BacktestJob = {
      id: backtestId,
      status: runningJobCount >= MAX_CONCURRENT_JOBS ? 'queued' : 'running',
      progress: 0,
      config: validatedConfig,
      createdAt: new Date().toISOString(),
    }
    
    if (job.status === 'running') {
      job.startedAt = new Date().toISOString()
    }
    
    backtestJobs.set(backtestId, job)
    persistBacktestIndex()
    
    // Run or queue
    if (job.status === 'running') {
    runBacktestSimulation(backtestId, validatedConfig)
    } else {
      watchJobQueue()
    }
    
    return NextResponse.json({
      success: true,
      backtestId,
      config: validatedConfig,
      status: job.status,
      message: job.status === 'queued' ? 'Backtest queued' : 'Backtest started',
    })
  } catch (error: any) {
    console.error('Backtest start error:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to start backtest' },
      { status: 500 }
    )
  }
}

/**
 * GET /api/backtest - Get backtest status or list
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const backtestId = searchParams.get('id')
  const stream = searchParams.get('stream') === 'true'
  const listAll = searchParams.get('list') === 'true'
  
  // List all backtests
  if (listAll || !backtestId) {
    const jobs = Array.from(backtestJobs.values())
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    
    return NextResponse.json({ 
      jobs,
      runningCount: jobs.filter(j => j.status === 'running').length,
      queuedCount: jobs.filter(j => j.status === 'queued').length,
      completedCount: jobs.filter(j => j.status === 'completed').length,
    })
  }
  
  const job = backtestJobs.get(backtestId)
  
  if (!job) {
    return NextResponse.json(
      { error: 'Backtest not found' },
      { status: 404 }
    )
  }
  
  if (stream) {
    const encoder = new TextEncoder()
    
    const readableStream = new ReadableStream({
      async start(controller) {
        let lastProgress = -1
        let lastStatus = ''
        
        const sendUpdate = () => {
          const data = backtestJobs.get(backtestId)
          if (!data) {
            controller.close()
            return
          }
          
          if (data.progress !== lastProgress || data.status !== lastStatus) {
            lastProgress = data.progress
            lastStatus = data.status
            const event = `data: ${JSON.stringify({
              id: data.id,
              status: data.status,
              progress: data.progress,
              result: data.result,
              error: data.error,
            })}\n\n`
            controller.enqueue(encoder.encode(event))
          }
          
          if (data.status !== 'running' && data.status !== 'queued') {
            controller.close()
          }
        }
        
        const interval = setInterval(sendUpdate, 500)
        sendUpdate()
        
        return () => clearInterval(interval)
      },
    })
    
    return new Response(readableStream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    })
  }
  
  return NextResponse.json(job)
}

/**
 * DELETE /api/backtest - Cancel/remove a backtest
 */
export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const backtestId = searchParams.get('id')
  
  if (!backtestId) {
    return NextResponse.json(
      { error: 'Backtest ID required' },
      { status: 400 }
    )
  }
  
  const job = backtestJobs.get(backtestId)
  
  if (!job) {
    return NextResponse.json(
      { error: 'Backtest not found' },
      { status: 404 }
    )
  }
  
  // Cancel if running
  if (job.status === 'running') {
    job.status = 'cancelled'
    job.completedAt = new Date().toISOString()
    runningJobCount--
  } else if (job.status === 'queued') {
    job.status = 'cancelled'
    job.completedAt = new Date().toISOString()
  }
  
  backtestJobs.delete(backtestId)
  persistBacktestIndex()
  watchJobQueue()
  
  return NextResponse.json({
    success: true,
    message: 'Backtest removed',
  })
}

/**
 * Watch job queue and start queued jobs
 */
function watchJobQueue() {
  if (runningJobCount >= MAX_CONCURRENT_JOBS) return
  
  const queuedJobs = Array.from(backtestJobs.values())
    .filter(j => j.status === 'queued')
    .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
  
  for (const job of queuedJobs) {
    if (runningJobCount >= MAX_CONCURRENT_JOBS) break
    
    job.status = 'running'
    job.startedAt = new Date().toISOString()
    runBacktestSimulation(job.id, job.config)
  }
}

/**
 * Real backtest runner using BacktestEngine with CCXT historical data
 */
async function runBacktestSimulation(backtestId: string, config: any) {
  const job = backtestJobs.get(backtestId)
  if (!job) return
  
  runningJobCount++
  
  try {
    // Parse dates
    const startDate = config.startDate ? new Date(config.startDate) : undefined
    const endDate = config.endDate ? new Date(config.endDate) : undefined
    
    // Convert config to BacktestConfig format
    const backtestConfig: BacktestConfig = {
      symbols: config.symbols || ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
      timeframe: (config.timeframe || '5m') as '1m' | '5m' | '15m',
      initialBalance: config.initialBalance || 100000,
      maxPositionSize: config.maxPositionSize || 0.1,
      maxConcurrentPositions: config.maxConcurrentPositions || 3,
      tradingFee: config.tradingFee || 0.001,
      slippage: config.slippage || 0.0005,
      maxDrawdownLimit: config.maxDrawdownLimit || 0.15,
      riskPerTrade: config.riskPerTrade || 0.02,
      stopLossPercent: config.stopLossPercent || 0.02,
      takeProfitPercent: config.takeProfitPercent || 0.04,
      days: config.days || 7,
      startDate,
      endDate,
      modelName: config.modelName || 'persrm-trading', // Model version for this backtest
    }
    
    // Create and run backtest engine
    const engine = new BacktestEngine(backtestConfig)
    
    // Set up progress callback
    const onProgress = (progress: any) => {
      const currentJob = backtestJobs.get(backtestId)
      if (!currentJob || currentJob.status === 'cancelled') {
        engine.stop()
        return
      }
      
      currentJob.progress = progress.percentComplete
      persistBacktestIndex()
    }
    
    // Run the backtest
    const result = await engine.run(onProgress)
    
    // Check if cancelled
    const finalJob = backtestJobs.get(backtestId)
    if (!finalJob || finalJob.status === 'cancelled') {
      runningJobCount--
      watchJobQueue()
      return
    }
    
    // Format result for API response
    const formattedResult = {
      config: backtestConfig,
      portfolio: result.portfolio,
      trades: result.trades,
      metrics: result.metrics,
      equityCurve: result.equityCurve,
      signals: result.signals,
      dateRange: {
        start: (startDate || new Date(Date.now() - config.days * 24 * 60 * 60 * 1000)).toISOString(),
        end: (endDate || new Date()).toISOString(),
      },
      startTime: job.startedAt,
      endTime: result.endTime.toISOString(),
      duration: result.duration,
    }
    
    job.status = 'completed'
    job.progress = 100
    job.result = formattedResult
    job.completedAt = new Date().toISOString()
    
    await saveBacktestResult(backtestId, formattedResult)
    persistBacktestIndex()
    
  } catch (error: any) {
    console.error('Backtest error:', error)
    const currentJob = backtestJobs.get(backtestId)
    if (currentJob) {
      currentJob.status = 'failed'
      currentJob.error = error.message || String(error)
      currentJob.completedAt = new Date().toISOString()
      persistBacktestIndex()
    }
  } finally {
    runningJobCount--
    watchJobQueue()
  }
}

/**
 * Save backtest result to file
 */
async function saveBacktestResult(backtestId: string, result: any) {
  try {
    const dataDir = path.join(process.cwd(), 'data', 'backtests')
    await fs.mkdir(dataDir, { recursive: true })
    
    const date = new Date().toISOString().slice(0, 10)
    const filePath = path.join(dataDir, `${date}-${backtestId}.json`)
    
    await fs.writeFile(filePath, JSON.stringify(result, null, 2))
    console.log(`Saved backtest result to ${filePath}`)
  } catch (error) {
    console.error('Failed to save backtest result:', error)
  }
}
