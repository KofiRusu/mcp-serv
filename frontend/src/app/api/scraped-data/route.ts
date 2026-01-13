import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

const DATA_DIR = path.join(process.cwd(), 'data')
const MARKET_DATA_DIR = path.join(DATA_DIR, 'market-history')
const NEWS_DATA_DIR = path.join(DATA_DIR, 'news')
const SENTIMENT_DATA_DIR = path.join(DATA_DIR, 'sentiment')

interface ScrapedDataRequest {
  type: 'market' | 'markets' | 'news' | 'sentiment' | 'status'
  symbol?: string
  dataType?: 'tickers' | 'orderbooks' | 'trades' | 'ohlcv'
  date?: string
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const type = searchParams.get('type') || 'status'
    const symbol = searchParams.get('symbol') || 'BTCUSDT'
    const dataType = searchParams.get('dataType') || 'tickers'
    const date = searchParams.get('date') || new Date().toISOString().slice(0, 10)

    switch (type) {
      case 'status':
        return NextResponse.json(await getScraperStatus())
      
      case 'market':
        return NextResponse.json(await getMarketData(symbol, dataType, date))
      
      case 'markets':
        return NextResponse.json(await getAllMarketTickers(date))
      
      case 'news':
        return NextResponse.json(await getNewsData(date))
      
      case 'sentiment':
        return NextResponse.json(await getSentimentData())
      
      default:
        return NextResponse.json({ error: 'Invalid type' }, { status: 400 })
    }
  } catch (error: any) {
    console.error('Scraped data error:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to fetch scraped data' },
      { status: 500 }
    )
  }
}

async function getScraperStatus() {
  const status = {
    marketData: { available: false, lastUpdate: null as string | null, files: 0 },
    news: { available: false, lastUpdate: null as string | null, count: 0 },
    sentiment: { available: false, lastUpdate: null as string | null },
  }

  try {
    // Check market data
    const today = new Date().toISOString().slice(0, 10)
    const marketDir = path.join(MARKET_DATA_DIR, today)
    
    try {
      const symbols = await fs.readdir(marketDir)
      status.marketData.available = symbols.length > 0
      status.marketData.files = symbols.length
      
      // Get latest update time
      if (symbols.length > 0) {
        const tickerFile = path.join(marketDir, symbols[0], 'tickers.json')
        const stat = await fs.stat(tickerFile)
        status.marketData.lastUpdate = stat.mtime.toISOString()
      }
    } catch {
      // Directory doesn't exist
    }

    // Check news
    try {
      const newsFile = path.join(NEWS_DATA_DIR, `${today}.json`)
      const newsData = await fs.readFile(newsFile, 'utf-8')
      const news = JSON.parse(newsData)
      status.news.available = true
      status.news.count = news.length
      const stat = await fs.stat(newsFile)
      status.news.lastUpdate = stat.mtime.toISOString()
    } catch {
      // File doesn't exist
    }

    // Check sentiment
    try {
      const sentimentFile = path.join(SENTIMENT_DATA_DIR, 'latest.json')
      const stat = await fs.stat(sentimentFile)
      status.sentiment.available = true
      status.sentiment.lastUpdate = stat.mtime.toISOString()
    } catch {
      // File doesn't exist
    }
  } catch (error) {
    console.error('Error getting scraper status:', error)
  }

  return status
}

async function getMarketData(symbol: string, dataType: string, date: string) {
  const filePath = path.join(MARKET_DATA_DIR, date, symbol, `${dataType}.json`)
  
  try {
    const content = await fs.readFile(filePath, 'utf-8')
    const data = JSON.parse(content)
    
    // Return latest entry or full data based on type
    if (dataType === 'tickers') {
      return { 
        latest: data[data.length - 1],
        count: data.length,
        symbol,
      }
    }
    
    return {
      data: data.slice(-100), // Last 100 entries
      count: data.length,
      symbol,
    }
  } catch (error) {
    return {
      error: 'No data available',
      symbol,
      dataType,
      date,
    }
  }
}

async function getAllMarketTickers(date: string) {
  const marketDir = path.join(MARKET_DATA_DIR, date)
  const markets: Array<{
    symbol: string
    base: string
    quote: string
    price: number
    change24h: number
    volume24h: number
    high24h: number
    low24h: number
  }> = []

  try {
    const symbols = await fs.readdir(marketDir)
    
    for (const symbol of symbols) {
      try {
        const tickerPath = path.join(marketDir, symbol, 'tickers.json')
        const content = await fs.readFile(tickerPath, 'utf-8')
        const data = JSON.parse(content)
        
        // Get latest ticker
        const latest = data[data.length - 1]
        if (latest) {
          markets.push({
            symbol: symbol,
            base: symbol.replace('USDT', ''),
            quote: 'USDT',
            price: latest.last || 0,
            change24h: latest.percentage || 0,
            volume24h: latest.volume || 0,
            high24h: latest.high || 0,
            low24h: latest.low || 0,
          })
        }
      } catch {
        // Skip symbols with no ticker data
      }
    }

    return {
      markets,
      timestamp: Date.now(),
      source: 'scrapers',
      date,
    }
  } catch (error) {
    // If today's directory doesn't exist, try yesterday
    const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
    if (date !== yesterday) {
      return getAllMarketTickers(yesterday)
    }
    
    return {
      markets: [],
      timestamp: Date.now(),
      source: 'scrapers',
      error: 'No market data available',
    }
  }
}

async function getNewsData(date: string) {
  try {
    const filePath = path.join(NEWS_DATA_DIR, `${date}.json`)
    const content = await fs.readFile(filePath, 'utf-8')
    const news = JSON.parse(content)
    
    return {
      news: news.slice(-50), // Last 50 news items
      count: news.length,
      date,
    }
  } catch {
    return {
      news: [],
      count: 0,
      date,
      error: 'No news data available',
    }
  }
}

async function getSentimentData() {
  try {
    // Try to get latest sentiment
    const latestPath = path.join(SENTIMENT_DATA_DIR, 'latest.json')
    const content = await fs.readFile(latestPath, 'utf-8')
    const sentiment = JSON.parse(content)
    
    return {
      sentiment,
      available: true,
    }
  } catch {
    // Return mock sentiment if no data
    return {
      sentiment: {
        timestamp: new Date().toISOString(),
        fear_greed_index: 55,
        fear_greed_label: 'Neutral',
        btc_dominance: 52.4,
        total_market_cap: 2.45,
        funding_rate: 0.015,
        long_short_ratio: 1.1,
        social_volume: {
          twitter: 25,
          reddit: 15,
          telegram: 10,
        },
        symbols: {
          BTCUSDT: { sentiment_score: 65, social_mentions: 3000, funding_rate: 0.01 },
          ETHUSDT: { sentiment_score: 60, social_mentions: 1500, funding_rate: 0.008 },
          SOLUSDT: { sentiment_score: 70, social_mentions: 800, funding_rate: 0.015 },
        }
      },
      available: false,
      message: 'Using default data - scraper not running',
    }
  }
}

export async function POST(request: NextRequest) {
  // Endpoint to trigger scraper actions (if needed)
  try {
    const body = await request.json()
    const { action } = body

    switch (action) {
      case 'refresh':
        // Could trigger a manual scrape here
        return NextResponse.json({ success: true, message: 'Refresh triggered' })
      
      default:
        return NextResponse.json({ error: 'Invalid action' }, { status: 400 })
    }
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Failed to process action' },
      { status: 500 }
    )
  }
}

