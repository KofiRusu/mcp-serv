/**
 * Market Data Recorder Service
 * 
 * Records live market data (prices, order book, trades, candles) to JSON files
 * for PersRM training and analysis.
 */

// =============================================================================
// Types
// =============================================================================

export interface RecorderConfig {
  symbols: string[]
  intervalMs: number  // Recording interval in milliseconds
  enabled: boolean
}

export interface RecordingStats {
  isRecording: boolean
  startedAt: string | null
  symbolsRecording: string[]
  recordCounts: Record<string, Record<string, number>>
}

// =============================================================================
// Data Recorder Class
// =============================================================================

class DataRecorder {
  private config: RecorderConfig = {
    symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
    intervalMs: 30000, // 30 seconds default
    enabled: false,
  }
  
  private intervalId: NodeJS.Timeout | null = null
  private startedAt: Date | null = null
  private recordCounts: Record<string, Record<string, number>> = {}
  private listeners: Set<(stats: RecordingStats) => void> = new Set()

  /**
   * Start recording market data
   */
  start(config?: Partial<RecorderConfig>) {
    if (this.intervalId) {
      this.stop()
    }
    
    if (config) {
      this.config = { ...this.config, ...config }
    }
    
    this.config.enabled = true
    this.startedAt = new Date()
    this.recordCounts = {}
    
    // Initialize counts
    for (const symbol of this.config.symbols) {
      this.recordCounts[symbol] = {
        tickers: 0,
        orderbooks: 0,
        trades: 0,
        candles: 0,
      }
    }
    
    // Start recording loop
    this.intervalId = setInterval(() => this.recordSnapshot(), this.config.intervalMs)
    
    // Record first snapshot immediately
    this.recordSnapshot()
    
    this.notifyListeners()
    console.log('[DataRecorder] Started recording', this.config.symbols)
  }

  /**
   * Stop recording
   */
  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId)
      this.intervalId = null
    }
    
    this.config.enabled = false
    this.startedAt = null
    this.notifyListeners()
    console.log('[DataRecorder] Stopped recording')
  }

  /**
   * Check if recording is active
   */
  isRecording(): boolean {
    return this.config.enabled && this.intervalId !== null
  }

  /**
   * Get current recording stats
   */
  getStats(): RecordingStats {
    return {
      isRecording: this.isRecording(),
      startedAt: this.startedAt?.toISOString() || null,
      symbolsRecording: this.config.symbols,
      recordCounts: { ...this.recordCounts },
    }
  }

  /**
   * Subscribe to stats updates
   */
  subscribe(listener: (stats: RecordingStats) => void) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<RecorderConfig>) {
    const wasRecording = this.isRecording()
    
    if (wasRecording) {
      this.stop()
    }
    
    this.config = { ...this.config, ...config }
    
    if (wasRecording && config.enabled !== false) {
      this.start()
    }
  }

  /**
   * Record a single snapshot of all market data
   */
  private async recordSnapshot() {
    if (!this.config.enabled) return
    
    for (const symbol of this.config.symbols) {
      try {
        await Promise.all([
          this.recordTicker(symbol),
          this.recordOrderBook(symbol),
          this.recordTrades(symbol),
          this.recordCandles(symbol),
        ])
      } catch (error) {
        console.error(`[DataRecorder] Error recording ${symbol}:`, error)
      }
    }
    
    this.notifyListeners()
  }

  /**
   * Record ticker data
   */
  private async recordTicker(symbol: string) {
    try {
      const response = await fetch(`/api/market?action=ticker&symbol=${symbol}`)
      if (!response.ok) return
      
      const ticker = await response.json()
      
      await this.saveRecord(symbol, 'tickers', {
        last: ticker.last,
        bid: ticker.bid,
        ask: ticker.ask,
        high: ticker.high,
        low: ticker.low,
        volume: ticker.volume,
        change: ticker.change,
        percentage: ticker.percentage,
      })
      
      this.recordCounts[symbol].tickers++
    } catch (error) {
      console.error(`[DataRecorder] Ticker error for ${symbol}:`, error)
    }
  }

  /**
   * Record order book snapshot
   */
  private async recordOrderBook(symbol: string) {
    try {
      const response = await fetch(`/api/market?action=orderbook&symbol=${symbol}&limit=20`)
      if (!response.ok) return
      
      const orderbook = await response.json()
      
      await this.saveRecord(symbol, 'orderbooks', {
        bids: orderbook.bids,
        asks: orderbook.asks,
      })
      
      this.recordCounts[symbol].orderbooks++
    } catch (error) {
      console.error(`[DataRecorder] Order book error for ${symbol}:`, error)
    }
  }

  /**
   * Record recent trades
   */
  private async recordTrades(symbol: string) {
    try {
      const response = await fetch(`/api/market?action=trades&symbol=${symbol}&limit=50`)
      if (!response.ok) return
      
      const data = await response.json()
      
      await this.saveRecord(symbol, 'trades', {
        trades: data.trades,
      })
      
      this.recordCounts[symbol].trades++
    } catch (error) {
      console.error(`[DataRecorder] Trades error for ${symbol}:`, error)
    }
  }

  /**
   * Record OHLCV candles
   */
  private async recordCandles(symbol: string) {
    try {
      const response = await fetch(`/api/market?action=ohlcv&symbol=${symbol}&timeframe=1h&limit=24`)
      if (!response.ok) return
      
      const data = await response.json()
      
      await this.saveRecord(symbol, 'candles', {
        timeframe: '1h',
        candles: data.candles,
      })
      
      this.recordCounts[symbol].candles++
    } catch (error) {
      console.error(`[DataRecorder] Candles error for ${symbol}:`, error)
    }
  }

  /**
   * Save a record to the API
   */
  private async saveRecord(symbol: string, dataType: string, data: any) {
    try {
      await fetch('/api/data-recorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, dataType, data }),
      })
    } catch (error) {
      console.error(`[DataRecorder] Save error:`, error)
    }
  }

  /**
   * Notify all listeners of stats update
   */
  private notifyListeners() {
    const stats = this.getStats()
    for (const listener of this.listeners) {
      try {
        listener(stats)
      } catch (error) {
        console.error('[DataRecorder] Listener error:', error)
      }
    }
  }
}

// =============================================================================
// Export Singleton Instance
// =============================================================================

export const dataRecorder = new DataRecorder()

