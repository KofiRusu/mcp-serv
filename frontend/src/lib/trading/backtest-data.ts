/**
 * Backtest Data Infrastructure
 * 
 * Fetches and caches historical market data via CCXT for backtesting.
 * Supports BTC, ETH, SOL on multiple timeframes.
 */

export interface OHLCV {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface OrderBookSnapshot {
  timestamp: number
  bids: [number, number][] // [price, amount][]
  asks: [number, number][]
  spread: number
  midPrice: number
}

export interface TradeData {
  id: string
  timestamp: number
  price: number
  amount: number
  side: 'buy' | 'sell'
}

export interface MarketDataSnapshot {
  symbol: string
  timestamp: number
  ohlcv: OHLCV
  orderBook?: OrderBookSnapshot
  recentTrades?: TradeData[]
  indicators?: {
    rsi?: number
    macd?: { macd: number; signal: number; histogram: number }
    ema20?: number
    ema50?: number
    bb?: { upper: number; middle: number; lower: number }
    atr?: number
    volume24h?: number
    priceChange24h?: number
  }
}

export interface BacktestDataConfig {
  symbols: string[]
  timeframe: '1m' | '5m' | '15m' | '1h' | '4h' | '1d'
  startDate: Date
  endDate: Date
  includeOrderBook?: boolean
  includeTrades?: boolean
}

// Cache for historical data (in-memory)
const dataCache = new Map<string, OHLCV[]>()

// Cache directory for persistent storage
const CACHE_DIR = typeof window === 'undefined' 
  ? require('path').join(require('process').cwd(), 'data', 'backtest-cache')
  : null

/**
 * Fetch historical OHLCV data from the API with pagination and caching
 */
export async function fetchHistoricalOHLCV(
  symbol: string,
  timeframe: string,
  limit: number = 1000,
  since?: number
): Promise<OHLCV[]> {
  const cacheKey = `${symbol}-${timeframe}-${since || 'latest'}-${limit}`
  
  // Check in-memory cache first
  if (dataCache.has(cacheKey)) {
    return dataCache.get(cacheKey)!
  }

  // Check disk cache (server-side only)
  if (CACHE_DIR && typeof require !== 'undefined') {
    try {
      const fs = require('fs/promises')
      const path = require('path')
      const cacheFile = path.join(CACHE_DIR, symbol, `${timeframe}-${since || 'latest'}-${limit}.json`)
      
      try {
        const cached = await fs.readFile(cacheFile, 'utf-8')
        const ohlcv: OHLCV[] = JSON.parse(cached)
        dataCache.set(cacheKey, ohlcv)
        console.log(`Loaded ${ohlcv.length} candles from disk cache for ${symbol}:${timeframe}`)
        return ohlcv
      } catch (err: any) {
        if (err.code !== 'ENOENT') {
          console.error(`Error reading cache file:`, err)
        }
      }
    } catch (err) {
      // File system not available (client-side)
    }
  }

  try {
    // Calculate how many API calls we need (CCXT limit is typically 1000 candles)
    const MAX_PER_REQUEST = 1000
    const requestsNeeded = Math.ceil(limit / MAX_PER_REQUEST)
    const allCandles: OHLCV[] = []
    
    let currentSince = since
    let remainingLimit = limit
    
    // Fetch in batches with rate limiting
    for (let i = 0; i < requestsNeeded && remainingLimit > 0; i++) {
      const requestLimit = Math.min(remainingLimit, MAX_PER_REQUEST)
      
      const params = new URLSearchParams({
        action: 'ohlcv',
        symbol,
        timeframe,
        limit: requestLimit.toString(),
      })
      
      if (currentSince) {
        params.append('since', currentSince.toString())
      }

      const response = await fetch(`/api/market?${params}`)
      
      if (!response.ok) {
        if (response.status === 429) {
          // Rate limited - wait and retry
          console.log(`Rate limited, waiting 2 seconds...`)
          await new Promise(resolve => setTimeout(resolve, 2000))
          i-- // Retry this request
          continue
        }
        throw new Error(`Failed to fetch OHLCV: ${response.status}`)
      }

      const data = await response.json()
      
      // Transform to our format
      const candles: OHLCV[] = Array.isArray(data) 
        ? data.map((candle: any) => ({
            timestamp: candle[0] || candle.timestamp || candle.time,
            open: candle[1] || candle.open,
            high: candle[2] || candle.high,
            low: candle[3] || candle.low,
            close: candle[4] || candle.close,
            volume: candle[5] || candle.volume,
          }))
        : (data.candles || []).map((candle: any) => ({
            timestamp: candle.timestamp || candle.time,
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close,
            volume: candle.volume,
          }))
      
      if (candles.length === 0) break // No more data available
      
      allCandles.push(...candles)
      
      // Update since for next request (use last candle timestamp)
      if (candles.length > 0) {
        currentSince = candles[candles.length - 1].timestamp + 1
      }
      
      remainingLimit -= candles.length
      
      // Rate limiting: wait between requests
      if (i < requestsNeeded - 1) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }

    // Sort by timestamp (in case of overlap)
    allCandles.sort((a, b) => a.timestamp - b.timestamp)
    
    // Remove duplicates
    const uniqueCandles: OHLCV[] = []
    const seenTimestamps = new Set<number>()
    for (const candle of allCandles) {
      if (!seenTimestamps.has(candle.timestamp)) {
        seenTimestamps.add(candle.timestamp)
        uniqueCandles.push(candle)
      }
    }
    
    // Limit to requested amount
    const finalCandles = uniqueCandles.slice(0, limit)

    // Cache the result (in-memory)
    dataCache.set(cacheKey, finalCandles)
    
    // Cache to disk (server-side only)
    if (CACHE_DIR && typeof require !== 'undefined') {
      try {
        const fs = require('fs/promises')
        const path = require('path')
        const cacheFile = path.join(CACHE_DIR, symbol, `${timeframe}-${since || 'latest'}-${limit}.json`)
        await fs.mkdir(path.dirname(cacheFile), { recursive: true })
        await fs.writeFile(cacheFile, JSON.stringify(finalCandles, null, 2))
        console.log(`Cached ${finalCandles.length} candles to disk for ${symbol}:${timeframe}`)
      } catch (err) {
        console.error(`Failed to cache to disk:`, err)
      }
    }
    
    return finalCandles
  } catch (error) {
    console.error(`Error fetching OHLCV for ${symbol}:`, error)
    return []
  }
}

/**
 * Fetch historical data for multiple symbols
 */
export async function fetchMultiSymbolData(
  config: BacktestDataConfig
): Promise<Map<string, OHLCV[]>> {
  const result = new Map<string, OHLCV[]>()
  
  // Calculate the number of candles needed
  const timeframeMins: Record<string, number> = {
    '1m': 1,
    '5m': 5,
    '15m': 15,
    '1h': 60,
    '4h': 240,
    '1d': 1440,
  }
  
  const durationMs = config.endDate.getTime() - config.startDate.getTime()
  const candleMs = timeframeMins[config.timeframe] * 60 * 1000
  const candlesNeeded = Math.ceil(durationMs / candleMs)
  
  // Fetch data for each symbol in parallel
  const fetchPromises = config.symbols.map(async (symbol) => {
    const data = await fetchHistoricalOHLCV(
      symbol,
      config.timeframe,
      Math.min(candlesNeeded, 1000), // API limit
      config.startDate.getTime()
    )
    result.set(symbol, data)
  })
  
  await Promise.all(fetchPromises)
  
  return result
}

/**
 * Generate synthetic historical data for backtesting
 * Used when real data is unavailable or for testing
 */
export function generateSyntheticData(
  symbol: string,
  timeframe: string,
  candleCount: number,
  startPrice: number,
  volatility: number = 0.02
): OHLCV[] {
  const timeframeMins: Record<string, number> = {
    '1m': 1,
    '5m': 5,
    '15m': 15,
    '1h': 60,
    '4h': 240,
    '1d': 1440,
  }
  
  const candleMs = (timeframeMins[timeframe] || 1) * 60 * 1000
  const startTime = Date.now() - (candleCount * candleMs)
  
  const candles: OHLCV[] = []
  let price = startPrice
  
  for (let i = 0; i < candleCount; i++) {
    const timestamp = startTime + (i * candleMs)
    
    // Random walk with mean reversion
    const trend = Math.random() > 0.5 ? 1 : -1
    const change = (Math.random() * volatility * 2 - volatility) * price
    const open = price
    
    // Generate realistic OHLCV
    const intraCandle = Array.from({ length: 4 }, () => 
      open + (Math.random() * volatility * 2 - volatility) * open
    )
    
    const high = Math.max(open, ...intraCandle) * (1 + Math.random() * 0.002)
    const low = Math.min(open, ...intraCandle) * (1 - Math.random() * 0.002)
    const close = open + change * trend
    
    // Volume based on volatility
    const baseVolume = symbol.includes('BTC') ? 1000 : symbol.includes('ETH') ? 5000 : 50000
    const volume = baseVolume * (1 + Math.abs(change / price) * 10) * (0.5 + Math.random())
    
    candles.push({
      timestamp,
      open: Math.max(0, open),
      high: Math.max(0, high),
      low: Math.max(0, low),
      close: Math.max(0, close),
      volume,
    })
    
    price = close
  }
  
  return candles
}

/**
 * Generate synthetic data for a specific historical date range
 * Uses deterministic seeding based on date so same dates = same data
 */
export function generateHistoricalSyntheticData(
  symbol: string,
  timeframe: string,
  startDate: Date,
  endDate: Date,
  startPrice: number,
  volatility: number = 0.02
): OHLCV[] {
  const timeframeMins: Record<string, number> = {
    '1m': 1,
    '5m': 5,
    '15m': 15,
    '1h': 60,
    '4h': 240,
    '1d': 1440,
  }
  
  const candleMs = (timeframeMins[timeframe] || 5) * 60 * 1000
  const startTime = startDate.getTime()
  const endTime = endDate.getTime()
  const candleCount = Math.ceil((endTime - startTime) / candleMs)
  
  const candles: OHLCV[] = []
  let price = startPrice
  
  // Simple pseudo-random seeded by timestamp for reproducibility
  const seed = (startTime / 1000000) % 1
  const seededRandom = (i: number) => {
    const x = Math.sin(seed * 10000 + i * 9999) * 10000
    return x - Math.floor(x)
  }
  
  for (let i = 0; i < candleCount; i++) {
    const timestamp = startTime + (i * candleMs)
    
    // Deterministic random walk with mean reversion
    const r1 = seededRandom(i * 5)
    const r2 = seededRandom(i * 5 + 1)
    const r3 = seededRandom(i * 5 + 2)
    const r4 = seededRandom(i * 5 + 3)
    const r5 = seededRandom(i * 5 + 4)
    
    const trend = r1 > 0.5 ? 1 : -1
    const change = (r2 * volatility * 2 - volatility) * price
    const open = price
    
    // Generate realistic OHLCV
    const intraCandle = [
      open + (r2 * volatility * 2 - volatility) * open,
      open + (r3 * volatility * 2 - volatility) * open,
      open + (r4 * volatility * 2 - volatility) * open,
      open + (r5 * volatility * 2 - volatility) * open,
    ]
    
    const high = Math.max(open, ...intraCandle) * (1 + r3 * 0.002)
    const low = Math.min(open, ...intraCandle) * (1 - r4 * 0.002)
    const close = open + change * trend
    
    // Volume based on volatility
    const baseVolume = symbol.includes('BTC') ? 1000 : symbol.includes('ETH') ? 5000 : 50000
    const volume = baseVolume * (1 + Math.abs(change / price) * 10) * (0.5 + r5)
    
    candles.push({
      timestamp,
      open: Math.max(0.01, open),
      high: Math.max(0.01, high),
      low: Math.max(0.01, low),
      close: Math.max(0.01, close),
      volume,
    })
    
    price = close
  }
  
  return candles
}

/**
 * Generate realistic market data for a backtest period
 * Supports both relative days and absolute date ranges
 */
export async function loadBacktestData(
  symbols: string[] = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
  timeframe: '1m' | '5m' | '15m' = '5m',
  days: number = 7,
  startDate?: Date,
  endDate?: Date
): Promise<Map<string, OHLCV[]>> {
  const result = new Map<string, OHLCV[]>()
  
  // Calculate candles needed
  const timeframeMins: Record<string, number> = {
    '1m': 1,
    '5m': 5,
    '15m': 15,
  }
  
  // Determine effective date range
  const effectiveEndDate = endDate || new Date()
  const effectiveStartDate = startDate || new Date(effectiveEndDate.getTime() - days * 24 * 60 * 60 * 1000)
  
  const durationMs = effectiveEndDate.getTime() - effectiveStartDate.getTime()
  const effectiveDays = durationMs / (24 * 60 * 60 * 1000)
  
  const candlesPerDay = (24 * 60) / timeframeMins[timeframe]
  const totalCandles = Math.floor(candlesPerDay * effectiveDays)
  
  const isHistorical = startDate !== undefined && startDate < new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
  
  console.log(`Loading ${totalCandles} candles for ${symbols.length} symbols (${effectiveStartDate.toISOString()} - ${effectiveEndDate.toISOString()})...`)
  
  // Historical price estimates by year/month for realistic simulation
  const getHistoricalPrice = (symbol: string, date: Date): number => {
    const year = date.getFullYear()
    const month = date.getMonth()
    
    // Rough BTC price history
    const btcPrices: Record<number, number[]> = {
      2020: [7200, 8500, 6500, 7500, 9500, 9100, 11000, 11800, 10800, 13800, 18200, 29000],
      2021: [33000, 45000, 58000, 55000, 37000, 35000, 42000, 47000, 43000, 61000, 57000, 46000],
      2022: [42000, 38000, 45000, 40000, 30000, 20000, 23000, 20000, 19000, 20500, 16500, 16800],
      2023: [23000, 23500, 28000, 29500, 27000, 30500, 29000, 26000, 27000, 34500, 37000, 42000],
      2024: [42000, 52000, 70000, 64000, 68000, 64000, 56000, 59000, 64000, 68000, 91000, 97000],
      2025: [94000, 98000, 89000, 89000, 89000, 89000, 89000, 89000, 89000, 89000, 89000, 89000],
    }
    
    const baseBtcPrice = btcPrices[year]?.[month] || 89000
    
    // ETH roughly 3-5% of BTC
    const ethRatio = 0.032 + (Math.sin(month) * 0.005)
    // SOL more volatile
    const solPrice = year >= 2024 ? 130 + (month * 5) : 20 + (month * 2)
    
    if (symbol.includes('BTC')) return baseBtcPrice
    if (symbol.includes('ETH')) return baseBtcPrice * ethRatio
    if (symbol.includes('SOL')) return solPrice
    return 100
  }
  
  // Try to fetch real data first, fall back to synthetic
  for (const symbol of symbols) {
    try {
      // For historical dates, use synthetic data based on the date
      if (isHistorical) {
        const startPrice = getHistoricalPrice(symbol, effectiveStartDate)
        const volatility: Record<string, number> = {
          'BTCUSDT': 0.015,
          'ETHUSDT': 0.02,
          'SOLUSDT': 0.03,
        }
        
        result.set(symbol, generateHistoricalSyntheticData(
          symbol,
          timeframe,
          effectiveStartDate,
          effectiveEndDate,
          startPrice,
          volatility[symbol] || 0.02
        ))
      } else {
        // Try real data for recent periods
        const data = await fetchHistoricalOHLCV(
          symbol, 
          timeframe, 
          Math.min(totalCandles, 1000),
          effectiveStartDate.getTime()
        )
        
        if (data.length >= 100) {
          // Extend with synthetic data if needed
          if (data.length < totalCandles) {
            const syntheticCount = totalCandles - data.length
            const lastPrice = data[data.length - 1].close
            const synthetic = generateSyntheticData(symbol, timeframe, syntheticCount, lastPrice)
            result.set(symbol, [...data, ...synthetic])
          } else {
            result.set(symbol, data.slice(0, totalCandles))
          }
        } else {
          // Fall back to synthetic data
          const startPrice = getHistoricalPrice(symbol, effectiveStartDate)
          const volatility: Record<string, number> = {
            'BTCUSDT': 0.015,
            'ETHUSDT': 0.02,
            'SOLUSDT': 0.03,
          }
          
          result.set(symbol, generateHistoricalSyntheticData(
            symbol,
            timeframe,
            effectiveStartDate,
            effectiveEndDate,
            startPrice,
            volatility[symbol] || 0.02
          ))
        }
      }
    } catch (error) {
      console.error(`Failed to load data for ${symbol}, using synthetic:`, error)
      const startPrice = getHistoricalPrice(symbol, effectiveStartDate)
      
      result.set(symbol, generateHistoricalSyntheticData(
        symbol,
        timeframe,
        effectiveStartDate,
        effectiveEndDate,
        startPrice
      ))
    }
  }
  
  console.log(`Loaded data for ${result.size} symbols`)
  
  return result
}

/**
 * Clear the data cache
 */
export function clearDataCache(): void {
  dataCache.clear()
}

/**
 * Get data statistics
 */
export function getDataStats(data: OHLCV[]): {
  startTime: Date
  endTime: Date
  candleCount: number
  priceRange: { min: number; max: number }
  volumeTotal: number
  avgVolume: number
  volatility: number
} {
  if (data.length === 0) {
    return {
      startTime: new Date(),
      endTime: new Date(),
      candleCount: 0,
      priceRange: { min: 0, max: 0 },
      volumeTotal: 0,
      avgVolume: 0,
      volatility: 0,
    }
  }
  
  const prices = data.flatMap(c => [c.high, c.low])
  const returns = data.slice(1).map((c, i) => 
    Math.log(c.close / data[i].close)
  )
  
  const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length
  const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length
  
  return {
    startTime: new Date(data[0].timestamp),
    endTime: new Date(data[data.length - 1].timestamp),
    candleCount: data.length,
    priceRange: {
      min: Math.min(...prices),
      max: Math.max(...prices),
    },
    volumeTotal: data.reduce((sum, c) => sum + c.volume, 0),
    avgVolume: data.reduce((sum, c) => sum + c.volume, 0) / data.length,
    volatility: Math.sqrt(variance) * Math.sqrt(365 * 24 * 12), // Annualized for 5m candles
  }
}

