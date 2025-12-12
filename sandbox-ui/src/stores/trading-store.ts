import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// =============================================================================
// Types
// =============================================================================

export type Exchange = 'binance' | 'bybit' | 'hyperliquid' | 'coinbase' | 'paper'

export type AccountType = 'spot' | 'futures' | 'margin' | 'paper'

export type OrderSide = 'buy' | 'sell'

export type OrderType = 'market' | 'limit' | 'stop' | 'stop_limit'

export type TradingMode = 'view' | 'paper' | 'live'

export interface ExchangeAccount {
  id: string
  exchange: Exchange
  name: string
  type: AccountType
  balance: number
  currency: string
  connected: boolean
  apiKeySet: boolean
  // Hyperliquid specific
  walletAddress?: string
  network?: 'mainnet' | 'testnet'
}

// Hyperliquid connection credentials (stored in session only)
export interface HyperliquidCredentials {
  walletAddress: string
  privateKey: string
  network: 'mainnet' | 'testnet'
}

// Helper to manage Hyperliquid credentials in sessionStorage (survives refresh, not browser close)
const HYPERLIQUID_CREDS_KEY = 'hyperliquid-session-creds'

function saveHyperliquidCredsToSession(creds: HyperliquidCredentials | null) {
  if (typeof window === 'undefined') return
  if (creds) {
    // Encrypt/encode the private key for session storage (basic base64, in production use proper encryption)
    const encoded = btoa(JSON.stringify(creds))
    sessionStorage.setItem(HYPERLIQUID_CREDS_KEY, encoded)
  } else {
    sessionStorage.removeItem(HYPERLIQUID_CREDS_KEY)
  }
}

function loadHyperliquidCredsFromSession(): HyperliquidCredentials | null {
  if (typeof window === 'undefined') return null
  try {
    const encoded = sessionStorage.getItem(HYPERLIQUID_CREDS_KEY)
    if (!encoded) return null
    return JSON.parse(atob(encoded))
  } catch {
    return null
  }
}

export interface MarketSymbol {
  symbol: string
  baseAsset: string
  quoteAsset: string
  exchange: Exchange
  price: number
  change24h: number
  volume24h: number
  high24h: number
  low24h: number
}

export interface Position {
  id: string
  symbol: string
  side: 'long' | 'short'
  size: number
  entryPrice: number
  currentPrice: number
  pnl: number
  pnlPercent: number
  leverage: number
  stopLoss?: number
  takeProfit?: number
  strategy?: string
  openedAt: string
}

export interface Order {
  id: string
  symbol: string
  side: OrderSide
  type: OrderType
  size: number
  price?: number
  stopPrice?: number
  status: 'pending' | 'filled' | 'cancelled' | 'rejected'
  createdAt: string
  filledAt?: string
}

export interface PortfolioStats {
  totalValue: number
  dayPnl: number
  dayPnlPercent: number
  weekPnl: number
  monthPnl: number
  maxDrawdown: number
  winRate: number
  totalTrades: number
}

export interface WatchlistItem {
  symbol: string
  name: string
  price: number
  change24h: number
}

export interface NewsItem {
  id: string
  title: string
  source: string
  url: string
  timestamp: string
  sentiment: 'bullish' | 'bearish' | 'neutral'
  symbols: string[]
}

export interface JournalEntry {
  id: string
  type: 'trade' | 'note' | 'analysis'
  title: string
  content: string
  symbols: string[]
  tradeId?: string
  createdAt: string
  tags: string[]
}

// =============================================================================
// Backtest Types
// =============================================================================

export interface BacktestConfig {
  symbols: string[]
  timeframe: '1m' | '5m' | '15m'
  initialBalance: number
  days: number
  maxPositionSize: number
  riskPerTrade: number
  stopLossPercent: number
  takeProfitPercent: number
  modelName?: string // PersRM model version used for this backtest
}

export interface BacktestMetrics {
  totalReturn: number
  annualizedReturn: number
  totalTrades: number
  winningTrades: number
  losingTrades: number
  winRate: number
  profitFactor: number
  maxDrawdown: number
  sharpeRatio: number
  sortinoRatio: number
  averageTradeReturn: number
  expectancy: number
}

export interface BacktestTrade {
  id: string
  symbol: string
  side: 'long' | 'short'
  entryPrice: number
  exitPrice: number
  entryTime: number
  exitTime: number
  size: number
  pnl: number
  pnlPercent: number
  fees: number
  reason: string
}

export interface BacktestResult {
  id: string
  config: BacktestConfig
  metrics: BacktestMetrics
  trades: BacktestTrade[]
  equityCurve: { timestamp: number; equity: number }[]
  duration: number
  startTime: string
  endTime: string
  status: 'completed' | 'error'
  error?: string
}

// =============================================================================
// Store State
// =============================================================================

interface TradingState {
  // Connection state
  accounts: ExchangeAccount[]
  currentAccountId: string | null
  mode: TradingMode
  
  // Market state
  currentSymbol: string
  watchlists: { [key: string]: WatchlistItem[] }
  markets: MarketSymbol[]
  
  // Trading state
  positions: Position[]
  orders: Order[]
  positionHistory: Position[]
  orderHistory: Order[]
  
  // Portfolio
  portfolio: PortfolioStats
  
  // News & sentiment
  news: NewsItem[]
  
  // Journal
  journal: JournalEntry[]
  
  // UI state
  selectedTab: 'markets' | 'portfolio' | 'journal'
  rightPanelTab: 'assistant' | 'news' | 'sentiment' | 'alerts' | 'auto' | 'backtest' | 'data' | 'paper' | 'validate'
  isLabOpen: boolean
  
  // Auto-trading state
  autoTradingEnabled: boolean
  autoTradingMode: 'paper' | 'live'
  
  // Backtest history state
  backtestHistory: BacktestResult[]
  currentBacktestId: string | null
  isBacktesting: boolean
  backtestProgress: number
  
  // Actions
  setCurrentAccount: (accountId: string) => void
  setMode: (mode: TradingMode) => void
  setCurrentSymbol: (symbol: string) => void
  setSelectedTab: (tab: 'markets' | 'portfolio' | 'journal') => void
  setRightPanelTab: (tab: 'assistant' | 'news' | 'sentiment' | 'alerts' | 'auto') => void
  setLabOpen: (open: boolean) => void
  setAutoTradingEnabled: (enabled: boolean) => void
  setAutoTradingMode: (mode: 'paper' | 'live') => void
  
  // Trading actions
  addPosition: (position: Omit<Position, 'id'>) => void
  closePosition: (positionId: string, exitPrice: number) => void
  updatePosition: (positionId: string, updates: Partial<Position>) => void
  
  addOrder: (order: Omit<Order, 'id' | 'createdAt' | 'status'>) => void
  cancelOrder: (orderId: string) => void
  
  // Journal actions
  addJournalEntry: (entry: Omit<JournalEntry, 'id' | 'createdAt'>) => void
  
  // Exchange actions
  connectExchange: (exchange: Exchange, apiKey: string, secret: string) => Promise<boolean>
  connectHyperliquid: (walletAddress: string, privateKey: string, network: 'mainnet' | 'testnet') => Promise<boolean>
  disconnectExchange: (accountId: string) => void
  
  // Hyperliquid credentials (session only)
  hyperliquidCredentials: HyperliquidCredentials | null
  setHyperliquidCredentials: (creds: HyperliquidCredentials | null) => void
  
  // Backtest actions
  addBacktestResult: (result: BacktestResult) => void
  setCurrentBacktestId: (id: string | null) => void
  clearBacktestHistory: () => void
  loadBacktestHistory: () => Promise<void>
  setBacktestProgress: (progress: number) => void
  setIsBacktesting: (isBacktesting: boolean) => void
  getBacktestById: (id: string) => BacktestResult | undefined
  
  // Mock data
  initializeMockData: () => void
}

// =============================================================================
// Mock Data
// =============================================================================

const mockAccounts: ExchangeAccount[] = [
  {
    id: 'paper-main',
    exchange: 'paper',
    name: 'Paper Trading',
    type: 'paper',
    balance: 100000,
    currency: 'USDT',
    connected: true,
    apiKeySet: false,
  },
]

// Live prices - these will be updated from API
const mockMarkets: MarketSymbol[] = [
  { symbol: 'BTCUSDT', baseAsset: 'BTC', quoteAsset: 'USDT', exchange: 'binance', price: 101500, change24h: 2.5, volume24h: 45000000000, high24h: 103000, low24h: 99000 },
  { symbol: 'ETHUSDT', baseAsset: 'ETH', quoteAsset: 'USDT', exchange: 'binance', price: 3900, change24h: 1.8, volume24h: 18000000000, high24h: 3980, low24h: 3820 },
  { symbol: 'SOLUSDT', baseAsset: 'SOL', quoteAsset: 'USDT', exchange: 'binance', price: 230, change24h: 4.2, volume24h: 3500000000, high24h: 240, low24h: 220 },
  { symbol: 'BNBUSDT', baseAsset: 'BNB', quoteAsset: 'USDT', exchange: 'binance', price: 720, change24h: -0.8, volume24h: 1200000000, high24h: 735, low24h: 705 },
  { symbol: 'XRPUSDT', baseAsset: 'XRP', quoteAsset: 'USDT', exchange: 'binance', price: 2.40, change24h: 3.1, volume24h: 2800000000, high24h: 2.50, low24h: 2.30 },
  { symbol: 'ADAUSDT', baseAsset: 'ADA', quoteAsset: 'USDT', exchange: 'binance', price: 1.10, change24h: 1.2, volume24h: 890000000, high24h: 1.15, low24h: 1.05 },
]

const mockWatchlists = {
  favorites: [
    { symbol: 'BTCUSDT', name: 'Bitcoin', price: 101500, change24h: 2.5 },
    { symbol: 'ETHUSDT', name: 'Ethereum', price: 3900, change24h: 1.8 },
    { symbol: 'SOLUSDT', name: 'Solana', price: 230, change24h: 4.2 },
  ],
  crypto: [
    { symbol: 'BTCUSDT', name: 'Bitcoin', price: 101500, change24h: 2.5 },
    { symbol: 'ETHUSDT', name: 'Ethereum', price: 3900, change24h: 1.8 },
    { symbol: 'SOLUSDT', name: 'Solana', price: 230, change24h: 4.2 },
    { symbol: 'BNBUSDT', name: 'BNB', price: 720, change24h: -0.8 },
    { symbol: 'XRPUSDT', name: 'XRP', price: 2.40, change24h: 3.1 },
  ],
}

// Empty mock positions - real data comes from connected exchanges
const mockPositions: Position[] = []

// News will be loaded from scraped data API, not mock
const mockNews: NewsItem[] = []

// Portfolio stats will be computed from actual positions
const computePortfolioStats = (positions: Position[], balance: number): PortfolioStats => {
  const totalPnl = positions.reduce((sum, p) => sum + p.pnl, 0)
  const winningTrades = positions.filter(p => p.pnl > 0).length
  const totalTrades = positions.length
  
  return {
    totalValue: balance + totalPnl,
    dayPnl: totalPnl, // In real implementation, filter by today's positions
    dayPnlPercent: balance > 0 ? (totalPnl / balance) * 100 : 0,
    weekPnl: totalPnl, // In real implementation, filter by week's positions
    monthPnl: totalPnl, // In real implementation, filter by month's positions
    maxDrawdown: 0, // Calculated from equity curve
    winRate: totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0,
    totalTrades,
  }
}

const defaultPortfolio: PortfolioStats = {
  totalValue: 100000,
  dayPnl: 0,
  dayPnlPercent: 0,
  weekPnl: 0,
  monthPnl: 0,
  maxDrawdown: 0,
  winRate: 0,
  totalTrades: 0,
}

// =============================================================================
// Store
// =============================================================================

export const useTradingStore = create<TradingState>()(
  persist(
    (set, get) => ({
      // Initial state
      accounts: [],
      currentAccountId: null,
      mode: 'paper',
      currentSymbol: 'BTCUSDT',
      watchlists: {},
      markets: [],
      positions: [],
      orders: [],
      positionHistory: [],
      orderHistory: [],
      portfolio: {
        totalValue: 0,
        dayPnl: 0,
        dayPnlPercent: 0,
        weekPnl: 0,
        monthPnl: 0,
        maxDrawdown: 0,
        winRate: 0,
        totalTrades: 0,
      },
      news: [],
      journal: [],
      selectedTab: 'markets',
      rightPanelTab: 'assistant',
      isLabOpen: false,
      
      // Auto-trading state
      autoTradingEnabled: false,
      autoTradingMode: 'paper',
      
      // Backtest history state
      backtestHistory: [],
      currentBacktestId: null,
      isBacktesting: false,
      backtestProgress: 0,
      
      // Hyperliquid credentials (session only, not persisted)
      hyperliquidCredentials: null,

      // Actions
      setCurrentAccount: (accountId) => set({ currentAccountId: accountId }),
      setMode: (mode) => set({ mode }),
      setCurrentSymbol: (symbol) => set({ currentSymbol: symbol }),
      setSelectedTab: (tab) => set({ selectedTab: tab }),
      setRightPanelTab: (tab) => set({ rightPanelTab: tab }),
      setLabOpen: (open) => set({ isLabOpen: open }),
      setAutoTradingEnabled: (enabled) => set({ autoTradingEnabled: enabled }),
      setAutoTradingMode: (mode) => set({ autoTradingMode: mode }),

      addPosition: (position) => {
        const id = `pos-${Date.now()}`
        const newPosition: Position = {
          ...position,
          id,
        }
        set((state) => ({
          positions: [...state.positions, newPosition],
        }))
        
        // Auto-create journal entry
        get().addJournalEntry({
          type: 'trade',
          title: `Opened ${position.side.toUpperCase()} ${position.symbol}`,
          content: `Entry: $${position.entryPrice}, Size: ${position.size}, SL: ${position.stopLoss || 'None'}, TP: ${position.takeProfit || 'None'}`,
          symbols: [position.symbol],
          tradeId: id,
          tags: ['trade', position.side],
        })
      },

      closePosition: (positionId, exitPrice) => {
        const position = get().positions.find((p) => p.id === positionId)
        if (!position) return

        const pnl = position.side === 'long'
          ? (exitPrice - position.entryPrice) * position.size
          : (position.entryPrice - exitPrice) * position.size

        const pnlPercent = ((exitPrice - position.entryPrice) / position.entryPrice) * 100 * (position.side === 'long' ? 1 : -1)

        // Create closed position record for history
        const closedPosition = {
          ...position,
          exitPrice,
          pnl,
          pnlPercent,
          closedAt: new Date().toISOString(),
        }

        set((state) => ({
          positions: state.positions.filter((p) => p.id !== positionId),
          positionHistory: [closedPosition, ...state.positionHistory].slice(0, 100), // Keep last 100
        }))

        // Auto-create journal entry
        get().addJournalEntry({
          type: 'trade',
          title: `Closed ${position.side.toUpperCase()} ${position.symbol}`,
          content: `Exit: $${exitPrice}, PnL: $${pnl.toFixed(2)} (${((pnl / (position.entryPrice * position.size)) * 100).toFixed(2)}%)`,
          symbols: [position.symbol],
          tradeId: positionId,
          tags: ['trade', 'closed', pnl > 0 ? 'win' : 'loss'],
        })
      },

      updatePosition: (positionId, updates) => {
        set((state) => ({
          positions: state.positions.map((p) =>
            p.id === positionId ? { ...p, ...updates } : p
          ),
        }))
      },

      addOrder: (order) => {
        const id = `order-${Date.now()}`
        const newOrder: Order = {
          ...order,
          id,
          status: 'pending',
          createdAt: new Date().toISOString(),
        }
        set((state) => ({
          orders: [...state.orders, newOrder],
        }))
      },

      cancelOrder: (orderId) => {
        const order = get().orders.find((o) => o.id === orderId)
        if (!order) return

        const cancelledOrder = {
          ...order,
          status: 'cancelled' as const,
          filledAt: new Date().toISOString(),
        }

        set((state) => ({
          orders: state.orders.filter((o) => o.id !== orderId),
          orderHistory: [cancelledOrder, ...state.orderHistory].slice(0, 100), // Keep last 100
        }))
      },

      addJournalEntry: (entry) => {
        const id = `journal-${Date.now()}`
        const newEntry: JournalEntry = {
          ...entry,
          id,
          createdAt: new Date().toISOString(),
        }
        set((state) => ({
          journal: [newEntry, ...state.journal],
        }))
      },

      connectExchange: async (exchange, apiKey, secret) => {
        // Mock connection - in reality would call API
        await new Promise((resolve) => setTimeout(resolve, 1000))
        
        const newAccount: ExchangeAccount = {
          id: `${exchange}-${Date.now()}`,
          exchange,
          name: `${exchange.charAt(0).toUpperCase() + exchange.slice(1)} Spot`,
          type: 'spot',
          balance: 10000,
          currency: 'USDT',
          connected: true,
          apiKeySet: true,
        }
        
        set((state) => ({
          accounts: [...state.accounts, newAccount],
          currentAccountId: newAccount.id,
        }))
        
        return true
      },

      connectHyperliquid: async (walletAddress, privateKey, network) => {
        try {
          const creds = { walletAddress, privateKey, network }
          
          // Store credentials in session storage (survives page refresh)
          saveHyperliquidCredsToSession(creds)
          set({ hyperliquidCredentials: creds })
          
          // Verify connection via API
          const response = await fetch('/api/hyperliquid/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ walletAddress, privateKey, network }),
          })

          if (!response.ok) {
            const data = await response.json()
            throw new Error(data.error || 'Connection failed')
          }

          const data = await response.json()
          
          // Create account entry with a stable ID based on wallet address
          const accountId = `hyperliquid-${network}-${walletAddress.slice(-8)}`
          
          const newAccount: ExchangeAccount = {
            id: accountId,
            exchange: 'hyperliquid',
            name: `Hyperliquid ${network === 'testnet' ? 'Testnet' : 'Mainnet'}`,
            type: 'futures',
            balance: data.balance || 0,
            currency: 'USDC',
            connected: true,
            apiKeySet: true,
            walletAddress,
            network,
          }
          
          set((state) => ({
            accounts: [...state.accounts.filter(a => 
              !(a.exchange === 'hyperliquid' && a.network === network)
            ), newAccount],
            currentAccountId: newAccount.id,
            mode: network === 'testnet' ? 'paper' : 'live',
          }))
          
          return true
        } catch (error) {
          console.error('Hyperliquid connection error:', error)
          saveHyperliquidCredsToSession(null)
          set({ hyperliquidCredentials: null })
          return false
        }
      },
      
      setHyperliquidCredentials: (creds) => {
        saveHyperliquidCredsToSession(creds)
        set({ hyperliquidCredentials: creds })
      },

      // Backtest actions
      addBacktestResult: (result) => {
        set((state) => ({
          backtestHistory: [result, ...state.backtestHistory].slice(0, 50), // Keep last 50
          currentBacktestId: result.id,
          isBacktesting: false,
          backtestProgress: 100,
        }))
      },

      setCurrentBacktestId: (id) => set({ currentBacktestId: id }),

      clearBacktestHistory: () => set({ 
        backtestHistory: [], 
        currentBacktestId: null 
      }),

      loadBacktestHistory: async () => {
        try {
          const response = await fetch('/api/backtest/history')
          if (response.ok) {
            const data = await response.json()
            set({ backtestHistory: data.backtests || [] })
          }
        } catch (error) {
          console.error('Failed to load backtest history:', error)
        }
      },

      setBacktestProgress: (progress) => set({ backtestProgress: progress }),

      setIsBacktesting: (isBacktesting) => set({ isBacktesting }),

      getBacktestById: (id) => {
        return get().backtestHistory.find(b => b.id === id)
      },

      disconnectExchange: (accountId) => {
        const account = get().accounts.find(a => a.id === accountId)
        
        // Clear Hyperliquid credentials if disconnecting Hyperliquid
        if (account?.exchange === 'hyperliquid') {
          saveHyperliquidCredsToSession(null)
          set({ hyperliquidCredentials: null })
        }
        
        set((state) => ({
          accounts: state.accounts.filter((a) => a.id !== accountId),
          currentAccountId: state.currentAccountId === accountId
            ? state.accounts.find(a => a.id !== accountId)?.id || null
            : state.currentAccountId,
        }))
      },

      initializeMockData: () => {
        const currentState = get()
        
        // Preserve any connected exchange accounts (like Hyperliquid)
        const connectedAccounts = currentState.accounts.filter(a => 
          a.connected && a.exchange !== 'paper'
        )
        
        // Restore Hyperliquid credentials from session storage
        const savedCreds = loadHyperliquidCredsFromSession()
        if (savedCreds && !currentState.hyperliquidCredentials) {
          set({ hyperliquidCredentials: savedCreds })
        }
        
        // Merge paper account with connected accounts
        const mergedAccounts = [
          ...mockAccounts,
          ...connectedAccounts.filter(a => !mockAccounts.some(m => m.id === a.id))
        ]
        
        // Determine current account - prefer connected exchange over paper
        const preferredAccount = connectedAccounts.length > 0 
          ? connectedAccounts[0].id 
          : (currentState.currentAccountId || 'paper-main')
        
        // Check if using a real exchange - don't load mock positions
        const usingRealExchange = connectedAccounts.length > 0 && 
          connectedAccounts.some(a => a.id === preferredAccount)
        
        // Filter out mock positions if using real exchange, keep real positions
        const positionsToUse = usingRealExchange 
          ? currentState.positions.filter((p: any) => p.exchange && p.exchange !== 'mock')
          : currentState.positions // Keep existing positions (empty if none)
        
        // Get current account balance for portfolio calculation
        const currentAccount = mergedAccounts.find(a => a.id === preferredAccount)
        const accountBalance = currentAccount?.balance || 100000
        
        // Compute portfolio from actual positions instead of using mock stats
        const portfolio = positionsToUse.length > 0 
          ? computePortfolioStats(positionsToUse, accountBalance)
          : { ...defaultPortfolio, totalValue: accountBalance }
        
        set({
          accounts: mergedAccounts,
          currentAccountId: preferredAccount,
          markets: mockMarkets, // Initial values, will be updated by CCXT API
          watchlists: currentState.watchlists && Object.keys(currentState.watchlists).length > 0 
            ? currentState.watchlists 
            : mockWatchlists,
          positions: positionsToUse,
          portfolio, // Computed from real positions
          news: currentState.news.length > 0 ? currentState.news : [], // Don't load fake news
        })
      },
    }),
    {
      name: 'trading-store',
      partialize: (state) => ({
        // Persist accounts (but filter out sensitive data like private keys)
        accounts: state.accounts.map(a => ({
          ...a,
          // Don't persist the private key in localStorage
        })),
        currentAccountId: state.currentAccountId,
        currentSymbol: state.currentSymbol,
        mode: state.mode,
        watchlists: state.watchlists,
        journal: state.journal,
        positions: state.positions,
        autoTradingMode: state.autoTradingMode,
        // Persist backtest history (survives tab switch and refresh)
        backtestHistory: state.backtestHistory,
        currentBacktestId: state.currentBacktestId,
      }),
    }
  )
)

