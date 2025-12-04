import { NextRequest, NextResponse } from 'next/server'

// CCXT will be imported dynamically on the server side
let ccxt: any = null

async function getCCXT() {
  if (!ccxt) {
    ccxt = await import('ccxt')
  }
  return ccxt
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const action = searchParams.get('action')
  const exchange = searchParams.get('exchange') || 'binance'
  const symbol = searchParams.get('symbol') || 'BTC/USDT'
  const timeframe = searchParams.get('timeframe') || '1h'
  const limit = parseInt(searchParams.get('limit') || '100')

  try {
    const ccxtLib = await getCCXT()
    
    // Create exchange instance (public APIs only, no auth needed for market data)
    const exchangeClass = ccxtLib[exchange]
    if (!exchangeClass) {
      return NextResponse.json({ error: `Exchange ${exchange} not supported` }, { status: 400 })
    }
    
    const exchangeInstance = new exchangeClass({
      enableRateLimit: true,
    })

    switch (action) {
      case 'ohlcv': {
        // Fetch OHLCV (candlestick) data
        const ohlcv = await exchangeInstance.fetchOHLCV(symbol, timeframe, undefined, limit)
        
        // Transform to chart-friendly format
        const candles = ohlcv.map(([timestamp, open, high, low, close, volume]: number[]) => ({
          time: timestamp,
          open,
          high,
          low,
          close,
          volume,
        }))

        return NextResponse.json({ candles, symbol, timeframe, exchange })
      }

      case 'ticker': {
        // Fetch current ticker
        const ticker = await exchangeInstance.fetchTicker(symbol)
        return NextResponse.json({
          symbol: ticker.symbol,
          last: ticker.last,
          bid: ticker.bid,
          ask: ticker.ask,
          high: ticker.high,
          low: ticker.low,
          volume: ticker.baseVolume,
          change: ticker.percentage,
          timestamp: ticker.timestamp,
        })
      }

      case 'orderbook': {
        // Fetch order book
        const orderbook = await exchangeInstance.fetchOrderBook(symbol, 20)
        return NextResponse.json({
          bids: orderbook.bids.slice(0, 15).map(([price, size]: number[]) => ({ price, size })),
          asks: orderbook.asks.slice(0, 15).map(([price, size]: number[]) => ({ price, size })),
          timestamp: orderbook.timestamp,
        })
      }

      case 'trades': {
        // Fetch recent trades
        const trades = await exchangeInstance.fetchTrades(symbol, undefined, 50)
        return NextResponse.json({
          trades: trades.map((t: any) => ({
            id: t.id,
            price: t.price,
            amount: t.amount,
            side: t.side,
            timestamp: t.timestamp,
          }))
        })
      }

      case 'markets': {
        // Fetch available markets
        const markets = await exchangeInstance.loadMarkets()
        const marketList = Object.values(markets)
          .filter((m: any) => m.quote === 'USDT' && m.active)
          .slice(0, 100)
          .map((m: any) => ({
            symbol: m.symbol,
            base: m.base,
            quote: m.quote,
            type: m.type,
          }))
        return NextResponse.json({ markets: marketList })
      }

      default:
        return NextResponse.json({ error: 'Invalid action. Use: ohlcv, ticker, orderbook, trades, markets' }, { status: 400 })
    }

  } catch (error: any) {
    console.error('CCXT Error:', error.message)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

