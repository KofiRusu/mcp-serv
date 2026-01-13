/**
 * Backtesting Engine
 * 
 * Simulates trading strategies on historical data with realistic
 * market conditions, fees, and slippage.
 * 
 * Inspired by TradeSyS-Demo and magic-beta reinforcement learning environment.
 */

import { OHLCV, loadBacktestData, getDataStats } from './backtest-data'
import { 
  calculateAllIndicators, 
  generateSignal, 
  TechnicalIndicators, 
  TradingSignal 
} from './indicators'
import {
  simulateOrderFillWithTiming,
  getVolatilityFromCandles,
  ExecutionConfig,
  OrderBookSnapshot,
} from './execution-model'

export interface Position {
  id: string
  symbol: string
  side: 'long' | 'short'
  entryPrice: number
  entryTime: number
  size: number
  stopLoss?: number
  takeProfit?: number
  pnl: number
  pnlPercent: number
}

export interface Trade {
  id: string
  symbol: string
  side: 'long' | 'short'
  entryPrice: number
  entryTime: number
  exitPrice: number
  exitTime: number
  size: number
  pnl: number
  pnlPercent: number
  fees: number
  reason: string
}

export interface PortfolioState {
  balance: number
  equity: number
  positions: Position[]
  totalPnl: number
  totalPnlPercent: number
  maxDrawdown: number
  currentDrawdown: number
  peakEquity: number
}

export interface BacktestConfig {
  symbols: string[]
  timeframe: '1m' | '5m' | '15m'
  initialBalance: number
  maxPositionSize: number // Percentage of equity per position
  maxConcurrentPositions: number
  tradingFee: number // As decimal (0.001 = 0.1%)
  slippage: number // As decimal
  maxDrawdownLimit: number // Stop trading if exceeded
  riskPerTrade: number // Percentage of equity at risk per trade
  stopLossPercent: number
  takeProfitPercent: number
  days: number
  startDate?: Date // Historical start date for backtest
  endDate?: Date   // Historical end date for backtest
  modelName?: string // PersRM model version (e.g. "persrm-trading-v1")
}

export interface BacktestProgress {
  currentStep: number
  totalSteps: number
  percentComplete: number
  currentEquity: number
  tradesCompleted: number
  elapsedTime: number
}

export interface BacktestResult {
  config: BacktestConfig
  portfolio: PortfolioState
  trades: Trade[]
  metrics: BacktestMetrics
  equityCurve: { timestamp: number; equity: number }[]
  signals: { timestamp: number; symbol: string; signal: TradingSignal }[]
  startTime: Date
  endTime: Date
  duration: number
}

export interface BacktestMetrics {
  totalReturn: number
  annualizedReturn: number
  totalTrades: number
  winningTrades: number
  losingTrades: number
  winRate: number
  profitFactor: number
  maxDrawdown: number
  sharpeRatio: number
  sortinoRatio: number
  averageTradeReturn: number
  averageTradeDuration: number
  largestWin: number
  largestLoss: number
  consecutiveWins: number
  consecutiveLosses: number
  expectancy: number
}

type ProgressCallback = (progress: BacktestProgress) => void

export class BacktestEngine {
  private config: BacktestConfig
  private portfolio: PortfolioState
  private trades: Trade[]
  private equityCurve: { timestamp: number; equity: number }[]
  private signals: { timestamp: number; symbol: string; signal: TradingSignal }[]
  private marketData: Map<string, OHLCV[]>
  private indicators: Map<string, TechnicalIndicators>
  private isRunning: boolean = false
  private shouldStop: boolean = false
  private executionConfig: ExecutionConfig
  
  constructor(config: Partial<BacktestConfig> = {}) {
    // Calculate days from date range if provided
    let days = config.days || 7
    if (config.startDate && config.endDate) {
      const diffMs = config.endDate.getTime() - config.startDate.getTime()
      days = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
    }
    
    this.config = {
      symbols: config.symbols || ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
      timeframe: config.timeframe || '5m',
      initialBalance: config.initialBalance || 100000,
      maxPositionSize: config.maxPositionSize || 0.1,
      maxConcurrentPositions: config.maxConcurrentPositions || 3,
      tradingFee: config.tradingFee || 0.001,
      slippage: config.slippage || 0.0005,
      maxDrawdownLimit: config.maxDrawdownLimit || 0.15,
      riskPerTrade: config.riskPerTrade || 0.02,
      stopLossPercent: config.stopLossPercent || 0.02,
      takeProfitPercent: config.takeProfitPercent || 0.04,
      days,
      startDate: config.startDate,
      endDate: config.endDate,
      modelName: config.modelName || 'persrm-trading', // Default model version
    }
    
    console.log(`[BacktestEngine] Using model: ${this.config.modelName}`)
    
    // Execution config for realistic fills
    this.executionConfig = {
      tradingFee: config.tradingFee || 0.001,
      takerFee: config.tradingFee || 0.001, // Same for spot
      baseSlippage: config.slippage || 0.0005,
      volatilityMultiplier: 2.0,
      orderBookDepth: 10,
    }
    
    this.portfolio = this.createInitialPortfolio()
    this.trades = []
    this.equityCurve = []
    this.signals = []
    this.marketData = new Map()
    this.indicators = new Map()
  }
  
  private createInitialPortfolio(): PortfolioState {
    return {
      balance: this.config.initialBalance,
      equity: this.config.initialBalance,
      positions: [],
      totalPnl: 0,
      totalPnlPercent: 0,
      maxDrawdown: 0,
      currentDrawdown: 0,
      peakEquity: this.config.initialBalance,
    }
  }
  
  /**
   * Run the backtest simulation
   */
  async run(onProgress?: ProgressCallback): Promise<BacktestResult> {
    const startTime = new Date()
    this.isRunning = true
    this.shouldStop = false
    
    console.log('Loading market data...')
    this.marketData = await loadBacktestData(
      this.config.symbols,
      this.config.timeframe,
      this.config.days,
      this.config.startDate,
      this.config.endDate
    )
    
    console.log('Calculating indicators...')
    for (const [symbol, candles] of this.marketData) {
      this.indicators.set(symbol, calculateAllIndicators(candles))
      console.log(`Calculated indicators for ${symbol}: ${candles.length} candles`)
    }
    
    // Find the symbol with the most data points
    const maxCandles = Math.max(
      ...Array.from(this.marketData.values()).map(c => c.length)
    )
    
    console.log(`Starting simulation with ${maxCandles} steps...`)
    const startStep = 50 // Skip warmup period for indicators
    
    for (let step = startStep; step < maxCandles && !this.shouldStop; step++) {
      // Process each symbol
      for (const symbol of this.config.symbols) {
        const candles = this.marketData.get(symbol)
        const indicators = this.indicators.get(symbol)
        
        if (!candles || !indicators || step >= candles.length) continue
        
        const currentCandle = candles[step]
        
        // Generate trading signal
        const signal = generateSignal(candles, indicators, step)
        
        if (signal.action !== 'HOLD') {
          this.signals.push({
            timestamp: currentCandle.timestamp,
            symbol,
            signal,
          })
        }
        
        // Update existing positions
        this.updatePositions(symbol, currentCandle)
        
        // Execute new trades based on signal
        if (signal.action !== 'HOLD' && signal.confidence >= 0.5) {
          await this.executeSignal(symbol, signal, currentCandle)
        }
      }
      
      // Update portfolio equity
      this.updateEquity(step)
      
      // Check drawdown limit
      if (this.portfolio.currentDrawdown > this.config.maxDrawdownLimit) {
        console.log(`Max drawdown limit reached: ${(this.portfolio.currentDrawdown * 100).toFixed(2)}%`)
        break
      }
      
      // Report progress
      if (onProgress && step % 100 === 0) {
        onProgress({
          currentStep: step,
          totalSteps: maxCandles,
          percentComplete: ((step - startStep) / (maxCandles - startStep)) * 100,
          currentEquity: this.portfolio.equity,
          tradesCompleted: this.trades.length,
          elapsedTime: Date.now() - startTime.getTime(),
        })
      }
    }
    
    // Close all remaining positions
    await this.closeAllPositions()
    
    const endTime = new Date()
    const metrics = this.calculateMetrics()
    
    this.isRunning = false
    
    return {
      config: this.config,
      portfolio: this.portfolio,
      trades: this.trades,
      metrics,
      equityCurve: this.equityCurve,
      signals: this.signals,
      startTime,
      endTime,
      duration: endTime.getTime() - startTime.getTime(),
    }
  }
  
  /**
   * Stop the backtest
   */
  stop(): void {
    this.shouldStop = true
  }
  
  /**
   * Update existing positions with current price
   */
  private updatePositions(symbol: string, candle: OHLCV): void {
    for (const position of this.portfolio.positions) {
      if (position.symbol !== symbol) continue
      
      const currentPrice = candle.close
      
      // Calculate P&L
      if (position.side === 'long') {
        position.pnl = (currentPrice - position.entryPrice) * position.size
        position.pnlPercent = (currentPrice - position.entryPrice) / position.entryPrice
      } else {
        position.pnl = (position.entryPrice - currentPrice) * position.size
        position.pnlPercent = (position.entryPrice - currentPrice) / position.entryPrice
      }
      
      // Check stop loss
      if (position.stopLoss) {
        const hitStopLoss = position.side === 'long' 
          ? candle.low <= position.stopLoss
          : candle.high >= position.stopLoss
        
        if (hitStopLoss) {
          this.closePosition(position, position.stopLoss, candle.timestamp, 'Stop Loss')
        }
      }
      
      // Check take profit
      if (position.takeProfit) {
        const hitTakeProfit = position.side === 'long'
          ? candle.high >= position.takeProfit
          : candle.low <= position.takeProfit
        
        if (hitTakeProfit) {
          this.closePosition(position, position.takeProfit, candle.timestamp, 'Take Profit')
        }
      }
    }
    
    // Remove closed positions
    this.portfolio.positions = this.portfolio.positions.filter(p => p.id !== undefined)
  }
  
  /**
   * Execute a trading signal
   */
  private async executeSignal(
    symbol: string, 
    signal: TradingSignal, 
    candle: OHLCV
  ): Promise<void> {
    const existingPosition = this.portfolio.positions.find(p => p.symbol === symbol)
    
    // Check if we should close existing position
    if (existingPosition) {
      if ((existingPosition.side === 'long' && signal.action === 'SELL') ||
          (existingPosition.side === 'short' && signal.action === 'BUY')) {
        this.closePosition(existingPosition, candle.close, candle.timestamp, 'Signal Reversal')
        return
      }
      // Already have a position in the same direction
      return
    }
    
    // Check if we can open a new position
    if (this.portfolio.positions.length >= this.config.maxConcurrentPositions) {
      return
    }
    
    // Calculate position size
    const riskAmount = this.portfolio.equity * this.config.riskPerTrade
    const stopDistance = candle.close * this.config.stopLossPercent
    const positionSize = riskAmount / stopDistance
    const positionValue = positionSize * candle.close
    
    // Check if we have enough balance
    const maxPositionValue = this.portfolio.balance * this.config.maxPositionSize
    const actualPositionValue = Math.min(positionValue, maxPositionValue)
    
    if (actualPositionValue < 100) return // Minimum position value
    
    // Get volatility from recent candles for realistic execution
    const candles = this.marketData.get(symbol) || []
    const volatility = getVolatilityFromCandles(candles)
    
    // Simulate realistic order fill
    const orderSide = signal.action === 'BUY' ? 'buy' : 'sell'
    const fill = simulateOrderFillWithTiming(
      actualPositionValue,
      orderSide,
      candle.close,
      candle.timestamp,
      undefined, // Order book not available in backtest
      candles,
      'market', // Market orders for backtesting
      this.executionConfig
    )
    
    const entryPrice = fill.fillPrice
    const actualSize = fill.fillSize
    const fees = fill.fees + fill.spreadCost
    
    // Create position
    const side = signal.action === 'BUY' ? 'long' : 'short'
    const position: Position = {
      id: `${symbol}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      symbol,
      side,
      entryPrice,
      entryTime: candle.timestamp,
      size: actualSize,
      stopLoss: side === 'long' 
        ? entryPrice * (1 - this.config.stopLossPercent)
        : entryPrice * (1 + this.config.stopLossPercent),
      takeProfit: side === 'long'
        ? entryPrice * (1 + this.config.takeProfitPercent)
        : entryPrice * (1 - this.config.takeProfitPercent),
      pnl: -fees,
      pnlPercent: 0,
    }
    
    // Update portfolio
    this.portfolio.balance -= fees
    this.portfolio.positions.push(position)
  }
  
  /**
   * Close a position with realistic execution
   */
  private closePosition(
    position: Position, 
    exitPrice: number, 
    exitTime: number,
    reason: string
  ): void {
    // Get volatility for realistic exit execution
    const candles = this.marketData.get(position.symbol) || []
    const volatility = getVolatilityFromCandles(candles)
    
    // Simulate realistic exit fill
    const orderSide = position.side === 'long' ? 'sell' : 'buy'
    const exitValue = position.size * exitPrice
    const fill = simulateOrderFillWithTiming(
      exitValue,
      orderSide,
      exitPrice,
      exitTime,
      undefined, // Order book not available
      candles,
      'market', // Market orders for exits (stop-loss/take-profit)
      this.executionConfig
    )
    
    const actualExitPrice = fill.fillPrice
    
    // Calculate P&L
    let pnl: number
    if (position.side === 'long') {
      pnl = (actualExitPrice - position.entryPrice) * position.size
    } else {
      pnl = (position.entryPrice - actualExitPrice) * position.size
    }
    
    // Apply exit costs (fees + spread)
    const exitCosts = fill.fees + fill.spreadCost
    pnl -= exitCosts
    
    // Record trade with execution details
    const trade: Trade = {
      id: position.id,
      symbol: position.symbol,
      side: position.side,
      entryPrice: position.entryPrice,
      entryTime: position.entryTime,
      exitPrice: actualExitPrice,
      exitTime,
      size: position.size,
      pnl,
      pnlPercent: pnl / (position.entryPrice * position.size),
      fees: exitCosts + (position.entryPrice * position.size * this.executionConfig.tradingFee),
      reason,
    }
    
    this.trades.push(trade)
    
    // Update portfolio
    this.portfolio.balance += (position.size * actualExitPrice) - exitCosts
    this.portfolio.totalPnl += pnl
    
    // Remove position
    const index = this.portfolio.positions.findIndex(p => p.id === position.id)
    if (index >= 0) {
      this.portfolio.positions.splice(index, 1)
    }
  }
  
  /**
   * Update portfolio equity
   */
  private updateEquity(step: number): void {
    // Calculate unrealized P&L
    let unrealizedPnl = 0
    for (const position of this.portfolio.positions) {
      unrealizedPnl += position.pnl
    }
    
    this.portfolio.equity = this.portfolio.balance + unrealizedPnl
    this.portfolio.totalPnlPercent = (this.portfolio.equity - this.config.initialBalance) / this.config.initialBalance
    
    // Update peak and drawdown
    if (this.portfolio.equity > this.portfolio.peakEquity) {
      this.portfolio.peakEquity = this.portfolio.equity
    }
    
    this.portfolio.currentDrawdown = (this.portfolio.peakEquity - this.portfolio.equity) / this.portfolio.peakEquity
    
    if (this.portfolio.currentDrawdown > this.portfolio.maxDrawdown) {
      this.portfolio.maxDrawdown = this.portfolio.currentDrawdown
    }
    
    // Record equity curve (sample every 10 steps)
    if (step % 10 === 0) {
      const firstCandle = this.marketData.get(this.config.symbols[0])?.[step]
      if (firstCandle) {
        this.equityCurve.push({
          timestamp: firstCandle.timestamp,
          equity: this.portfolio.equity,
        })
      }
    }
  }
  
  /**
   * Close all remaining positions
   */
  private async closeAllPositions(): Promise<void> {
    for (const position of [...this.portfolio.positions]) {
      const candles = this.marketData.get(position.symbol)
      if (candles && candles.length > 0) {
        const lastCandle = candles[candles.length - 1]
        this.closePosition(position, lastCandle.close, lastCandle.timestamp, 'End of Backtest')
      }
    }
  }
  
  /**
   * Calculate performance metrics
   */
  private calculateMetrics(): BacktestMetrics {
    const winningTrades = this.trades.filter(t => t.pnl > 0)
    const losingTrades = this.trades.filter(t => t.pnl <= 0)
    
    const grossProfit = winningTrades.reduce((sum, t) => sum + t.pnl, 0)
    const grossLoss = Math.abs(losingTrades.reduce((sum, t) => sum + t.pnl, 0))
    
    const returns = this.trades.map(t => t.pnlPercent)
    const avgReturn = returns.length > 0 
      ? returns.reduce((a, b) => a + b, 0) / returns.length 
      : 0
    const stdReturn = returns.length > 1
      ? Math.sqrt(returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / (returns.length - 1))
      : 0
    
    // Calculate consecutive wins/losses
    let maxConsecutiveWins = 0, maxConsecutiveLosses = 0
    let currentWins = 0, currentLosses = 0
    
    for (const trade of this.trades) {
      if (trade.pnl > 0) {
        currentWins++
        currentLosses = 0
        maxConsecutiveWins = Math.max(maxConsecutiveWins, currentWins)
      } else {
        currentLosses++
        currentWins = 0
        maxConsecutiveLosses = Math.max(maxConsecutiveLosses, currentLosses)
      }
    }
    
    // Calculate Sharpe Ratio (assuming 0% risk-free rate for simplicity)
    const sharpeRatio = stdReturn > 0 ? (avgReturn / stdReturn) * Math.sqrt(252 * 24 * 12) : 0 // Annualized for 5m
    
    // Calculate Sortino Ratio (only downside deviation)
    const negativeReturns = returns.filter(r => r < 0)
    const downsideDeviation = negativeReturns.length > 0
      ? Math.sqrt(negativeReturns.reduce((sum, r) => sum + Math.pow(r, 2), 0) / negativeReturns.length)
      : 0
    const sortinoRatio = downsideDeviation > 0 ? (avgReturn / downsideDeviation) * Math.sqrt(252 * 24 * 12) : 0
    
    // Calculate average trade duration
    const durations = this.trades.map(t => t.exitTime - t.entryTime)
    const avgDuration = durations.length > 0 
      ? durations.reduce((a, b) => a + b, 0) / durations.length / (1000 * 60) // in minutes
      : 0
    
    // Expectancy = (Win% * Avg Win) - (Loss% * Avg Loss)
    const avgWin = winningTrades.length > 0 
      ? winningTrades.reduce((sum, t) => sum + t.pnl, 0) / winningTrades.length 
      : 0
    const avgLoss = losingTrades.length > 0 
      ? losingTrades.reduce((sum, t) => sum + Math.abs(t.pnl), 0) / losingTrades.length 
      : 0
    const winRate = this.trades.length > 0 ? winningTrades.length / this.trades.length : 0
    const expectancy = (winRate * avgWin) - ((1 - winRate) * avgLoss)
    
    return {
      totalReturn: this.portfolio.totalPnlPercent,
      annualizedReturn: this.portfolio.totalPnlPercent * (365 / this.config.days),
      totalTrades: this.trades.length,
      winningTrades: winningTrades.length,
      losingTrades: losingTrades.length,
      winRate,
      profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0,
      maxDrawdown: this.portfolio.maxDrawdown,
      sharpeRatio,
      sortinoRatio,
      averageTradeReturn: avgReturn,
      averageTradeDuration: avgDuration,
      largestWin: winningTrades.length > 0 ? Math.max(...winningTrades.map(t => t.pnl)) : 0,
      largestLoss: losingTrades.length > 0 ? Math.min(...losingTrades.map(t => t.pnl)) : 0,
      consecutiveWins: maxConsecutiveWins,
      consecutiveLosses: maxConsecutiveLosses,
      expectancy,
    }
  }
}

/**
 * Create and run a backtest
 */
export async function runBacktest(
  config: Partial<BacktestConfig>,
  onProgress?: ProgressCallback
): Promise<BacktestResult> {
  const engine = new BacktestEngine(config)
  return engine.run(onProgress)
}

