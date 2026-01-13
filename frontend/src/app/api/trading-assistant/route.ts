import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

/**
 * Trading Assistant API
 * 
 * Connects to PersRM or Mistral via Ollama for natural trading conversations.
 * Falls back to local responses quickly if Ollama is unavailable.
 * Records all interactions for PersRM training data.
 */

const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434'

// Model priority - try fine-tuned PersRM trading model first, then fall back to general models
// To add your own fine-tuned model, add it to the top of this list
const MODELS = [
  'persrm-trading',         // Fine-tuned PersRM trading model (created via persrm_trading_cycle.sh)
  'ft-qwen25-v1-quality',   // Fine-tuned PersRM model (older)
  'mistral:7b',             // Mistral as fallback
  'qwen2.5:7b',             // Qwen as second fallback
  'llama3.2:3b',            // Lightweight fallback
]

// Quick timeout - fail fast if Ollama isn't responding
const OLLAMA_TIMEOUT = 5000 // 5 seconds

interface ConversationMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

interface TradingContext {
  currentSymbol: string
  positions: any[]
  balance: number
  mode: 'paper' | 'live' | 'view'
}

// Trading-focused system prompt with structured output for trade decisions
// When trained with persrm_trading_cycle.sh, the model learns to output <think>/<action> blocks
const TRADING_SYSTEM_PROMPT = `You are PersRM, a friendly and experienced crypto trading assistant.

PERSONALITY:
- Conversational and natural - talk like a knowledgeable friend
- Concise but helpful - get to the point but explain when needed
- Risk-aware - always consider downside protection
- Data-driven - reference actual numbers and levels

STRICT RULES (NEVER VIOLATE):
- Maximum risk per trade: 2% of account
- Every trade suggestion MUST include a stop-loss
- Minimum risk/reward ratio: 1.5:1
- If uncertain, recommend HOLD - never force a trade

WHEN SUGGESTING A TRADE, use this structured format:
<think>
Your analysis and reasoning (2-4 sentences covering technicals, sentiment, risk)
</think>

<action>
{
  "signal": "LONG" | "SHORT" | "HOLD",
  "symbol": "BTCUSDT",
  "entry": 95000,
  "stop_loss": 93100,
  "take_profit": 100700,
  "risk_percent": 1.5,
  "risk_reward": 3.0,
  "confidence": 0.75,
  "reasoning": "Brief one-line summary"
}
</action>

FOR GENERAL QUESTIONS (analysis, portfolio review, etc.):
- Just respond naturally without the <think>/<action> blocks
- Be helpful and conversational

Remember: You're helping a trader make decisions, not trading for them. Protect capital above all else.`

// Check if Ollama is available (cached for 30 seconds)
let ollamaAvailable: boolean | null = null
let lastOllamaCheck = 0
const OLLAMA_CHECK_INTERVAL = 30000 // 30 seconds

async function checkOllamaAvailable(): Promise<boolean> {
  const now = Date.now()
  if (ollamaAvailable !== null && now - lastOllamaCheck < OLLAMA_CHECK_INTERVAL) {
    return ollamaAvailable
  }

  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 2000)
    
    const response = await fetch(`${OLLAMA_URL}/api/tags`, {
      signal: controller.signal,
    })
    
    clearTimeout(timeoutId)
    ollamaAvailable = response.ok
    lastOllamaCheck = now
    return ollamaAvailable
  } catch {
    ollamaAvailable = false
    lastOllamaCheck = now
    return false
  }
}

async function tryGenerateWithModel(
  model: string,
  messages: Array<{ role: string; content: string }>
): Promise<{ success: boolean; response?: string; model?: string; error?: string }> {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), OLLAMA_TIMEOUT)

    const response = await fetch(`${OLLAMA_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model,
        messages,
        stream: false,
        options: {
          temperature: 0.7,
          num_predict: 512, // Shorter responses for faster generation
          top_p: 0.9,
        },
      }),
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      return { success: false, error: `Model ${model} not available` }
    }

    const data = await response.json()
    return {
      success: true,
      response: data.message?.content || '',
      model,
    }
  } catch (err: any) {
    return { success: false, error: `Model ${model} failed` }
  }
}

// Enhanced local response generator
function generateLocalResponse(
  userMessage: string,
  tradingContext: TradingContext
): string {
  const lowerMessage = userMessage.toLowerCase()
  const { currentSymbol, positions, balance, mode } = tradingContext

  // Market analysis
  if (lowerMessage.includes('analyz') || lowerMessage.includes('trend') || 
      lowerMessage.includes('market') || lowerMessage.includes('take') ||
      lowerMessage.includes('btc') || lowerMessage.includes('eth') ||
      lowerMessage.includes('what') && lowerMessage.includes('think')) {
    return `Looking at **${currentSymbol}** - here's what I'm seeing:\n\n` +
      `📊 The market's been choppy lately. Key levels to watch:\n` +
      `• Watch for support around recent lows\n` +
      `• Resistance at the previous swing highs\n\n` +
      `Volume's been decent. I'd wait for a clear break before jumping in. What timeframe are you trading?`
  }

  // Portfolio/positions
  if (lowerMessage.includes('portfolio') || lowerMessage.includes('position') || 
      lowerMessage.includes('looking') || lowerMessage.includes('how am i')) {
    if (positions.length === 0) {
      return `You're flat right now - no open positions.\n\n` +
        `Account balance: **$${balance.toLocaleString()}**\n\n` +
        `Looking for opportunities? I can help with trade ideas.`
    }
    
    const totalPnl = positions.reduce((sum: number, p: any) => sum + (p.pnl || 0), 0)
    const positionList = positions.map((p: any) => 
      `• **${p.symbol}** ${p.side?.toUpperCase()} - ${(p.pnl || 0) >= 0 ? '🟢' : '🔴'} ${(p.pnl || 0) >= 0 ? '+' : ''}$${(p.pnl || 0).toFixed(2)}`
    ).join('\n')
    
    return `Here's your rundown:\n\n${positionList}\n\n` +
      `**Total P&L:** ${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}\n` +
      `**Account:** $${balance.toLocaleString()}`
  }

  // Risk check
  if (lowerMessage.includes('risk') || lowerMessage.includes('overexposed') || 
      lowerMessage.includes('exposure')) {
    const posCount = positions.length
    const withSL = positions.filter((p: any) => p.stopLoss).length
    
    if (posCount === 0) {
      return `No positions open, so no risk exposure right now! ✅\n\n` +
        `Account balance: **$${balance.toLocaleString()}**`
    }

    const riskEstimate = (posCount * 2) // Rough estimate
    return `Risk check:\n\n` +
      `• Open positions: **${posCount}**\n` +
      `• With stop losses: **${withSL}/${posCount}**\n` +
      `• Estimated risk: ~${riskEstimate}% of account\n\n` +
      `${withSL < posCount ? "⚠️ Consider adding stops to unprotected positions." : "✅ Looking good - all positions have stops."}`
  }

  // Trade ideas/setups
  if (lowerMessage.includes('setup') || lowerMessage.includes('trade idea') || 
      lowerMessage.includes('entry') || lowerMessage.includes('opportunity')) {
    return `Looking at **${currentSymbol}** for setups:\n\n` +
      `📈 **Long Setup:**\n` +
      `• Wait for pullback to support\n` +
      `• Look for bullish reversal candle\n` +
      `• Stop below the swing low\n\n` +
      `📉 **Short Setup:**\n` +
      `• Wait for rally to resistance\n` +
      `• Look for rejection pattern\n` +
      `• Stop above the swing high\n\n` +
      `Risk 1-2% max per trade. What's your bias?`
  }

  // Greeting/help
  if (lowerMessage.includes('hello') || lowerMessage.includes('hi') || 
      lowerMessage.includes('hey') || lowerMessage.includes('help') ||
      lowerMessage.includes('what can you')) {
    return `Hey! I'm your trading assistant. I can help with:\n\n` +
      `📊 **Market Analysis** - "What's your take on BTC?"\n` +
      `💼 **Portfolio Review** - "How are my positions?"\n` +
      `⚠️ **Risk Check** - "Am I overexposed?"\n` +
      `📈 **Trade Ideas** - "Any good setups?"\n\n` +
      `Currently watching **${currentSymbol}** in ${mode} mode. What's on your mind?`
  }

  // Thanks
  if (lowerMessage.includes('thank') || lowerMessage.includes('appreciate')) {
    return `You got it! 👍 Let me know if you need anything else.`
  }

  // Default
  return `I can help with market analysis, trade ideas, or review your positions.\n\n` +
    `Try asking:\n` +
    `• "What's your take on ${currentSymbol}?"\n` +
    `• "How are my positions looking?"\n` +
    `• "Got any trade setups?"`
}

async function generateResponse(
  userMessage: string,
  conversationHistory: ConversationMessage[],
  tradingContext: TradingContext,
  modelOverride?: string
): Promise<{ response: string; model: string }> {
  // Check if Ollama is available first
  const ollamaUp = await checkOllamaAvailable()
  
  if (!ollamaUp) {
    // Use local response immediately
    return {
      response: generateLocalResponse(userMessage, tradingContext),
      model: 'local',
    }
  }

  // Build context-aware system prompt
  const contextPrompt = `${TRADING_SYSTEM_PROMPT}

Current trading context:
- Symbol: ${tradingContext.currentSymbol}
- Mode: ${tradingContext.mode} trading
- Account Balance: $${tradingContext.balance.toLocaleString()}
- Open Positions: ${tradingContext.positions.length}
${tradingContext.positions.map(p => 
  `  • ${p.symbol}: ${p.side} ${p.size} @ $${p.entryPrice} (${p.pnl >= 0 ? '+' : ''}$${p.pnl?.toFixed(2) || '0.00'})`
).join('\n')}`

  // Build messages array with history
  const messages: Array<{ role: string; content: string }> = [
    { role: 'system', content: contextPrompt },
    ...conversationHistory.slice(-6).map(m => ({
      role: m.role,
      content: m.content,
    })),
    { role: 'user', content: userMessage },
  ]

  // If model override specified, try that model first
  if (modelOverride) {
    const result = await tryGenerateWithModel(modelOverride, messages)
    if (result.success && result.response) {
      return { response: result.response, model: result.model! }
    }
    // If override model fails, continue with priority chain
  }

  // Try models in priority order
  for (const model of MODELS) {
    const result = await tryGenerateWithModel(model, messages)
    if (result.success && result.response) {
      return { response: result.response, model: result.model! }
    }
  }

  // Fallback to local response
  return {
    response: generateLocalResponse(userMessage, tradingContext),
    model: 'local',
  }
}

async function recordConversation(
  sessionId: string,
  userMessage: string,
  assistantResponse: string,
  tradingContext: TradingContext,
  model: string
): Promise<void> {
  try {
    const dataDir = path.join(process.cwd(), 'data', 'trading-conversations')
    await fs.mkdir(dataDir, { recursive: true })

    const date = new Date().toISOString().slice(0, 10)
    const filePath = path.join(dataDir, `${date}.jsonl`)

    const record = {
      timestamp: new Date().toISOString(),
      sessionId,
      model,
      context: {
        symbol: tradingContext.currentSymbol,
        mode: tradingContext.mode,
        positionCount: tradingContext.positions.length,
        balance: tradingContext.balance,
      },
      conversation: {
        user: userMessage,
        assistant: assistantResponse,
      },
      // For PersRM training - format as instruction/response pair
      training_format: {
        instruction: userMessage,
        input: JSON.stringify({
          symbol: tradingContext.currentSymbol,
          positions: tradingContext.positions.map(p => ({
            symbol: p.symbol,
            side: p.side,
            pnl: p.pnl,
          })),
        }),
        output: assistantResponse,
      },
    }

    await fs.appendFile(filePath, JSON.stringify(record) + '\n')
  } catch (err) {
    console.error('Failed to record conversation:', err)
  }
}

export async function POST(request: NextRequest) {
  try {
    // Check for model override header
    const modelOverride = request.headers.get('x-llm-model')
    
    const body = await request.json()
    const {
      message,
      conversationHistory = [],
      tradingContext,
      sessionId = `session-${Date.now()}`,
    } = body

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      )
    }

    // Default trading context
    const context: TradingContext = tradingContext || {
      currentSymbol: 'BTCUSDT',
      positions: [],
      balance: 100000,
      mode: 'paper',
    }

    // Generate response (with optional model override)
    const { response, model } = await generateResponse(
      message,
      conversationHistory,
      context,
      modelOverride || undefined
    )

    // Record for training (async, don't wait)
    recordConversation(sessionId, message, response, context, model).catch(() => {})

    return NextResponse.json({
      response,
      model,
      sessionId,
      timestamp: new Date().toISOString(),
    })
  } catch (error: any) {
    console.error('Trading assistant error:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to generate response' },
      { status: 500 }
    )
  }
}

// Health check / model availability
export async function GET() {
  const ollamaUp = await checkOllamaAvailable()
  
  return NextResponse.json({
    status: 'ok',
    ollama_url: OLLAMA_URL,
    ollama_available: ollamaUp,
    fallback_mode: !ollamaUp,
  })
}
