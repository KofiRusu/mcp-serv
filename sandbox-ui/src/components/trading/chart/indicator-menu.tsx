'use client'

import { useState } from 'react'
import { 
  TrendingUp, 
  BarChart3, 
  Waves, 
  Target, 
  Activity,
  Zap,
  ChevronDown,
  ChevronRight,
  Search,
  Star,
  StarOff,
  Info
} from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

// ============================================================================
// INDICATOR DEFINITIONS - Based on aggr.trade indicators
// ============================================================================

export interface Indicator {
  id: string
  name: string
  shortName: string
  description: string
  category: 'trend' | 'momentum' | 'volume' | 'volatility' | 'orderflow' | 'custom'
  enabled: boolean
  favorite: boolean
  settings?: Record<string, any>
  color?: string
  overlay: boolean // true = drawn on price chart, false = separate pane
}

// Full list of indicators from aggr.trade + traditional TA
export const INDICATOR_DEFINITIONS: Omit<Indicator, 'enabled' | 'favorite'>[] = [
  // ============ TREND INDICATORS ============
  {
    id: 'vwap',
    name: 'VWAP',
    shortName: 'VWAP',
    description: 'Volume Weighted Average Price - Key institutional reference level',
    category: 'trend',
    overlay: true,
    color: '#f59e0b',
    settings: { period: 'session' }
  },
  {
    id: 'ichimoku',
    name: 'Ichimoku Cloud',
    shortName: 'Ichi',
    description: 'Japanese cloud indicator showing support, resistance, and trend direction',
    category: 'trend',
    overlay: true,
    settings: { tenkan: 9, kijun: 26, senkou: 52 }
  },
  {
    id: 'ema',
    name: 'EMA (Exponential Moving Average)',
    shortName: 'EMA',
    description: 'Fast-reacting moving average for trend identification',
    category: 'trend',
    overlay: true,
    color: '#3b82f6',
    settings: { periods: [9, 21, 50, 200] }
  },
  {
    id: 'sma',
    name: 'SMA (Simple Moving Average)',
    shortName: 'SMA',
    description: 'Classic moving average for support/resistance',
    category: 'trend',
    overlay: true,
    color: '#8b5cf6',
    settings: { periods: [20, 50, 100, 200] }
  },
  {
    id: 'supertrend',
    name: 'SuperTrend',
    shortName: 'ST',
    description: 'Trend-following indicator with clear buy/sell signals',
    category: 'trend',
    overlay: true,
    settings: { period: 10, multiplier: 3 }
  },
  {
    id: 'td_sequential',
    name: 'TD Sequential',
    shortName: 'TDS',
    description: 'Tom DeMark sequential - Identifies exhaustion points',
    category: 'trend',
    overlay: true,
    settings: { mode: 'setup' }
  },

  // ============ MOMENTUM INDICATORS ============
  {
    id: 'rsi',
    name: 'RSI (Relative Strength Index)',
    shortName: 'RSI',
    description: 'Momentum oscillator measuring overbought/oversold conditions',
    category: 'momentum',
    overlay: false,
    color: '#8b5cf6',
    settings: { period: 14, overbought: 70, oversold: 30 }
  },
  {
    id: 'macd',
    name: 'MACD',
    shortName: 'MACD',
    description: 'Moving Average Convergence Divergence - Trend momentum indicator',
    category: 'momentum',
    overlay: false,
    color: '#3b82f6',
    settings: { fast: 12, slow: 26, signal: 9 }
  },
  {
    id: 'stochastic',
    name: 'Stochastic Oscillator',
    shortName: 'Stoch',
    description: 'Compares closing price to price range over time',
    category: 'momentum',
    overlay: false,
    settings: { k: 14, d: 3, smooth: 3 }
  },
  {
    id: 'mfi',
    name: 'MFI (Money Flow Index)',
    shortName: 'MFI',
    description: 'Volume-weighted RSI - Shows buying/selling pressure',
    category: 'momentum',
    overlay: false,
    color: '#22c55e',
    settings: { period: 14 }
  },
  {
    id: 'cci',
    name: 'CCI (Commodity Channel Index)',
    shortName: 'CCI',
    description: 'Identifies cyclical trends and extreme conditions',
    category: 'momentum',
    overlay: false,
    settings: { period: 20 }
  },

  // ============ VOLUME INDICATORS ============
  {
    id: 'volume',
    name: 'Volume',
    shortName: 'Vol',
    description: 'Trading volume bars with delta coloring',
    category: 'volume',
    overlay: false,
    color: '#10b981'
  },
  {
    id: 'cvd',
    name: 'CVD (Cumulative Volume Delta)',
    shortName: 'CVD',
    description: 'Cumulative difference between buy and sell volume - Key orderflow metric',
    category: 'volume',
    overlay: false,
    color: '#10b981',
    settings: { reset: 'session' }
  },
  {
    id: 'obv',
    name: 'OBV (On-Balance Volume)',
    shortName: 'OBV',
    description: 'Running total of volume based on price direction',
    category: 'volume',
    overlay: false,
    color: '#06b6d4'
  },
  {
    id: 'vol_delta_avg',
    name: 'VOL Δ Average',
    shortName: 'VolΔ',
    description: 'Average volume delta showing buying/selling imbalance',
    category: 'volume',
    overlay: false,
    color: '#f59e0b'
  },
  {
    id: 'delta_divs',
    name: 'Delta Divergences',
    shortName: 'ΔDiv',
    description: 'Spots divergences between price and volume delta',
    category: 'volume',
    overlay: true,
    color: '#ef4444'
  },
  {
    id: 'vwap_bands',
    name: 'VWAP Bands',
    shortName: 'VWAPB',
    description: 'Standard deviation bands around VWAP',
    category: 'volume',
    overlay: true,
    settings: { stdDev: [1, 2, 3] }
  },

  // ============ VOLATILITY INDICATORS ============
  {
    id: 'bollinger',
    name: 'Bollinger Bands',
    shortName: 'BB',
    description: 'Volatility bands around a moving average',
    category: 'volatility',
    overlay: true,
    color: '#6366f1',
    settings: { period: 20, stdDev: 2 }
  },
  {
    id: 'atr',
    name: 'ATR (Average True Range)',
    shortName: 'ATR',
    description: 'Measures market volatility',
    category: 'volatility',
    overlay: false,
    settings: { period: 14 }
  },
  {
    id: 'keltner',
    name: 'Keltner Channels',
    shortName: 'KC',
    description: 'Volatility-based envelope indicator',
    category: 'volatility',
    overlay: true,
    settings: { period: 20, multiplier: 2 }
  },
  {
    id: 'chandelier',
    name: 'Chandelier Exit',
    shortName: 'CE',
    description: 'Trailing stop-loss based on ATR',
    category: 'volatility',
    overlay: true,
    color: '#ef4444',
    settings: { period: 22, multiplier: 3 }
  },

  // ============ ORDERFLOW INDICATORS (aggr.trade specific) ============
  {
    id: 'liquidation_heatmap',
    name: 'Liquidation Heatmap',
    shortName: 'LiqH',
    description: 'Visualizes potential liquidation levels - Shows where stop-losses cluster',
    category: 'orderflow',
    overlay: true,
    color: '#fbbf24',
    settings: { threshold: 50000 }
  },
  {
    id: 'liquidations',
    name: 'Liquidations',
    shortName: 'Liq',
    description: 'Real-time liquidation events by side (long/short)',
    category: 'orderflow',
    overlay: false,
    color: '#ef4444',
    settings: { minSize: 10000 }
  },
  {
    id: 'large_trades',
    name: 'Large Trades (Whale Activity)',
    shortName: 'Whale',
    description: 'Highlights trades above threshold ($100K+)',
    category: 'orderflow',
    overlay: true,
    color: '#22d3ee',
    settings: { threshold: 100000 }
  },
  {
    id: 'aggr_trades',
    name: 'Aggregated Trades',
    shortName: 'AggrT',
    description: 'Groups trades by price level and time',
    category: 'orderflow',
    overlay: true,
    settings: { timeWindow: 5 }
  },
  {
    id: 'footprint',
    name: 'Footprint Chart',
    shortName: 'FP',
    description: 'Volume profile within each candle',
    category: 'orderflow',
    overlay: true,
  },

  // ============ CUSTOM/OTHER ============
  {
    id: 'fibonacci',
    name: 'Fibonacci Retracement',
    shortName: 'Fib',
    description: 'Auto-drawn Fibonacci levels from swing highs/lows',
    category: 'custom',
    overlay: true,
    settings: { levels: [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1] }
  },
  {
    id: 'pivot_points',
    name: 'Pivot Points',
    shortName: 'Pivot',
    description: 'Support/resistance levels based on previous period',
    category: 'custom',
    overlay: true,
    settings: { type: 'traditional' }
  },
  {
    id: 'pvsra',
    name: 'PVSRA',
    shortName: 'PVSRA',
    description: 'Price Volume Spread Analysis - Volume-based candle coloring',
    category: 'custom',
    overlay: true,
  },
  {
    id: 'session_vwap',
    name: 'Session VWAP',
    shortName: 'SVWAP',
    description: 'VWAP calculated per trading session (Asia/London/NY)',
    category: 'custom',
    overlay: true,
    settings: { sessions: ['asia', 'london', 'newyork'] }
  },
]

// Category metadata
const CATEGORIES = {
  trend: { name: 'Trend', icon: TrendingUp, color: 'text-blue-400' },
  momentum: { name: 'Momentum', icon: Activity, color: 'text-purple-400' },
  volume: { name: 'Volume', icon: BarChart3, color: 'text-green-400' },
  volatility: { name: 'Volatility', icon: Waves, color: 'text-orange-400' },
  orderflow: { name: 'Order Flow', icon: Zap, color: 'text-cyan-400' },
  custom: { name: 'Custom', icon: Target, color: 'text-pink-400' },
}

// ============================================================================
// INDICATOR MENU COMPONENT
// ============================================================================

interface IndicatorMenuProps {
  indicators: Indicator[]
  onToggle: (id: string) => void
  onFavorite: (id: string) => void
  onSettingsChange?: (id: string, settings: Record<string, any>) => void
}

export function IndicatorMenu({ 
  indicators, 
  onToggle, 
  onFavorite,
  onSettingsChange 
}: IndicatorMenuProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['orderflow']))
  const [selectedIndicator, setSelectedIndicator] = useState<string | null>(null)

  // Filter indicators
  const filteredIndicators = indicators.filter(ind => 
    ind.name.toLowerCase().includes(search.toLowerCase()) ||
    ind.shortName.toLowerCase().includes(search.toLowerCase()) ||
    ind.description.toLowerCase().includes(search.toLowerCase())
  )

  // Group by category
  const groupedIndicators = Object.entries(CATEGORIES).map(([key, cat]) => ({
    category: key as keyof typeof CATEGORIES,
    ...cat,
    indicators: filteredIndicators.filter(i => i.category === key)
  }))

  // Get favorites
  const favorites = indicators.filter(i => i.favorite)
  
  // Get enabled count
  const enabledCount = indicators.filter(i => i.enabled).length

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button 
          variant="outline" 
          size="sm"
          className="h-8 px-3 bg-gray-900 border-gray-700 hover:bg-gray-800 hover:border-purple-500/50"
        >
          <Activity className="w-4 h-4 mr-2 text-purple-400" />
          <span className="text-xs">Indicators</span>
          {enabledCount > 0 && (
            <Badge className="ml-2 h-5 px-1.5 bg-purple-600 text-white text-[10px]">
              {enabledCount}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      
      <PopoverContent 
        className="w-[400px] p-0 bg-[#0d0d14] border-gray-800"
        align="start"
      >
        {/* Header */}
        <div className="p-3 border-b border-gray-800">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-sm text-white">Indicators</h3>
            <span className="text-[10px] text-gray-500">{enabledCount} active</span>
          </div>
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <Input
              placeholder="Search indicators..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 h-8 text-xs bg-gray-900 border-gray-700"
            />
          </div>
        </div>

        {/* Favorites Section */}
        {favorites.length > 0 && !search && (
          <div className="p-2 border-b border-gray-800">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 px-1">
              Favorites
            </div>
            <div className="flex flex-wrap gap-1">
              {favorites.map(ind => (
                <button
                  key={ind.id}
                  onClick={() => onToggle(ind.id)}
                  className={cn(
                    "px-2 py-1 text-[10px] rounded-full transition-colors",
                    ind.enabled 
                      ? "bg-purple-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  )}
                >
                  {ind.shortName}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Categories */}
        <div className="max-h-[400px] overflow-y-auto">
          {groupedIndicators.map(({ category, name, icon: Icon, color, indicators: catIndicators }) => (
            catIndicators.length > 0 && (
              <div key={category} className="border-b border-gray-800/50 last:border-0">
                {/* Category Header */}
                <button
                  onClick={() => toggleCategory(category)}
                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-900/50 transition-colors"
                >
                  {expandedCategories.has(category) ? (
                    <ChevronDown className="w-3 h-3 text-gray-500" />
                  ) : (
                    <ChevronRight className="w-3 h-3 text-gray-500" />
                  )}
                  <Icon className={cn("w-4 h-4", color)} />
                  <span className="text-xs text-gray-300">{name}</span>
                  <span className="ml-auto text-[10px] text-gray-600">{catIndicators.length}</span>
                </button>

                {/* Indicators List */}
                {expandedCategories.has(category) && (
                  <div className="pb-2">
                    {catIndicators.map(ind => (
                      <div
                        key={ind.id}
                        className={cn(
                          "flex items-center gap-2 mx-2 px-2 py-1.5 rounded-md transition-colors",
                          ind.enabled ? "bg-purple-900/20" : "hover:bg-gray-900/50"
                        )}
                      >
                        {/* Toggle button */}
                        <button
                          onClick={() => onToggle(ind.id)}
                          className={cn(
                            "w-5 h-5 rounded border-2 flex items-center justify-center transition-colors",
                            ind.enabled 
                              ? "border-purple-500 bg-purple-600"
                              : "border-gray-600 hover:border-gray-500"
                          )}
                        >
                          {ind.enabled && (
                            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </button>

                        {/* Indicator info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-white">{ind.name}</span>
                            {ind.overlay && (
                              <span className="text-[9px] text-gray-500 bg-gray-800 px-1 rounded">overlay</span>
                            )}
                          </div>
                          <p className="text-[10px] text-gray-500 truncate">{ind.description}</p>
                        </div>

                        {/* Favorite toggle */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            onFavorite(ind.id)
                          }}
                          className="p-1 hover:bg-gray-800 rounded transition-colors"
                        >
                          {ind.favorite ? (
                            <Star className="w-3.5 h-3.5 text-yellow-500 fill-yellow-500" />
                          ) : (
                            <StarOff className="w-3.5 h-3.5 text-gray-600 hover:text-gray-400" />
                          )}
                        </button>

                        {/* Settings button (if has settings) */}
                        {ind.settings && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setSelectedIndicator(selectedIndicator === ind.id ? null : ind.id)
                            }}
                            className="p-1 hover:bg-gray-800 rounded transition-colors"
                          >
                            <Info className="w-3.5 h-3.5 text-gray-600 hover:text-gray-400" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          ))}
        </div>

        {/* Footer */}
        <div className="p-2 border-t border-gray-800 flex items-center justify-between">
          <span className="text-[10px] text-gray-500">
            Powered by aggr.trade indicators
          </span>
          <button
            onClick={() => {
              indicators.forEach(ind => {
                if (ind.enabled) onToggle(ind.id)
              })
            }}
            className="text-[10px] text-red-400 hover:text-red-300"
          >
            Clear All
          </button>
        </div>
      </PopoverContent>
    </Popover>
  )
}

// ============================================================================
// HOOK FOR MANAGING INDICATOR STATE
// ============================================================================

export function useIndicators() {
  const [indicators, setIndicators] = useState<Indicator[]>(() => 
    INDICATOR_DEFINITIONS.map(def => ({
      ...def,
      enabled: ['volume', 'vwap'].includes(def.id), // Default enabled
      favorite: ['vwap', 'cvd', 'rsi', 'liquidation_heatmap'].includes(def.id), // Default favorites
    }))
  )

  const toggleIndicator = (id: string) => {
    setIndicators(prev => prev.map(ind => 
      ind.id === id ? { ...ind, enabled: !ind.enabled } : ind
    ))
  }

  const toggleFavorite = (id: string) => {
    setIndicators(prev => prev.map(ind => 
      ind.id === id ? { ...ind, favorite: !ind.favorite } : ind
    ))
  }

  const updateSettings = (id: string, settings: Record<string, any>) => {
    setIndicators(prev => prev.map(ind => 
      ind.id === id ? { ...ind, settings: { ...ind.settings, ...settings } } : ind
    ))
  }

  const enabledIndicators = indicators.filter(i => i.enabled)
  const overlayIndicators = enabledIndicators.filter(i => i.overlay)
  const paneIndicators = enabledIndicators.filter(i => !i.overlay)

  return {
    indicators,
    enabledIndicators,
    overlayIndicators,
    paneIndicators,
    toggleIndicator,
    toggleFavorite,
    updateSettings,
  }
}

