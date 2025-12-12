'use client'

import { useState, useEffect, useCallback } from 'react'
import { useTradingStore } from '@/stores/trading-store'
import { TradingChart } from './chart/trading-chart'
import { OrderTicket } from './order-ticket/order-ticket'
import { PositionsTable } from './positions/positions-table'
import { OrderBook } from './chart/order-book'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { 
  CandlestickChart, 
  Book, 
  History,
  ListOrdered,
  TrendingUp,
  RefreshCw,
  Clock,
  FileText
} from 'lucide-react'

interface LiveTicker {
  symbol: string
  last: number
  high: number
  low: number
  volume: number
  change: number
  percentage: number
}

export function CenterPanel() {
  const { currentSymbol, positions, orders } = useTradingStore()
  const [chartTab, setChartTab] = useState<'depth' | 'trades'>('depth')
  const [ticker, setTicker] = useState<LiveTicker | null>(null)
  const [tickerLoading, setTickerLoading] = useState(true)
  const [timeframe, setTimeframe] = useState('1h')

  const fetchTicker = useCallback(async () => {
    try {
      const response = await fetch(`/api/market?action=ticker&symbol=${currentSymbol}`)
      if (!response.ok) throw new Error('Failed to fetch ticker')
      const data = await response.json()
      setTicker({
        symbol: data.symbol,
        last: data.last,
        high: data.high,
        low: data.low,
        volume: data.volume,
        change: data.change,
        percentage: data.percentage,
      })
      setTickerLoading(false)
    } catch (err) {
      console.error('Error fetching ticker:', err)
      setTickerLoading(false)
    }
  }, [currentSymbol])

  // Fetch ticker on mount and every 5 seconds
  useEffect(() => {
    fetchTicker()
    const interval = setInterval(fetchTicker, 5000)
    return () => clearInterval(interval)
  }, [fetchTicker])

  const openOrders = orders.filter(o => o.status === 'pending')

  return (
    <div className="h-full flex-1 flex flex-col bg-[#0a0a0f] min-w-0 overflow-hidden">
      {/* Chart Area - fills remaining space */}
      <div className="flex flex-1 min-w-0 overflow-hidden">
        {/* Main Chart */}
        <div className="flex flex-col border-r border-gray-800 flex-1 min-w-0 overflow-hidden">
          {/* Timeframe Selector - compact bar */}
          <div className="flex-shrink-0 flex items-center justify-between px-3 py-1.5 border-b border-gray-800 bg-[#0d0d14]">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">{currentSymbol}</span>
              {ticker && (
                <Badge variant={ticker.percentage >= 0 ? 'default' : 'destructive'} className="text-[10px]">
                  {ticker.percentage >= 0 ? '+' : ''}{ticker.percentage.toFixed(2)}%
                </Badge>
              )}
            </div>
            {/* Timeframe Selector */}
            <div className="flex items-center gap-0.5 bg-gray-900 rounded p-0.5">
              {['1m', '5m', '15m', '1H', '4H', '1D'].map((tf) => {
                const apiTimeframe = tf === '1H' ? '1h' : tf === '4H' ? '4h' : tf === '1D' ? '1d' : tf.toLowerCase()
                const isActive = timeframe === apiTimeframe
                return (
                  <button
                    key={tf}
                    onClick={() => setTimeframe(apiTimeframe)}
                    className={`px-2 py-0.5 text-[10px] font-medium rounded transition-colors ${
                      isActive
                        ? 'bg-purple-600 text-white'
                        : 'hover:bg-gray-800 text-gray-400 hover:text-white'
                    }`}
                  >
                    {tf}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Chart - flex-1 to fill available space */}
          <div className="flex-1 overflow-hidden">
            <TradingChart symbol={currentSymbol} timeframe={timeframe} />
          </div>
        </div>

        {/* Order Book / Recent Trades */}
        <div className="w-48 flex-shrink-0 flex flex-col border-r border-gray-800 bg-[#0d0d14] overflow-hidden">
          <Tabs value={chartTab} onValueChange={(v) => setChartTab(v as any)} className="flex-1 flex flex-col">
            <TabsList className="w-full justify-start gap-1 px-2 pt-2 bg-transparent rounded-none h-auto pb-2 border-b border-gray-800">
              <TabsTrigger 
                value="depth"
                className="data-[state=active]:bg-gray-800 px-3 py-1 text-xs"
              >
                <Book className="w-3 h-3 mr-1" />
                Order Book
              </TabsTrigger>
              <TabsTrigger 
                value="trades"
                className="data-[state=active]:bg-gray-800 px-3 py-1 text-xs"
              >
                <History className="w-3 h-3 mr-1" />
                Trades
              </TabsTrigger>
            </TabsList>

            <TabsContent value="depth" className="flex-1 mt-0 overflow-hidden">
              <OrderBook symbol={currentSymbol} />
            </TabsContent>

            <TabsContent value="trades" className="flex-1 mt-0">
              <RecentTrades symbol={currentSymbol} />
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Bottom Section: Order Ticket + Positions */}
      <div className="flex h-[200px] flex-shrink-0 border-t border-gray-800 overflow-hidden">
        {/* Order Ticket */}
        <div className="w-60 flex-shrink-0 border-r border-gray-800 overflow-y-auto">
          <OrderTicket />
        </div>

        {/* Positions & Orders */}
        <div className="flex-1 flex flex-col">
          <Tabs defaultValue="positions" className="flex-1 flex flex-col">
            <TabsList className="w-full justify-start gap-1 px-4 pt-2 bg-[#0d0d14] rounded-none h-auto pb-2 border-b border-gray-800">
              <TabsTrigger 
                value="positions"
                className="data-[state=active]:bg-gray-800 px-3 py-1.5 text-xs"
              >
                <TrendingUp className="w-3 h-3 mr-1.5" />
                Positions
                {positions.length > 0 && (
                  <Badge variant="secondary" className="ml-1.5 text-[10px] px-1.5">{positions.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger 
                value="orders"
                className="data-[state=active]:bg-gray-800 px-3 py-1.5 text-xs"
              >
                <ListOrdered className="w-3 h-3 mr-1.5" />
                Orders
                {openOrders.length > 0 && (
                  <Badge variant="secondary" className="ml-1.5 text-[10px] px-1.5">{openOrders.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger 
                value="position-history"
                className="data-[state=active]:bg-gray-800 px-3 py-1.5 text-xs"
              >
                <Clock className="w-3 h-3 mr-1.5" />
                Position History
              </TabsTrigger>
              <TabsTrigger 
                value="order-history"
                className="data-[state=active]:bg-gray-800 px-3 py-1.5 text-xs"
              >
                <FileText className="w-3 h-3 mr-1.5" />
                Order History
              </TabsTrigger>
            </TabsList>

            <TabsContent value="positions" className="flex-1 mt-0 overflow-auto">
              <PositionsTable />
            </TabsContent>

            <TabsContent value="orders" className="flex-1 mt-0 overflow-auto">
              <OrdersTable />
            </TabsContent>

            <TabsContent value="position-history" className="flex-1 mt-0 overflow-auto">
              <PositionHistoryTable />
            </TabsContent>

            <TabsContent value="order-history" className="flex-1 mt-0 overflow-auto">
              <OrderHistoryTable />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}

function RecentTrades({ symbol }: { symbol: string }) {
  const [trades, setTrades] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const fetchTrades = useCallback(async () => {
    try {
      const response = await fetch(`/api/market?action=trades&symbol=${symbol}&limit=20`)
      if (!response.ok) throw new Error('Failed to fetch trades')
      const data = await response.json()
      setTrades(data.trades || [])
      setLoading(false)
    } catch (err) {
      console.error('Error fetching trades:', err)
      setLoading(false)
    }
  }, [symbol])

  useEffect(() => {
    fetchTrades()
    const interval = setInterval(fetchTrades, 5000)
    return () => clearInterval(interval)
  }, [fetchTrades])

  if (loading && trades.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <RefreshCw className="w-5 h-5 animate-spin" />
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-[#0d0d14]">
          <tr className="text-gray-500">
            <th className="text-left p-2 font-medium">Price</th>
            <th className="text-right p-2 font-medium">Size</th>
            <th className="text-right p-2 font-medium">Time</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade, i) => (
            <tr key={trade.id || i} className="hover:bg-gray-900/50">
              <td className={`p-2 font-mono ${trade.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                ${trade.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </td>
              <td className="p-2 text-right font-mono text-gray-400">
                {trade.amount.toFixed(4)}
              </td>
              <td className="p-2 text-right text-gray-500">
                {new Date(trade.timestamp).toLocaleTimeString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function OrdersTable() {
  const { orders, cancelOrder } = useTradingStore()
  const openOrders = orders.filter(o => o.status === 'pending')

  if (openOrders.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <ListOrdered className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No open orders</p>
        </div>
      </div>
    )
  }

  return (
    <table className="w-full text-sm">
      <thead className="bg-[#0d0d14] sticky top-0">
        <tr className="text-gray-500 text-xs">
          <th className="text-left p-3 font-medium">Symbol</th>
          <th className="text-left p-3 font-medium">Type</th>
          <th className="text-left p-3 font-medium">Side</th>
          <th className="text-right p-3 font-medium">Size</th>
          <th className="text-right p-3 font-medium">Price</th>
          <th className="text-right p-3 font-medium">Actions</th>
        </tr>
      </thead>
      <tbody>
        {openOrders.map((order) => (
          <tr key={order.id} className="border-b border-gray-800 hover:bg-gray-900/50">
            <td className="p-3 font-medium">{order.symbol}</td>
            <td className="p-3 text-gray-400">{order.type}</td>
            <td className="p-3">
              <Badge variant={order.side === 'buy' ? 'default' : 'destructive'}>
                {order.side.toUpperCase()}
              </Badge>
            </td>
            <td className="p-3 text-right font-mono">{order.size}</td>
            <td className="p-3 text-right font-mono">${order.price?.toLocaleString() || 'Market'}</td>
            <td className="p-3 text-right">
              <button
                onClick={() => cancelOrder(order.id)}
                className="text-red-400 hover:text-red-300 text-xs"
              >
                Cancel
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function PositionHistoryTable() {
  const { positionHistory } = useTradingStore()
  const history = positionHistory || []

  if (history.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No position history</p>
          <p className="text-xs text-gray-600 mt-1">Closed positions will appear here</p>
        </div>
      </div>
    )
  }

  return (
    <table className="w-full text-sm">
      <thead className="bg-[#0d0d14] sticky top-0">
        <tr className="text-gray-500 text-xs">
          <th className="text-left p-3 font-medium">Symbol</th>
          <th className="text-left p-3 font-medium">Side</th>
          <th className="text-right p-3 font-medium">Entry</th>
          <th className="text-right p-3 font-medium">Exit</th>
          <th className="text-right p-3 font-medium">Size</th>
          <th className="text-right p-3 font-medium">P&L</th>
          <th className="text-right p-3 font-medium">Closed</th>
        </tr>
      </thead>
      <tbody>
        {history.map((pos: any) => (
          <tr key={pos.id} className="border-b border-gray-800 hover:bg-gray-900/50">
            <td className="p-3 font-medium">{pos.symbol}</td>
            <td className="p-3">
              <Badge variant={pos.side === 'long' ? 'default' : 'destructive'}>
                {pos.side?.toUpperCase()}
              </Badge>
            </td>
            <td className="p-3 text-right font-mono">${pos.entryPrice?.toLocaleString()}</td>
            <td className="p-3 text-right font-mono">${pos.exitPrice?.toLocaleString()}</td>
            <td className="p-3 text-right font-mono">{pos.size}</td>
            <td className={`p-3 text-right font-mono ${(pos.pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {(pos.pnl || 0) >= 0 ? '+' : ''}{pos.pnlPercent?.toFixed(2)}%
            </td>
            <td className="p-3 text-right text-gray-500 text-xs">
              {pos.closedAt ? new Date(pos.closedAt).toLocaleDateString() : '-'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function OrderHistoryTable() {
  const { orderHistory } = useTradingStore()
  const history = orderHistory || []

  if (history.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No order history</p>
          <p className="text-xs text-gray-600 mt-1">Filled and cancelled orders will appear here</p>
        </div>
      </div>
    )
  }

  return (
    <table className="w-full text-sm">
      <thead className="bg-[#0d0d14] sticky top-0">
        <tr className="text-gray-500 text-xs">
          <th className="text-left p-3 font-medium">Symbol</th>
          <th className="text-left p-3 font-medium">Type</th>
          <th className="text-left p-3 font-medium">Side</th>
          <th className="text-right p-3 font-medium">Size</th>
          <th className="text-right p-3 font-medium">Price</th>
          <th className="text-left p-3 font-medium">Status</th>
          <th className="text-right p-3 font-medium">Time</th>
        </tr>
      </thead>
      <tbody>
        {history.map((order: any) => (
          <tr key={order.id} className="border-b border-gray-800 hover:bg-gray-900/50">
            <td className="p-3 font-medium">{order.symbol}</td>
            <td className="p-3 text-gray-400">{order.type}</td>
            <td className="p-3">
              <Badge variant={order.side === 'buy' ? 'default' : 'destructive'}>
                {order.side?.toUpperCase()}
              </Badge>
            </td>
            <td className="p-3 text-right font-mono">{order.size}</td>
            <td className="p-3 text-right font-mono">${order.price?.toLocaleString() || 'Market'}</td>
            <td className="p-3">
              <Badge variant={order.status === 'filled' ? 'default' : 'secondary'} className="text-[10px]">
                {order.status?.toUpperCase()}
              </Badge>
            </td>
            <td className="p-3 text-right text-gray-500 text-xs">
              {order.filledAt ? new Date(order.filledAt).toLocaleString() : '-'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
