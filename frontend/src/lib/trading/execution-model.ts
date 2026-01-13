/**
 * Realistic Execution Model
 * 
 * Simulates realistic order execution with:
 * - Slippage based on order size, volatility, and order book depth
 * - Dynamic spread costs
 * - Order book depth simulation
 * - Market impact for large orders
 */

import { OHLCV } from './backtest-data'

export interface OrderBookSnapshot {
  bids: Array<[number, number]> // [price, amount][]
  asks: Array<[number, number]>
  timestamp: number
}

export interface OrderFill {
  fillPrice: number
  fillSize: number
  slippage: number // In price units (not percentage)
  slippagePercent: number
  spreadCost: number
  fees: number
  totalCost: number
}

export interface ExecutionConfig {
  tradingFee: number // Maker fee (0.001 = 0.1%)
  takerFee: number // Taker fee (usually higher)
  baseSlippage: number // Base slippage in decimal (0.0005 = 0.05%)
  volatilityMultiplier: number // How much volatility affects slippage
  orderBookDepth: number // How many levels to consider
}

const DEFAULT_CONFIG: ExecutionConfig = {
  tradingFee: 0.001, // 0.1% maker fee
  takerFee: 0.001, // 0.1% taker fee (Binance spot)
  baseSlippage: 0.0005, // 0.05% base slippage
  volatilityMultiplier: 2.0, // Volatility doubles slippage impact
  orderBookDepth: 10, // Consider top 10 levels
}

/**
 * Calculate ATR (Average True Range) for volatility estimation
 */
function calculateATR(candles: OHLCV[], period: number = 14): number {
  if (candles.length < period + 1) {
    return candles[0] ? (candles[0].high - candles[0].low) : 0
  }
  
  const trueRanges: number[] = []
  
  for (let i = candles.length - period; i < candles.length; i++) {
    if (i === 0) continue
    
    const prevClose = candles[i - 1].close
    const high = candles[i].high
    const low = candles[i].low
    
    const tr = Math.max(
      high - low,
      Math.abs(high - prevClose),
      Math.abs(low - prevClose)
    )
    
    trueRanges.push(tr)
  }
  
  return trueRanges.length > 0
    ? trueRanges.reduce((a, b) => a + b, 0) / trueRanges.length
    : 0
}

/**
 * Calculate volatility from recent candles
 */
function calculateVolatility(candles: OHLCV[], period: number = 20): number {
  if (candles.length < period) {
    return 0.02 // Default 2% volatility
  }
  
  const recentCandles = candles.slice(-period)
  const returns = recentCandles.slice(1).map((c, i) => 
    Math.log(c.close / recentCandles[i].close)
  )
  
  if (returns.length === 0) return 0.02
  
  const meanReturn = returns.reduce((a, b) => a + b, 0) / returns.length
  const variance = returns.reduce((sum, r) => 
    sum + Math.pow(r - meanReturn, 2), 0
  ) / returns.length
  
  // Annualized volatility (assuming 5m candles)
  const volatility = Math.sqrt(variance) * Math.sqrt(252 * 24 * 12)
  
  return Math.max(0.005, Math.min(0.5, volatility)) // Clamp between 0.5% and 50%
}

/**
 * Calculate slippage based on order size, volatility, and order type
 */
export function calculateSlippage(
  orderSize: number, // In quote currency (e.g., USDT)
  currentPrice: number,
  volatility: number,
  orderType: 'market' | 'limit' = 'market',
  config: ExecutionConfig = DEFAULT_CONFIG
): number {
  // Base slippage (in price units)
  let slippage = currentPrice * config.baseSlippage
  
  // Volatility adjustment (higher volatility = more slippage)
  const volatilityAdjustment = 1 + (volatility * config.volatilityMultiplier)
  slippage *= volatilityAdjustment
  
  // Order type adjustment
  if (orderType === 'limit') {
    // Limit orders have less slippage (but may not fill)
    slippage *= 0.3
  } else {
    // Market orders have full slippage
    slippage *= 1.0
  }
  
  // Order size impact (larger orders = more slippage)
  // Estimate market impact: sqrt(orderSize / averageDailyVolume)
  // For simplicity, use a power law: slippage * (orderSize / 10000) ^ 0.5
  const sizeImpact = Math.pow(Math.min(orderSize / 10000, 10), 0.5)
  slippage *= (1 + sizeImpact * 0.1) // Up to 10% additional slippage for large orders
  
  return slippage
}

/**
 * Calculate spread cost
 */
export function calculateSpreadCost(
  symbol: string,
  volatility: number,
  isMaker: boolean = false,
  config: ExecutionConfig = DEFAULT_CONFIG
): number {
  // Base spread varies by symbol
  const baseSpreads: Record<string, number> = {
    'BTCUSDT': 0.0001, // 0.01% (1 bps)
    'ETHUSDT': 0.0002, // 0.02% (2 bps)
    'SOLUSDT': 0.0005, // 0.05% (5 bps)
  }
  
  const baseSpread = baseSpreads[symbol] || 0.0003 // Default 0.03%
  
  // Volatility widens spreads
  const volatilitySpread = baseSpread * (1 + volatility * 5)
  
  // Maker orders pay maker fee, taker orders pay taker fee + spread
  if (isMaker) {
    return config.tradingFee // Just the maker fee
  } else {
    return config.takerFee + volatilitySpread // Taker fee + spread cost
  }
}

/**
 * Simulate order fill using order book depth
 */
export function simulateOrderFill(
  orderSize: number, // In quote currency
  orderSide: 'buy' | 'sell',
  currentPrice: number,
  orderBook?: OrderBookSnapshot,
  volatility: number = 0.02,
  orderType: 'market' | 'limit' = 'market',
  config: ExecutionConfig = DEFAULT_CONFIG
): OrderFill {
  // If no order book, use simplified model
  if (!orderBook || orderBook.bids.length === 0 || orderBook.asks.length === 0) {
    return simulateOrderFillSimple(orderSize, orderSide, currentPrice, volatility, orderType, config)
  }
  
  const orderBookSide = orderSide === 'buy' ? orderBook.asks : orderBook.bids
  const oppositeSide = orderSide === 'buy' ? orderBook.bids : orderBook.asks
  
  // Calculate mid price
  const bestBid = orderBook.bids[0]?.[0] || currentPrice
  const bestAsk = orderBook.asks[0]?.[0] || currentPrice
  const midPrice = (bestBid + bestAsk) / 2
  const spread = bestAsk - bestBid
  
  // Calculate how much we can fill at each level
  let remainingSize = orderSize
  let totalCost = 0
  let totalSize = 0
  let weightedPrice = 0
  
  for (const [price, amount] of orderBookSide.slice(0, config.orderBookDepth)) {
    if (remainingSize <= 0) break
    
    const levelValue = amount * price
    const fillAmount = Math.min(remainingSize, levelValue)
    const fillSize = fillAmount / price
    
    totalCost += fillAmount
    totalSize += fillSize
    weightedPrice += price * fillSize
    
    remainingSize -= fillAmount
  }
  
  // If we couldn't fill completely, estimate remaining fill at worse price
  if (remainingSize > 0) {
    const lastPrice = orderBookSide[orderBookSide.length - 1]?.[0] || currentPrice
    const slippageEstimate = calculateSlippage(remainingSize, lastPrice, volatility, orderType, config)
    const estimatedPrice = orderSide === 'buy' 
      ? lastPrice + slippageEstimate
      : lastPrice - slippageEstimate
    
    const estimatedSize = remainingSize / estimatedPrice
    totalCost += remainingSize
    totalSize += estimatedSize
    weightedPrice += estimatedPrice * estimatedSize
  }
  
  const avgFillPrice = totalSize > 0 ? weightedPrice / totalSize : currentPrice
  
  // Calculate slippage vs. mid price
  const slippage = orderSide === 'buy'
    ? avgFillPrice - midPrice
    : midPrice - avgFillPrice
  
  const slippagePercent = (slippage / midPrice) * 100
  
  // Calculate fees
  const isMaker = orderType === 'limit'
  const spreadCost = calculateSpreadCost('', volatility, isMaker, config)
  const fees = totalCost * (isMaker ? config.tradingFee : config.takerFee)
  
  return {
    fillPrice: avgFillPrice,
    fillSize: totalSize,
    slippage,
    slippagePercent,
    spreadCost: totalCost * spreadCost,
    fees,
    totalCost: totalCost + fees,
  }
}

/**
 * Simplified order fill simulation (when order book not available)
 */
function simulateOrderFillSimple(
  orderSize: number,
  orderSide: 'buy' | 'sell',
  currentPrice: number,
  volatility: number,
  orderType: 'market' | 'limit',
  config: ExecutionConfig
): OrderFill {
  // Calculate slippage
  const slippage = calculateSlippage(orderSize, currentPrice, volatility, orderType, config)
  
  // Apply slippage to fill price
  const fillPrice = orderSide === 'buy'
    ? currentPrice + slippage
    : currentPrice - slippage
  
  const fillSize = orderSize / fillPrice
  
  // Calculate costs
  const isMaker = orderType === 'limit'
  const spreadCost = calculateSpreadCost('', volatility, isMaker, config)
  const fees = orderSize * (isMaker ? config.tradingFee : config.takerFee)
  
  return {
    fillPrice,
    fillSize,
    slippage,
    slippagePercent: (slippage / currentPrice) * 100,
    spreadCost: orderSize * spreadCost,
    fees,
    totalCost: orderSize + fees,
  }
}

/**
 * Get volatility from recent candles
 */
export function getVolatilityFromCandles(
  candles: OHLCV[],
  period: number = 20
): number {
  return calculateVolatility(candles, period)
}

/**
 * Get ATR from recent candles
 */
export function getATRFromCandles(
  candles: OHLCV[],
  period: number = 14
): number {
  return calculateATR(candles, period)
}

/**
 * Estimate time-of-day liquidity factor
 * Lower liquidity = higher slippage
 */
export function getLiquidityFactor(timestamp: number): number {
  const date = new Date(timestamp)
  const hour = date.getUTCHours()
  
  // Crypto markets are most liquid during:
  // - US hours (13:00-22:00 UTC)
  // - Asian hours (00:00-09:00 UTC)
  // Less liquid during European morning (09:00-13:00 UTC)
  
  if ((hour >= 13 && hour < 22) || (hour >= 0 && hour < 9)) {
    return 1.0 // Normal liquidity
  } else {
    return 1.3 // 30% worse liquidity
  }
}

/**
 * Enhanced order fill with time-of-day adjustment
 */
export function simulateOrderFillWithTiming(
  orderSize: number,
  orderSide: 'buy' | 'sell',
  currentPrice: number,
  timestamp: number,
  orderBook?: OrderBookSnapshot,
  candles?: OHLCV[],
  orderType: 'market' | 'limit' = 'market',
  config: ExecutionConfig = DEFAULT_CONFIG
): OrderFill {
  // Get volatility from candles if available
  const volatility = candles && candles.length > 0
    ? getVolatilityFromCandles(candles)
    : 0.02 // Default 2%
  
  // Get liquidity factor
  const liquidityFactor = getLiquidityFactor(timestamp)
  
  // Adjust config for liquidity
  const adjustedConfig: ExecutionConfig = {
    ...config,
    baseSlippage: config.baseSlippage * liquidityFactor,
  }
  
  // Simulate fill
  const fill = simulateOrderFill(
    orderSize,
    orderSide,
    currentPrice,
    orderBook,
    volatility,
    orderType,
    adjustedConfig
  )
  
  return fill
}

