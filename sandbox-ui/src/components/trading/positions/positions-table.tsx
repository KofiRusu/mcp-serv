'use client'

import { useState } from 'react'
import { useTradingStore } from '@/stores/trading-store'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Slider } from '@/components/ui/slider'
import { 
  X, 
  Edit, 
  TrendingUp,
  Shield,
  Target
} from 'lucide-react'

export function PositionsTable() {
  const { positions, closePosition, updatePosition, markets, setCurrentSymbol } = useTradingStore()
  const [editingPosition, setEditingPosition] = useState<string | null>(null)
  const [newSL, setNewSL] = useState<number[]>([0])
  const [newTP, setNewTP] = useState<number[]>([0])

  if (positions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <TrendingUp className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No open positions</p>
          <p className="text-xs mt-1">Place a trade to get started</p>
        </div>
      </div>
    )
  }

  const openEditModal = (positionId: string) => {
    const position = positions.find(p => p.id === positionId)
    if (position) {
      setNewSL([position.stopLoss || position.entryPrice * 0.95])
      setNewTP([position.takeProfit || position.entryPrice * 1.1])
      setEditingPosition(positionId)
    }
  }

  const saveChanges = () => {
    if (editingPosition) {
      updatePosition(editingPosition, {
        stopLoss: newSL[0],
        takeProfit: newTP[0],
      })
      setEditingPosition(null)
    }
  }

  const editPosition = positions.find(p => p.id === editingPosition)

  return (
    <>
      <table className="w-full text-sm">
        <thead className="bg-[#0d0d14] sticky top-0">
          <tr className="text-gray-500 text-xs">
            <th className="text-left p-3 font-medium">Symbol</th>
            <th className="text-left p-3 font-medium">Side</th>
            <th className="text-right p-3 font-medium">Size</th>
            <th className="text-right p-3 font-medium">Entry</th>
            <th className="text-right p-3 font-medium">Current</th>
            <th className="text-right p-3 font-medium">PnL</th>
            <th className="text-right p-3 font-medium">SL / TP</th>
            <th className="text-right p-3 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => {
            const market = markets.find(m => m.symbol === position.symbol)
            const currentPrice = market?.price || position.currentPrice
            const pnl = position.side === 'long'
              ? (currentPrice - position.entryPrice) * position.size
              : (position.entryPrice - currentPrice) * position.size
            const pnlPercent = (pnl / (position.entryPrice * position.size)) * 100

            return (
              <tr 
                key={position.id} 
                className="border-b border-gray-800 hover:bg-gray-900/50 cursor-pointer"
                onClick={() => setCurrentSymbol(position.symbol)}
              >
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-gray-800 flex items-center justify-center text-[10px] font-bold">
                      {position.symbol.slice(0, 2)}
                    </div>
                    <span className="font-medium">{position.symbol}</span>
                  </div>
                </td>
                <td className="p-3">
                  <Badge 
                    variant={position.side === 'long' ? 'default' : 'destructive'}
                    className="text-[10px]"
                  >
                    {position.side.toUpperCase()}
                  </Badge>
                </td>
                <td className="p-3 text-right font-mono">{position.size.toFixed(4)}</td>
                <td className="p-3 text-right font-mono">${position.entryPrice.toLocaleString()}</td>
                <td className="p-3 text-right font-mono">${currentPrice.toLocaleString()}</td>
                <td className="p-3 text-right">
                  <div className={`font-mono ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    <div>{pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}</div>
                    <div className="text-xs opacity-75">{pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%</div>
                  </div>
                </td>
                <td className="p-3 text-right">
                  <div className="text-xs font-mono">
                    {position.stopLoss && (
                      <div className="text-red-400">${position.stopLoss.toLocaleString()}</div>
                    )}
                    {position.takeProfit && (
                      <div className="text-green-400">${position.takeProfit.toLocaleString()}</div>
                    )}
                    {!position.stopLoss && !position.takeProfit && (
                      <span className="text-gray-500">-</span>
                    )}
                  </div>
                </td>
                <td className="p-3 text-right">
                  <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 text-gray-400 hover:text-white"
                      onClick={() => openEditModal(position.id)}
                    >
                      <Edit className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                      onClick={() => closePosition(position.id, currentPrice)}
                    >
                      <X className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {/* Edit Position Modal */}
      <Dialog open={!!editingPosition} onOpenChange={() => setEditingPosition(null)}>
        <DialogContent className="bg-[#0d0d14] border-gray-800 text-white">
          <DialogHeader>
            <DialogTitle>Edit Position - {editPosition?.symbol}</DialogTitle>
          </DialogHeader>
          
          {editPosition && (
            <div className="space-y-6 py-4">
              {/* Stop Loss */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-red-400" />
                  <span className="text-sm font-medium">Stop Loss</span>
                  <span className="ml-auto text-red-400 font-mono">${newSL[0].toFixed(2)}</span>
                </div>
                <Slider
                  value={newSL}
                  onValueChange={setNewSL}
                  min={editPosition.entryPrice * 0.8}
                  max={editPosition.entryPrice * 1.2}
                  step={1}
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>${(editPosition.entryPrice * 0.8).toFixed(0)}</span>
                  <span>Entry: ${editPosition.entryPrice.toFixed(0)}</span>
                  <span>${(editPosition.entryPrice * 1.2).toFixed(0)}</span>
                </div>
              </div>

              {/* Take Profit */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-green-400" />
                  <span className="text-sm font-medium">Take Profit</span>
                  <span className="ml-auto text-green-400 font-mono">${newTP[0].toFixed(2)}</span>
                </div>
                <Slider
                  value={newTP}
                  onValueChange={setNewTP}
                  min={editPosition.entryPrice * 0.8}
                  max={editPosition.entryPrice * 1.3}
                  step={1}
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>${(editPosition.entryPrice * 0.8).toFixed(0)}</span>
                  <span>Entry: ${editPosition.entryPrice.toFixed(0)}</span>
                  <span>${(editPosition.entryPrice * 1.3).toFixed(0)}</span>
                </div>
              </div>

              <Button onClick={saveChanges} className="w-full bg-purple-600 hover:bg-purple-700">
                Save Changes
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}

