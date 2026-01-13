/**
 * Market Data Summary API
 * 
 * GET /api/market-data/summary - Get summary of recorded market data
 */

import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

const MARKET_DATA_DIR = path.join(process.cwd(), 'data', 'market-history')

interface MarketDataSummary {
  symbol: string
  date: string
  types: string[]
  size: number
}

export async function GET(request: NextRequest) {
  try {
    // Ensure directory exists
    await fs.mkdir(MARKET_DATA_DIR, { recursive: true })
    
    const summary: MarketDataSummary[] = []
    
    // List date directories
    const dateDirs = await fs.readdir(MARKET_DATA_DIR)
    
    for (const dateDir of dateDirs) {
      const datePath = path.join(MARKET_DATA_DIR, dateDir)
      const stats = await fs.stat(datePath)
      
      if (!stats.isDirectory()) continue
      
      // List symbol directories
      const symbolDirs = await fs.readdir(datePath)
      
      for (const symbolDir of symbolDirs) {
        const symbolPath = path.join(datePath, symbolDir)
        const symbolStats = await fs.stat(symbolPath)
        
        if (!symbolStats.isDirectory()) continue
        
        // List data files
        const dataFiles = await fs.readdir(symbolPath)
        const jsonFiles = dataFiles.filter(f => f.endsWith('.json'))
        
        // Calculate total size
        let totalSize = 0
        const types: string[] = []
        
        for (const file of jsonFiles) {
          const filePath = path.join(symbolPath, file)
          const fileStats = await fs.stat(filePath)
          totalSize += fileStats.size
          types.push(file.replace('.json', ''))
        }
        
        if (types.length > 0) {
          summary.push({
            symbol: symbolDir,
            date: dateDir,
            types,
            size: totalSize,
          })
        }
      }
    }
    
    // Sort by date descending, then symbol
    summary.sort((a, b) => {
      const dateCompare = b.date.localeCompare(a.date)
      if (dateCompare !== 0) return dateCompare
      return a.symbol.localeCompare(b.symbol)
    })
    
    return NextResponse.json({
      success: true,
      summary,
      total: summary.length,
    })
    
  } catch (error: any) {
    console.error('Error getting market data summary:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to get summary' },
      { status: 500 }
    )
  }
}

