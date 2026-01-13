'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Database,
  Download,
  RefreshCw,
  History,
  MessageSquare,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Activity,
  ChevronRight,
  Calendar,
  Trash2,
  FileJson,
  Brain,
  Sparkles,
} from 'lucide-react'
import { useTradingStore } from '@/stores/trading-store'
import { useTrainingData } from '@/hooks/use-training-data'

type TabType = 'backtests' | 'conversations' | 'interactions' | 'market' | 'training'

interface ConversationLog {
  timestamp: string
  sessionId: string
  model: string
  context: {
    symbol: string
    mode: string
    positionCount: number
    balance: number
  }
  conversation: {
    user: string
    assistant: string
  }
}

interface InteractionLog {
  id: string
  type: string
  timestamp: string
  sessionId: string
  data: Record<string, any>
}

interface MarketDataSummary {
  symbol: string
  date: string
  types: string[]
  size: number
}

export function DataDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('backtests')
  const [loading, setLoading] = useState(false)
  const [conversations, setConversations] = useState<ConversationLog[]>([])
  const [interactions, setInteractions] = useState<InteractionLog[]>([])
  const [marketData, setMarketData] = useState<MarketDataSummary[]>([])
  
  const { backtestHistory, loadBacktestHistory } = useTradingStore()
  const { stats: trainingStats, downloadTrainingData, refreshStats: refreshTrainingStats, loading: trainingLoading } = useTrainingData()
  
  // Load data based on active tab
  useEffect(() => {
    if (activeTab === 'backtests') {
      loadBacktestHistory()
    } else if (activeTab === 'conversations') {
      loadConversations()
    } else if (activeTab === 'interactions') {
      loadInteractions()
    } else if (activeTab === 'market') {
      loadMarketData()
    }
  }, [activeTab, loadBacktestHistory])
  
  const loadConversations = async () => {
    setLoading(true)
    try {
      const today = new Date().toISOString().slice(0, 10)
      const response = await fetch(`/api/conversations?date=${today}`)
      if (response.ok) {
        const data = await response.json()
        setConversations(data.conversations || [])
      }
    } catch (error) {
      console.error('Failed to load conversations:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const loadInteractions = async () => {
    setLoading(true)
    try {
      const today = new Date().toISOString().slice(0, 10)
      const response = await fetch(`/api/interactions/log?date=${today}&limit=50`)
      if (response.ok) {
        const data = await response.json()
        setInteractions(data.logs || [])
      }
    } catch (error) {
      console.error('Failed to load interactions:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const loadMarketData = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/market-data/summary')
      if (response.ok) {
        const data = await response.json()
        setMarketData(data.summary || [])
      }
    } catch (error) {
      console.error('Failed to load market data:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const exportData = async (type: string) => {
    try {
      let data: any
      let filename: string
      
      switch (type) {
        case 'backtests':
          data = backtestHistory
          filename = `backtests-${new Date().toISOString().slice(0, 10)}.json`
          break
        case 'conversations':
          data = conversations
          filename = `conversations-${new Date().toISOString().slice(0, 10)}.json`
          break
        case 'interactions':
          data = interactions
          filename = `interactions-${new Date().toISOString().slice(0, 10)}.json`
          break
        default:
          return
      }
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
    }
  }
  
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  
  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : ''
    return `${sign}${(value * 100).toFixed(2)}%`
  }
  
  return (
    <div className="flex flex-col h-full bg-[#0d0d14] text-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Database className="w-5 h-5 text-purple-400" />
          <span className="font-semibold">Data History</span>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => exportData(activeTab)}
          className="text-gray-400 hover:text-white"
        >
          <Download className="w-4 h-4 mr-1" />
          Export
        </Button>
      </div>
      
      {/* Tab Navigation */}
      <div className="flex border-b border-gray-800">
        {[
          { id: 'backtests', label: 'Backtests', icon: BarChart3, count: backtestHistory.length },
          { id: 'conversations', label: 'Chats', icon: MessageSquare, count: conversations.length },
          { id: 'interactions', label: 'Activity', icon: Activity, count: interactions.length },
          { id: 'market', label: 'Market', icon: FileJson, count: marketData.length },
          { id: 'training', label: 'Training', icon: Brain, count: trainingStats?.total || 0 },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as TabType)}
            className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === tab.id
                ? 'text-purple-400 border-b-2 border-purple-400 bg-purple-500/5'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <tab.icon className="w-3.5 h-3.5 mx-auto mb-1" />
            <span className="block">{tab.label}</span>
            {tab.count > 0 && (
              <Badge variant="secondary" className="text-[10px] px-1 py-0 ml-1">
                {tab.count}
              </Badge>
            )}
          </button>
        ))}
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-5 h-5 animate-spin text-gray-500" />
          </div>
        ) : (
          <>
            {/* Backtests Tab */}
            {activeTab === 'backtests' && (
              <>
                {backtestHistory.length === 0 ? (
                  <EmptyState icon={BarChart3} message="No backtests yet" />
                ) : (
                  backtestHistory.map((bt) => (
                    <div
                      key={bt.id}
                      className="p-3 rounded-lg border border-gray-800 bg-gray-900/50 hover:bg-gray-900 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {bt.metrics.totalReturn >= 0 
                            ? <TrendingUp className="w-4 h-4 text-green-400" />
                            : <TrendingDown className="w-4 h-4 text-red-400" />
                          }
                          <span className={`font-medium ${
                            bt.metrics.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {formatPercent(bt.metrics.totalReturn)}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500">
                          {formatTime(bt.endTime)}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                          <span className="text-gray-500">Trades</span>
                          <span className="block font-medium">{bt.metrics.totalTrades}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Win Rate</span>
                          <span className="block font-medium">{formatPercent(bt.metrics.winRate)}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Sharpe</span>
                          <span className="block font-medium">{bt.metrics.sharpeRatio.toFixed(2)}</span>
                        </div>
                      </div>
                      <div className="mt-2 text-[10px] text-gray-600">
                        {bt.config.symbols.join(', ')} • {bt.config.days}d • {bt.config.timeframe}
                      </div>
                    </div>
                  ))
                )}
              </>
            )}
            
            {/* Conversations Tab */}
            {activeTab === 'conversations' && (
              <>
                {conversations.length === 0 ? (
                  <EmptyState icon={MessageSquare} message="No conversations today" />
                ) : (
                  conversations.map((conv, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg border border-gray-800 bg-gray-900/50"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant="outline" className="text-[10px]">
                          {conv.model}
                        </Badge>
                        <span className="text-xs text-gray-500">
                          {formatTime(conv.timestamp)}
                        </span>
                      </div>
                      <div className="space-y-2">
                        <div className="text-xs">
                          <span className="text-gray-500">User: </span>
                          <span className="text-gray-300 line-clamp-2">
                            {conv.conversation.user}
                          </span>
                        </div>
                        <div className="text-xs">
                          <span className="text-purple-400">AI: </span>
                          <span className="text-gray-400 line-clamp-2">
                            {conv.conversation.assistant}
                          </span>
                        </div>
                      </div>
                      <div className="mt-2 text-[10px] text-gray-600">
                        {conv.context.symbol} • {conv.context.mode} mode
                      </div>
                    </div>
                  ))
                )}
              </>
            )}
            
            {/* Interactions Tab */}
            {activeTab === 'interactions' && (
              <>
                {interactions.length === 0 ? (
                  <EmptyState icon={Activity} message="No activity logged today" />
                ) : (
                  interactions.map((log) => (
                    <div
                      key={log.id}
                      className="p-2 rounded border border-gray-800 bg-gray-900/30 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <Badge 
                          variant="outline" 
                          className={`text-[10px] ${
                            log.type.includes('error') ? 'text-red-400 border-red-400/50' :
                            log.type.includes('completed') ? 'text-green-400 border-green-400/50' :
                            'text-gray-400'
                          }`}
                        >
                          {log.type}
                        </Badge>
                        <span className="text-gray-500">
                          {formatTime(log.timestamp)}
                        </span>
                      </div>
                      {log.data && Object.keys(log.data).length > 0 && (
                        <div className="mt-1 text-gray-500 truncate">
                          {JSON.stringify(log.data).slice(0, 100)}...
                        </div>
                      )}
                    </div>
                  ))
                )}
              </>
            )}
            
            {/* Market Data Tab */}
            {activeTab === 'market' && (
              <>
                {marketData.length === 0 ? (
                  <EmptyState icon={FileJson} message="No market data recorded" />
                ) : (
                  marketData.map((data, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg border border-gray-800 bg-gray-900/50"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">{data.symbol}</span>
                        <span className="text-xs text-gray-500">{data.date}</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {data.types.map(type => (
                          <Badge key={type} variant="secondary" className="text-[10px]">
                            {type}
                          </Badge>
                        ))}
                      </div>
                      <div className="mt-2 text-[10px] text-gray-500">
                        {(data.size / 1024).toFixed(1)} KB
                      </div>
                    </div>
                  ))
                )}
              </>
            )}

            {/* Training Data Tab */}
            {activeTab === 'training' && (
              <>
                {/* Training Stats Summary */}
                <div className="p-3 rounded-lg border border-purple-500/30 bg-purple-500/10 mb-3">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="w-5 h-5 text-purple-400" />
                    <span className="font-semibold text-purple-300">PersRM Training Data</span>
                  </div>
                  
                  {trainingStats ? (
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-gray-500 text-xs">Total Examples</span>
                        <p className="font-medium text-lg">{trainingStats.total}</p>
                      </div>
                      <div>
                        <span className="text-gray-500 text-xs">Win Rate</span>
                        <p className="font-medium text-lg text-green-400">{trainingStats.winRate}</p>
                      </div>
                      <div>
                        <span className="text-gray-500 text-xs">High Quality</span>
                        <p className="font-medium">{trainingStats.highQuality}</p>
                      </div>
                      <div>
                        <span className="text-gray-500 text-xs">Pending Outcomes</span>
                        <p className="font-medium">{trainingStats.pendingOutcomes}</p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm">Loading stats...</p>
                  )}
                </div>

                {/* By Type */}
                {trainingStats && (
                  <div className="p-3 rounded-lg border border-gray-800 bg-gray-900/50 mb-3">
                    <h4 className="text-xs font-medium text-gray-400 mb-2">By Type</h4>
                    <div className="space-y-1">
                      {Object.entries(trainingStats.byType).map(([type, count]) => (
                        <div key={type} className="flex justify-between text-xs">
                          <span className="text-gray-400">{type.replace('_', ' ')}</span>
                          <span className="text-gray-200">{count as number}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* By Source */}
                {trainingStats && (
                  <div className="p-3 rounded-lg border border-gray-800 bg-gray-900/50 mb-3">
                    <h4 className="text-xs font-medium text-gray-400 mb-2">By Source</h4>
                    <div className="space-y-1">
                      {Object.entries(trainingStats.bySource).map(([source, count]) => (
                        <div key={source} className="flex justify-between text-xs">
                          <span className="text-gray-400">{source.replace('_', ' ')}</span>
                          <span className="text-gray-200">{count as number}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="space-y-2">
                  <Button
                    size="sm"
                    onClick={downloadTrainingData}
                    disabled={trainingLoading || (trainingStats?.total || 0) === 0}
                    className="w-full bg-purple-600 hover:bg-purple-700"
                  >
                    {trainingLoading ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Download className="w-4 h-4 mr-2" />
                    )}
                    Download for Training
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={refreshTrainingStats}
                    className="w-full"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Refresh Stats
                  </Button>
                </div>

                {/* Info */}
                <div className="mt-3 p-2 rounded bg-gray-900 text-[10px] text-gray-500">
                  <p>Training data is automatically collected from:</p>
                  <ul className="list-disc list-inside mt-1 space-y-0.5">
                    <li>AI Assistant conversations</li>
                    <li>Trade decisions & outcomes</li>
                    <li>Backtest results</li>
                    <li>Paper trading sessions</li>
                  </ul>
                </div>
              </>
            )}
          </>
        )}
      </div>
      
      {/* Footer */}
      <div className="p-2 border-t border-gray-800 text-center">
        <span className="text-[10px] text-gray-600">
          Data is automatically saved and persists across sessions
        </span>
      </div>
    </div>
  )
}

// Empty state component
function EmptyState({ icon: Icon, message }: { icon: any; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-gray-500">
      <Icon className="w-8 h-8 mb-2 opacity-50" />
      <span className="text-sm">{message}</span>
    </div>
  )
}

