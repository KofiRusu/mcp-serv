'use client'

/**
 * auto-trading-panel.tsx - PersRM Auto-Trading Activity Display
 * 
 * Shows real-time auto-trading activity:
 * - Start/Stop controls
 * - Live activity feed with decisions and reasoning
 * - Position and PnL stats
 * - Connection status
 * - Hyperliquid integration
 */

import { useState, useRef, useEffect } from 'react'
import { useAutoTrading, ActivityEntry, ActivityType, TradingSignal } from '@/hooks/use-auto-trading'
import { useTradingStore } from '@/stores/trading-store'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { HyperliquidConnectModal } from '../hyperliquid-connect-modal'
import {
  Play,
  Square,
  RefreshCw,
  Wifi,
  WifiOff,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Info,
  Search,
  Zap,
  Bot,
  RotateCcw,
  Wallet,
  Link,
  Unlink,
} from 'lucide-react'

// =============================================================================
// Activity Entry Component
// =============================================================================

interface ActivityItemProps {
  entry: ActivityEntry
}

function ActivityItem({ entry }: ActivityItemProps) {
  const getIcon = () => {
    switch (entry.type) {
      case 'analyzing':
        return <Search className="w-3 h-3 text-blue-400 animate-pulse" />
      case 'signal':
        if (entry.signal === 'LONG') return <TrendingUp className="w-3 h-3 text-green-400" />
        if (entry.signal === 'SHORT') return <TrendingDown className="w-3 h-3 text-red-400" />
        if (entry.signal === 'CLOSE') return <CheckCircle className="w-3 h-3 text-yellow-400" />
        return <Info className="w-3 h-3 text-gray-400" />
      case 'executed':
        return <Zap className="w-3 h-3 text-amber-400" />
      case 'error':
        return <AlertTriangle className="w-3 h-3 text-red-500" />
      case 'info':
        return <Info className="w-3 h-3 text-blue-400" />
      default:
        return <Info className="w-3 h-3 text-gray-400" />
    }
  }

  const getBackgroundColor = () => {
    switch (entry.type) {
      case 'signal':
        if (entry.signal === 'LONG') return 'bg-green-500/10 border-green-500/30'
        if (entry.signal === 'SHORT') return 'bg-red-500/10 border-red-500/30'
        if (entry.signal === 'CLOSE') return 'bg-yellow-500/10 border-yellow-500/30'
        return 'bg-gray-800/50'
      case 'executed':
        return 'bg-amber-500/10 border-amber-500/30'
      case 'error':
        return 'bg-red-500/10 border-red-500/30'
      default:
        return 'bg-gray-800/50 border-gray-700/50'
    }
  }

  return (
    <div className={`p-2 rounded-lg border ${getBackgroundColor()} text-xs`}>
      <div className="flex items-start gap-2">
        <span className="flex-shrink-0 mt-0.5">{getIcon()}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-gray-500 font-mono text-[10px]">{entry.timestamp}</span>
            <span className="font-medium text-white truncate">{entry.message}</span>
          </div>
          
          {entry.reasoning && (
            <p className="text-gray-400 text-[11px] leading-relaxed line-clamp-2">
              {entry.reasoning}
            </p>
          )}
          
          {(entry.entry_price || entry.stop_loss || entry.take_profit) && (
            <div className="flex flex-wrap gap-2 mt-1 text-[10px]">
              {entry.entry_price && (
                <span className="text-gray-400">
                  Entry: <span className="text-white font-mono">${entry.entry_price.toLocaleString()}</span>
                </span>
              )}
              {entry.stop_loss && (
                <span className="text-gray-400">
                  SL: <span className="text-red-400 font-mono">${entry.stop_loss.toLocaleString()}</span>
                </span>
              )}
              {entry.take_profit && (
                <span className="text-gray-400">
                  TP: <span className="text-green-400 font-mono">${entry.take_profit.toLocaleString()}</span>
                </span>
              )}
              {entry.pnl !== undefined && (
                <span className={entry.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                  PnL: ${entry.pnl.toFixed(2)}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Stats Bar Component
// =============================================================================

interface StatsBarProps {
  totalTrades: number
  winningTrades: number
  currentPnl: number
  cyclesCompleted: number
}

function StatsBar({ totalTrades, winningTrades, currentPnl, cyclesCompleted }: StatsBarProps) {
  const winRate = totalTrades > 0 ? ((winningTrades / totalTrades) * 100).toFixed(1) : '0.0'
  
  return (
    <div className="grid grid-cols-4 gap-2 p-2 bg-gray-900/50 rounded-lg text-[10px]">
      <div className="text-center">
        <div className="text-gray-500">Trades</div>
        <div className="font-bold text-white">{totalTrades}</div>
      </div>
      <div className="text-center">
        <div className="text-gray-500">Win Rate</div>
        <div className={`font-bold ${parseFloat(winRate) >= 50 ? 'text-green-400' : 'text-red-400'}`}>
          {winRate}%
        </div>
      </div>
      <div className="text-center">
        <div className="text-gray-500">PnL</div>
        <div className={`font-bold ${currentPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          ${currentPnl.toFixed(2)}
        </div>
      </div>
      <div className="text-center">
        <div className="text-gray-500">Cycles</div>
        <div className="font-bold text-white">{cyclesCompleted}</div>
      </div>
    </div>
  )
}

// =============================================================================
// Main Component
// =============================================================================

export function AutoTradingPanel() {
  const {
    connected,
    connecting,
    status,
    activities,
    error,
    connect,
    disconnect,
    start,
    stop,
    reset,
    refreshStatus,
    clearActivities,
  } = useAutoTrading({ autoConnect: true })

  const { accounts, mode, disconnectExchange } = useTradingStore()
  const hyperliquidAccount = accounts.find(a => a.exchange === 'hyperliquid' && a.connected)

  const scrollRef = useRef<HTMLDivElement>(null)
  const [selectedSymbols, setSelectedSymbols] = useState(['BTCUSDT'])
  const [intervalSeconds, setIntervalSeconds] = useState(15)
  const [showHyperliquidModal, setShowHyperliquidModal] = useState(false)

  // Auto-scroll to bottom when new activities arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [activities])

  const handleStart = async () => {
    await start({
      mode: 'paper',
      interval_seconds: intervalSeconds,
      symbols: selectedSymbols,
    })
  }

  const handleStop = async () => {
    await stop()
  }

  const handleReset = async () => {
    await reset()
  }

  const isRunning = status?.running || false

  return (
    <div className="flex flex-col h-full">
      {/* Hyperliquid Connection Banner */}
      {!hyperliquidAccount ? (
        <div className="p-3 border-b border-gray-800 bg-gradient-to-r from-blue-500/10 to-purple-500/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-lg">💧</span>
              <div>
                <div className="text-sm font-medium">Connect Hyperliquid</div>
                <div className="text-[10px] text-gray-400">Trade on the fastest DEX</div>
              </div>
            </div>
            <Button
              size="sm"
              className="bg-purple-600 hover:bg-purple-700 text-xs h-7"
              onClick={() => setShowHyperliquidModal(true)}
            >
              <Link className="w-3 h-3 mr-1" />
              Connect
            </Button>
          </div>
        </div>
      ) : (
        <div className="p-2 border-b border-gray-800 bg-green-500/5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm">💧</span>
              <div className="text-[10px]">
                <div className="flex items-center gap-1">
                  <span className="text-green-400">Connected</span>
                  <Badge className={`text-[8px] px-1 ${hyperliquidAccount.network === 'testnet' ? 'bg-green-500/20 text-green-400' : 'bg-purple-500/20 text-purple-400'}`}>
                    {hyperliquidAccount.network?.toUpperCase()}
                  </Badge>
                </div>
                <div className="font-mono text-gray-500">
                  {hyperliquidAccount.walletAddress?.slice(0, 6)}...{hyperliquidAccount.walletAddress?.slice(-4)}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-green-400 font-mono">
                ${hyperliquidAccount.balance.toLocaleString()}
              </span>
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-2 text-gray-400 hover:text-red-400"
                onClick={() => disconnectExchange(hyperliquidAccount.id)}
              >
                <Unlink className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4 text-purple-400" />
            <span className="font-semibold text-sm">Auto Trading</span>
            {isRunning && (
              <Badge className="bg-green-500/20 text-green-400 text-[10px] px-1.5">
                RUNNING
              </Badge>
            )}
          </div>
          
          {/* Connection indicator */}
          <div className="flex items-center gap-1">
            {connected ? (
              <Wifi className="w-3 h-3 text-green-400" />
            ) : connecting ? (
              <Wifi className="w-3 h-3 text-yellow-400 animate-pulse" />
            ) : (
              <WifiOff className="w-3 h-3 text-red-400" />
            )}
            <span className="text-[10px] text-gray-500">
              {connected ? 'Live' : connecting ? 'Connecting...' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Controls */}
        <div className="flex gap-2">
          {!isRunning ? (
            <Button
              size="sm"
              className="flex-1 bg-green-600 hover:bg-green-700 text-xs h-8"
              onClick={handleStart}
              disabled={!connected}
            >
              <Play className="w-3 h-3 mr-1" />
              Start
            </Button>
          ) : (
            <Button
              size="sm"
              variant="destructive"
              className="flex-1 text-xs h-8"
              onClick={handleStop}
            >
              <Square className="w-3 h-3 mr-1" />
              Stop
            </Button>
          )}
          
          <Button
            size="sm"
            variant="outline"
            className="h-8 px-2 border-gray-700"
            onClick={refreshStatus}
            disabled={isRunning}
          >
            <RefreshCw className="w-3 h-3" />
          </Button>
          
          <Button
            size="sm"
            variant="outline"
            className="h-8 px-2 border-gray-700"
            onClick={handleReset}
            disabled={isRunning}
          >
            <RotateCcw className="w-3 h-3" />
          </Button>
        </div>

        {/* Symbol Selection (only when not running) */}
        {!isRunning && (
          <div className="mt-2">
            <div className="flex flex-wrap gap-1">
              {['BTCUSDT', 'ETHUSDT', 'SOLUSDT'].map((symbol) => (
                <button
                  key={symbol}
                  onClick={() => {
                    setSelectedSymbols((prev) =>
                      prev.includes(symbol)
                        ? prev.filter((s) => s !== symbol)
                        : [...prev, symbol]
                    )
                  }}
                  className={`px-2 py-0.5 text-[10px] rounded-full transition-colors ${
                    selectedSymbols.includes(symbol)
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {symbol.replace('USDT', '')}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error display */}
        {error && (
          <div className="mt-2 p-2 bg-red-500/10 border border-red-500/30 rounded text-[10px] text-red-400">
            {error}
          </div>
        )}
      </div>

      {/* Stats */}
      {status && (
        <div className="p-2 border-b border-gray-800">
          <StatsBar
            totalTrades={status.total_trades}
            winningTrades={status.winning_trades}
            currentPnl={status.current_pnl}
            cyclesCompleted={status.cycles_completed}
          />
        </div>
      )}

      {/* Open Positions */}
      {status && status.positions.length > 0 && (
        <div className="p-2 border-b border-gray-800">
          <div className="text-[10px] text-gray-500 mb-1">Open Positions</div>
          <div className="space-y-1">
            {status.positions.map((pos) => (
              <div
                key={pos.id}
                className="flex items-center justify-between p-1.5 bg-gray-800/50 rounded text-[10px]"
              >
                <div className="flex items-center gap-2">
                  {pos.side === 'long' ? (
                    <TrendingUp className="w-3 h-3 text-green-400" />
                  ) : (
                    <TrendingDown className="w-3 h-3 text-red-400" />
                  )}
                  <span className="font-medium">{pos.symbol.replace('USDT', '')}</span>
                  <span className="text-gray-500">{pos.size.toFixed(4)}</span>
                </div>
                <span className={pos.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Activity Feed */}
      <ScrollArea className="flex-1 p-2" ref={scrollRef}>
        <div className="space-y-2">
          {activities.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-gray-500">
              <Bot className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-xs">No activity yet</p>
              <p className="text-[10px]">Start auto-trading to see live activity</p>
            </div>
          ) : (
            activities.map((entry) => (
              <ActivityItem key={entry.id} entry={entry} />
            ))
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="p-2 border-t border-gray-800 bg-gray-900/30">
        <div className="flex items-center justify-between text-[10px] text-gray-500">
          <span>
            Mode: <span className={hyperliquidAccount ? 'text-green-400' : 'text-purple-400'}>
              {hyperliquidAccount 
                ? (hyperliquidAccount.network === 'testnet' ? 'TESTNET' : 'LIVE') 
                : 'PAPER'}
            </span>
          </span>
          <span>
            Interval: {status?.config?.interval_seconds || intervalSeconds}s
          </span>
          <button
            onClick={clearActivities}
            className="text-gray-500 hover:text-white transition-colors"
          >
            Clear Log
          </button>
        </div>
      </div>

      {/* Hyperliquid Connect Modal */}
      <HyperliquidConnectModal
        open={showHyperliquidModal}
        onClose={() => setShowHyperliquidModal(false)}
      />
    </div>
  )
}

