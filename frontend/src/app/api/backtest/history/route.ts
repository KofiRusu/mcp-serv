/**
 * Backtest History API Endpoints
 * 
 * GET /api/backtest/history - List all saved backtests
 * GET /api/backtest/history?id=xxx - Get specific backtest by ID
 * DELETE /api/backtest/history?id=xxx - Delete specific backtest
 */

import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

const BACKTESTS_DIR = path.join(process.cwd(), 'data', 'backtests')

interface BacktestSummary {
  id: string
  date: string
  config: {
    symbols: string[]
    timeframe: string
    days: number
    initialBalance: number
  }
  metrics: {
    totalReturn: number
    winRate: number
    profitFactor: number
    maxDrawdown: number
    totalTrades: number
    sharpeRatio: number
  }
  duration: number
  status: 'completed' | 'error'
}

/**
 * GET /api/backtest/history - List all saved backtests or get specific one
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const backtestId = searchParams.get('id')
  
  try {
    // Ensure directory exists
    await fs.mkdir(BACKTESTS_DIR, { recursive: true })
    
    // If specific ID requested, return that backtest
    if (backtestId) {
      const files = await fs.readdir(BACKTESTS_DIR)
      const matchingFile = files.find(f => f.includes(backtestId))
      
      if (!matchingFile) {
        return NextResponse.json(
          { error: 'Backtest not found' },
          { status: 404 }
        )
      }
      
      const filePath = path.join(BACKTESTS_DIR, matchingFile)
      const content = await fs.readFile(filePath, 'utf-8')
      const backtest = JSON.parse(content)
      
      return NextResponse.json({
        success: true,
        backtest: {
          ...backtest,
          id: backtestId,
        },
      })
    }
    
    // List all backtests
    const files = await fs.readdir(BACKTESTS_DIR)
    const jsonFiles = files.filter(f => f.endsWith('.json'))
    
    const backtests: BacktestSummary[] = []
    
    for (const file of jsonFiles) {
      try {
        const filePath = path.join(BACKTESTS_DIR, file)
        const content = await fs.readFile(filePath, 'utf-8')
        const data = JSON.parse(content)
        
        // Extract ID from filename (format: YYYY-MM-DD-bt-xxx.json)
        const idMatch = file.match(/bt-[\w-]+/)
        const id = idMatch ? idMatch[0] : file.replace('.json', '')
        
        // Extract date from filename
        const dateMatch = file.match(/^\d{4}-\d{2}-\d{2}/)
        const date = dateMatch ? dateMatch[0] : new Date().toISOString().slice(0, 10)
        
        backtests.push({
          id,
          date,
          config: {
            symbols: data.config?.symbols || [],
            timeframe: data.config?.timeframe || '5m',
            days: data.config?.days || 7,
            initialBalance: data.config?.initialBalance || 100000,
          },
          metrics: {
            totalReturn: data.metrics?.totalReturn || 0,
            winRate: data.metrics?.winRate || 0,
            profitFactor: data.metrics?.profitFactor || 0,
            maxDrawdown: data.metrics?.maxDrawdown || 0,
            totalTrades: data.metrics?.totalTrades || 0,
            sharpeRatio: data.metrics?.sharpeRatio || 0,
          },
          duration: data.duration || 0,
          status: 'completed',
        })
      } catch (err) {
        console.error(`Error parsing backtest file ${file}:`, err)
      }
    }
    
    // Sort by date, newest first
    backtests.sort((a, b) => b.date.localeCompare(a.date))
    
    return NextResponse.json({
      success: true,
      backtests,
      total: backtests.length,
    })
    
  } catch (error: any) {
    console.error('Error listing backtests:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to list backtests' },
      { status: 500 }
    )
  }
}

/**
 * DELETE /api/backtest/history?id=xxx - Delete specific backtest
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
  
  try {
    const files = await fs.readdir(BACKTESTS_DIR)
    const matchingFile = files.find(f => f.includes(backtestId))
    
    if (!matchingFile) {
      return NextResponse.json(
        { error: 'Backtest not found' },
        { status: 404 }
      )
    }
    
    const filePath = path.join(BACKTESTS_DIR, matchingFile)
    await fs.unlink(filePath)
    
    return NextResponse.json({
      success: true,
      message: `Backtest ${backtestId} deleted`,
    })
    
  } catch (error: any) {
    console.error('Error deleting backtest:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to delete backtest' },
      { status: 500 }
    )
  }
}

