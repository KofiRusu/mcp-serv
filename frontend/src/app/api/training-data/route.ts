import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

const DATA_DIR = path.join(process.cwd(), 'data', 'training')
const EXAMPLES_FILE = 'persrm_training_examples.jsonl'
const STATS_FILE = 'training_stats.json'

// Ensure data directory exists
async function ensureDataDir() {
  try {
    await fs.mkdir(DATA_DIR, { recursive: true })
  } catch (error) {
    // Directory already exists
  }
}

export async function POST(request: NextRequest) {
  try {
    const { examples } = await request.json()

    if (!examples || !Array.isArray(examples)) {
      return NextResponse.json(
        { error: 'Missing or invalid examples array' },
        { status: 400 }
      )
    }

    await ensureDataDir()

    // Append examples to JSONL file
    const filePath = path.join(DATA_DIR, EXAMPLES_FILE)
    const lines = examples.map((ex: any) => JSON.stringify(ex)).join('\n') + '\n'
    
    await fs.appendFile(filePath, lines, 'utf-8')

    // Update stats
    await updateStats(examples.length)

    return NextResponse.json({
      success: true,
      saved: examples.length,
      message: `Saved ${examples.length} training examples`,
    })
  } catch (error: any) {
    console.error('Training data save error:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to save training data' },
      { status: 500 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const action = searchParams.get('action') || 'stats'

    await ensureDataDir()

    switch (action) {
      case 'stats':
        return NextResponse.json(await getStats())

      case 'export':
        return await exportTrainingData(searchParams)

      case 'list':
        return await listExamples(searchParams)

      default:
        return NextResponse.json({ error: 'Invalid action' }, { status: 400 })
    }
  } catch (error: any) {
    console.error('Training data fetch error:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to fetch training data' },
      { status: 500 }
    )
  }
}

async function getStats() {
  const statsPath = path.join(DATA_DIR, STATS_FILE)
  const examplesPath = path.join(DATA_DIR, EXAMPLES_FILE)

  let stats = {
    totalExamples: 0,
    lastUpdated: null as string | null,
    byType: {} as Record<string, number>,
    bySource: {} as Record<string, number>,
    qualityStats: {
      profitable: 0,
      highQuality: 0,
    },
  }

  try {
    const storedStats = await fs.readFile(statsPath, 'utf-8')
    stats = JSON.parse(storedStats)
  } catch {
    // Stats file doesn't exist, calculate from examples
    try {
      const content = await fs.readFile(examplesPath, 'utf-8')
      const lines = content.trim().split('\n').filter(l => l)
      
      stats.totalExamples = lines.length
      
      lines.forEach(line => {
        try {
          const example = JSON.parse(line)
          stats.byType[example.type] = (stats.byType[example.type] || 0) + 1
          stats.bySource[example.source] = (stats.bySource[example.source] || 0) + 1
          if (example.quality?.profitable) stats.qualityStats.profitable++
          if ((example.quality?.timingScore || 0) >= 70) stats.qualityStats.highQuality++
        } catch {}
      })
      
      stats.lastUpdated = new Date().toISOString()
    } catch {
      // Examples file doesn't exist
    }
  }

  // Check file size
  let fileSizeBytes = 0
  let fileSizeMB = '0'
  try {
    const fileStat = await fs.stat(path.join(DATA_DIR, EXAMPLES_FILE))
    fileSizeBytes = fileStat.size
    fileSizeMB = (fileStat.size / 1024 / 1024).toFixed(2)
  } catch {}

  return { ...stats, fileSizeBytes, fileSizeMB }
}

async function updateStats(newExamplesCount: number) {
  const statsPath = path.join(DATA_DIR, STATS_FILE)
  
  let stats = await getStats()
  stats.totalExamples += newExamplesCount
  stats.lastUpdated = new Date().toISOString()
  
  await fs.writeFile(statsPath, JSON.stringify(stats, null, 2), 'utf-8')
}

async function exportTrainingData(params: URLSearchParams) {
  const format = params.get('format') || 'jsonl'
  const minQuality = parseInt(params.get('minQuality') || '0')
  const profitableOnly = params.get('profitableOnly') === 'true'
  
  const examplesPath = path.join(DATA_DIR, EXAMPLES_FILE)
  
  try {
    const content = await fs.readFile(examplesPath, 'utf-8')
    const lines = content.trim().split('\n').filter(l => l)
    
    let examples = lines.map(line => {
      try {
        return JSON.parse(line)
      } catch {
        return null
      }
    }).filter(Boolean)
    
    // Apply filters
    if (minQuality > 0) {
      examples = examples.filter(e => (e.quality?.timingScore || 0) >= minQuality)
    }
    
    if (profitableOnly) {
      examples = examples.filter(e => e.quality?.profitable)
    }
    
    if (format === 'jsonl') {
      // Return as JSONL for direct training use
      const trainingLines = examples.map(example => {
        const systemPrompt = `You are PersRM, an expert crypto trading AI. Analyze markets and provide trading decisions with structured reasoning.`
        
        let userContent = example.userPrompt || 
          `Analyze ${example.marketContext?.symbol || 'market'} at $${example.marketContext?.price || 0}`
        
        let assistantContent = ''
        if (example.decision) {
          assistantContent = `<think>\n${example.decision.reasoning || 'Analyzing market conditions...'}\n</think>\n\n<action>\n${JSON.stringify(example.decision, null, 2)}\n</action>`
        } else if (example.response) {
          assistantContent = example.response
        }
        
        return JSON.stringify({
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userContent },
            { role: 'assistant', content: assistantContent },
          ],
        })
      }).join('\n')
      
      return new NextResponse(trainingLines, {
        headers: {
          'Content-Type': 'application/jsonl',
          'Content-Disposition': `attachment; filename="persrm_training_${Date.now()}.jsonl"`,
        },
      })
    }
    
    // Return as JSON
    return NextResponse.json({
      examples,
      count: examples.length,
      exportedAt: new Date().toISOString(),
    })
  } catch (error) {
    return NextResponse.json({
      examples: [],
      count: 0,
      error: 'No training data available',
    })
  }
}

async function listExamples(params: URLSearchParams) {
  const limit = parseInt(params.get('limit') || '50')
  const offset = parseInt(params.get('offset') || '0')
  const type = params.get('type')
  
  const examplesPath = path.join(DATA_DIR, EXAMPLES_FILE)
  
  try {
    const content = await fs.readFile(examplesPath, 'utf-8')
    let lines = content.trim().split('\n').filter(l => l)
    
    // Parse and filter
    let examples = lines.map((line, index) => {
      try {
        const parsed = JSON.parse(line)
        parsed._index = index
        return parsed
      } catch {
        return null
      }
    }).filter(Boolean)
    
    if (type) {
      examples = examples.filter(e => e.type === type)
    }
    
    // Sort by timestamp descending (newest first)
    examples.sort((a, b) => 
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    )
    
    // Paginate
    const paginated = examples.slice(offset, offset + limit)
    
    return NextResponse.json({
      examples: paginated,
      total: examples.length,
      limit,
      offset,
      hasMore: offset + limit < examples.length,
    })
  } catch {
    return NextResponse.json({
      examples: [],
      total: 0,
      limit,
      offset,
      hasMore: false,
    })
  }
}

// DELETE endpoint to clear training data
export async function DELETE(request: NextRequest) {
  try {
    const examplesPath = path.join(DATA_DIR, EXAMPLES_FILE)
    const statsPath = path.join(DATA_DIR, STATS_FILE)
    
    // Create backup before deleting
    const backupPath = path.join(DATA_DIR, `backup_${Date.now()}.jsonl`)
    try {
      await fs.copyFile(examplesPath, backupPath)
    } catch {}
    
    // Clear files
    await fs.writeFile(examplesPath, '', 'utf-8')
    await fs.unlink(statsPath).catch(() => {})
    
    return NextResponse.json({
      success: true,
      message: 'Training data cleared',
      backupCreated: backupPath,
    })
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Failed to clear training data' },
      { status: 500 }
    )
  }
}

