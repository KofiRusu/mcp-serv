/**
 * Conversations API
 * 
 * GET /api/conversations - List trading assistant conversations
 */

import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

const CONVERSATIONS_DIR = path.join(process.cwd(), 'data', 'trading-conversations')

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const date = searchParams.get('date') || new Date().toISOString().slice(0, 10)
    const limit = parseInt(searchParams.get('limit') || '50')
    
    // Ensure directory exists
    await fs.mkdir(CONVERSATIONS_DIR, { recursive: true })
    
    const filePath = path.join(CONVERSATIONS_DIR, `${date}.jsonl`)
    
    let conversations: any[] = []
    
    try {
      const content = await fs.readFile(filePath, 'utf-8')
      const lines = content.trim().split('\n').filter(Boolean)
      
      for (const line of lines) {
        try {
          conversations.push(JSON.parse(line))
        } catch {
          // Skip malformed lines
        }
      }
    } catch (error: any) {
      if (error.code !== 'ENOENT') {
        throw error
      }
      // File doesn't exist
    }
    
    // Sort by timestamp descending
    conversations.sort((a, b) => 
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    )
    
    // Limit results
    conversations = conversations.slice(0, limit)
    
    return NextResponse.json({
      success: true,
      date,
      conversations,
      total: conversations.length,
    })
    
  } catch (error: any) {
    console.error('Error listing conversations:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to list conversations' },
      { status: 500 }
    )
  }
}

