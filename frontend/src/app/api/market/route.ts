import { NextRequest, NextResponse } from 'next/server'

// =============================================================================
// Real-Time Market Data via CCXT
// Uses Binance public API (no auth required for market data)
// =============================================================================

// Dynamic import to avoid client-side bundling issues
let ccxtModule: any = null

async function getCCXT() {
  if (!ccxtModule) {
    ccxtModule = await import('ccxt')
  }
  return ccxtModule.default || ccxtModule
}

// Cache for price data (refresh every 10 seconds)
let priceCache: { data: Record<string, any>; timestamp: number } | null = null
const CACHE_DURATION = 10000 // 10 seconds

// Supported symbols
const SYMBOLS = [
  'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
  'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
  'MATIC/USDT', 'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'TRX/USDT'
]

async function fetchAllTickers(): Promise<Record<string, any>> {
  // Return cached data if still valid
  if (priceCache && Date.now() - priceCache.timestamp < CACHE_DURATION) {
    return priceCache.data
  }

  try {
    const ccxt = await getCCXT()
    const exchange = new ccxt.binance({
      enableRateLimit: true,
    })

    // Fetch all tickers at once (more efficient)
    const tickers = await exchange.fetchTickers(SYMBOLS)
    
    // Update cache
    priceCache = { data: tickers, timestamp: Date.now() }
    
    return tickers
  } catch (error) {
    console.error('CCXT fetch error:', error)
    // Return cached data if available
    if (priceCache) {
      return priceCache.data
    }
    throw error
  }
}

async function fetchTicker(symbol: string): Promise<any> {
  try {
    const ccxt = await getCCXT()
    const exchange = new ccxt.binance({
      enableRateLimit: true,
    })
    
    // Normalize symbol format
    const normalizedSymbol = symbol.includes('/') ? symbol : symbol.replace('USDT', '/USDT')
    
    const ticker = await exchange.fetchTicker(normalizedSymbol)
    return ticker
  } catch (error) {
    console.error(`Failed to fetch ticker for ${symbol}:`, error)
    throw error
  }
}

async function fetchOHLCV(symbol: string, timeframe: string, limit: number): Promise<any[]> {
  try {
    const ccxt = await getCCXT()
    const exchange = new ccxt.binance({
      enableRateLimit: true,
    })
    
    // Normalize symbol
    const normalizedSymbol = symbol.includes('/') ? symbol : symbol.replace('USDT', '/USDT')
    
    // Fetch OHLCV data
    const ohlcv = await exchange.fetchOHLCV(normalizedSymbol, timeframe, undefined, limit)
    
    // Transform to our format
    return ohlcv.map((candle: number[]) => ({
      time: candle[0],
      open: candle[1],
      high: candle[2],
      low: candle[3],
      close: candle[4],
      volume: candle[5],
    }))
  } catch (error) {
    console.error(`Failed to fetch OHLCV for ${symbol}:`, error)
    throw error
  }
}

async function fetchOrderBook(symbol: string, limit: number = 20): Promise<any> {
  try {
    const ccxt = await getCCXT()
    const exchange = new ccxt.binance({
      enableRateLimit: true,
    })
    
    const normalizedSymbol = symbol.includes('/') ? symbol : symbol.replace('USDT', '/USDT')
    const orderBook = await exchange.fetchOrderBook(normalizedSymbol, limit)
    
    return {
      bids: orderBook.bids.map((b: number[]) => ({ price: b[0], size: b[1] })),
      asks: orderBook.asks.map((a: number[]) => ({ price: a[0], size: a[1] })),
      timestamp: orderBook.timestamp || Date.now(),
    }
  } catch (error) {
    console.error(`Failed to fetch order book for ${symbol}:`, error)
    throw error
  }
}

async function fetchTrades(symbol: string, limit: number = 50): Promise<any[]> {
  try {
    const ccxt = await getCCXT()
    const exchange = new ccxt.binance({
      enableRateLimit: true,
    })
    
    const normalizedSymbol = symbol.includes('/') ? symbol : symbol.replace('USDT', '/USDT')
    const trades = await exchange.fetchTrades(normalizedSymbol, undefined, limit)
    
    return trades.map((t: any) => ({
      id: t.id,
      price: t.price,
      amount: t.amount,
      side: t.side,
      timestamp: t.timestamp,
    }))
  } catch (error) {
    console.error(`Failed to fetch trades for ${symbol}:`, error)
    throw error
  }
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const action = searchParams.get('action')
  const symbol = searchParams.get('symbol') || 'BTC/USDT'
  const timeframe = searchParams.get('timeframe') || '1h'
  const limit = parseInt(searchParams.get('limit') || '100')

  try {
    switch (action) {
      case 'ohlcv': {
        const candles = await fetchOHLCV(symbol, timeframe, limit)
        return NextResponse.json({ 
          candles, 
          symbol, 
          timeframe,
          source: 'binance',
          timestamp: Date.now()
        })
      }

      case 'ticker': {
        const ticker = await fetchTicker(symbol)
        return NextResponse.json({
          symbol: ticker.symbol,
          last: ticker.last,
          bid: ticker.bid,
          ask: ticker.ask,
          high: ticker.high,
          low: ticker.low,
          volume: ticker.baseVolume,
          change: ticker.change,
          percentage: ticker.percentage,
          timestamp: ticker.timestamp || Date.now(),
          source: 'binance',
        })
      }

      case 'orderbook': {
        const orderBook = await fetchOrderBook(symbol, limit)
        return NextResponse.json(orderBook)
      }

      case 'trades': {
        const trades = await fetchTrades(symbol, limit)
        return NextResponse.json({ trades })
      }

      case 'prices': {
        const tickers = await fetchAllTickers()
        const prices: Record<string, number> = {}
        
        for (const [sym, ticker] of Object.entries(tickers)) {
          if (ticker && (ticker as any).last) {
            const base = sym.split('/')[0]
            prices[base] = (ticker as any).last
            prices[sym] = (ticker as any).last
            prices[sym.replace('/', '')] = (ticker as any).last
          }
        }
        
        return NextResponse.json({
          prices, 
          timestamp: Date.now(),
          source: 'binance'
        })
      }

      case 'markets': {
        const tickers = await fetchAllTickers()
        const markets = Object.entries(tickers).map(([sym, ticker]: [string, any]) => ({
          symbol: sym.replace('/', ''),
          base: sym.split('/')[0],
          quote: sym.split('/')[1],
          price: ticker?.last || 0,
          change24h: ticker?.percentage || 0,
          volume24h: ticker?.quoteVolume || 0,
          high24h: ticker?.high || 0,
          low24h: ticker?.low || 0,
          }))
        
        return NextResponse.json({ markets, timestamp: Date.now() })
      }

      default:
        return NextResponse.json({ 
          error: 'Invalid action. Use: ohlcv, ticker, orderbook, trades, prices, markets' 
        }, { status: 400 })
    }

  } catch (error: any) {
    console.error('Market API Error:', error.message)
    return NextResponse.json({ 
      error: error.message || 'Failed to fetch market data',
      details: 'CCXT/Binance API error'
    }, { status: 500 })
  }
}
