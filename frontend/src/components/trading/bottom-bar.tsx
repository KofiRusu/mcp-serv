'use client'

import { useTradingStore } from '@/stores/trading-store'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  FlaskConical, 
  TrendingUp, 
  TrendingDown,
  Activity
} from 'lucide-react'
import Link from 'next/link'

export function BottomBar() {
  const { portfolio, positions, mode, isLabOpen, setLabOpen } = useTradingStore()

  // Calculate total unrealized PnL
  const totalPnl = positions.reduce((sum, p) => sum + p.pnl, 0)

  return (
    <div className="h-10 border-t border-gray-800 bg-[#0d0d14] flex items-center px-4 justify-between text-xs">
      {/* Left: Strategy info */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-gray-500">
          <Activity className="w-3.5 h-3.5" />
          <span>Positions: <span className="text-white font-medium">{positions.length}</span></span>
        </div>

        {positions.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Unrealized:</span>
            <span className={`font-mono font-medium ${totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)} USDT
            </span>
          </div>
        )}
      </div>

      {/* Center: PnL sparkline */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-gray-500">Today:</span>
          <div className={`flex items-center gap-1 font-mono font-medium ${portfolio.dayPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {portfolio.dayPnl >= 0 ? (
              <TrendingUp className="w-3 h-3" />
            ) : (
              <TrendingDown className="w-3 h-3" />
            )}
            {portfolio.dayPnl >= 0 ? '+' : ''}{portfolio.dayPnlPercent.toFixed(2)}%
          </div>
        </div>

        {/* Mini sparkline placeholder */}
        <div className="w-20 h-4 bg-gray-800 rounded overflow-hidden flex items-end gap-px px-0.5">
          {[40, 45, 42, 48, 52, 50, 55, 58, 54, 60].map((h, i) => (
            <div
              key={i}
              className={`w-1.5 ${h > 50 ? 'bg-green-500' : 'bg-red-500'}`}
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      </div>

      {/* Right: Mode & Lab button */}
      <div className="flex items-center gap-3">
        <Badge 
          variant="outline" 
          className={`text-[10px] ${
            mode === 'live' 
              ? 'border-green-500 text-green-400' 
              : mode === 'paper' 
                ? 'border-amber-500 text-amber-400' 
                : 'border-gray-600 text-gray-400'
          }`}
        >
          {mode.toUpperCase()} MODE
        </Badge>

        <Link href="/trading/lab">
          <Button 
            size="sm" 
            variant="outline" 
            className="h-7 text-xs border-purple-500/50 text-purple-400 hover:bg-purple-500/10"
          >
            <FlaskConical className="w-3 h-3 mr-1.5" />
            Open Algo Lab
          </Button>
        </Link>
      </div>
    </div>
  )
}

