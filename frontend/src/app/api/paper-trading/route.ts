/**
 * Paper Trading API Endpoints
 * 
 * POST /api/paper-trading/start - Start paper trading session
 * POST /api/paper-trading/stop - Stop paper trading
 * GET /api/paper-trading/status - Get current positions and P&L
 * GET /api/paper-trading/trades - Get trade history
 * GET /api/paper-trading/comparison - Compare to backtest results
 */

import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

// In-memory store for paper trading sessions (in production, use Redis or DB)
const paperTradingSessions = new Map<string, {
  id: string
  config: any
  portfolio: any
  trades: any[]
  startedAt: string
  isRunning: boolean
}>()

/**
 * POST /api/paper-trading/start - Start paper trading session
 */
export async function POST(request: NextRequest) {
  try {
    const { action, config } = await request.json()
    
    if (action === 'start') {
      const sessionId = `paper-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      
      const validatedConfig = {
        symbols: config.symbols || ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
        initialBalance: config.initialBalance || 100000,
        maxPositionSize: config.maxPositionSize || 0.1,
        maxConcurrentPositions: config.maxConcurrentPositions || 3,
        riskPerTrade: config.riskPerTrade || 0.02,
        stopLossPercent: config.stopLossPercent || 0.02,
        takeProfitPercent: config.takeProfitPercent || 0.04,
        tradingFee: config.tradingFee || 0.001,
        slippage: config.slippage || 0.0005,
      }
      
      // Create session
      paperTradingSessions.set(sessionId, {
        id: sessionId,
        config: validatedConfig,
        portfolio: {
          balance: validatedConfig.initialBalance,
          equity: validatedConfig.initialBalance,
          positions: [],
          totalPnl: 0,
          totalPnlPercent: 0,
          maxDrawdown: 0,
          currentDrawdown: 0,
          peakEquity: validatedConfig.initialBalance,
        },
        trades: [],
        startedAt: new Date().toISOString(),
        isRunning: true,
      })
      
      // Start paper trading engine (client-side will handle actual trading)
      // This API just manages the session state
      
      return NextResponse.json({
        success: true,
        sessionId,
        config: validatedConfig,
        message: 'Paper trading started',
      })
      
    } else if (action === 'stop') {
      const { sessionId } = await request.json()
      
      const session = paperTradingSessions.get(sessionId)
      if (!session) {
        return NextResponse.json(
          { error: 'Session not found' },
          { status: 404 }
        )
      }
      
      session.isRunning = false
      
      // Save session to disk
      await savePaperTradingSession(session)
      
      return NextResponse.json({
        success: true,
        message: 'Paper trading stopped',
      })
      
    } else if (action === 'update') {
      // Update session state from client
      const { sessionId, portfolio, trades } = await request.json()
      
      const session = paperTradingSessions.get(sessionId)
      if (!session) {
        return NextResponse.json(
          { error: 'Session not found' },
          { status: 404 }
        )
      }
      
      if (portfolio) {
        session.portfolio = portfolio
      }
      if (trades) {
        session.trades = trades
      }
      
      return NextResponse.json({
        success: true,
      })
    }
    
    return NextResponse.json(
      { error: 'Invalid action' },
      { status: 400 }
    )
    
  } catch (error: any) {
    console.error('Paper trading API error:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to process request' },
      { status: 500 }
    )
  }
}

/**
 * GET /api/paper-trading/status - Get current status
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const sessionId = searchParams.get('sessionId')
  const action = searchParams.get('action') || 'status'
  
  if (action === 'status' && sessionId) {
    const session = paperTradingSessions.get(sessionId)
    
    if (!session) {
      return NextResponse.json(
        { error: 'Session not found' },
        { status: 404 }
      )
    }
    
    return NextResponse.json({
      success: true,
      session: {
        id: session.id,
        config: session.config,
        portfolio: session.portfolio,
        trades: session.trades,
        startedAt: session.startedAt,
        isRunning: session.isRunning,
      },
    })
    
  } else if (action === 'trades' && sessionId) {
    const session = paperTradingSessions.get(sessionId)
    
    if (!session) {
      return NextResponse.json(
        { error: 'Session not found' },
        { status: 404 }
      )
    }
    
    return NextResponse.json({
      success: true,
      trades: session.trades,
      total: session.trades.length,
    })
    
  } else if (action === 'comparison' && sessionId) {
    // Compare paper trading results to backtest
    const session = paperTradingSessions.get(sessionId)
    
    if (!session) {
      return NextResponse.json(
        { error: 'Session not found' },
        { status: 404 }
      )
    }
    
    // Load most recent backtest for comparison
    const backtestId = searchParams.get('backtestId')
    let backtestResult = null
    
    if (backtestId) {
      try {
        const dataDir = path.join(process.cwd(), 'data', 'backtests')
        const date = new Date().toISOString().slice(0, 10)
        const files = await fs.readdir(dataDir)
        const matchingFile = files.find(f => f.includes(backtestId))
        
        if (matchingFile) {
          const filePath = path.join(dataDir, matchingFile)
          const content = await fs.readFile(filePath, 'utf-8')
          backtestResult = JSON.parse(content)
        }
      } catch (error) {
        console.error('Failed to load backtest for comparison:', error)
      }
    }
    
    // Calculate comparison metrics
    const comparison = backtestResult ? {
      backtest: {
        totalReturn: backtestResult.metrics?.totalReturn || 0,
        winRate: backtestResult.metrics?.winRate || 0,
        sharpeRatio: backtestResult.metrics?.sharpeRatio || 0,
        totalTrades: backtestResult.metrics?.totalTrades || 0,
      },
      paper: {
        totalReturn: session.portfolio.totalPnlPercent,
        winRate: session.trades.length > 0
          ? session.trades.filter((t: any) => t.pnl > 0).length / session.trades.length
          : 0,
        sharpeRatio: 0, // Calculate if needed
        totalTrades: session.trades.length,
      },
      differences: {
        returnDiff: session.portfolio.totalPnlPercent - (backtestResult.metrics?.totalReturn || 0),
        winRateDiff: (session.trades.length > 0
          ? session.trades.filter((t: any) => t.pnl > 0).length / session.trades.length
          : 0) - (backtestResult.metrics?.winRate || 0),
      },
    } : null
    
    return NextResponse.json({
      success: true,
      session: {
        portfolio: session.portfolio,
        trades: session.trades,
      },
      comparison,
    })
    
  } else if (action === 'list') {
    // List all sessions
    const sessions = Array.from(paperTradingSessions.values())
      .sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
    
    return NextResponse.json({
      success: true,
      sessions: sessions.map(s => ({
        id: s.id,
        startedAt: s.startedAt,
        isRunning: s.isRunning,
        portfolio: s.portfolio,
        tradeCount: s.trades.length,
      })),
    })
  }
  
  return NextResponse.json(
    { error: 'Invalid request' },
    { status: 400 }
  )
}

/**
 * Save paper trading session to disk
 */
async function savePaperTradingSession(session: any): Promise<void> {
  try {
    const dataDir = path.join(process.cwd(), 'data', 'paper-trading')
    await fs.mkdir(dataDir, { recursive: true })
    
    const date = new Date().toISOString().slice(0, 10)
    const filePath = path.join(dataDir, `${date}-${session.id}.json`)
    
    await fs.writeFile(filePath, JSON.stringify(session, null, 2))
    console.log(`Saved paper trading session to ${filePath}`)
  } catch (error) {
    console.error('Failed to save paper trading session:', error)
  }
}

