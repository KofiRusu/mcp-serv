'use client'

import { useState, useMemo } from 'react'
import { useTradingStore, OrderSide, OrderType } from '@/stores/trading-store'
import { useLivePrices } from '@/hooks/use-live-prices'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle,
  Shield,
  Target,
  Percent
} from 'lucide-react'

export function OrderTicket() {
  const { 
    currentSymbol, 
    markets, 
    accounts, 
    currentAccountId,
    mode,
    addPosition,
    addOrder
  } = useTradingStore()

  // Use live prices for accurate order calculations
  const { getPrice } = useLivePrices({ refreshInterval: 5000 })

  const [side, setSide] = useState<OrderSide>('buy')
  const [orderType, setOrderType] = useState<OrderType>('market')
  const [amount, setAmount] = useState('')
  const [limitPrice, setLimitPrice] = useState('')
  const [useSlider, setUseSlider] = useState(true)
  const [sliderValue, setSliderValue] = useState([25])
  const [enableSL, setEnableSL] = useState(true)
  const [enableTP, setEnableTP] = useState(true)
  const [slPercent, setSlPercent] = useState([2])
  const [tpPercent, setTpPercent] = useState([6])
  const [isAdvanced, setIsAdvanced] = useState(false)

  const currentMarket = markets.find(m => m.symbol === currentSymbol)
  const currentAccount = accounts.find(a => a.id === currentAccountId)
  // Use live price if available, fall back to market price from store
  const livePrice = getPrice(currentSymbol)
  const currentPrice = livePrice?.price || currentMarket?.price || 0

  // Calculate order details
  const calculations = useMemo(() => {
    const balance = currentAccount?.balance || 0
    const percentOfBalance = sliderValue[0] / 100
    const orderValue = useSlider ? balance * percentOfBalance : parseFloat(amount) || 0
    const size = orderValue / currentPrice
    
    const slPrice = side === 'buy' 
      ? currentPrice * (1 - slPercent[0] / 100)
      : currentPrice * (1 + slPercent[0] / 100)
    
    const tpPrice = side === 'buy'
      ? currentPrice * (1 + tpPercent[0] / 100)
      : currentPrice * (1 - tpPercent[0] / 100)

    const riskAmount = enableSL ? Math.abs(currentPrice - slPrice) * size : orderValue
    const riskPercent = (riskAmount / balance) * 100
    const rewardAmount = enableTP ? Math.abs(tpPrice - currentPrice) * size : 0
    const rMultiple = enableSL && enableTP ? rewardAmount / riskAmount : 0

    return {
      orderValue,
      size,
      slPrice,
      tpPrice,
      riskAmount,
      riskPercent,
      rewardAmount,
      rMultiple
    }
  }, [sliderValue, amount, useSlider, currentPrice, slPercent, tpPercent, side, enableSL, enableTP, currentAccount])

  const handleSubmit = () => {
    if (mode === 'view') {
      alert('Switch to Paper or Live mode to place orders')
      return
    }

    const position = {
      symbol: currentSymbol,
      side: side === 'buy' ? 'long' as const : 'short' as const,
      size: calculations.size,
      entryPrice: currentPrice,
      currentPrice: currentPrice,
      pnl: 0,
      pnlPercent: 0,
      leverage: 1,
      stopLoss: enableSL ? calculations.slPrice : undefined,
      takeProfit: enableTP ? calculations.tpPrice : undefined,
      strategy: 'Manual',
      openedAt: new Date().toISOString(),
    }

    if (orderType === 'market') {
      addPosition(position)
    } else {
      addOrder({
        symbol: currentSymbol,
        side,
        type: orderType,
        size: calculations.size,
        price: parseFloat(limitPrice) || currentPrice,
      })
    }

    // Reset form
    setAmount('')
    setSliderValue([25])
  }

  return (
    <div className="h-full flex flex-col bg-[#0d0d14] overflow-y-auto">
      {/* Header */}
      <div className="px-3 pt-3 pb-2 border-b border-gray-800">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-bold text-white">{currentSymbol}</span>
          <Badge variant="outline" className="text-[10px]">
            {mode === 'paper' ? 'Paper' : mode === 'live' ? 'Live' : 'View'}
          </Badge>
        </div>
        <div className="text-xs text-gray-500">
          Price: <span className="text-white font-mono">${currentPrice.toFixed(2)}</span>
        </div>
      </div>

      <div className="p-3 flex-1">
      {/* Side Toggle - More Prominent */}
      <div className="flex gap-2 mb-4">
        <Button
          onClick={() => setSide('buy')}
          variant={side === 'buy' ? 'default' : 'outline'}
          className={`flex-1 py-3 text-sm font-bold transition-all ${
            side === 'buy' 
              ? 'bg-green-600 hover:bg-green-700 border-2 border-green-500 text-white shadow-lg shadow-green-500/30' 
              : 'border-2 border-gray-600 text-gray-400 hover:border-green-500/50 hover:text-green-400 hover:bg-green-500/10'
          }`}
        >
          <TrendingUp className="w-5 h-5 mr-2" />
          Long
        </Button>
        <Button
          onClick={() => setSide('sell')}
          variant={side === 'sell' ? 'default' : 'outline'}
          className={`flex-1 py-3 text-sm font-bold transition-all ${
            side === 'sell' 
              ? 'bg-red-600 hover:bg-red-700 border-2 border-red-500 text-white shadow-lg shadow-red-500/30' 
              : 'border-2 border-gray-600 text-gray-400 hover:border-red-500/50 hover:text-red-400 hover:bg-red-500/10'
          }`}
        >
          <TrendingDown className="w-5 h-5 mr-2" />
          Short
        </Button>
      </div>

      {/* Order Type Tabs */}
      <Tabs value={orderType} onValueChange={(v) => setOrderType(v as OrderType)} className="mb-4">
        <TabsList className="w-full bg-gray-900 border border-gray-800 h-9">
          <TabsTrigger value="market" className="flex-1 text-xs font-medium data-[state=active]:bg-purple-600 data-[state=active]:text-white">Market</TabsTrigger>
          <TabsTrigger value="limit" className="flex-1 text-xs font-medium data-[state=active]:bg-purple-600 data-[state=active]:text-white">Limit</TabsTrigger>
          <TabsTrigger value="stop" className="flex-1 text-xs font-medium data-[state=active]:bg-purple-600 data-[state=active]:text-white">Stop</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Amount Input */}
      <div className="space-y-2.5 mb-4">
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium text-gray-300">Amount</Label>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">% of Balance</span>
            <Switch 
              checked={useSlider} 
              onCheckedChange={setUseSlider}
              className="scale-75"
            />
          </div>
        </div>
        
        {useSlider ? (
          <div className="space-y-2">
            <Slider
              value={sliderValue}
              onValueChange={setSliderValue}
              max={100}
              step={5}
              className="py-2"
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>0%</span>
              <span className="text-white font-medium">{sliderValue[0]}%</span>
              <span>100%</span>
            </div>
          </div>
        ) : (
          <Input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00 USDT"
            className="bg-gray-900 border-gray-700"
          />
        )}
      </div>

      {/* Limit Price (for limit orders) */}
      {orderType !== 'market' && (
        <div className="space-y-1.5 mb-3">
          <Label className="text-xs text-gray-400">
            {orderType === 'limit' ? 'Limit Price' : 'Stop Price'}
          </Label>
          <Input
            type="number"
            value={limitPrice}
            onChange={(e) => setLimitPrice(e.target.value)}
            placeholder={`$${currentPrice.toFixed(2)}`}
            className="bg-gray-900 border-gray-700"
          />
        </div>
      )}

      {/* SL/TP Controls */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {/* Stop Loss */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-medium text-gray-300 flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-red-400" />
              Stop Loss
            </Label>
            <Switch 
              checked={enableSL} 
              onCheckedChange={setEnableSL}
              className="scale-75"
            />
          </div>
          {enableSL && (
            <div className="space-y-1">
              <Slider
                value={slPercent}
                onValueChange={setSlPercent}
                max={10}
                step={0.5}
                className="py-1"
              />
              <div className="flex justify-between text-[10px]">
                <span className="text-red-400">${calculations.slPrice.toFixed(2)}</span>
                <span className="text-gray-500">{slPercent[0]}%</span>
              </div>
            </div>
          )}
        </div>

        {/* Take Profit */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-medium text-gray-300 flex items-center gap-1.5">
              <Target className="w-3.5 h-3.5 text-green-400" />
              Take Profit
            </Label>
            <Switch 
              checked={enableTP} 
              onCheckedChange={setEnableTP}
              className="scale-75"
            />
          </div>
          {enableTP && (
            <div className="space-y-1">
              <Slider
                value={tpPercent}
                onValueChange={setTpPercent}
                max={20}
                step={1}
                className="py-1"
              />
              <div className="flex justify-between text-[10px]">
                <span className="text-green-400">${calculations.tpPrice.toFixed(2)}</span>
                <span className="text-gray-500">{tpPercent[0]}%</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Order Summary */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-3 mb-4 space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-400">Order Value</span>
          <span className="font-mono">${calculations.orderValue.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Size</span>
          <span className="font-mono">{calculations.size.toFixed(6)} {currentSymbol.replace('USDT', '')}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            Risk
          </span>
          <span className={`font-mono ${calculations.riskPercent > 2 ? 'text-red-400' : 'text-amber-400'}`}>
            ${calculations.riskAmount.toFixed(2)} ({calculations.riskPercent.toFixed(2)}%)
          </span>
        </div>
        {enableSL && enableTP && (
          <div className="flex justify-between">
            <span className="text-gray-400">R:R</span>
            <span className="font-mono text-purple-400">1:{calculations.rMultiple.toFixed(1)}</span>
          </div>
        )}
      </div>

      {/* Submit Button */}
      <Button
        onClick={handleSubmit}
        disabled={calculations.orderValue <= 0 || mode === 'view'}
        className={`w-full py-3 text-sm font-bold shadow-lg transition-all ${
          side === 'buy' 
            ? 'bg-green-600 hover:bg-green-700 border-2 border-green-500 shadow-green-500/30' 
            : 'bg-red-600 hover:bg-red-700 border-2 border-red-500 shadow-red-500/30'
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {mode === 'view' ? 'View Only Mode' : (
          <>
            Place {side === 'buy' ? 'Long' : 'Short'} {orderType.charAt(0).toUpperCase() + orderType.slice(1)} Order
            {mode === 'paper' && <Badge variant="outline" className="ml-2 text-[10px]">Paper</Badge>}
          </>
        )}
      </Button>

      {/* Risk Warning */}
      {calculations.riskPercent > 2 && (
        <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-xs text-red-400">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>Risk exceeds 2% of account</span>
        </div>
      )}
      </div>
    </div>
  )
}

