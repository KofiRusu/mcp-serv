/**
 * Paper Trading Engine
 * 
 * Runs strategies on live market data without real funds.
 * Uses the same execution model as backtesting for consistency.
 */

import { OHLCV } from './backtest-data'
import {
  simulateOrderFillWithTiming,
  getVolatilityFromCandles,
  ExecutionConfig,
} from './execution-model'
import {
  calculateAllIndicators,
  generateSignal,
  TechnicalIndicators,
  TradingSignal,
} from './indicators'

export interface PaperPosition {
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

export interface PaperTrade {
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
  slippage: number
  reason: string
}

export interface PaperPortfolio {
  balance: number
  equity: number
  positions: PaperPosition[]
  totalPnl: number
  totalPnlPercent: number
  maxDrawdown: number
  currentDrawdown: number
  peakEquity: number
}

export interface PaperTradingConfig {
  symbols: string[]
  initialBalance: number
  maxPositionSize: number
  maxConcurrentPositions: number
  riskPerTrade: number
  stopLossPercent: number
  takeProfitPercent: number
  tradingFee: number
  slippage: number
}

const DEFAULT_CONFIG: PaperTradingConfig = {
  symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
  initialBalance: 100000,
  maxPositionSize: 0.1,
  maxConcurrentPositions: 3,
  riskPerTrade: 0.02,
  stopLossPercent: 0.02,
  takeProfitPercent: 0.04,
  tradingFee: 0.001,
  slippage: 0.0005,
}

export class PaperTradingEngine {
  private config: PaperTradingConfig
  private portfolio: PaperPortfolio
  private trades: PaperTrade[]
  private isRunning: boolean = false
  private shouldStop: boolean = false
  private priceUpdateInterval: NodeJS.Timeout | null = null
  private candles: Map<string, OHLCV[]>
  private indicators: Map<string, TechnicalIndicators>
  private executionConfig: ExecutionConfig
  
  // Price update callback
  private onPriceUpdate?: (symbol: string, price: number) => void
  private onTrade?: (trade: PaperTrade) => void
  private onPortfolioUpdate?: (portfolio: PaperPortfolio) => void

  constructor(config: Partial<PaperTradingConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config }
    this.portfolio = this.createInitialPortfolio()
    this.trades = []
    this.candles = new Map()
    this.indicators = new Map()
    
    this.executionConfig = {
      tradingFee: this.config.tradingFee,
      takerFee: this.config.tradingFee,
      baseSlippage: this.config.slippage,
      volatilityMultiplier: 2.0,
      orderBookDepth: 10,
    }
  }

  private createInitialPortfolio(): PaperPortfolio {
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
   * Start paper trading
   */
  async start(
    onPriceUpdate?: (symbol: string, price: number) => void,
    onTrade?: (trade: PaperTrade) => void,
    onPortfolioUpdate?: (portfolio: PaperPortfolio) => void
  ): Promise<void> {
    if (this.isRunning) {
      console.warn('Paper trading already running')
      return
    }

    this.onPriceUpdate = onPriceUpdate
    this.onTrade = onTrade
    this.onPortfolioUpdate = onPortfolioUpdate
    
    this.isRunning = true
    this.shouldStop = false

    console.log('Starting paper trading...')
    
    // Initialize candles for each symbol
    await this.initializeCandles()
    
    // Start price update loop
    this.startPriceUpdateLoop()
  }

  /**
   * Stop paper trading
   */
  stop(): void {
    this.shouldStop = true
    this.isRunning = false
    
    if (this.priceUpdateInterval) {
      clearInterval(this.priceUpdateInterval)
      this.priceUpdateInterval = null
    }
    
    console.log('Paper trading stopped')
  }

  /**
   * Initialize candles for indicators
   */
  private async initializeCandles(): Promise<void> {
    for (const symbol of this.config.symbols) {
      try {
        const response = await fetch(`/api/market?action=ohlcv&symbol=${symbol}&timeframe=5m&limit=100`)
        if (response.ok) {
          const data = await response.json()
          const candles: OHLCV[] = Array.isArray(data)
            ? data.map((c: any) => ({
                timestamp: c[0] || c.timestamp || c.time,
                open: c[1] || c.open,
                high: c[2] || c.high,
                low: c[3] || c.low,
                close: c[4] || c.close,
                volume: c[5] || c.volume,
              }))
            : (data.candles || []).map((c: any) => ({
                timestamp: c.timestamp || c.time,
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close,
                volume: c.volume,
              }))
          
          this.candles.set(symbol, candles)
          this.indicators.set(symbol, calculateAllIndicators(candles))
        }
      } catch (error) {
        console.error(`Failed to initialize candles for ${symbol}:`, error)
      }
    }
  }

  /**
   * Start price update loop
   */
  private startPriceUpdateLoop(): void {
    // Update prices every 5 seconds
    this.priceUpdateInterval = setInterval(async () => {
      if (this.shouldStop) {
        this.stop()
        return
      }

      await this.updatePrices()
    }, 5000)
    
    // Initial update
    this.updatePrices()
  }

  /**
   * Update prices and process trades
   */
  private async updatePrices(): Promise<void> {
    for (const symbol of this.config.symbols) {
      try {
        // Fetch latest ticker
        const response = await fetch(`/api/market?action=ticker&symbol=${symbol}`)
        if (!response.ok) continue
        
        const ticker = await response.json()
        const currentPrice = ticker.last || ticker.close
        
        // Update candles (add new candle if timeframe passed)
        await this.updateCandles(symbol, currentPrice)
        
        // Update positions
        this.updatePositions(symbol, currentPrice)
        
        // Generate signals and execute trades
        await this.processSignals(symbol, currentPrice)
        
        // Update portfolio
        this.updatePortfolio()
        
        // Notify callbacks
        this.onPriceUpdate?.(symbol, currentPrice)
        this.onPortfolioUpdate?.(this.portfolio)
        
      } catch (error) {
        console.error(`Error updating price for ${symbol}:`, error)
      }
    }
  }

  /**
   * Update candles with latest price
   */
  private async updateCandles(symbol: string, currentPrice: number): Promise<void> {
    const candles = this.candles.get(symbol) || []
    
    // Check if we need a new candle (every 5 minutes)
    const now = Date.now()
    const lastCandle = candles[candles.length - 1]
    
    if (!lastCandle || now - lastCandle.timestamp >= 5 * 60 * 1000) {
      // Fetch latest candles to get accurate OHLCV
      try {
        const response = await fetch(`/api/market?action=ohlcv&symbol=${symbol}&timeframe=5m&limit=1`)
        if (response.ok) {
          const data = await response.json()
          const newCandle: OHLCV = Array.isArray(data) && data.length > 0
            ? {
                timestamp: data[0][0] || now,
                open: data[0][1],
                high: data[0][2],
                low: data[0][3],
                close: data[0][4],
                volume: data[0][5],
              }
            : {
                timestamp: now,
                open: currentPrice,
                high: currentPrice,
                low: currentPrice,
                close: currentPrice,
                volume: 0,
              }
          
          candles.push(newCandle)
          
          // Keep only last 200 candles
          if (candles.length > 200) {
            candles.shift()
          }
          
          this.candles.set(symbol, candles)
          this.indicators.set(symbol, calculateAllIndicators(candles))
        }
      } catch (error) {
        console.error(`Failed to update candles for ${symbol}:`, error)
      }
    } else {
      // Update current candle's high/low/close
      lastCandle.high = Math.max(lastCandle.high, currentPrice)
      lastCandle.low = Math.min(lastCandle.low, currentPrice)
      lastCandle.close = currentPrice
    }
  }

  /**
   * Update positions with current price
   */
  private updatePositions(symbol: string, currentPrice: number): void {
    for (const position of this.portfolio.positions) {
      if (position.symbol !== symbol) continue
      
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
          ? currentPrice <= position.stopLoss
          : currentPrice >= position.stopLoss
        
        if (hitStopLoss) {
          this.closePosition(position, position.stopLoss, 'Stop Loss')
        }
      }
      
      // Check take profit
      if (position.takeProfit) {
        const hitTakeProfit = position.side === 'long'
          ? currentPrice >= position.takeProfit
          : currentPrice <= position.takeProfit
        
        if (hitTakeProfit) {
          this.closePosition(position, position.takeProfit, 'Take Profit')
        }
      }
    }
    
    // Remove closed positions
    this.portfolio.positions = this.portfolio.positions.filter(p => p.id !== undefined)
  }

  /**
   * Process trading signals
   */
  private async processSignals(symbol: string, currentPrice: number): Promise<void> {
    const candles = this.candles.get(symbol)
    const indicators = this.indicators.get(symbol)
    
    if (!candles || !indicators || candles.length < 50) return
    
    // Generate signal
    const signal = generateSignal(candles, indicators, candles.length - 1)
    
    if (signal.action === 'HOLD' || signal.confidence < 0.5) return
    
    // Check if we already have a position
    const existingPosition = this.portfolio.positions.find(p => p.symbol === symbol)
    
    if (existingPosition) {
      // Check if we should reverse
      if ((existingPosition.side === 'long' && signal.action === 'SELL') ||
          (existingPosition.side === 'short' && signal.action === 'BUY')) {
        this.closePosition(existingPosition, currentPrice, 'Signal Reversal')
      }
      return
    }
    
    // Check if we can open a new position
    if (this.portfolio.positions.length >= this.config.maxConcurrentPositions) {
      return
    }
    
    // Calculate position size
    const riskAmount = this.portfolio.equity * this.config.riskPerTrade
    const stopDistance = currentPrice * this.config.stopLossPercent
    const positionSize = riskAmount / stopDistance
    const positionValue = positionSize * currentPrice
    
    const maxPositionValue = this.portfolio.balance * this.config.maxPositionSize
    const actualPositionValue = Math.min(positionValue, maxPositionValue)
    
    if (actualPositionValue < 100) return // Minimum position value
    
    // Simulate realistic entry fill
    const orderSide = signal.action === 'BUY' ? 'buy' : 'sell'
    const volatility = getVolatilityFromCandles(candles)
    
    const fill = simulateOrderFillWithTiming(
      actualPositionValue,
      orderSide,
      currentPrice,
      Date.now(),
      undefined, // Order book not available
      candles,
      'market',
      this.executionConfig
    )
    
    // Create position
    const side = signal.action === 'BUY' ? 'long' : 'short'
    const position: PaperPosition = {
      id: `paper-${symbol}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      symbol,
      side,
      entryPrice: fill.fillPrice,
      entryTime: Date.now(),
      size: fill.fillSize,
      stopLoss: side === 'long'
        ? fill.fillPrice * (1 - this.config.stopLossPercent)
        : fill.fillPrice * (1 + this.config.stopLossPercent),
      takeProfit: side === 'long'
        ? fill.fillPrice * (1 + this.config.takeProfitPercent)
        : fill.fillPrice * (1 - this.config.takeProfitPercent),
      pnl: -fill.fees - fill.spreadCost,
      pnlPercent: 0,
    }
    
    // Update portfolio
    this.portfolio.balance -= fill.totalCost
    this.portfolio.positions.push(position)
  }

  /**
   * Close a position
   */
  private closePosition(position: PaperPosition, exitPrice: number, reason: string): void {
    const candles = this.candles.get(position.symbol) || []
    const volatility = getVolatilityFromCandles(candles)
    
    // Simulate realistic exit fill
    const orderSide = position.side === 'long' ? 'sell' : 'buy'
    const exitValue = position.size * exitPrice
    
    const fill = simulateOrderFillWithTiming(
      exitValue,
      orderSide,
      exitPrice,
      Date.now(),
      undefined,
      candles,
      'market',
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
    
    // Apply exit costs
    const exitCosts = fill.fees + fill.spreadCost
    pnl -= exitCosts
    
    // Record trade
    const trade: PaperTrade = {
      id: position.id,
      symbol: position.symbol,
      side: position.side,
      entryPrice: position.entryPrice,
      entryTime: position.entryTime,
      exitPrice: actualExitPrice,
      exitTime: Date.now(),
      size: position.size,
      pnl,
      pnlPercent: pnl / (position.entryPrice * position.size),
      fees: exitCosts + (position.entryPrice * position.size * this.executionConfig.tradingFee),
      slippage: fill.slippage,
      reason,
    }
    
    this.trades.push(trade)
    
    // Update portfolio
    this.portfolio.balance += exitValue - exitCosts
    this.portfolio.totalPnl += pnl
    
    // Remove position
    const index = this.portfolio.positions.findIndex(p => p.id === position.id)
    if (index >= 0) {
      this.portfolio.positions.splice(index, 1)
    }
    
    // Notify callback
    this.onTrade?.(trade)
  }

  /**
   * Update portfolio equity
   */
  private updatePortfolio(): void {
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
  }

  /**
   * Get current portfolio state
   */
  getPortfolio(): PaperPortfolio {
    return { ...this.portfolio }
  }

  /**
   * Get trade history
   */
  getTrades(): PaperTrade[] {
    return [...this.trades]
  }

  /**
   * Get current positions
   */
  getPositions(): PaperPosition[] {
    return [...this.portfolio.positions]
  }

  /**
   * Reset portfolio
   */
  reset(): void {
    this.stop()
    this.portfolio = this.createInitialPortfolio()
    this.trades = []
    this.candles.clear()
    this.indicators.clear()
  }
}

// Singleton instance
let paperTradingInstance: PaperTradingEngine | null = null

export function getPaperTradingEngine(): PaperTradingEngine {
  if (!paperTradingInstance) {
    paperTradingInstance = new PaperTradingEngine()
  }
  return paperTradingInstance
}

