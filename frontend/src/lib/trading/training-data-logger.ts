/**
 * Training Data Logger for PersRM
 * 
 * Captures all trading interactions, decisions, and outcomes
 * to create high-quality training examples for the AI model.
 */

// Types for training data
export interface MarketContext {
  symbol: string
  price: number
  change24h: number
  volume24h: number
  rsi?: number
  macd?: { line: number; signal: number; histogram: number }
  ema20?: number
  ema50?: number
  support?: number
  resistance?: number
  sentiment?: {
    fearGreed: number
    socialVolume: number
    fundingRate: number
  }
  timestamp: string
}

export interface TradeDecision {
  action: 'LONG' | 'SHORT' | 'HOLD' | 'CLOSE'
  symbol: string
  entryPrice?: number
  stopLoss?: number
  takeProfit?: number[]
  riskPercent?: number
  confidence: number
  reasoning: string
}

export interface TradeOutcome {
  entryPrice: number
  exitPrice: number
  pnl: number
  pnlPercent: number
  duration: number // in minutes
  exitReason: 'take_profit' | 'stop_loss' | 'manual' | 'timeout'
  maxDrawdown: number
  maxProfit: number
}

export interface TrainingExample {
  id: string
  type: 'trade_decision' | 'market_analysis' | 'risk_assessment' | 'conversation' | 'backtest_result'
  timestamp: string
  
  // Input context
  userPrompt?: string
  marketContext: MarketContext
  accountState?: {
    balance: number
    openPositions: number
    unrealizedPnl: number
  }
  
  // Model output
  decision?: TradeDecision
  response?: string
  
  // Outcome (filled in later)
  outcome?: TradeOutcome
  
  // Quality metrics
  quality?: {
    profitable: boolean
    riskRewardRatio: number
    followedRules: boolean
    timingScore: number // 0-100
  }
  
  // Metadata
  source: 'user' | 'auto_trading' | 'backtest' | 'paper_trading'
  modelUsed?: string
  sessionId: string
}

// Cookie/localStorage keys
const STORAGE_KEYS = {
  TRAINING_EXAMPLES: 'persrm_training_examples',
  SESSION_ID: 'persrm_session_id',
  PENDING_OUTCOMES: 'persrm_pending_outcomes',
}

// Maximum examples to keep in localStorage (to avoid quota issues)
const MAX_LOCAL_EXAMPLES = 500

class TrainingDataLogger {
  private sessionId: string
  private examples: TrainingExample[] = []
  private pendingOutcomes: Map<string, { positionId: string; example: TrainingExample }> = new Map()
  private initialized = false

  constructor() {
    this.sessionId = this.getOrCreateSessionId()
  }

  private getOrCreateSessionId(): string {
    if (typeof window === 'undefined') return `server-${Date.now()}`
    
    let sessionId = sessionStorage.getItem(STORAGE_KEYS.SESSION_ID)
    if (!sessionId) {
      sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      sessionStorage.setItem(STORAGE_KEYS.SESSION_ID, sessionId)
    }
    return sessionId
  }

  /**
   * Initialize and load existing data from storage
   */
  initialize() {
    if (this.initialized || typeof window === 'undefined') return
    
    try {
      // Load existing examples from localStorage
      const stored = localStorage.getItem(STORAGE_KEYS.TRAINING_EXAMPLES)
      if (stored) {
        this.examples = JSON.parse(stored)
      }
      
      // Load pending outcomes
      const pending = localStorage.getItem(STORAGE_KEYS.PENDING_OUTCOMES)
      if (pending) {
        const pendingArray = JSON.parse(pending)
        pendingArray.forEach((item: any) => {
          this.pendingOutcomes.set(item.positionId, item)
        })
      }
      
      this.initialized = true
      console.log(`TrainingDataLogger initialized with ${this.examples.length} examples`)
    } catch (error) {
      console.error('Failed to initialize TrainingDataLogger:', error)
    }
  }

  /**
   * Save examples to localStorage and optionally to backend
   */
  private async saveToStorage() {
    if (typeof window === 'undefined') return
    
    try {
      // Trim to max size
      if (this.examples.length > MAX_LOCAL_EXAMPLES) {
        this.examples = this.examples.slice(-MAX_LOCAL_EXAMPLES)
      }
      
      localStorage.setItem(STORAGE_KEYS.TRAINING_EXAMPLES, JSON.stringify(this.examples))
      
      // Save pending outcomes
      const pendingArray = Array.from(this.pendingOutcomes.entries()).map(([k, v]) => ({
        ...v,
        positionId: k,
      }))
      localStorage.setItem(STORAGE_KEYS.PENDING_OUTCOMES, JSON.stringify(pendingArray))
      
      // Also save to backend for permanent storage
      await this.syncToBackend()
    } catch (error) {
      console.error('Failed to save training data:', error)
    }
  }

  /**
   * Sync examples to backend for permanent storage
   */
  private async syncToBackend() {
    // Get examples that haven't been synced yet
    const unsynced = this.examples.filter(e => !(e as any)._synced)
    
    if (unsynced.length === 0) return
    
    try {
      const response = await fetch('/api/training-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ examples: unsynced }),
      })
      
      if (response.ok) {
        // Mark as synced
        unsynced.forEach(e => (e as any)._synced = true)
        console.log(`Synced ${unsynced.length} training examples to backend`)
      }
    } catch (error) {
      // Silent fail - will retry next time
    }
  }

  /**
   * Log a trade decision
   */
  logTradeDecision(
    decision: TradeDecision,
    marketContext: MarketContext,
    userPrompt?: string,
    accountState?: { balance: number; openPositions: number; unrealizedPnl: number },
    positionId?: string
  ): string {
    const example: TrainingExample = {
      id: `trade-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: 'trade_decision',
      timestamp: new Date().toISOString(),
      userPrompt,
      marketContext,
      accountState,
      decision,
      source: userPrompt ? 'user' : 'auto_trading',
      sessionId: this.sessionId,
    }
    
    this.examples.push(example)
    
    // Track for outcome matching
    if (positionId && decision.action !== 'HOLD') {
      this.pendingOutcomes.set(positionId, { positionId, example })
    }
    
    this.saveToStorage()
    return example.id
  }

  /**
   * Log a conversation with the trading assistant
   */
  logConversation(
    userPrompt: string,
    assistantResponse: string,
    marketContext: MarketContext,
    modelUsed?: string,
    decision?: TradeDecision
  ): string {
    const example: TrainingExample = {
      id: `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: 'conversation',
      timestamp: new Date().toISOString(),
      userPrompt,
      marketContext,
      response: assistantResponse,
      decision,
      source: 'user',
      modelUsed,
      sessionId: this.sessionId,
    }
    
    this.examples.push(example)
    this.saveToStorage()
    return example.id
  }

  /**
   * Log market analysis
   */
  logMarketAnalysis(
    analysis: string,
    marketContext: MarketContext,
    decision?: TradeDecision
  ): string {
    const example: TrainingExample = {
      id: `analysis-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: 'market_analysis',
      timestamp: new Date().toISOString(),
      marketContext,
      response: analysis,
      decision,
      source: 'auto_trading',
      sessionId: this.sessionId,
    }
    
    this.examples.push(example)
    this.saveToStorage()
    return example.id
  }

  /**
   * Log backtest result as training example
   */
  logBacktestResult(
    config: any,
    result: any,
    trades: any[]
  ): string {
    // Create training examples from profitable trades
    const profitableTrades = trades.filter(t => t.pnl > 0)
    
    profitableTrades.forEach(trade => {
      const example: TrainingExample = {
        id: `bt-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        type: 'backtest_result',
        timestamp: new Date().toISOString(),
        marketContext: {
          symbol: trade.symbol,
          price: trade.entryPrice,
          change24h: 0,
          volume24h: 0,
          timestamp: new Date(trade.entryTime).toISOString(),
        },
        decision: {
          action: trade.side === 'long' ? 'LONG' : 'SHORT',
          symbol: trade.symbol,
          entryPrice: trade.entryPrice,
          stopLoss: trade.stopLoss,
          takeProfit: trade.takeProfit ? [trade.takeProfit] : undefined,
          riskPercent: config.riskPerTrade * 100,
          confidence: 0.7,
          reasoning: `Backtest winning trade: ${trade.reason || 'Signal triggered'}`,
        },
        outcome: {
          entryPrice: trade.entryPrice,
          exitPrice: trade.exitPrice,
          pnl: trade.pnl,
          pnlPercent: trade.pnlPercent,
          duration: (trade.exitTime - trade.entryTime) / 60000,
          exitReason: trade.reason?.toLowerCase().includes('stop') ? 'stop_loss' : 'take_profit',
          maxDrawdown: 0,
          maxProfit: trade.pnl,
        },
        quality: {
          profitable: true,
          riskRewardRatio: Math.abs(trade.pnl / (trade.entryPrice * config.riskPerTrade)),
          followedRules: true,
          timingScore: trade.pnlPercent > 2 ? 90 : trade.pnlPercent > 0 ? 70 : 50,
        },
        source: 'backtest',
        sessionId: this.sessionId,
      }
      
      this.examples.push(example)
    })
    
    this.saveToStorage()
    return `Logged ${profitableTrades.length} winning trades from backtest`
  }

  /**
   * Record trade outcome and calculate quality metrics
   */
  recordOutcome(positionId: string, outcome: TradeOutcome) {
    const pending = this.pendingOutcomes.get(positionId)
    if (!pending) return
    
    const example = pending.example
    example.outcome = outcome
    
    // Calculate quality metrics
    const decision = example.decision!
    const riskAmount = decision.stopLoss 
      ? Math.abs(decision.entryPrice! - decision.stopLoss)
      : decision.entryPrice! * 0.02
    
    example.quality = {
      profitable: outcome.pnl > 0,
      riskRewardRatio: Math.abs(outcome.pnl) / riskAmount,
      followedRules: decision.stopLoss !== undefined && decision.riskPercent !== undefined && decision.riskPercent <= 2,
      timingScore: this.calculateTimingScore(outcome),
    }
    
    // Remove from pending
    this.pendingOutcomes.delete(positionId)
    
    this.saveToStorage()
  }

  private calculateTimingScore(outcome: TradeOutcome): number {
    // Score based on how well the entry/exit timing was
    let score = 50
    
    // Good: Exited at profit
    if (outcome.pnl > 0) score += 20
    
    // Good: High max profit captured
    if (outcome.maxProfit > 0 && outcome.pnl > outcome.maxProfit * 0.5) score += 15
    
    // Good: Low drawdown
    if (outcome.maxDrawdown < Math.abs(outcome.pnl) * 0.5) score += 15
    
    // Penalty for hitting stop loss
    if (outcome.exitReason === 'stop_loss') score -= 10
    
    return Math.max(0, Math.min(100, score))
  }

  /**
   * Get all examples for export/training
   */
  getExamples(filter?: {
    type?: TrainingExample['type']
    source?: TrainingExample['source']
    profitableOnly?: boolean
    minQuality?: number
  }): TrainingExample[] {
    let filtered = [...this.examples]
    
    if (filter?.type) {
      filtered = filtered.filter(e => e.type === filter.type)
    }
    
    if (filter?.source) {
      filtered = filtered.filter(e => e.source === filter.source)
    }
    
    if (filter?.profitableOnly) {
      filtered = filtered.filter(e => e.quality?.profitable)
    }
    
    if (filter?.minQuality !== undefined) {
      const minQ = filter.minQuality
      filtered = filtered.filter(e => (e.quality?.timingScore || 0) >= minQ)
    }
    
    return filtered
  }

  /**
   * Export examples in JSONL format for training
   */
  exportForTraining(): string {
    const qualityExamples = this.getExamples({ profitableOnly: true, minQuality: 60 })
    
    const trainingLines = qualityExamples.map(example => {
      // Format as instruction-following format
      const systemPrompt = `You are PersRM, an expert crypto trading AI. Analyze the market and provide trading decisions with reasoning.`
      
      let userContent = ''
      if (example.userPrompt) {
        userContent = example.userPrompt
      } else {
        userContent = `Analyze ${example.marketContext.symbol} at $${example.marketContext.price}. RSI: ${example.marketContext.rsi || 'N/A'}, 24h Change: ${example.marketContext.change24h}%`
      }
      
      let assistantContent = ''
      if (example.decision) {
        assistantContent = `<think>
Analyzing ${example.decision.symbol}:
- Current price: $${example.marketContext.price}
- 24h change: ${example.marketContext.change24h}%
- Market sentiment: ${example.marketContext.sentiment?.fearGreed || 'N/A'}

${example.decision.reasoning}
</think>

<action>
${JSON.stringify({
  action: example.decision.action,
  entry_price: example.decision.entryPrice,
  stop_loss: example.decision.stopLoss,
  take_profit: example.decision.takeProfit,
  risk_percent: example.decision.riskPercent,
  confidence: example.decision.confidence,
}, null, 2)}
</action>`
      } else if (example.response) {
        assistantContent = example.response
      }
      
      return JSON.stringify({
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userContent },
          { role: 'assistant', content: assistantContent },
        ],
        metadata: {
          outcome: example.outcome,
          quality: example.quality,
        },
      })
    })
    
    return trainingLines.join('\n')
  }

  /**
   * Get statistics about collected data
   */
  getStats() {
    const total = this.examples.length
    const withOutcomes = this.examples.filter(e => e.outcome).length
    const profitable = this.examples.filter(e => e.quality?.profitable).length
    const highQuality = this.examples.filter(e => (e.quality?.timingScore || 0) >= 70).length
    
    const byType = {
      trade_decision: this.examples.filter(e => e.type === 'trade_decision').length,
      conversation: this.examples.filter(e => e.type === 'conversation').length,
      market_analysis: this.examples.filter(e => e.type === 'market_analysis').length,
      backtest_result: this.examples.filter(e => e.type === 'backtest_result').length,
    }
    
    const bySource = {
      user: this.examples.filter(e => e.source === 'user').length,
      auto_trading: this.examples.filter(e => e.source === 'auto_trading').length,
      backtest: this.examples.filter(e => e.source === 'backtest').length,
      paper_trading: this.examples.filter(e => e.source === 'paper_trading').length,
    }
    
    return {
      total,
      withOutcomes,
      profitable,
      highQuality,
      winRate: withOutcomes > 0 ? (profitable / withOutcomes * 100).toFixed(1) + '%' : 'N/A',
      byType,
      bySource,
      pendingOutcomes: this.pendingOutcomes.size,
      sessionId: this.sessionId,
    }
  }

  /**
   * Clear all stored data
   */
  clearAll() {
    this.examples = []
    this.pendingOutcomes.clear()
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEYS.TRAINING_EXAMPLES)
      localStorage.removeItem(STORAGE_KEYS.PENDING_OUTCOMES)
    }
  }
}

// Singleton instance
export const trainingDataLogger = new TrainingDataLogger()

// Initialize on client side
if (typeof window !== 'undefined') {
  trainingDataLogger.initialize()
}

