/**
 * Technical Indicators Library
 * 
 * Comprehensive technical analysis indicators for trading.
 * Based on patterns from TradeSyS-Demo and magic-beta.
 */

import { OHLCV } from './backtest-data'

export interface IndicatorResult {
  timestamp: number
  value: number
}

export interface MACDResult {
  timestamp: number
  macd: number
  signal: number
  histogram: number
}

export interface BollingerBandsResult {
  timestamp: number
  upper: number
  middle: number
  lower: number
  width: number
  percentB: number
}

export interface StochResult {
  timestamp: number
  k: number
  d: number
}

export interface ATRResult {
  timestamp: number
  atr: number
  atrPercent: number
}

export interface TechnicalIndicators {
  rsi: number[]
  macd: MACDResult[]
  ema20: number[]
  ema50: number[]
  sma20: number[]
  sma50: number[]
  bb: BollingerBandsResult[]
  atr: ATRResult[]
  stoch: StochResult[]
  adx: number[]
  volume: number[]
  volumeMA: number[]
}

/**
 * Calculate Simple Moving Average (SMA)
 */
export function calculateSMA(data: number[], period: number): number[] {
  const result: number[] = []
  
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(NaN)
    } else {
      const slice = data.slice(i - period + 1, i + 1)
      const sum = slice.reduce((a, b) => a + b, 0)
      result.push(sum / period)
    }
  }
  
  return result
}

/**
 * Calculate Exponential Moving Average (EMA)
 */
export function calculateEMA(data: number[], period: number): number[] {
  const result: number[] = []
  const multiplier = 2 / (period + 1)
  
  // First EMA is the SMA
  let ema = data.slice(0, period).reduce((a, b) => a + b, 0) / period
  
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(NaN)
    } else if (i === period - 1) {
      result.push(ema)
    } else {
      ema = (data[i] - ema) * multiplier + ema
      result.push(ema)
    }
  }
  
  return result
}

/**
 * Calculate Relative Strength Index (RSI)
 */
export function calculateRSI(candles: OHLCV[], period: number = 14): number[] {
  const closes = candles.map(c => c.close)
  const result: number[] = []
  
  // Calculate price changes
  const changes: number[] = []
  for (let i = 1; i < closes.length; i++) {
    changes.push(closes[i] - closes[i - 1])
  }
  
  // Initialize gains and losses
  let avgGain = 0
  let avgLoss = 0
  
  for (let i = 0; i < changes.length; i++) {
    if (i < period) {
      result.push(50) // Neutral during warmup
      if (i === period - 1) {
        // Calculate initial average
        let gains = 0, losses = 0
        for (let j = 0; j < period; j++) {
          if (changes[j] > 0) gains += changes[j]
          else losses -= changes[j]
        }
        avgGain = gains / period
        avgLoss = losses / period
      }
    } else {
      // Smoothed RS
      const gain = changes[i] > 0 ? changes[i] : 0
      const loss = changes[i] < 0 ? -changes[i] : 0
      
      avgGain = (avgGain * (period - 1) + gain) / period
      avgLoss = (avgLoss * (period - 1) + loss) / period
      
      if (avgLoss === 0) {
        result.push(100)
      } else {
        const rs = avgGain / avgLoss
        result.push(100 - (100 / (1 + rs)))
      }
    }
  }
  
  // Pad the beginning
  result.unshift(50)
  
  return result
}

/**
 * Calculate MACD (Moving Average Convergence Divergence)
 */
export function calculateMACD(
  candles: OHLCV[],
  fastPeriod: number = 12,
  slowPeriod: number = 26,
  signalPeriod: number = 9
): MACDResult[] {
  const closes = candles.map(c => c.close)
  const fastEMA = calculateEMA(closes, fastPeriod)
  const slowEMA = calculateEMA(closes, slowPeriod)
  
  // Calculate MACD line
  const macdLine: number[] = []
  for (let i = 0; i < closes.length; i++) {
    if (isNaN(fastEMA[i]) || isNaN(slowEMA[i])) {
      macdLine.push(0)
    } else {
      macdLine.push(fastEMA[i] - slowEMA[i])
    }
  }
  
  // Calculate Signal line
  const signalLine = calculateEMA(macdLine, signalPeriod)
  
  // Build results
  return candles.map((candle, i) => ({
    timestamp: candle.timestamp,
    macd: macdLine[i] || 0,
    signal: signalLine[i] || 0,
    histogram: (macdLine[i] || 0) - (signalLine[i] || 0),
  }))
}

/**
 * Calculate Bollinger Bands
 */
export function calculateBollingerBands(
  candles: OHLCV[],
  period: number = 20,
  stdDev: number = 2
): BollingerBandsResult[] {
  const closes = candles.map(c => c.close)
  const sma = calculateSMA(closes, period)
  
  return candles.map((candle, i) => {
    if (i < period - 1 || isNaN(sma[i])) {
      return {
        timestamp: candle.timestamp,
        upper: candle.close * 1.02,
        middle: candle.close,
        lower: candle.close * 0.98,
        width: 0.04,
        percentB: 0.5,
      }
    }
    
    // Calculate standard deviation
    const slice = closes.slice(i - period + 1, i + 1)
    const mean = sma[i]
    const variance = slice.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / period
    const std = Math.sqrt(variance)
    
    const upper = mean + (std * stdDev)
    const lower = mean - (std * stdDev)
    const width = (upper - lower) / mean
    const percentB = (candle.close - lower) / (upper - lower)
    
    return {
      timestamp: candle.timestamp,
      upper,
      middle: mean,
      lower,
      width,
      percentB,
    }
  })
}

/**
 * Calculate Average True Range (ATR)
 */
export function calculateATR(candles: OHLCV[], period: number = 14): ATRResult[] {
  const trueRanges: number[] = []
  
  for (let i = 0; i < candles.length; i++) {
    if (i === 0) {
      trueRanges.push(candles[i].high - candles[i].low)
    } else {
      const tr = Math.max(
        candles[i].high - candles[i].low,
        Math.abs(candles[i].high - candles[i - 1].close),
        Math.abs(candles[i].low - candles[i - 1].close)
      )
      trueRanges.push(tr)
    }
  }
  
  const atrValues = calculateEMA(trueRanges, period)
  
  return candles.map((candle, i) => ({
    timestamp: candle.timestamp,
    atr: atrValues[i] || trueRanges[i],
    atrPercent: (atrValues[i] || trueRanges[i]) / candle.close * 100,
  }))
}

/**
 * Calculate Stochastic Oscillator
 */
export function calculateStochastic(
  candles: OHLCV[],
  kPeriod: number = 14,
  dPeriod: number = 3
): StochResult[] {
  const kValues: number[] = []
  
  for (let i = 0; i < candles.length; i++) {
    if (i < kPeriod - 1) {
      kValues.push(50)
    } else {
      const slice = candles.slice(i - kPeriod + 1, i + 1)
      const highest = Math.max(...slice.map(c => c.high))
      const lowest = Math.min(...slice.map(c => c.low))
      
      if (highest === lowest) {
        kValues.push(50)
      } else {
        const k = ((candles[i].close - lowest) / (highest - lowest)) * 100
        kValues.push(k)
      }
    }
  }
  
  const dValues = calculateSMA(kValues, dPeriod)
  
  return candles.map((candle, i) => ({
    timestamp: candle.timestamp,
    k: kValues[i],
    d: dValues[i] || kValues[i],
  }))
}

/**
 * Calculate ADX (Average Directional Index)
 */
export function calculateADX(candles: OHLCV[], period: number = 14): number[] {
  const plusDM: number[] = []
  const minusDM: number[] = []
  const tr: number[] = []
  
  for (let i = 0; i < candles.length; i++) {
    if (i === 0) {
      plusDM.push(0)
      minusDM.push(0)
      tr.push(candles[i].high - candles[i].low)
    } else {
      const upMove = candles[i].high - candles[i - 1].high
      const downMove = candles[i - 1].low - candles[i].low
      
      plusDM.push(upMove > downMove && upMove > 0 ? upMove : 0)
      minusDM.push(downMove > upMove && downMove > 0 ? downMove : 0)
      
      tr.push(Math.max(
        candles[i].high - candles[i].low,
        Math.abs(candles[i].high - candles[i - 1].close),
        Math.abs(candles[i].low - candles[i - 1].close)
      ))
    }
  }
  
  const smoothedTR = calculateEMA(tr, period)
  const smoothedPlusDM = calculateEMA(plusDM, period)
  const smoothedMinusDM = calculateEMA(minusDM, period)
  
  const plusDI: number[] = []
  const minusDI: number[] = []
  const dx: number[] = []
  
  for (let i = 0; i < candles.length; i++) {
    if (smoothedTR[i] === 0 || isNaN(smoothedTR[i])) {
      plusDI.push(0)
      minusDI.push(0)
      dx.push(0)
    } else {
      const pdi = (smoothedPlusDM[i] / smoothedTR[i]) * 100
      const mdi = (smoothedMinusDM[i] / smoothedTR[i]) * 100
      plusDI.push(pdi)
      minusDI.push(mdi)
      
      const diSum = pdi + mdi
      dx.push(diSum === 0 ? 0 : (Math.abs(pdi - mdi) / diSum) * 100)
    }
  }
  
  return calculateEMA(dx, period)
}

/**
 * Calculate Volume Moving Average
 */
export function calculateVolumeMA(candles: OHLCV[], period: number = 20): number[] {
  const volumes = candles.map(c => c.volume)
  return calculateSMA(volumes, period)
}

/**
 * Calculate all technical indicators for a dataset
 */
export function calculateAllIndicators(candles: OHLCV[]): TechnicalIndicators {
  const closes = candles.map(c => c.close)
  
  return {
    rsi: calculateRSI(candles, 14),
    macd: calculateMACD(candles, 12, 26, 9),
    ema20: calculateEMA(closes, 20),
    ema50: calculateEMA(closes, 50),
    sma20: calculateSMA(closes, 20),
    sma50: calculateSMA(closes, 50),
    bb: calculateBollingerBands(candles, 20, 2),
    atr: calculateATR(candles, 14),
    stoch: calculateStochastic(candles, 14, 3),
    adx: calculateADX(candles, 14),
    volume: candles.map(c => c.volume),
    volumeMA: calculateVolumeMA(candles, 20),
  }
}

/**
 * Generate trading signal based on multiple indicators
 */
export interface TradingSignal {
  action: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  reasons: string[]
  indicators: {
    rsi: number
    macd: { macd: number; signal: number; histogram: number }
    bbPosition: number
    trend: 'bullish' | 'bearish' | 'neutral'
    momentum: number
    volatility: number
  }
}

export function generateSignal(
  candles: OHLCV[],
  indicators: TechnicalIndicators,
  index: number
): TradingSignal {
  const reasons: string[] = []
  let bullishScore = 0
  let bearishScore = 0
  
  const rsi = indicators.rsi[index] || 50
  const macd = indicators.macd[index]
  const bb = indicators.bb[index]
  const stoch = indicators.stoch[index]
  const adx = indicators.adx[index] || 25
  
  // RSI signals
  if (rsi < 30) {
    bullishScore += 2
    reasons.push('RSI oversold')
  } else if (rsi > 70) {
    bearishScore += 2
    reasons.push('RSI overbought')
  } else if (rsi < 45) {
    bullishScore += 1
  } else if (rsi > 55) {
    bearishScore += 1
  }
  
  // MACD signals
  if (macd) {
    if (macd.histogram > 0 && macd.macd > macd.signal) {
      bullishScore += 2
      reasons.push('MACD bullish crossover')
    } else if (macd.histogram < 0 && macd.macd < macd.signal) {
      bearishScore += 2
      reasons.push('MACD bearish crossover')
    }
  }
  
  // Bollinger Bands signals
  if (bb) {
    if (bb.percentB < 0.1) {
      bullishScore += 2
      reasons.push('Price at lower BB')
    } else if (bb.percentB > 0.9) {
      bearishScore += 2
      reasons.push('Price at upper BB')
    }
  }
  
  // Stochastic signals
  if (stoch) {
    if (stoch.k < 20 && stoch.d < 20) {
      bullishScore += 1
      reasons.push('Stochastic oversold')
    } else if (stoch.k > 80 && stoch.d > 80) {
      bearishScore += 1
      reasons.push('Stochastic overbought')
    }
  }
  
  // Trend confirmation with ADX
  const trendStrength = adx > 25 ? 'strong' : 'weak'
  
  // EMA trend
  const ema20 = indicators.ema20[index]
  const ema50 = indicators.ema50[index]
  const currentPrice = candles[index]?.close || 0
  
  let trend: 'bullish' | 'bearish' | 'neutral' = 'neutral'
  if (ema20 > ema50 && currentPrice > ema20) {
    trend = 'bullish'
    bullishScore += 1
  } else if (ema20 < ema50 && currentPrice < ema20) {
    trend = 'bearish'
    bearishScore += 1
  }
  
  // Calculate final signal
  const totalScore = bullishScore + bearishScore
  const netScore = bullishScore - bearishScore
  const confidence = totalScore > 0 ? Math.abs(netScore) / totalScore : 0
  
  let action: 'BUY' | 'SELL' | 'HOLD' = 'HOLD'
  if (netScore >= 3 && confidence >= 0.5) {
    action = 'BUY'
  } else if (netScore <= -3 && confidence >= 0.5) {
    action = 'SELL'
  }
  
  // Volume confirmation
  const volume = indicators.volume[index] || 0
  const volumeMA = indicators.volumeMA[index] || volume
  if (volume < volumeMA * 0.7 && action !== 'HOLD') {
    action = 'HOLD'
    reasons.push('Low volume - signal weakened')
  }
  
  return {
    action,
    confidence: Math.min(confidence, 1),
    reasons,
    indicators: {
      rsi,
      macd: macd || { macd: 0, signal: 0, histogram: 0 },
      bbPosition: bb?.percentB || 0.5,
      trend,
      momentum: netScore / 10,
      volatility: bb?.width || 0.02,
    },
  }
}

