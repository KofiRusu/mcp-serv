'use client'

import { useState } from 'react'
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
  TrendingUp
} from 'lucide-react'

export function CenterPanel() {
  const { currentSymbol, positions, orders, markets } = useTradingStore()
  const [chartTab, setChartTab] = useState<'depth' | 'trades'>('depth')

  const currentMarket = markets.find(m => m.symbol === currentSymbol)

  const openOrders = orders.filter(o => o.status === 'pending')

  return (
    <div className="flex-1 flex flex-col bg-[#0a0a0f] overflow-hidden">
      {/* Chart Area */}
      <div className="flex-1 flex min-h-0">
        {/* Main Chart */}
        <div className="flex-1 flex flex-col border-r border-gray-800">
          {/* Chart Header */}
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-[#0d0d14]">
            <div className="flex items-center gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold">{currentSymbol}</span>
                  {currentMarket && (
                    <Badge variant={currentMarket.change24h >= 0 ? 'default' : 'destructive'} className="text-xs">
                      {currentMarket.change24h >= 0 ? '+' : ''}{currentMarket.change24h.toFixed(2)}%
                    </Badge>
                  )}
                </div>
                {currentMarket && (
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>H: ${currentMarket.high24h.toLocaleString()}</span>
                    <span>L: ${currentMarket.low24h.toLocaleString()}</span>
                    <span>Vol: ${(currentMarket.volume24h / 1e9).toFixed(2)}B</span>
                  </div>
                )}
              </div>
            </div>

            {/* Timeframe Selector */}
            <div className="flex items-center gap-1 bg-gray-900 rounded-lg p-0.5">
              {['1m', '5m', '15m', '1H', '4H', '1D'].map((tf) => (
                <button
                  key={tf}
                  className="px-2.5 py-1 text-xs font-medium rounded-md hover:bg-gray-800 transition-colors text-gray-400 hover:text-white"
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Chart */}
          <div className="flex-1 min-h-0">
            <TradingChart symbol={currentSymbol} />
          </div>
        </div>

        {/* Order Book / Recent Trades */}
        <div className="w-72 flex flex-col border-r border-gray-800 bg-[#0d0d14]">
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
      <div className="h-80 border-t border-gray-800 flex">
        {/* Order Ticket */}
        <div className="w-80 border-r border-gray-800">
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
            </TabsList>

            <TabsContent value="positions" className="flex-1 mt-0 overflow-auto">
              <PositionsTable />
            </TabsContent>

            <TabsContent value="orders" className="flex-1 mt-0 overflow-auto">
              <OrdersTable />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}

function RecentTrades({ symbol }: { symbol: string }) {
  // Mock recent trades
  const trades = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    price: 67500 + (Math.random() - 0.5) * 200,
    size: Math.random() * 2,
    side: Math.random() > 0.5 ? 'buy' : 'sell',
    time: new Date(Date.now() - i * 5000).toLocaleTimeString(),
  }))

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
          {trades.map((trade) => (
            <tr key={trade.id} className="hover:bg-gray-900/50">
              <td className={`p-2 font-mono ${trade.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                ${trade.price.toFixed(2)}
              </td>
              <td className="p-2 text-right font-mono text-gray-400">
                {trade.size.toFixed(4)}
              </td>
              <td className="p-2 text-right text-gray-500">
                {trade.time}
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

