'use client'

import { useState, useEffect, useCallback } from 'react'

interface ScraperStatus {
  marketData: { available: boolean; lastUpdate: string | null; files: number }
  news: { available: boolean; lastUpdate: string | null; count: number }
  sentiment: { available: boolean; lastUpdate: string | null }
}

interface NewsItem {
  id: string
  title: string
  source: string
  url: string
  timestamp: string
  sentiment: 'bullish' | 'bearish' | 'neutral'
  symbols: string[]
}

interface SentimentData {
  timestamp: string
  fear_greed_index: number
  fear_greed_label: string
  btc_dominance: number
  total_market_cap: number
  total_market_cap_t?: number
  funding_rate: number
  long_short_ratio: number
  social_volume: {
    twitter: number
    reddit: number
    telegram: number
  }
  symbols: Record<string, {
    sentiment_score: number
    social_mentions: number
    funding_rate: number
  }>
}

interface TickerData {
  symbol: string
  last: number
  bid: number
  ask: number
  high: number
  low: number
  volume: number
  change: number
  percentage: number
  timestamp: string
}

export function useScrapedData() {
  const [status, setStatus] = useState<ScraperStatus | null>(null)
  const [news, setNews] = useState<NewsItem[]>([])
  const [sentiment, setSentiment] = useState<SentimentData | null>(null)
  const [tickers, setTickers] = useState<Record<string, TickerData>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch scraper status
  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/scraped-data?type=status')
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
      }
    } catch (err) {
      console.error('Error fetching scraper status:', err)
    }
  }, [])

  // Fetch news data
  const fetchNews = useCallback(async () => {
    try {
      const response = await fetch('/api/scraped-data?type=news')
      if (response.ok) {
        const data = await response.json()
        setNews(data.news || [])
      }
    } catch (err) {
      console.error('Error fetching news:', err)
    }
  }, [])

  // Fetch sentiment data
  const fetchSentiment = useCallback(async () => {
    try {
      const response = await fetch('/api/scraped-data?type=sentiment')
      if (response.ok) {
        const data = await response.json()
        setSentiment(data.sentiment)
      }
    } catch (err) {
      console.error('Error fetching sentiment:', err)
    }
  }, [])

  // Fetch ticker data for a symbol
  const fetchTicker = useCallback(async (symbol: string) => {
    try {
      const response = await fetch(`/api/scraped-data?type=market&symbol=${symbol}&dataType=tickers`)
      if (response.ok) {
        const data = await response.json()
        if (data.latest) {
          setTickers(prev => ({ ...prev, [symbol]: data.latest }))
        }
      }
    } catch (err) {
      console.error(`Error fetching ticker for ${symbol}:`, err)
    }
  }, [])

  // Initial load
  useEffect(() => {
    const loadAll = async () => {
      setLoading(true)
      try {
        await Promise.all([
          fetchStatus(),
          fetchNews(),
          fetchSentiment(),
          fetchTicker('BTCUSDT'),
          fetchTicker('ETHUSDT'),
          fetchTicker('SOLUSDT'),
        ])
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    loadAll()

    // Poll for updates
    const statusInterval = setInterval(fetchStatus, 30000) // Status every 30s
    const newsInterval = setInterval(fetchNews, 60000) // News every 1 min
    const sentimentInterval = setInterval(fetchSentiment, 60000) // Sentiment every 1 min
    const tickerInterval = setInterval(() => {
      fetchTicker('BTCUSDT')
      fetchTicker('ETHUSDT')
      fetchTicker('SOLUSDT')
    }, 10000) // Tickers every 10s

    return () => {
      clearInterval(statusInterval)
      clearInterval(newsInterval)
      clearInterval(sentimentInterval)
      clearInterval(tickerInterval)
    }
  }, [fetchStatus, fetchNews, fetchSentiment, fetchTicker])

  return {
    status,
    news,
    sentiment,
    tickers,
    loading,
    error,
    refetch: {
      status: fetchStatus,
      news: fetchNews,
      sentiment: fetchSentiment,
      ticker: fetchTicker,
    },
  }
}

// Hook specifically for the sentiment panel
export function useSentimentData() {
  const [sentiment, setSentiment] = useState<SentimentData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchSentiment = async () => {
      try {
        const response = await fetch('/api/scraped-data?type=sentiment')
        if (response.ok) {
          const data = await response.json()
          setSentiment(data.sentiment)
        }
      } catch (err) {
        console.error('Error fetching sentiment:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchSentiment()
    const interval = setInterval(fetchSentiment, 60000)
    return () => clearInterval(interval)
  }, [])

  return { sentiment, loading }
}

// Hook specifically for news feed
export function useNewsData(symbolFilter?: string) {
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchNews = async () => {
      try {
        const response = await fetch('/api/scraped-data?type=news')
        if (response.ok) {
          const data = await response.json()
          let newsItems = data.news || []
          
          // Filter by symbol if provided
          if (symbolFilter) {
            newsItems = newsItems.filter((item: NewsItem) => 
              item.symbols.length === 0 || item.symbols.includes(symbolFilter)
            )
          }
          
          setNews(newsItems)
        }
      } catch (err) {
        console.error('Error fetching news:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchNews()
    const interval = setInterval(fetchNews, 60000)
    return () => clearInterval(interval)
  }, [symbolFilter])

  return { news, loading }
}

