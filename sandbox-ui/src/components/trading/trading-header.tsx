'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useTradingStore, Exchange, TradingMode } from '@/stores/trading-store'
import { useDataRecorder } from '@/hooks/use-data-recorder'
import { Button } from '@/components/ui/button'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { 
  Search, 
  Settings, 
  User, 
  Zap,
  Eye,
  FileText,
  Radio,
  RefreshCw,
  Circle,
  Database,
  Home,
  MessageSquare
} from 'lucide-react'

interface TradingHeaderProps {
  onConnectExchange: () => void
}

interface LiveMarket {
  symbol: string
  base: string
  quote: string
  price: number
  change24h: number
  volume24h: number
  high24h: number
  low24h: number
}

export function TradingHeader({ onConnectExchange }: TradingHeaderProps) {
  const { 
    accounts, 
    currentAccountId, 
    setCurrentAccount, 
    mode, 
    setMode,
    currentSymbol,
    setCurrentSymbol,
  } = useTradingStore()

  const {
    isRecording,
    totalRecords,
    toggleRecording,
    symbolsRecording,
  } = useDataRecorder()

  const [searchQuery, setSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)
  const [liveMarkets, setLiveMarkets] = useState<LiveMarket[]>([])
  const [currentTicker, setCurrentTicker] = useState<{ price: number; change: number } | null>(null)
  const [loading, setLoading] = useState(true)

  // Fetch live markets
  const fetchMarkets = useCallback(async () => {
    try {
      const response = await fetch('/api/market?action=markets')
      if (!response.ok) throw new Error('Failed to fetch markets')
      const data = await response.json()
      setLiveMarkets(data.markets || [])
      setLoading(false)
    } catch (err) {
      console.error('Error fetching markets:', err)
      setLoading(false)
    }
  }, [])

  // Fetch current ticker
  const fetchTicker = useCallback(async () => {
    try {
      const response = await fetch(`/api/market?action=ticker&symbol=${currentSymbol}`)
      if (!response.ok) throw new Error('Failed to fetch ticker')
      const data = await response.json()
      setCurrentTicker({ price: data.last, change: data.percentage })
    } catch (err) {
      console.error('Error fetching ticker:', err)
    }
  }, [currentSymbol])

  // Initial fetch and periodic refresh
  useEffect(() => {
    fetchMarkets()
    fetchTicker()
    const marketInterval = setInterval(fetchMarkets, 30000) // 30 seconds
    const tickerInterval = setInterval(fetchTicker, 5000) // 5 seconds
    return () => {
      clearInterval(marketInterval)
      clearInterval(tickerInterval)
    }
  }, [fetchMarkets, fetchTicker])

  const currentAccount = accounts.find(a => a.id === currentAccountId)

  const filteredMarkets = liveMarkets.filter(m => 
    m.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.base.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const modeConfig: Record<TradingMode, { icon: React.ReactNode; color: string; label: string }> = {
    view: { icon: <Eye className="w-4 h-4" />, color: 'bg-gray-600', label: 'View Only' },
    paper: { icon: <FileText className="w-4 h-4" />, color: 'bg-amber-600', label: 'Paper' },
    live: { icon: <Radio className="w-4 h-4" />, color: 'bg-green-600', label: 'Live' },
  }

  return (
    <header className="h-14 border-b border-gray-800 bg-[#0d0d14] flex items-center px-4 gap-4">
      {/* Back to Chat */}
      <Link href="/" className="flex items-center gap-1.5 text-gray-400 hover:text-white transition-colors">
        <Home className="w-4 h-4" />
        <span className="text-sm hidden sm:inline">Chat</span>
      </Link>

      <div className="w-px h-8 bg-gray-700" />

      {/* Logo & Title */}
      <div className="flex items-center gap-2">
        <Zap className="w-6 h-6 text-purple-500" />
        <span className="font-bold text-lg">Trading</span>
      </div>

      <div className="w-px h-8 bg-gray-700" />

      {/* Exchange Selector */}
      <Select
        value={currentAccountId || ''}
        onValueChange={setCurrentAccount}
      >
        <SelectTrigger className="w-48 bg-gray-900 border-gray-700">
          <SelectValue placeholder="Select account" />
        </SelectTrigger>
        <SelectContent className="bg-gray-900 border-gray-700">
          {accounts.map((account) => (
            <SelectItem key={account.id} value={account.id}>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${account.connected ? 'bg-green-500' : 'bg-gray-500'}`} />
                <span>{account.name}</span>
                <span className="text-xs text-gray-500">
                  ${account.balance.toLocaleString()}
                </span>
              </div>
            </SelectItem>
          ))}
          <div className="border-t border-gray-700 mt-1 pt-1">
            <button
              onClick={onConnectExchange}
              className="w-full px-2 py-1.5 text-sm text-purple-400 hover:bg-gray-800 rounded text-left"
            >
              + Connect Exchange
            </button>
          </div>
        </SelectContent>
      </Select>

      {/* Market Search */}
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <Input
          placeholder="Search markets... (⌘K)"
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value)
            setShowSearch(true)
          }}
          onFocus={() => setShowSearch(true)}
          onBlur={() => setTimeout(() => setShowSearch(false), 200)}
          className="pl-10 bg-gray-900 border-gray-700 focus:border-purple-500"
        />
        
        {/* Search Results Dropdown */}
        {showSearch && searchQuery && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50 max-h-80 overflow-auto">
            {loading ? (
              <div className="p-4 text-center text-gray-500">
                <RefreshCw className="w-5 h-5 animate-spin mx-auto" />
              </div>
            ) : filteredMarkets.length === 0 ? (
              <div className="p-4 text-center text-gray-500">No markets found</div>
            ) : (
              filteredMarkets.map((market) => (
                <button
                  key={market.symbol}
                  onClick={() => {
                    setCurrentSymbol(market.symbol)
                    setSearchQuery('')
                    setShowSearch(false)
                  }}
                  className="w-full px-4 py-2 flex items-center justify-between hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center text-xs font-bold">
                      {market.base.slice(0, 2)}
                    </div>
                    <div className="text-left">
                      <div className="font-medium">{market.symbol}</div>
                      <div className="text-xs text-gray-500">{market.base}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono">
                      ${market.price.toLocaleString(undefined, { maximumFractionDigits: market.price < 1 ? 4 : 2 })}
                    </div>
                    <div className={`text-xs ${market.change24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {market.change24h >= 0 ? '+' : ''}{market.change24h.toFixed(2)}%
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Current Symbol Display */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900 rounded-lg border border-gray-700">
        <span className="font-bold">{currentSymbol}</span>
        {currentTicker ? (
          <span className={`text-sm ${currentTicker.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            ${currentTicker.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </span>
        ) : (
          <RefreshCw className="w-3 h-3 animate-spin text-gray-500" />
        )}
      </div>

      <div className="flex-1" />

      {/* Data Recording Toggle */}
      <button
        onClick={() => toggleRecording({
          symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
          intervalMs: 30000,
        })}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors ${
          isRecording
            ? 'bg-red-500/20 border-red-500/50 text-red-400'
            : 'bg-gray-900 border-gray-700 text-gray-400 hover:text-white hover:border-gray-600'
        }`}
        title={isRecording ? `Recording ${symbolsRecording.length} symbols (${totalRecords} records)` : 'Start recording market data for PersRM'}
      >
        {isRecording ? (
          <>
            <Circle className="w-3 h-3 fill-red-500 animate-pulse" />
            <span className="text-xs font-medium">REC</span>
            <span className="text-xs text-gray-500">{totalRecords}</span>
          </>
        ) : (
          <>
            <Database className="w-4 h-4" />
            <span className="text-xs font-medium">Record</span>
          </>
        )}
      </button>

      {/* Mode Toggle */}
      <div className="flex items-center gap-1 bg-gray-900 rounded-lg p-1 border border-gray-700">
        {(Object.keys(modeConfig) as TradingMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              mode === m 
                ? `${modeConfig[m].color} text-white` 
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            {modeConfig[m].icon}
            {modeConfig[m].label}
          </button>
        ))}
      </div>

      {/* User & Settings */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" className="text-gray-400 hover:text-white">
          <Settings className="w-5 h-5" />
        </Button>
        <Button variant="ghost" size="icon" className="text-gray-400 hover:text-white">
          <User className="w-5 h-5" />
        </Button>
      </div>
    </header>
  )
}
