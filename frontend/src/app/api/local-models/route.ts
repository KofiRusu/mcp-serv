import { NextResponse } from 'next/server'

/**
 * Local Models API
 * 
 * Returns list of installed Ollama models for model selection.
 */

const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434'

interface OllamaModel {
  name: string
  size: number
  digest: string
  modified_at: string
}

interface OllamaTagsResponse {
  models: OllamaModel[]
}

export async function GET() {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000)

    const response = await fetch(`${OLLAMA_URL}/api/tags`, {
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      return NextResponse.json({
        models: [],
        error: 'Ollama not responding',
        ollama_available: false,
      })
    }

    const data: OllamaTagsResponse = await response.json()

    // Format models for frontend
    const models = data.models.map((m) => ({
      name: m.name,
      size: formatSize(m.size),
      modified: m.modified_at,
    }))

    return NextResponse.json({
      models,
      ollama_available: true,
    })
  } catch (error: any) {
    // Ollama not running or network error
    return NextResponse.json({
      models: [],
      error: error.name === 'AbortError' ? 'Ollama timeout' : 'Ollama unavailable',
      ollama_available: false,
    })
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(0)}MB`
  }
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)}GB`
}

