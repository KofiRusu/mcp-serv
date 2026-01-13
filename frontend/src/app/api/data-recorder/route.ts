import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

// =============================================================================
// Market Data Recorder API
// Stores market data snapshots to JSON files for PersRM training/analysis
// =============================================================================

const DATA_DIR = path.join(process.cwd(), 'data', 'market-history')

// Ensure directory exists
async function ensureDir(dirPath: string) {
  try {
    await fs.access(dirPath)
  } catch {
    await fs.mkdir(dirPath, { recursive: true })
  }
}

// Get today's date string
function getDateString() {
  return new Date().toISOString().split('T')[0]
}

// Get file path for a specific data type
function getFilePath(symbol: string, dataType: string) {
  const dateStr = getDateString()
  return path.join(DATA_DIR, dateStr, symbol, `${dataType}.json`)
}

// Append data to a JSON file (array format)
async function appendToFile(filePath: string, data: any) {
  await ensureDir(path.dirname(filePath))
  
  let existing: any[] = []
  try {
    const content = await fs.readFile(filePath, 'utf-8')
    existing = JSON.parse(content)
  } catch {
    // File doesn't exist yet, start with empty array
  }
  
  existing.push(data)
  await fs.writeFile(filePath, JSON.stringify(existing, null, 2))
  
  return existing.length
}

// POST: Record market data snapshot
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { symbol, dataType, data } = body
    
    if (!symbol || !dataType || !data) {
      return NextResponse.json(
        { error: 'Missing required fields: symbol, dataType, data' },
        { status: 400 }
      )
    }
    
    // Add timestamp to the data
    const record = {
      timestamp: Date.now(),
      recordedAt: new Date().toISOString(),
      ...data,
    }
    
    const filePath = getFilePath(symbol, dataType)
    const count = await appendToFile(filePath, record)
    
    return NextResponse.json({
      success: true,
      symbol,
      dataType,
      recordCount: count,
      filePath: filePath.replace(process.cwd(), ''),
    })
  } catch (error: any) {
    console.error('Data recorder error:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to record data' },
      { status: 500 }
    )
  }
}

// GET: Retrieve recorded data or stats
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const action = searchParams.get('action') || 'stats'
  const symbol = searchParams.get('symbol')
  const dataType = searchParams.get('dataType')
  const date = searchParams.get('date') || getDateString()
  
  try {
    switch (action) {
      case 'stats': {
        // Get recording statistics
        const statsPath = path.join(DATA_DIR, date)
        let stats: any = { date, symbols: {} }
        
        try {
          const symbols = await fs.readdir(statsPath)
          for (const sym of symbols) {
            const symPath = path.join(statsPath, sym)
            const stat = await fs.stat(symPath)
            if (stat.isDirectory()) {
              const files = await fs.readdir(symPath)
              stats.symbols[sym] = {}
              
              for (const file of files) {
                const filePath = path.join(symPath, file)
                const content = await fs.readFile(filePath, 'utf-8')
                const records = JSON.parse(content)
                const dataTypeName = file.replace('.json', '')
                stats.symbols[sym][dataTypeName] = {
                  count: records.length,
                  firstRecord: records[0]?.recordedAt,
                  lastRecord: records[records.length - 1]?.recordedAt,
                }
              }
            }
          }
        } catch {
          // No data for this date
        }
        
        return NextResponse.json(stats)
      }
      
      case 'data': {
        // Get specific data
        if (!symbol || !dataType) {
          return NextResponse.json(
            { error: 'Missing symbol or dataType parameter' },
            { status: 400 }
          )
        }
        
        const filePath = path.join(DATA_DIR, date, symbol, `${dataType}.json`)
        
        try {
          const content = await fs.readFile(filePath, 'utf-8')
          const records = JSON.parse(content)
          
          // Optional: limit results
          const limit = parseInt(searchParams.get('limit') || '100')
          const offset = parseInt(searchParams.get('offset') || '0')
          
          return NextResponse.json({
            symbol,
            dataType,
            date,
            total: records.length,
            records: records.slice(offset, offset + limit),
          })
        } catch {
          return NextResponse.json({
            symbol,
            dataType,
            date,
            total: 0,
            records: [],
          })
        }
      }
      
      case 'dates': {
        // List available dates
        try {
          const dates = await fs.readdir(DATA_DIR)
          return NextResponse.json({
            dates: dates.filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d)).sort().reverse(),
          })
        } catch {
          return NextResponse.json({ dates: [] })
        }
      }
      
      default:
        return NextResponse.json(
          { error: 'Invalid action. Use: stats, data, dates' },
          { status: 400 }
        )
    }
  } catch (error: any) {
    console.error('Data recorder GET error:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to retrieve data' },
      { status: 500 }
    )
  }
}

// DELETE: Clear recorded data (optional)
export async function DELETE(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const date = searchParams.get('date')
  const symbol = searchParams.get('symbol')
  
  if (!date) {
    return NextResponse.json(
      { error: 'Date parameter required' },
      { status: 400 }
    )
  }
  
  try {
    const targetPath = symbol 
      ? path.join(DATA_DIR, date, symbol)
      : path.join(DATA_DIR, date)
    
    await fs.rm(targetPath, { recursive: true, force: true })
    
    return NextResponse.json({
      success: true,
      deleted: targetPath.replace(process.cwd(), ''),
    })
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Failed to delete data' },
      { status: 500 }
    )
  }
}

