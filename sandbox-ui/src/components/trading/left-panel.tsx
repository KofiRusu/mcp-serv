'use client'

import { useTradingStore } from '@/stores/trading-store'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { 
  TrendingUp, 
  Wallet, 
  BookOpen,
  Star,
  Globe,
  DollarSign,
  BarChart3
} from 'lucide-react'

export function LeftPanel() {
  const { 
    selectedTab, 
    setSelectedTab, 
    watchlists, 
    currentSymbol, 
    setCurrentSymbol,
    portfolio,
    positions,
    journal
  } = useTradingStore()

  return (
    <div className="w-64 border-r border-gray-800 bg-[#0d0d14] flex flex-col">
      <Tabs value={selectedTab} onValueChange={(v) => setSelectedTab(v as any)} className="flex-1 flex flex-col">
        <TabsList className="w-full justify-start gap-1 px-2 pt-2 bg-transparent border-b border-gray-800 rounded-none h-auto pb-2">
          <TabsTrigger 
            value="markets" 
            className="data-[state=active]:bg-purple-600 data-[state=active]:text-white px-3 py-1.5 text-sm"
          >
            <TrendingUp className="w-4 h-4 mr-1.5" />
            Markets
          </TabsTrigger>
          <TabsTrigger 
            value="portfolio"
            className="data-[state=active]:bg-purple-600 data-[state=active]:text-white px-3 py-1.5 text-sm"
          >
            <Wallet className="w-4 h-4 mr-1.5" />
            Portfolio
          </TabsTrigger>
          <TabsTrigger 
            value="journal"
            className="data-[state=active]:bg-purple-600 data-[state=active]:text-white px-3 py-1.5 text-sm"
          >
            <BookOpen className="w-4 h-4 mr-1.5" />
            Journal
          </TabsTrigger>
        </TabsList>

        {/* Markets Tab */}
        <TabsContent value="markets" className="flex-1 mt-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-2 space-y-4">
              {/* Favorites */}
              <div>
                <div className="flex items-center gap-2 px-2 py-1 text-xs font-semibold text-gray-500 uppercase">
                  <Star className="w-3 h-3" />
                  Favorites
                </div>
                <div className="space-y-0.5">
                  {watchlists.favorites?.map((item) => (
                    <WatchlistRow
                      key={item.symbol}
                      item={item}
                      isActive={currentSymbol === item.symbol}
                      onClick={() => setCurrentSymbol(item.symbol)}
                    />
                  ))}
                </div>
              </div>

              {/* Crypto */}
              <div>
                <div className="flex items-center gap-2 px-2 py-1 text-xs font-semibold text-gray-500 uppercase">
                  <Globe className="w-3 h-3" />
                  Crypto
                </div>
                <div className="space-y-0.5">
                  {watchlists.crypto?.map((item) => (
                    <WatchlistRow
                      key={item.symbol}
                      item={item}
                      isActive={currentSymbol === item.symbol}
                      onClick={() => setCurrentSymbol(item.symbol)}
                    />
                  ))}
                </div>
              </div>
            </div>
          </ScrollArea>
        </TabsContent>

        {/* Portfolio Tab */}
        <TabsContent value="portfolio" className="flex-1 mt-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-3 space-y-4">
              {/* Portfolio Summary */}
              <div className="bg-gray-900/50 rounded-lg p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Total Value</span>
                  <span className="text-lg font-bold">${portfolio.totalValue.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Today</span>
                  <span className={`font-medium ${portfolio.dayPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {portfolio.dayPnl >= 0 ? '+' : ''}{portfolio.dayPnlPercent.toFixed(2)}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Win Rate</span>
                  <span className="font-medium text-amber-400">{portfolio.winRate}%</span>
                </div>
              </div>

              {/* Open Positions Mini */}
              <div>
                <div className="flex items-center justify-between px-1 mb-2">
                  <span className="text-xs font-semibold text-gray-500 uppercase">Positions</span>
                  <Badge variant="secondary" className="text-xs">{positions.length}</Badge>
                </div>
                <div className="space-y-1">
                  {positions.slice(0, 5).map((pos) => (
                    <div
                      key={pos.id}
                      className="flex items-center justify-between p-2 bg-gray-900/50 rounded-lg cursor-pointer hover:bg-gray-800/50"
                      onClick={() => setCurrentSymbol(pos.symbol)}
                    >
                      <div className="flex items-center gap-2">
                        <Badge variant={pos.side === 'long' ? 'default' : 'destructive'} className="text-[10px] px-1.5">
                          {pos.side.toUpperCase()}
                        </Badge>
                        <span className="text-sm font-medium">{pos.symbol}</span>
                      </div>
                      <span className={`text-sm font-mono ${pos.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {pos.pnl >= 0 ? '+' : ''}{pos.pnlPercent.toFixed(2)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </ScrollArea>
        </TabsContent>

        {/* Journal Tab */}
        <TabsContent value="journal" className="flex-1 mt-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-3 space-y-2">
              {journal.slice(0, 10).map((entry) => (
                <div
                  key={entry.id}
                  className="p-3 bg-gray-900/50 rounded-lg cursor-pointer hover:bg-gray-800/50 transition-colors"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="outline" className="text-[10px]">
                      {entry.type}
                    </Badge>
                    <span className="text-xs text-gray-500">
                      {new Date(entry.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="text-sm font-medium line-clamp-1">{entry.title}</div>
                  <div className="text-xs text-gray-500 line-clamp-2 mt-1">{entry.content}</div>
                </div>
              ))}
              {journal.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No journal entries yet</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  )
}

interface WatchlistRowProps {
  item: { symbol: string; name: string; price: number; change24h: number }
  isActive: boolean
  onClick: () => void
}

function WatchlistRow({ item, isActive, onClick }: WatchlistRowProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between px-2 py-2 rounded-lg transition-colors ${
        isActive 
          ? 'bg-purple-600/20 border border-purple-500/30' 
          : 'hover:bg-gray-800/50'
      }`}
    >
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-gray-800 flex items-center justify-center text-[10px] font-bold">
          {item.symbol.slice(0, 2)}
        </div>
        <div className="text-left">
          <div className="text-sm font-medium">{item.symbol.replace('USDT', '')}</div>
          <div className="text-[10px] text-gray-500">{item.name}</div>
        </div>
      </div>
      <div className="text-right">
        <div className="text-sm font-mono">${item.price.toLocaleString()}</div>
        <div className={`text-[10px] ${item.change24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {item.change24h >= 0 ? '+' : ''}{item.change24h.toFixed(2)}%
        </div>
      </div>
    </button>
  )
}

