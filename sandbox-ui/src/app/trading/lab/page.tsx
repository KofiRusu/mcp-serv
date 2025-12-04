'use client'

import { useState } from 'react'
import { useTradingStore } from '@/stores/trading-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { 
  ArrowLeft, 
  Play, 
  FileCode, 
  FolderTree,
  Bot,
  BarChart3,
  Save,
  Plus,
  Trash2,
  Send,
  CheckCircle,
  TrendingUp,
  TrendingDown
} from 'lucide-react'
import Link from 'next/link'

// Strategy templates
const strategyTemplates = {
  meanReversion: `# Mean Reversion Strategy
# Buy when price is oversold, sell when overbought

def strategy(data, params):
    """
    Mean reversion strategy using RSI
    
    Parameters:
    - rsi_period: RSI calculation period (default: 14)
    - oversold: RSI level for buy signal (default: 30)
    - overbought: RSI level for sell signal (default: 70)
    """
    rsi = calculate_rsi(data['close'], params.get('rsi_period', 14))
    
    signals = []
    
    for i in range(len(data)):
        if rsi[i] < params.get('oversold', 30):
            signals.append('BUY')
        elif rsi[i] > params.get('overbought', 70):
            signals.append('SELL')
        else:
            signals.append('HOLD')
    
    return signals

# Default parameters
PARAMS = {
    'rsi_period': 14,
    'oversold': 30,
    'overbought': 70,
    'risk_per_trade': 0.01,  # 1% risk per trade
    'stop_loss_atr_mult': 1.5,
    'take_profit_atr_mult': 3.0,
}
`,
  breakout: `# Breakout Strategy
# Enter on breakout of recent high/low

def strategy(data, params):
    """
    Breakout strategy using Donchian channels
    
    Parameters:
    - lookback: Period for high/low calculation (default: 20)
    - atr_mult: ATR multiplier for stop loss (default: 2)
    """
    lookback = params.get('lookback', 20)
    
    signals = []
    
    for i in range(lookback, len(data)):
        highest = max(data['high'][i-lookback:i])
        lowest = min(data['low'][i-lookback:i])
        current = data['close'][i]
        
        if current > highest:
            signals.append('BUY')
        elif current < lowest:
            signals.append('SELL')
        else:
            signals.append('HOLD')
    
    return signals

# Default parameters
PARAMS = {
    'lookback': 20,
    'atr_mult': 2.0,
    'risk_per_trade': 0.01,
}
`,
  momentum: `# Momentum Strategy
# Follow the trend using moving averages

def strategy(data, params):
    """
    Momentum strategy using EMA crossover
    
    Parameters:
    - fast_ema: Fast EMA period (default: 12)
    - slow_ema: Slow EMA period (default: 26)
    - signal_ema: Signal line period (default: 9)
    """
    fast = calculate_ema(data['close'], params.get('fast_ema', 12))
    slow = calculate_ema(data['close'], params.get('slow_ema', 26))
    
    signals = []
    
    for i in range(len(data)):
        if fast[i] > slow[i]:
            signals.append('BUY')
        elif fast[i] < slow[i]:
            signals.append('SELL')
        else:
            signals.append('HOLD')
    
    return signals

# Default parameters
PARAMS = {
    'fast_ema': 12,
    'slow_ema': 26,
    'signal_ema': 9,
    'risk_per_trade': 0.01,
}
`,
}

// Mock backtest results
const mockBacktestResults = {
  totalReturn: 45.2,
  sharpeRatio: 1.85,
  maxDrawdown: -12.4,
  winRate: 58,
  avgWin: 2.3,
  avgLoss: -1.1,
  profitFactor: 2.1,
  totalTrades: 147,
  trades: [
    { id: 1, symbol: 'BTCUSDT', side: 'long', entry: 64500, exit: 67200, pnl: 4.18, date: '2024-01-15' },
    { id: 2, symbol: 'BTCUSDT', side: 'short', entry: 68000, exit: 65500, pnl: 3.68, date: '2024-01-18' },
    { id: 3, symbol: 'BTCUSDT', side: 'long', entry: 62000, exit: 61200, pnl: -1.29, date: '2024-01-22' },
    { id: 4, symbol: 'BTCUSDT', side: 'long', entry: 59800, exit: 63400, pnl: 6.02, date: '2024-01-25' },
    { id: 5, symbol: 'BTCUSDT', side: 'short', entry: 66500, exit: 67200, pnl: -1.05, date: '2024-01-28' },
  ],
}

export default function AlgoLabPage() {
  const { currentSymbol } = useTradingStore()
  const [strategies, setStrategies] = useState([
    { id: '1', name: 'Mean Reversion', code: strategyTemplates.meanReversion },
    { id: '2', name: 'Breakout', code: strategyTemplates.breakout },
    { id: '3', name: 'Momentum', code: strategyTemplates.momentum },
  ])
  const [activeStrategy, setActiveStrategy] = useState(strategies[0])
  const [code, setCode] = useState(strategies[0].code)
  const [backtestSymbol, setBacktestSymbol] = useState('BTCUSDT')
  const [backtestTimeframe, setBacktestTimeframe] = useState('1h')
  const [backtestPeriod, setBacktestPeriod] = useState('30')
  const [initialCapital, setInitialCapital] = useState('10000')
  const [isRunning, setIsRunning] = useState(false)
  const [results, setResults] = useState<typeof mockBacktestResults | null>(null)
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([
    { role: 'assistant', content: 'Welcome to the Lab Assistant! I can help you write, debug, and optimize your trading strategies. What would you like to work on?' }
  ])
  const [chatInput, setChatInput] = useState('')

  const runBacktest = async () => {
    setIsRunning(true)
    setResults(null)
    
    // Simulate backtest running
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    setResults(mockBacktestResults)
    setIsRunning(false)
  }

  const handleChatSend = () => {
    if (!chatInput.trim()) return
    
    setChatMessages(prev => [...prev, { role: 'user', content: chatInput }])
    
    // Simulate AI response
    setTimeout(() => {
      let response = ''
      const lower = chatInput.toLowerCase()
      
      if (lower.includes('rsi') || lower.includes('oversold')) {
        response = `For RSI-based strategies, I recommend:\n\n1. **RSI Period**: 14 is standard, but try 21 for less noise\n2. **Oversold**: 30 is typical, but 25 can filter more signals\n3. **Overbought**: 70 is standard, try 75 for stronger signals\n\nWould you like me to add RSI divergence detection to your strategy?`
      } else if (lower.includes('optimize') || lower.includes('improve')) {
        response = `To optimize your strategy:\n\n1. Add a trend filter (e.g., price > 200 EMA)\n2. Use ATR-based stops instead of fixed %\n3. Add time-of-day filters\n4. Implement position sizing based on volatility\n\nWhich optimization would you like to implement first?`
      } else if (lower.includes('stop') || lower.includes('loss')) {
        response = `For stop losses, I suggest:\n\n\`\`\`python\natr = calculate_atr(data, 14)\nstop_loss = entry_price - (atr * 1.5)\n\`\`\`\n\nThis gives you dynamic stops based on market volatility. Want me to add this to your code?`
      } else {
        response = `I can help you with:\n\n- Strategy logic and conditions\n- Risk management parameters\n- Code optimization\n- Backtesting setup\n- Debugging errors\n\nWhat specific aspect of your strategy would you like to improve?`
      }
      
      setChatMessages(prev => [...prev, { role: 'assistant', content: response }])
    }, 1000)
    
    setChatInput('')
  }

  return (
    <div className="flex flex-col h-screen bg-[#0a0a0f] text-gray-100">
      {/* Header */}
      <header className="h-12 border-b border-gray-800 bg-[#0d0d14] flex items-center px-4 gap-4">
        <Link href="/trading">
          <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
            <ArrowLeft className="w-4 h-4 mr-1.5" />
            Back to Trading
          </Button>
        </Link>
        
        <div className="w-px h-6 bg-gray-700" />
        
        <div className="flex items-center gap-2">
          <FileCode className="w-5 h-5 text-purple-400" />
          <span className="font-semibold">Algo Lab</span>
        </div>

        <div className="flex-1" />

        <Button size="sm" variant="outline" className="border-gray-700">
          <Save className="w-4 h-4 mr-1.5" />
          Save
        </Button>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: File Tree */}
        <div className="w-56 border-r border-gray-800 bg-[#0d0d14]">
          <div className="p-3 border-b border-gray-800 flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase">Strategies</span>
            <Button size="icon" variant="ghost" className="h-6 w-6 text-gray-400">
              <Plus className="w-4 h-4" />
            </Button>
          </div>
          <ScrollArea className="h-full">
            <div className="p-2 space-y-1">
              {strategies.map((strategy) => (
                <button
                  key={strategy.id}
                  onClick={() => {
                    setActiveStrategy(strategy)
                    setCode(strategy.code)
                  }}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors ${
                    activeStrategy.id === strategy.id
                      ? 'bg-purple-600/20 text-purple-400 border border-purple-500/30'
                      : 'hover:bg-gray-800 text-gray-300'
                  }`}
                >
                  <FileCode className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">{strategy.name}</span>
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>

        {/* Center: Code Editor */}
        <div className="flex-1 flex flex-col">
          <div className="h-10 border-b border-gray-800 flex items-center px-4 gap-2 bg-[#0d0d14]">
            <FileCode className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-400">{activeStrategy.name}.py</span>
          </div>
          <div className="flex-1 overflow-auto bg-[#0a0a0f]">
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-full p-4 bg-transparent text-gray-300 font-mono text-sm resize-none focus:outline-none"
              spellCheck={false}
            />
          </div>
        </div>

        {/* Right: AI + Backtest */}
        <div className="w-96 border-l border-gray-800 bg-[#0d0d14] flex flex-col">
          <Tabs defaultValue="assistant" className="flex-1 flex flex-col">
            <TabsList className="w-full justify-start gap-1 px-2 pt-2 bg-transparent rounded-none h-auto pb-2 border-b border-gray-800">
              <TabsTrigger 
                value="assistant"
                className="data-[state=active]:bg-purple-600 data-[state=active]:text-white px-3 py-1.5 text-xs"
              >
                <Bot className="w-3.5 h-3.5 mr-1.5" />
                Assistant
              </TabsTrigger>
              <TabsTrigger 
                value="backtest"
                className="data-[state=active]:bg-purple-600 data-[state=active]:text-white px-3 py-1.5 text-xs"
              >
                <BarChart3 className="w-3.5 h-3.5 mr-1.5" />
                Backtest
              </TabsTrigger>
            </TabsList>

            {/* AI Assistant */}
            <TabsContent value="assistant" className="flex-1 flex flex-col mt-0 overflow-hidden">
              <ScrollArea className="flex-1 p-3">
                <div className="space-y-4">
                  {chatMessages.map((msg, i) => (
                    <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                      {msg.role === 'assistant' && (
                        <div className="w-7 h-7 rounded-full bg-purple-600 flex items-center justify-center flex-shrink-0">
                          <Bot className="w-4 h-4" />
                        </div>
                      )}
                      <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                        msg.role === 'user' 
                          ? 'bg-purple-600 text-white' 
                          : 'bg-gray-800 text-gray-100'
                      }`}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
              
              <div className="p-3 border-t border-gray-800">
                <div className="flex gap-2">
                  <Input
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleChatSend()}
                    placeholder="Ask about your strategy..."
                    className="flex-1 bg-gray-900 border-gray-700 text-sm"
                  />
                  <Button size="icon" onClick={handleChatSend} className="bg-purple-600 hover:bg-purple-700">
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </TabsContent>

            {/* Backtest */}
            <TabsContent value="backtest" className="flex-1 flex flex-col mt-0 overflow-hidden">
              <div className="p-3 border-b border-gray-800 space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs text-gray-500">Symbol</Label>
                    <Select value={backtestSymbol} onValueChange={setBacktestSymbol}>
                      <SelectTrigger className="bg-gray-900 border-gray-700 h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-700">
                        <SelectItem value="BTCUSDT">BTCUSDT</SelectItem>
                        <SelectItem value="ETHUSDT">ETHUSDT</SelectItem>
                        <SelectItem value="SOLUSDT">SOLUSDT</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">Timeframe</Label>
                    <Select value={backtestTimeframe} onValueChange={setBacktestTimeframe}>
                      <SelectTrigger className="bg-gray-900 border-gray-700 h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-700">
                        <SelectItem value="15m">15m</SelectItem>
                        <SelectItem value="1h">1H</SelectItem>
                        <SelectItem value="4h">4H</SelectItem>
                        <SelectItem value="1d">1D</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs text-gray-500">Period (days)</Label>
                    <Input 
                      value={backtestPeriod}
                      onChange={(e) => setBacktestPeriod(e.target.value)}
                      className="bg-gray-900 border-gray-700 h-8 text-xs"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">Initial Capital</Label>
                    <Input 
                      value={initialCapital}
                      onChange={(e) => setInitialCapital(e.target.value)}
                      className="bg-gray-900 border-gray-700 h-8 text-xs"
                    />
                  </div>
                </div>
                <Button 
                  onClick={runBacktest} 
                  disabled={isRunning}
                  className="w-full bg-green-600 hover:bg-green-700"
                >
                  {isRunning ? (
                    <>Running...</>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-1.5" />
                      Run Backtest
                    </>
                  )}
                </Button>
              </div>

              {/* Results */}
              <ScrollArea className="flex-1">
                {results ? (
                  <div className="p-3 space-y-4">
                    {/* Key Metrics */}
                    <div className="grid grid-cols-2 gap-2">
                      <MetricCard label="Total Return" value={`${results.totalReturn > 0 ? '+' : ''}${results.totalReturn}%`} positive={results.totalReturn > 0} />
                      <MetricCard label="Sharpe Ratio" value={results.sharpeRatio.toFixed(2)} positive={results.sharpeRatio > 1} />
                      <MetricCard label="Max Drawdown" value={`${results.maxDrawdown}%`} positive={false} />
                      <MetricCard label="Win Rate" value={`${results.winRate}%`} positive={results.winRate > 50} />
                      <MetricCard label="Profit Factor" value={results.profitFactor.toFixed(2)} positive={results.profitFactor > 1} />
                      <MetricCard label="Total Trades" value={results.totalTrades.toString()} />
                    </div>

                    {/* Equity Curve Placeholder */}
                    <div className="bg-gray-900 rounded-lg p-3">
                      <div className="text-xs text-gray-500 mb-2">Equity Curve</div>
                      <div className="h-24 flex items-end gap-0.5">
                        {[20, 22, 25, 23, 28, 32, 30, 35, 38, 40, 42, 45].map((h, i) => (
                          <div
                            key={i}
                            className="flex-1 bg-green-500/50 rounded-t"
                            style={{ height: `${h * 2}%` }}
                          />
                        ))}
                      </div>
                    </div>

                    {/* Trade List */}
                    <div>
                      <div className="text-xs text-gray-500 mb-2">Recent Trades</div>
                      <div className="space-y-1">
                        {results.trades.map((trade) => (
                          <div key={trade.id} className="flex items-center justify-between p-2 bg-gray-900/50 rounded text-xs">
                            <div className="flex items-center gap-2">
                              {trade.side === 'long' ? (
                                <TrendingUp className="w-3 h-3 text-green-400" />
                              ) : (
                                <TrendingDown className="w-3 h-3 text-red-400" />
                              )}
                              <span>{trade.symbol}</span>
                              <span className="text-gray-500">{trade.date}</span>
                            </div>
                            <span className={trade.pnl > 0 ? 'text-green-400' : 'text-red-400'}>
                              {trade.pnl > 0 ? '+' : ''}{trade.pnl}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" className="flex-1 border-gray-700 text-xs">
                        Export Report
                      </Button>
                      <Button size="sm" className="flex-1 bg-purple-600 hover:bg-purple-700 text-xs">
                        Send to Paper
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    <div className="text-center">
                      <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">Run a backtest to see results</p>
                    </div>
                  </div>
                )}
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}

function MetricCard({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <div className="bg-gray-900/50 rounded-lg p-2">
      <div className="text-[10px] text-gray-500">{label}</div>
      <div className={`text-sm font-mono font-medium ${
        positive === undefined ? 'text-white' : positive ? 'text-green-400' : 'text-red-400'
      }`}>
        {value}
      </div>
    </div>
  )
}

