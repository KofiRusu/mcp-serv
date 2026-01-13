/**
 * CCXT Client - Real-Time Market Data via API
 * 
 * Fetches live market data from Binance via our API endpoint.
 * The API uses CCXT server-side to get real-time prices.
 */

// =============================================================================
// Types
// =============================================================================

export interface Candle {
  timestamp: number
  time?: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface Ticker {
  symbol: string
  last: number
  bid: number
  ask: number
  high: number
  low: number
  volume: number
  change: number
  percentage: number
  timestamp: number
}

export interface OrderBookEntry {
  price: number
  amount: number
  size?: number
}

export interface OrderBook {
  symbol: string
  bids: OrderBookEntry[]
  asks: OrderBookEntry[]
  timestamp: number
}

export interface Trade {
  id: string
  timestamp: number
  symbol: string
  side: 'buy' | 'sell'
  price: number
  amount: number
}

// =============================================================================
// API Client
// =============================================================================

const API_BASE = '/api/market'

// Cache for prices
let priceCache: { prices: Record<string, number>; timestamp: number } | null = null
const PRICE_CACHE_DURATION = 10000 // 10 seconds

async function fetchFromAPI(action: string, params: Record<string, string> = {}): Promise<any> {
  const searchParams = new URLSearchParams({ action, ...params })
  const response = await fetch(`${API_BASE}?${searchParams}`)
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `API error: ${response.status}`)
  }
  
  return response.json()
}

// =============================================================================
// CCXT Client Class
// =============================================================================

class CCXTClient {
  private candleCache: Map<string, { candles: Candle[]; timestamp: number }> = new Map()
  
  /**
   * Get all live prices
   */
  async fetchPrices(): Promise<Record<string, number>> {
    // Return cached prices if still valid
    if (priceCache && Date.now() - priceCache.timestamp < PRICE_CACHE_DURATION) {
      return priceCache.prices
    }

    try {
      const data = await fetchFromAPI('prices')
      priceCache = { prices: data.prices, timestamp: Date.now() }
      return data.prices
    } catch (error) {
      console.error('Failed to fetch prices:', error)
      // Return cached if available
      return priceCache?.prices || {}
    }
  }
  
  /**
   * Fetch OHLCV candlestick data
   */
  async fetchOHLCV(symbol: string, timeframe: string = '1h', limit: number = 100): Promise<Candle[]> {
    const cacheKey = `${symbol}-${timeframe}`
    const cached = this.candleCache.get(cacheKey)
    
    // Return cached data if less than 30 seconds old
    if (cached && Date.now() - cached.timestamp < 30000) {
      return cached.candles
    }
    
    try {
      const data = await fetchFromAPI('ohlcv', { symbol, timeframe, limit: limit.toString() })
      
      const candles = data.candles.map((c: any) => ({
        timestamp: c.time || c.timestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
        volume: c.volume,
      }))
      
      // Update cache
      this.candleCache.set(cacheKey, { candles, timestamp: Date.now() })
      
      return candles
    } catch (error) {
      console.error(`Failed to fetch OHLCV for ${symbol}:`, error)
      // Return cached if available
      return cached?.candles || []
    }
  }
  
  /**
   * Fetch current ticker data
   */
  async fetchTicker(symbol: string): Promise<Ticker> {
    try {
      const data = await fetchFromAPI('ticker', { symbol })
      
      return {
        symbol: data.symbol,
        last: data.last,
        bid: data.bid,
        ask: data.ask,
        high: data.high,
        low: data.low,
        volume: data.volume,
        change: data.change,
        percentage: data.percentage,
        timestamp: data.timestamp,
      }
    } catch (error) {
      console.error(`Failed to fetch ticker for ${symbol}:`, error)
      throw error
    }
  }
  
  /**
   * Fetch order book
   */
  async fetchOrderBook(symbol: string, limit: number = 20): Promise<OrderBook> {
    try {
      const data = await fetchFromAPI('orderbook', { symbol, limit: limit.toString() })
      
      return {
        symbol,
        bids: data.bids.map((b: any) => ({ price: b.price, amount: b.size || b.amount })),
        asks: data.asks.map((a: any) => ({ price: a.price, amount: a.size || a.amount })),
        timestamp: data.timestamp,
      }
    } catch (error) {
      console.error(`Failed to fetch order book for ${symbol}:`, error)
      throw error
    }
  }
  
  /**
   * Fetch recent trades
   */
  async fetchTrades(symbol: string, limit: number = 50): Promise<Trade[]> {
    try {
      const data = await fetchFromAPI('trades', { symbol, limit: limit.toString() })
      
      return data.trades.map((t: any) => ({
        id: t.id,
        timestamp: t.timestamp,
        symbol,
        side: t.side,
        price: t.price,
        amount: t.amount,
      }))
    } catch (error) {
      console.error(`Failed to fetch trades for ${symbol}:`, error)
      throw error
    }
  }

  /**
   * Fetch markets with prices
   */
  async fetchMarkets(): Promise<any[]> {
    try {
      const data = await fetchFromAPI('markets')
      return data.markets
    } catch (error) {
      console.error('Failed to fetch markets:', error)
      throw error
    }
  }
}

// =============================================================================
// Export Singleton Instance
// =============================================================================

export const ccxtClient = new CCXTClient()
