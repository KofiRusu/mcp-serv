/**
 * Interactions Log API
 * 
 * POST /api/interactions/log - Store interaction logs
 * GET /api/interactions/log - Retrieve interaction logs
 */

import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

const INTERACTIONS_DIR = path.join(process.cwd(), 'data', 'interactions')

interface InteractionLog {
  id: string
  type: string
  timestamp: string
  sessionId: string
  data: Record<string, any>
  metadata?: Record<string, any>
}

/**
 * POST /api/interactions/log - Store interaction logs
 */
export async function POST(request: NextRequest) {
  try {
    const { logs } = await request.json()
    
    if (!logs || !Array.isArray(logs)) {
      return NextResponse.json(
        { error: 'Invalid logs format' },
        { status: 400 }
      )
    }
    
    // Ensure directory exists
    await fs.mkdir(INTERACTIONS_DIR, { recursive: true })
    
    // Group logs by date and type
    const today = new Date().toISOString().slice(0, 10)
    
    // Write to daily file
    const filePath = path.join(INTERACTIONS_DIR, `${today}.jsonl`)
    
    // Append each log as a JSONL line
    const logLines = logs.map((log: InteractionLog) => 
      JSON.stringify({
        ...log,
        receivedAt: new Date().toISOString(),
      })
    ).join('\n') + '\n'
    
    await fs.appendFile(filePath, logLines)
    
    return NextResponse.json({
      success: true,
      count: logs.length,
    })
    
  } catch (error: any) {
    console.error('Error storing interaction logs:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to store logs' },
      { status: 500 }
    )
  }
}

/**
 * GET /api/interactions/log - Retrieve interaction logs
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const date = searchParams.get('date') || new Date().toISOString().slice(0, 10)
    const type = searchParams.get('type')
    const sessionId = searchParams.get('sessionId')
    const limit = parseInt(searchParams.get('limit') || '100')
    
    // Ensure directory exists
    await fs.mkdir(INTERACTIONS_DIR, { recursive: true })
    
    const filePath = path.join(INTERACTIONS_DIR, `${date}.jsonl`)
    
    let logs: InteractionLog[] = []
    
    try {
      const content = await fs.readFile(filePath, 'utf-8')
      const lines = content.trim().split('\n').filter(Boolean)
      
      for (const line of lines) {
        try {
          const log = JSON.parse(line)
          
          // Apply filters
          if (type && log.type !== type) continue
          if (sessionId && log.sessionId !== sessionId) continue
          
          logs.push(log)
        } catch {
          // Skip malformed lines
        }
      }
    } catch (error: any) {
      if (error.code !== 'ENOENT') {
        throw error
      }
      // File doesn't exist, return empty array
    }
    
    // Sort by timestamp descending and limit
    logs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    logs = logs.slice(0, limit)
    
    return NextResponse.json({
      success: true,
      date,
      logs,
      total: logs.length,
    })
    
  } catch (error: any) {
    console.error('Error retrieving interaction logs:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to retrieve logs' },
      { status: 500 }
    )
  }
}

/**
 * Get summary of interaction logs
 */
export async function getSummary() {
  try {
    await fs.mkdir(INTERACTIONS_DIR, { recursive: true })
    
    const files = await fs.readdir(INTERACTIONS_DIR)
    const jsonlFiles = files.filter(f => f.endsWith('.jsonl'))
    
    const summary = {
      totalDays: jsonlFiles.length,
      dates: jsonlFiles.map(f => f.replace('.jsonl', '')).sort().reverse(),
    }
    
    return summary
  } catch {
    return { totalDays: 0, dates: [] }
  }
}

