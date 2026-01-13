/**
 * PersRM Trading Brain
 * 
 * Intelligent trading decision engine that combines:
 * - Technical analysis
 * - Pattern recognition
 * - Risk management
 * - Reinforcement learning from past trades
 * 
 * Inspired by magic-beta's NeuralEngine and TradingEnvironment.
 */

import { OHLCV } from './backtest-data'
import { 
  calculateAllIndicators, 
  generateSignal, 
  TechnicalIndicators,
  TradingSignal 
} from './indicators'
import { Position, Trade, BacktestMetrics } from './backtest-engine'

export interface MarketAnalysis {
  symbol: string
  timestamp: number
  price: number
  trend: 'bullish' | 'bearish' | 'neutral'
  trendStrength: number
  volatility: number
  momentum: number
  support: number
  resistance: number
  signals: TradingSignal
  patterns: PatternRecognition[]
  riskLevel: 'low' | 'medium' | 'high'
  confidence: number
}

export interface PatternRecognition {
  name: string
  type: 'continuation' | 'reversal'
  confidence: number
  direction: 'bullish' | 'bearish'
  targetPrice?: number
  stopLoss?: number
}

export interface TradingDecision {
  action: 'OPEN_LONG' | 'OPEN_SHORT' | 'CLOSE_LONG' | 'CLOSE_SHORT' | 'HOLD'
  confidence: number
  symbol: string
  size: number // As percentage of available capital
  stopLoss?: number
  takeProfit?: number
  reasoning: string[]
  riskReward: number
  expectedValue: number
}

export interface RiskAssessment {
  portfolioRisk: number
  positionRisk: number
  marketRisk: number
  correlationRisk: number
  maxPositionSize: number
  recommendedLeverage: number
}

export interface LearningState {
  totalTradesAnalyzed: number
  winningPatterns: Map<string, number>
  losingPatterns: Map<string, number>
  marketRegimeAccuracy: Map<string, number>
  strategyPerformance: Map<string, BacktestMetrics>
  lastUpdated: Date
}

export interface BrainConfig {
  // Risk parameters
  maxRiskPerTrade: number // Default 2%
  maxPortfolioRisk: number // Default 6%
  maxPositionSize: number // Default 10%
  minRiskReward: number // Default 2:1
  
  // Strategy parameters
  trendFollowing: boolean
  meanReversion: boolean
  breakoutTrading: boolean
  scalping: boolean
  
  // Confidence thresholds
  minSignalConfidence: number // Default 0.5
  minPatternConfidence: number // Default 0.6
  minDecisionConfidence: number // Default 0.65
  
  // Learning parameters
  learningEnabled: boolean
  adaptiveRisk: boolean
  patternMemory: number // Number of patterns to remember
}

export class PersRMBrain {
  private config: BrainConfig
  private learningState: LearningState
  private marketCache: Map<string, MarketAnalysis>
  private decisionHistory: TradingDecision[]
  private tradeHistory: Trade[]
  
  constructor(config: Partial<BrainConfig> = {}) {
    this.config = {
      maxRiskPerTrade: config.maxRiskPerTrade || 0.02,
      maxPortfolioRisk: config.maxPortfolioRisk || 0.06,
      maxPositionSize: config.maxPositionSize || 0.1,
      minRiskReward: config.minRiskReward || 2,
      trendFollowing: config.trendFollowing ?? true,
      meanReversion: config.meanReversion ?? true,
      breakoutTrading: config.breakoutTrading ?? true,
      scalping: config.scalping ?? false,
      minSignalConfidence: config.minSignalConfidence || 0.5,
      minPatternConfidence: config.minPatternConfidence || 0.6,
      minDecisionConfidence: config.minDecisionConfidence || 0.65,
      learningEnabled: config.learningEnabled ?? true,
      adaptiveRisk: config.adaptiveRisk ?? true,
      patternMemory: config.patternMemory || 1000,
    }
    
    this.learningState = {
      totalTradesAnalyzed: 0,
      winningPatterns: new Map(),
      losingPatterns: new Map(),
      marketRegimeAccuracy: new Map(),
      strategyPerformance: new Map(),
      lastUpdated: new Date(),
    }
    
    this.marketCache = new Map()
    this.decisionHistory = []
    this.tradeHistory = []
  }
  
  /**
   * Analyze market conditions for a symbol
   */
  analyzeMarket(
    symbol: string,
    candles: OHLCV[],
    indicators: TechnicalIndicators,
    currentIndex: number
  ): MarketAnalysis {
    const currentCandle = candles[currentIndex]
    const signal = generateSignal(candles, indicators, currentIndex)
    
    // Determine trend
    const ema20 = indicators.ema20[currentIndex]
    const ema50 = indicators.ema50[currentIndex]
    const price = currentCandle.close
    
    let trend: 'bullish' | 'bearish' | 'neutral' = 'neutral'
    let trendStrength = 0
    
    if (!isNaN(ema20) && !isNaN(ema50)) {
      if (ema20 > ema50 && price > ema20) {
        trend = 'bullish'
        trendStrength = (price - ema50) / ema50
      } else if (ema20 < ema50 && price < ema20) {
        trend = 'bearish'
        trendStrength = (ema50 - price) / ema50
      }
    }
    
    // Calculate volatility
    const atr = indicators.atr[currentIndex]
    const volatility = atr ? atr.atrPercent / 100 : 0.02
    
    // Calculate momentum
    const rsi = indicators.rsi[currentIndex] || 50
    const macd = indicators.macd[currentIndex]
    const momentum = ((rsi - 50) / 50) + (macd ? macd.histogram / price * 100 : 0)
    
    // Find support and resistance
    const { support, resistance } = this.findSupportResistance(candles, currentIndex)
    
    // Recognize patterns
    const patterns = this.recognizePatterns(candles, indicators, currentIndex)
    
    // Assess risk level
    let riskLevel: 'low' | 'medium' | 'high' = 'medium'
    if (volatility < 0.01) riskLevel = 'low'
    else if (volatility > 0.03) riskLevel = 'high'
    
    // Calculate overall confidence
    const confidence = this.calculateConfidence(signal, patterns, trend, volatility)
    
    const analysis: MarketAnalysis = {
      symbol,
      timestamp: currentCandle.timestamp,
      price,
      trend,
      trendStrength: Math.min(trendStrength, 1),
      volatility,
      momentum: Math.max(-1, Math.min(1, momentum)),
      support,
      resistance,
      signals: signal,
      patterns,
      riskLevel,
      confidence,
    }
    
    this.marketCache.set(symbol, analysis)
    return analysis
  }
  
  /**
   * Find support and resistance levels
   */
  private findSupportResistance(
    candles: OHLCV[],
    currentIndex: number,
    lookback: number = 50
  ): { support: number; resistance: number } {
    const start = Math.max(0, currentIndex - lookback)
    const relevantCandles = candles.slice(start, currentIndex + 1)
    
    const highs = relevantCandles.map(c => c.high)
    const lows = relevantCandles.map(c => c.low)
    
    // Simple pivot-based S/R
    const resistance = Math.max(...highs.slice(-20))
    const support = Math.min(...lows.slice(-20))
    
    return { support, resistance }
  }
  
  /**
   * Recognize chart patterns
   */
  private recognizePatterns(
    candles: OHLCV[],
    indicators: TechnicalIndicators,
    currentIndex: number
  ): PatternRecognition[] {
    const patterns: PatternRecognition[] = []
    
    if (currentIndex < 20) return patterns
    
    const recentCandles = candles.slice(currentIndex - 20, currentIndex + 1)
    const currentPrice = candles[currentIndex].close
    const rsi = indicators.rsi[currentIndex] || 50
    const bb = indicators.bb[currentIndex]
    const stoch = indicators.stoch[currentIndex]
    
    // RSI Divergence
    if (rsi < 30) {
      patterns.push({
        name: 'RSI Oversold',
        type: 'reversal',
        confidence: 0.7,
        direction: 'bullish',
        targetPrice: currentPrice * 1.03,
        stopLoss: currentPrice * 0.98,
      })
    } else if (rsi > 70) {
      patterns.push({
        name: 'RSI Overbought',
        type: 'reversal',
        confidence: 0.7,
        direction: 'bearish',
        targetPrice: currentPrice * 0.97,
        stopLoss: currentPrice * 1.02,
      })
    }
    
    // Bollinger Band Squeeze
    if (bb && bb.width < 0.02) {
      patterns.push({
        name: 'BB Squeeze',
        type: 'continuation',
        confidence: 0.65,
        direction: bb.percentB > 0.5 ? 'bullish' : 'bearish',
      })
    }
    
    // BB Breakout
    if (bb) {
      if (bb.percentB > 1) {
        patterns.push({
          name: 'BB Upper Breakout',
          type: 'continuation',
          confidence: 0.6,
          direction: 'bullish',
          targetPrice: currentPrice * 1.02,
        })
      } else if (bb.percentB < 0) {
        patterns.push({
          name: 'BB Lower Breakout',
          type: 'continuation',
          confidence: 0.6,
          direction: 'bearish',
          targetPrice: currentPrice * 0.98,
        })
      }
    }
    
    // Double Bottom/Top (simplified)
    const lows = recentCandles.map(c => c.low)
    const highs = recentCandles.map(c => c.high)
    const minLow = Math.min(...lows)
    const maxHigh = Math.max(...highs)
    
    // Count touches of support/resistance
    const supportTouches = lows.filter(l => l < minLow * 1.005).length
    const resistanceTouches = highs.filter(h => h > maxHigh * 0.995).length
    
    if (supportTouches >= 2 && currentPrice > minLow * 1.01) {
      patterns.push({
        name: 'Double Bottom',
        type: 'reversal',
        confidence: 0.75,
        direction: 'bullish',
        targetPrice: maxHigh,
        stopLoss: minLow * 0.99,
      })
    }
    
    if (resistanceTouches >= 2 && currentPrice < maxHigh * 0.99) {
      patterns.push({
        name: 'Double Top',
        type: 'reversal',
        confidence: 0.75,
        direction: 'bearish',
        targetPrice: minLow,
        stopLoss: maxHigh * 1.01,
      })
    }
    
    // Stochastic crossover
    if (stoch) {
      if (stoch.k < 20 && stoch.k > stoch.d) {
        patterns.push({
          name: 'Stochastic Bullish Crossover',
          type: 'reversal',
          confidence: 0.65,
          direction: 'bullish',
        })
      } else if (stoch.k > 80 && stoch.k < stoch.d) {
        patterns.push({
          name: 'Stochastic Bearish Crossover',
          type: 'reversal',
          confidence: 0.65,
          direction: 'bearish',
        })
      }
    }
    
    return patterns
  }
  
  /**
   * Calculate overall confidence score
   */
  private calculateConfidence(
    signal: TradingSignal,
    patterns: PatternRecognition[],
    trend: 'bullish' | 'bearish' | 'neutral',
    volatility: number
  ): number {
    let confidence = signal.confidence
    
    // Boost confidence if patterns agree with signal
    for (const pattern of patterns) {
      if (
        (signal.action === 'BUY' && pattern.direction === 'bullish') ||
        (signal.action === 'SELL' && pattern.direction === 'bearish')
      ) {
        confidence = Math.min(1, confidence + pattern.confidence * 0.1)
      } else if (
        (signal.action === 'BUY' && pattern.direction === 'bearish') ||
        (signal.action === 'SELL' && pattern.direction === 'bullish')
      ) {
        confidence = Math.max(0, confidence - pattern.confidence * 0.1)
      }
    }
    
    // Reduce confidence in high volatility
    if (volatility > 0.03) {
      confidence *= 0.9
    }
    
    // Boost confidence if signal aligns with trend
    if (
      (signal.action === 'BUY' && trend === 'bullish') ||
      (signal.action === 'SELL' && trend === 'bearish')
    ) {
      confidence = Math.min(1, confidence * 1.1)
    }
    
    return confidence
  }
  
  /**
   * Make a trading decision
   */
  makeDecision(
    analysis: MarketAnalysis,
    currentPositions: Position[],
    portfolioEquity: number,
    currentPrice: number
  ): TradingDecision {
    const reasoning: string[] = []
    let action: TradingDecision['action'] = 'HOLD'
    let confidence = 0
    let size = 0
    let stopLoss: number | undefined
    let takeProfit: number | undefined
    
    // Check existing positions
    const existingPosition = currentPositions.find(p => p.symbol === analysis.symbol)
    
    if (existingPosition) {
      // Decide whether to close existing position
      const shouldClose = this.shouldClosePosition(existingPosition, analysis)
      
      if (shouldClose.close) {
        action = existingPosition.side === 'long' ? 'CLOSE_LONG' : 'CLOSE_SHORT'
        confidence = shouldClose.confidence
        reasoning.push(...shouldClose.reasons)
      } else {
        action = 'HOLD'
        confidence = 0.5
        reasoning.push('Maintaining existing position')
      }
    } else {
      // Decide whether to open a new position
      const shouldOpen = this.shouldOpenPosition(analysis, currentPositions, portfolioEquity)
      
      if (shouldOpen.open) {
        action = shouldOpen.side === 'long' ? 'OPEN_LONG' : 'OPEN_SHORT'
        confidence = shouldOpen.confidence
        size = shouldOpen.size
        stopLoss = shouldOpen.stopLoss
        takeProfit = shouldOpen.takeProfit
        reasoning.push(...shouldOpen.reasons)
      } else {
        action = 'HOLD'
        confidence = analysis.confidence
        reasoning.push(...shouldOpen.reasons)
      }
    }
    
    // Calculate risk/reward
    let riskReward = 0
    if (stopLoss && takeProfit) {
      const risk = Math.abs(currentPrice - stopLoss)
      const reward = Math.abs(takeProfit - currentPrice)
      riskReward = reward / risk
    }
    
    // Calculate expected value
    const winRate = this.getHistoricalWinRate(analysis.symbol)
    const expectedValue = riskReward > 0 
      ? (winRate * riskReward) - ((1 - winRate) * 1)
      : 0
    
    const decision: TradingDecision = {
      action,
      confidence,
      symbol: analysis.symbol,
      size,
      stopLoss,
      takeProfit,
      reasoning,
      riskReward,
      expectedValue,
    }
    
    this.decisionHistory.push(decision)
    
    return decision
  }
  
  /**
   * Determine if we should open a new position
   */
  private shouldOpenPosition(
    analysis: MarketAnalysis,
    currentPositions: Position[],
    portfolioEquity: number
  ): {
    open: boolean
    side?: 'long' | 'short'
    size: number
    stopLoss?: number
    takeProfit?: number
    confidence: number
    reasons: string[]
  } {
    const reasons: string[] = []
    
    // Check signal strength
    if (analysis.signals.action === 'HOLD') {
      reasons.push('No clear signal')
      return { open: false, size: 0, confidence: 0, reasons }
    }
    
    if (analysis.confidence < this.config.minDecisionConfidence) {
      reasons.push(`Confidence too low: ${(analysis.confidence * 100).toFixed(1)}%`)
      return { open: false, size: 0, confidence: analysis.confidence, reasons }
    }
    
    // Check if we have too many positions
    if (currentPositions.length >= 3) {
      reasons.push('Maximum positions reached')
      return { open: false, size: 0, confidence: 0, reasons }
    }
    
    // Check market risk
    if (analysis.riskLevel === 'high' && !this.config.adaptiveRisk) {
      reasons.push('High market volatility')
      return { open: false, size: 0, confidence: 0, reasons }
    }
    
    // Determine side
    const side = analysis.signals.action === 'BUY' ? 'long' : 'short'
    
    // Find best pattern for stop/target
    const alignedPatterns = analysis.patterns.filter(p => 
      (side === 'long' && p.direction === 'bullish') ||
      (side === 'short' && p.direction === 'bearish')
    )
    
    // Calculate stop loss and take profit
    let stopLoss: number
    let takeProfit: number
    
    const bestPattern = alignedPatterns.sort((a, b) => b.confidence - a.confidence)[0]
    
    if (bestPattern?.stopLoss && bestPattern?.targetPrice) {
      stopLoss = bestPattern.stopLoss
      takeProfit = bestPattern.targetPrice
    } else {
      // Default to ATR-based stops
      const atrMultiplier = 2
      const atr = analysis.volatility * analysis.price
      
      if (side === 'long') {
        stopLoss = analysis.price - (atr * atrMultiplier)
        takeProfit = analysis.price + (atr * atrMultiplier * 2)
      } else {
        stopLoss = analysis.price + (atr * atrMultiplier)
        takeProfit = analysis.price - (atr * atrMultiplier * 2)
      }
    }
    
    // Calculate risk/reward
    const risk = Math.abs(analysis.price - stopLoss)
    const reward = Math.abs(takeProfit - analysis.price)
    const riskReward = reward / risk
    
    if (riskReward < this.config.minRiskReward) {
      reasons.push(`R/R ratio too low: ${riskReward.toFixed(2)}`)
      return { open: false, size: 0, confidence: 0, reasons }
    }
    
    // Calculate position size based on risk
    const riskAmount = portfolioEquity * this.config.maxRiskPerTrade
    const positionValue = riskAmount / (risk / analysis.price)
    const size = Math.min(positionValue / portfolioEquity, this.config.maxPositionSize)
    
    // Build reasoning
    reasons.push(`Signal: ${analysis.signals.action} (${(analysis.confidence * 100).toFixed(1)}%)`)
    reasons.push(`Trend: ${analysis.trend} (strength: ${(analysis.trendStrength * 100).toFixed(1)}%)`)
    reasons.push(`R/R: ${riskReward.toFixed(2)}`)
    
    if (alignedPatterns.length > 0) {
      reasons.push(`Patterns: ${alignedPatterns.map(p => p.name).join(', ')}`)
    }
    
    return {
      open: true,
      side,
      size,
      stopLoss,
      takeProfit,
      confidence: analysis.confidence,
      reasons,
    }
  }
  
  /**
   * Determine if we should close a position
   */
  private shouldClosePosition(
    position: Position,
    analysis: MarketAnalysis
  ): { close: boolean; confidence: number; reasons: string[] } {
    const reasons: string[] = []
    
    // Check for reversal signals
    if (
      (position.side === 'long' && analysis.signals.action === 'SELL') ||
      (position.side === 'short' && analysis.signals.action === 'BUY')
    ) {
      if (analysis.confidence >= this.config.minSignalConfidence) {
        reasons.push(`Reversal signal: ${analysis.signals.action}`)
        return { close: true, confidence: analysis.confidence, reasons }
      }
    }
    
    // Check for trend change
    if (
      (position.side === 'long' && analysis.trend === 'bearish' && analysis.trendStrength > 0.02) ||
      (position.side === 'short' && analysis.trend === 'bullish' && analysis.trendStrength > 0.02)
    ) {
      reasons.push(`Trend reversal: ${analysis.trend}`)
      return { close: true, confidence: 0.7, reasons }
    }
    
    // Check for bearish patterns on long position
    const dangerPatterns = analysis.patterns.filter(p =>
      (position.side === 'long' && p.direction === 'bearish' && p.type === 'reversal') ||
      (position.side === 'short' && p.direction === 'bullish' && p.type === 'reversal')
    )
    
    if (dangerPatterns.length > 0 && dangerPatterns[0].confidence >= this.config.minPatternConfidence) {
      reasons.push(`Warning pattern: ${dangerPatterns[0].name}`)
      return { close: true, confidence: dangerPatterns[0].confidence, reasons }
    }
    
    // Check profit target (trail stop)
    if (position.pnlPercent > 0.05) {
      if (analysis.momentum < -0.3) {
        reasons.push('Momentum fading on profitable position')
        return { close: true, confidence: 0.6, reasons }
      }
    }
    
    return { close: false, confidence: 0, reasons: ['Position healthy'] }
  }
  
  /**
   * Get historical win rate for a symbol
   */
  private getHistoricalWinRate(symbol: string): number {
    const symbolTrades = this.tradeHistory.filter(t => t.symbol === symbol)
    if (symbolTrades.length < 10) return 0.5 // Default
    
    const wins = symbolTrades.filter(t => t.pnl > 0).length
    return wins / symbolTrades.length
  }
  
  /**
   * Learn from completed trades
   */
  learnFromTrade(trade: Trade): void {
    if (!this.config.learningEnabled) return
    
    this.tradeHistory.push(trade)
    this.learningState.totalTradesAnalyzed++
    
    // Record patterns that led to win/loss
    const decision = this.decisionHistory.find(d => 
      d.symbol === trade.symbol && 
      Math.abs(d.confidence - trade.pnlPercent) < 1
    )
    
    if (decision) {
      const patternKey = decision.reasoning.join('|')
      
      if (trade.pnl > 0) {
        const count = this.learningState.winningPatterns.get(patternKey) || 0
        this.learningState.winningPatterns.set(patternKey, count + 1)
      } else {
        const count = this.learningState.losingPatterns.get(patternKey) || 0
        this.learningState.losingPatterns.set(patternKey, count + 1)
      }
    }
    
    this.learningState.lastUpdated = new Date()
  }
  
  /**
   * Assess current portfolio risk
   */
  assessRisk(
    positions: Position[],
    portfolioEquity: number
  ): RiskAssessment {
    // Calculate total position risk
    let totalRisk = 0
    for (const position of positions) {
      if (position.stopLoss) {
        const riskPercent = Math.abs(position.entryPrice - position.stopLoss) / position.entryPrice
        totalRisk += riskPercent * (position.size * position.entryPrice / portfolioEquity)
      } else {
        // Assume 5% risk if no stop loss
        totalRisk += 0.05 * (position.size * position.entryPrice / portfolioEquity)
      }
    }
    
    // Calculate correlation risk (simplified)
    const correlationRisk = positions.length > 1 ? 0.2 : 0
    
    // Calculate market risk from cached analyses
    let marketRisk = 0
    for (const analysis of this.marketCache.values()) {
      if (analysis.riskLevel === 'high') marketRisk += 0.3
      else if (analysis.riskLevel === 'medium') marketRisk += 0.15
      else marketRisk += 0.05
    }
    marketRisk /= Math.max(1, this.marketCache.size)
    
    // Determine max position size based on current risk
    const remainingRiskBudget = this.config.maxPortfolioRisk - totalRisk
    const maxPositionSize = Math.max(0, Math.min(
      this.config.maxPositionSize,
      remainingRiskBudget / this.config.maxRiskPerTrade * this.config.maxPositionSize
    ))
    
    return {
      portfolioRisk: totalRisk,
      positionRisk: totalRisk / Math.max(1, positions.length),
      marketRisk,
      correlationRisk,
      maxPositionSize,
      recommendedLeverage: 1, // No leverage recommended for safety
    }
  }
  
  /**
   * Get brain status
   */
  getStatus(): {
    config: BrainConfig
    learning: LearningState
    recentDecisions: TradingDecision[]
    cachedAnalyses: number
  } {
    return {
      config: this.config,
      learning: this.learningState,
      recentDecisions: this.decisionHistory.slice(-10),
      cachedAnalyses: this.marketCache.size,
    }
  }
  
  /**
   * Reset the brain state
   */
  reset(): void {
    this.marketCache.clear()
    this.decisionHistory = []
    // Keep learning state for continuity
  }
}

