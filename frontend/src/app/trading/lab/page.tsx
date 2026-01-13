'use client'

import { useState, useCallback } from 'react'
import { useTradingStore } from '@/stores/trading-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
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
  TrendingDown,
  Sparkles,
  Loader2,
  Wand2,
  Code,
  Lightbulb,
  Upload,
  FileUp,
  FileText,
  FileJson,
  FolderUp,
  Download,
  AlertCircle
} from 'lucide-react'
import Link from 'next/link'
import { useRef } from 'react'

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

// Strategy type templates for quick creation
const STRATEGY_TYPES = [
  { id: 'custom', name: 'Custom / Blank', icon: '📝', description: 'Start from scratch' },
  { id: 'trend', name: 'Trend Following', icon: '📈', description: 'Follow market momentum' },
  { id: 'meanrev', name: 'Mean Reversion', icon: '🔄', description: 'Fade extreme moves' },
  { id: 'breakout', name: 'Breakout', icon: '💥', description: 'Trade range breaks' },
  { id: 'scalp', name: 'Scalping', icon: '⚡', description: 'Quick in-and-out trades' },
  { id: 'swing', name: 'Swing Trading', icon: '🌊', description: 'Multi-day positions' },
]

const generateStrategyTemplate = (type: string, name: string, description: string = ''): string => {
  const templates: Record<string, string> = {
    custom: `# ${name}
# ${description || 'Custom trading strategy'}

def strategy(data, params):
    """
    ${name}
    
    Add your strategy logic here.
    """
    signals = []
    
    for i in range(len(data)):
        # Your logic here
        signals.append('HOLD')
    
    return signals

# Parameters
PARAMS = {
    'risk_per_trade': 0.01,  # 1% risk per trade
    'stop_loss_pct': 0.02,   # 2% stop loss
    'take_profit_pct': 0.04, # 4% take profit (2:1 R:R)
}
`,
    trend: `# ${name}
# ${description || 'Trend following strategy using moving average crossovers'}

def strategy(data, params):
    """
    ${name} - Trend Following
    
    Goes long when fast MA crosses above slow MA (uptrend)
    Goes short when fast MA crosses below slow MA (downtrend)
    
    Parameters:
    - fast_period: Fast moving average period (default: 20)
    - slow_period: Slow moving average period (default: 50)
    - atr_mult: ATR multiplier for stops (default: 2)
    """
    fast = calculate_sma(data['close'], params.get('fast_period', 20))
    slow = calculate_sma(data['close'], params.get('slow_period', 50))
    
    signals = []
    
    for i in range(len(data)):
        if i < params.get('slow_period', 50):
            signals.append('HOLD')
        elif fast[i] > slow[i] and fast[i-1] <= slow[i-1]:
            signals.append('BUY')  # Golden cross
        elif fast[i] < slow[i] and fast[i-1] >= slow[i-1]:
            signals.append('SELL')  # Death cross
        else:
            signals.append('HOLD')
    
    return signals

# Parameters
PARAMS = {
    'fast_period': 20,
    'slow_period': 50,
    'atr_mult': 2.0,
    'risk_per_trade': 0.01,
}
`,
    meanrev: `# ${name}
# ${description || 'Mean reversion strategy - fade extreme moves'}

def strategy(data, params):
    """
    ${name} - Mean Reversion
    
    Buys oversold conditions (RSI < threshold)
    Sells overbought conditions (RSI > threshold)
    
    Parameters:
    - rsi_period: RSI calculation period (default: 14)
    - oversold: Buy signal threshold (default: 30)
    - overbought: Sell signal threshold (default: 70)
    """
    rsi = calculate_rsi(data['close'], params.get('rsi_period', 14))
    
    signals = []
    
    for i in range(len(data)):
        if rsi[i] < params.get('oversold', 30):
            signals.append('BUY')   # Oversold - buy the dip
        elif rsi[i] > params.get('overbought', 70):
            signals.append('SELL')  # Overbought - sell the rip
        else:
            signals.append('HOLD')
    
    return signals

# Parameters
PARAMS = {
    'rsi_period': 14,
    'oversold': 30,
    'overbought': 70,
    'risk_per_trade': 0.01,
}
`,
    breakout: `# ${name}
# ${description || 'Breakout strategy - trade range expansions'}

def strategy(data, params):
    """
    ${name} - Breakout
    
    Enters on breakout of recent high/low (Donchian)
    Uses ATR for dynamic stop placement
    
    Parameters:
    - lookback: Period for high/low (default: 20)
    - atr_period: ATR period for stops (default: 14)
    - atr_mult: ATR multiplier (default: 1.5)
    """
    lookback = params.get('lookback', 20)
    
    signals = []
    
    for i in range(len(data)):
        if i < lookback:
            signals.append('HOLD')
            continue
            
        highest = max(data['high'][i-lookback:i])
        lowest = min(data['low'][i-lookback:i])
        current = data['close'][i]
        
        if current > highest:
            signals.append('BUY')   # Breakout long
        elif current < lowest:
            signals.append('SELL')  # Breakdown short
        else:
            signals.append('HOLD')
    
    return signals

# Parameters
PARAMS = {
    'lookback': 20,
    'atr_period': 14,
    'atr_mult': 1.5,
    'risk_per_trade': 0.01,
}
`,
    scalp: `# ${name}
# ${description || 'Scalping strategy - quick trades on short timeframes'}

def strategy(data, params):
    """
    ${name} - Scalping
    
    Quick entries/exits based on momentum and volume
    Best on 1m-5m charts with tight stops
    
    Parameters:
    - ema_fast: Fast EMA (default: 5)
    - ema_slow: Slow EMA (default: 13)
    - volume_mult: Volume spike threshold (default: 1.5)
    """
    ema_fast = calculate_ema(data['close'], params.get('ema_fast', 5))
    ema_slow = calculate_ema(data['close'], params.get('ema_slow', 13))
    avg_volume = calculate_sma(data['volume'], 20)
    
    signals = []
    
    for i in range(len(data)):
        volume_spike = data['volume'][i] > avg_volume[i] * params.get('volume_mult', 1.5)
        
        if ema_fast[i] > ema_slow[i] and volume_spike:
            signals.append('BUY')
        elif ema_fast[i] < ema_slow[i] and volume_spike:
            signals.append('SELL')
        else:
            signals.append('HOLD')
    
    return signals

# Parameters - tight for scalping
PARAMS = {
    'ema_fast': 5,
    'ema_slow': 13,
    'volume_mult': 1.5,
    'risk_per_trade': 0.005,  # 0.5% for scalps
    'stop_loss_pct': 0.003,   # 0.3% stop
    'take_profit_pct': 0.006, # 0.6% TP (2:1)
}
`,
    swing: `# ${name}
# ${description || 'Swing trading strategy - multi-day positions'}

def strategy(data, params):
    """
    ${name} - Swing Trading
    
    Identifies swing highs/lows and trend structure
    Holds positions for days to weeks
    
    Parameters:
    - trend_period: Trend MA period (default: 200)
    - swing_period: Swing detection period (default: 10)
    - atr_mult: ATR for stops (default: 2.5)
    """
    trend_ma = calculate_sma(data['close'], params.get('trend_period', 200))
    atr = calculate_atr(data, params.get('atr_period', 14))
    
    signals = []
    
    for i in range(len(data)):
        if i < params.get('trend_period', 200):
            signals.append('HOLD')
            continue
        
        in_uptrend = data['close'][i] > trend_ma[i]
        in_downtrend = data['close'][i] < trend_ma[i]
        
        # Swing low in uptrend = buy
        is_swing_low = is_local_min(data['low'], i, params.get('swing_period', 10))
        # Swing high in downtrend = sell
        is_swing_high = is_local_max(data['high'], i, params.get('swing_period', 10))
        
        if in_uptrend and is_swing_low:
            signals.append('BUY')
        elif in_downtrend and is_swing_high:
            signals.append('SELL')
        else:
            signals.append('HOLD')
    
    return signals

# Parameters
PARAMS = {
    'trend_period': 200,
    'swing_period': 10,
    'atr_period': 14,
    'atr_mult': 2.5,
    'risk_per_trade': 0.02,  # 2% for swings
}
`,
  }
  
  return templates[type] || templates.custom
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

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  model?: string
  action?: 'create_strategy' | 'modify_code' | null
  strategyData?: {
    name: string
    type: string
    description: string
  }
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
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { 
      role: 'assistant', 
      content: `Hey there! 👋 I'm your strategy lab assistant.\n\nI can help you:\n• **Create new strategies** - just describe what you want\n• **Optimize existing code** - ask me to improve your logic\n• **Debug issues** - paste errors and I'll help fix them\n• **Explain concepts** - RSI, MACD, order flow, etc.\n\nWhat would you like to build today?` 
    }
  ])
  const [chatInput, setChatInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  
  // New strategy dialog state
  const [showNewStrategyDialog, setShowNewStrategyDialog] = useState(false)
  const [newStrategyName, setNewStrategyName] = useState('')
  const [newStrategyType, setNewStrategyType] = useState('custom')
  const [newStrategyDescription, setNewStrategyDescription] = useState('')
  
  // File import state
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)
  
  // Create new strategy function
  const createStrategy = useCallback((name: string, type: string, description: string = '') => {
    const newCode = generateStrategyTemplate(type, name, description)
    const newStrategy = {
      id: `${Date.now()}`,
      name,
      code: newCode,
    }
    
    setStrategies(prev => [...prev, newStrategy])
    setActiveStrategy(newStrategy)
    setCode(newCode)
    setShowNewStrategyDialog(false)
    setNewStrategyName('')
    setNewStrategyType('custom')
    setNewStrategyDescription('')
    
    return newStrategy
  }, [])
  
  // Delete strategy
  const deleteStrategy = useCallback((id: string) => {
    setStrategies(prev => {
      const filtered = prev.filter(s => s.id !== id)
      if (activeStrategy.id === id && filtered.length > 0) {
        setActiveStrategy(filtered[0])
        setCode(filtered[0].code)
      }
      return filtered
    })
  }, [activeStrategy.id])

  // File import handlers
  const handleFileImport = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setImportError(null)
    
    for (const file of Array.from(files)) {
      try {
        const content = await file.text()
        const fileName = file.name.replace(/\.[^/.]+$/, '') // Remove extension
        
        // Detect file type
        const ext = file.name.split('.').pop()?.toLowerCase()
        
        if (ext === 'py' || ext === 'txt') {
          // Python strategy file
          const newStrategy = {
            id: `imported-${Date.now()}-${Math.random().toString(36).slice(2)}`,
            name: fileName,
            code: content,
          }
          setStrategies(prev => [...prev, newStrategy])
          setActiveStrategy(newStrategy)
          setCode(content)
          
          setChatMessages(prev => [...prev, {
            role: 'assistant',
            content: `📥 Imported **${fileName}** successfully!\n\nI've loaded it into the editor. The file contains ${content.split('\n').length} lines of code.\n\nWant me to analyze it or suggest improvements?`,
            model: 'system',
          }])
        } else if (ext === 'json') {
          // Try to parse as strategy config or parameters
          const data = JSON.parse(content)
          
          if (data.strategies && Array.isArray(data.strategies)) {
            // Bulk import multiple strategies
            for (const strat of data.strategies) {
              const newStrategy = {
                id: `imported-${Date.now()}-${Math.random().toString(36).slice(2)}`,
                name: strat.name || 'Imported Strategy',
                code: strat.code || '',
              }
              setStrategies(prev => [...prev, newStrategy])
            }
            setChatMessages(prev => [...prev, {
              role: 'assistant',
              content: `📥 Imported **${data.strategies.length} strategies** from ${fileName}.json!\n\nThey're now available in your strategy list.`,
              model: 'system',
            }])
          } else if (data.params || data.parameters || data.PARAMS) {
            // Strategy parameters - inject into current strategy
            const params = data.params || data.parameters || data.PARAMS
            const paramsCode = `\n# Imported parameters from ${file.name}\nPARAMS = ${JSON.stringify(params, null, 2)}\n`
            setCode(prev => prev + paramsCode)
            
            setChatMessages(prev => [...prev, {
              role: 'assistant',
              content: `📥 Imported parameters from **${fileName}.json**!\n\nI've appended the PARAMS to your current strategy:\n\`\`\`python\nPARAMS = ${JSON.stringify(params, null, 2)}\n\`\`\``,
              model: 'system',
            }])
          } else {
            // Generic JSON - create as a reference document
            const docCode = `# Configuration from ${file.name}\n# Data: ${JSON.stringify(data, null, 2).slice(0, 500)}...`
            setCode(prev => prev + '\n\n' + docCode)
          }
        } else if (ext === 'md' || ext === 'markdown') {
          // Markdown documentation - show in chat
          setChatMessages(prev => [...prev, {
            role: 'assistant',
            content: `📄 **Documentation Loaded: ${fileName}**\n\n${content.slice(0, 2000)}${content.length > 2000 ? '\n\n...(truncated)' : ''}`,
            model: 'system',
          }])
        } else {
          setImportError(`Unsupported file type: .${ext}. Use .py, .json, .txt, or .md files.`)
        }
        
      } catch (error) {
        console.error('Import error:', error)
        setImportError(`Failed to import ${file.name}: ${error instanceof Error ? error.message : 'Unknown error'}`)
      }
    }
    
    setShowImportDialog(false)
  }, [])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    handleFileImport(e.dataTransfer.files)
  }, [handleFileImport])

  const handleExport = useCallback(() => {
    const data = {
      exported_at: new Date().toISOString(),
      strategies: strategies.map(s => ({
        name: s.name,
        code: s.code,
      })),
    }
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `algo-lab-export-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
    
    setChatMessages(prev => [...prev, {
      role: 'assistant',
      content: `📤 Exported **${strategies.length} strategies** to JSON!\n\nYou can import this file later to restore your work.`,
      model: 'system',
    }])
  }, [strategies])

  const runBacktest = async () => {
    setIsRunning(true)
    setResults(null)
    
    // Simulate backtest running
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    setResults(mockBacktestResults)
    setIsRunning(false)
  }

  // Detect if user wants to create a strategy from chat
  const detectStrategyCreationIntent = (message: string): { 
    isCreation: boolean
    name?: string
    type?: string
    description?: string 
  } => {
    const lower = message.toLowerCase()
    
    // Keywords that suggest strategy creation
    const creationKeywords = ['create', 'make', 'build', 'new strategy', 'write me', 'generate', 'i want a', 'i need a']
    const isCreation = creationKeywords.some(kw => lower.includes(kw))
    
    if (!isCreation) return { isCreation: false }
    
    // Detect strategy type
    let type = 'custom'
    if (lower.includes('trend') || lower.includes('momentum')) type = 'trend'
    else if (lower.includes('mean') || lower.includes('reversion') || lower.includes('rsi')) type = 'meanrev'
    else if (lower.includes('breakout') || lower.includes('donchian')) type = 'breakout'
    else if (lower.includes('scalp')) type = 'scalp'
    else if (lower.includes('swing')) type = 'swing'
    
    // Try to extract a name
    const nameMatch = message.match(/(?:called?|named?)\s+["']?([^"'\n,]+)["']?/i)
    const name = nameMatch ? nameMatch[1].trim() : undefined
    
    return { isCreation: true, type, name, description: message }
  }
  
  const handleChatSend = async () => {
    if (!chatInput.trim() || isThinking) return
    
    const userMessage = chatInput.trim()
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setChatInput('')
    setIsThinking(true)
    
    // Check for strategy creation intent
    const creationIntent = detectStrategyCreationIntent(userMessage)
    
    try {
      // Try to call the AI API first
      const response = await fetch('/api/trading-assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `[STRATEGY LAB CONTEXT]
You are helping write algorithmic trading strategies. The user is in the Algo Lab code editor.

Current strategy being edited:
Name: ${activeStrategy.name}
Code preview: ${code.slice(0, 500)}...

User message: ${userMessage}

${creationIntent.isCreation ? `
The user wants to CREATE a new strategy. Respond with:
1. Acknowledge what kind of strategy they want
2. Suggest a good name if they didn't provide one
3. Explain what the strategy will do
4. Ask if they want you to create it now

Keep response friendly and concise.` : `
Help the user with their strategy question. Be specific, provide code examples when relevant, and be friendly.`}`,
          tradingContext: {
            currentSymbol,
            positions: [],
            balance: 100000,
            mode: 'paper',
          },
        }),
      })
      
      if (response.ok) {
        const data = await response.json()
        
        // If this was a creation intent, offer to create it
        if (creationIntent.isCreation) {
          const suggestedName = creationIntent.name || 
            (creationIntent.type === 'trend' ? 'Trend Follower' :
             creationIntent.type === 'meanrev' ? 'Mean Reversion Bot' :
             creationIntent.type === 'breakout' ? 'Breakout Hunter' :
             creationIntent.type === 'scalp' ? 'Quick Scalper' :
             creationIntent.type === 'swing' ? 'Swing Trader' : 'New Strategy')
          
          setChatMessages(prev => [...prev, { 
            role: 'assistant', 
            content: data.response + `\n\n✨ **Ready to create it?**`,
            model: data.model,
            action: 'create_strategy',
            strategyData: {
              name: suggestedName,
              type: creationIntent.type || 'custom',
              description: userMessage,
            }
          }])
        } else {
          setChatMessages(prev => [...prev, { 
            role: 'assistant', 
            content: data.response,
            model: data.model,
          }])
        }
      } else {
        throw new Error('API not available')
      }
    } catch (error) {
      // Fallback to local response
      const lower = userMessage.toLowerCase()
      let response = ''
      
      if (creationIntent.isCreation) {
        const typeNames: Record<string, string> = {
          trend: 'trend following',
          meanrev: 'mean reversion',
          breakout: 'breakout',
          scalp: 'scalping',
          swing: 'swing trading',
          custom: 'custom',
        }
        
        const suggestedName = creationIntent.name || 
          (creationIntent.type === 'trend' ? 'Trend Follower' :
           creationIntent.type === 'meanrev' ? 'Mean Reversion Bot' :
           creationIntent.type === 'breakout' ? 'Breakout Hunter' :
           creationIntent.type === 'scalp' ? 'Quick Scalper' :
           creationIntent.type === 'swing' ? 'Swing Trader' : 'New Strategy')
        
        response = `Sounds great! 🎯 I'll help you create a **${typeNames[creationIntent.type || 'custom']}** strategy.\n\n` +
          `I'll set it up with:\n` +
          `• Clear entry/exit signals\n` +
          `• Risk management (stop loss, position sizing)\n` +
          `• Configurable parameters\n\n` +
          `✨ **Ready to create it?**`
        
        setChatMessages(prev => [...prev, { 
          role: 'assistant', 
          content: response,
          model: 'local',
          action: 'create_strategy',
          strategyData: {
            name: suggestedName,
            type: creationIntent.type || 'custom',
            description: userMessage,
          }
        }])
      } else if (lower.includes('rsi') || lower.includes('oversold')) {
        response = `For RSI-based strategies, here are my recommendations:\n\n` +
          `📊 **Settings**:\n` +
          `• **Period**: 14 is standard, try 21 for smoother signals\n` +
          `• **Oversold**: 30 typical, use 25 for fewer but stronger signals\n` +
          `• **Overbought**: 70 standard, 75 for quality shorts\n\n` +
          `💡 **Pro tip**: Add a trend filter - only take RSI oversold signals when price is above the 200 SMA (uptrend).\n\n` +
          `Want me to add RSI divergence detection to your code?`
        setChatMessages(prev => [...prev, { role: 'assistant', content: response, model: 'local' }])
      } else if (lower.includes('optimize') || lower.includes('improve')) {
        response = `Here's how to level up your strategy:\n\n` +
          `🎯 **Quick wins**:\n` +
          `1. Add trend filter (price > 200 EMA for longs)\n` +
          `2. Use ATR-based stops (adapts to volatility)\n` +
          `3. Avoid trading during news events\n\n` +
          `📈 **Advanced**:\n` +
          `4. Position sizing based on volatility\n` +
          `5. Multiple timeframe confirmation\n` +
          `6. Volume spike filters\n\n` +
          `Which one should we implement first?`
        setChatMessages(prev => [...prev, { role: 'assistant', content: response, model: 'local' }])
      } else if (lower.includes('stop') || lower.includes('loss')) {
        response = `Smart stop loss placement is crucial! Here's a dynamic approach:\n\n` +
          `\`\`\`python\n# ATR-based stop loss\natr = calculate_atr(data, 14)\nstop_loss = entry_price - (atr * 1.5)  # 1.5x ATR below entry\n\n# Or percentage-based\nstop_loss = entry_price * (1 - 0.02)  # 2% stop\n\`\`\`\n\n` +
          `💡 **Rule of thumb**: Your stop should be where your trade thesis is invalidated, not just a random percentage.\n\n` +
          `Want me to add this to your code?`
        setChatMessages(prev => [...prev, { role: 'assistant', content: response, model: 'local' }])
      } else {
        response = `I'm here to help! 🚀\n\n` +
          `Try asking me to:\n` +
          `• **"Create a scalping strategy"** → I'll generate the code\n` +
          `• **"Add RSI to my strategy"** → I'll show you how\n` +
          `• **"Optimize my stops"** → Better risk management\n` +
          `• **"Explain MACD crossover"** → Learn concepts\n\n` +
          `What would you like to build?`
        setChatMessages(prev => [...prev, { role: 'assistant', content: response, model: 'local' }])
      }
    } finally {
      setIsThinking(false)
    }
  }
  
  // Handle creating strategy from chat action
  const handleCreateFromChat = (strategyData: { name: string; type: string; description: string }) => {
    const newStrategy = createStrategy(strategyData.name, strategyData.type, strategyData.description)
    
    setChatMessages(prev => [...prev, {
      role: 'assistant',
      content: `✅ Done! I've created **"${newStrategy.name}"** and loaded it in the editor.\n\nThe code includes:\n• Entry/exit signal logic\n• Configurable parameters\n• Risk management settings\n\nFeel free to customize it! Ask me if you want to modify anything.`,
      model: 'local',
    }])
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

        {/* Import/Export buttons */}
        <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
          <DialogTrigger asChild>
            <Button size="sm" variant="outline" className="border-gray-700 hover:border-purple-500 hover:bg-purple-500/10">
              <Upload className="w-4 h-4 mr-1.5" />
              Import
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#0d0d14] border-gray-800 text-white max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileUp className="w-5 h-5 text-purple-400" />
                Import Strategy / Document
              </DialogTitle>
              <DialogDescription className="text-gray-400">
                Import Python strategies, JSON configs, or documentation.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              {/* Drag & Drop Zone */}
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive 
                    ? 'border-purple-500 bg-purple-500/10' 
                    : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <FolderUp className={`w-12 h-12 mx-auto mb-3 ${dragActive ? 'text-purple-400' : 'text-gray-500'}`} />
                <p className="text-sm text-gray-300 mb-2">
                  Drag & drop files here, or
                </p>
                <Button
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-purple-600 hover:bg-purple-700"
                >
                  Browse Files
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".py,.json,.txt,.md,.markdown"
                  className="hidden"
                  onChange={(e) => handleFileImport(e.target.files)}
                />
              </div>
              
              {/* Supported formats */}
              <div className="space-y-2">
                <p className="text-xs text-gray-500 font-medium">Supported formats:</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-2 text-gray-400">
                    <FileCode className="w-3.5 h-3.5 text-green-400" />
                    <span>.py - Python strategies</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <FileJson className="w-3.5 h-3.5 text-yellow-400" />
                    <span>.json - Configs/params</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <FileText className="w-3.5 h-3.5 text-blue-400" />
                    <span>.txt - Text strategies</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <FileText className="w-3.5 h-3.5 text-purple-400" />
                    <span>.md - Documentation</span>
                  </div>
                </div>
              </div>
              
              {/* Error display */}
              {importError && (
                <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-red-300">{importError}</p>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>

        <Button size="sm" variant="outline" className="border-gray-700" onClick={handleExport}>
          <Download className="w-4 h-4 mr-1.5" />
          Export
        </Button>

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
            <Dialog open={showNewStrategyDialog} onOpenChange={setShowNewStrategyDialog}>
              <DialogTrigger asChild>
                <Button size="icon" variant="ghost" className="h-6 w-6 text-gray-400 hover:text-purple-400 hover:bg-purple-500/10">
                  <Plus className="w-4 h-4" />
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-[#0d0d14] border-gray-800 text-white">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <Wand2 className="w-5 h-5 text-purple-400" />
                    Create New Strategy
                  </DialogTitle>
                  <DialogDescription className="text-gray-400">
                    Start with a template or build from scratch. The AI assistant can help you customize it later.
                  </DialogDescription>
                </DialogHeader>
                
                <div className="space-y-4 py-4">
                  {/* Strategy Name */}
                  <div className="space-y-2">
                    <Label htmlFor="strategy-name" className="text-gray-300">Strategy Name</Label>
                    <Input
                      id="strategy-name"
                      value={newStrategyName}
                      onChange={(e) => setNewStrategyName(e.target.value)}
                      placeholder="My Awesome Strategy"
                      className="bg-gray-900 border-gray-700"
                    />
                  </div>
                  
                  {/* Strategy Type */}
                  <div className="space-y-2">
                    <Label className="text-gray-300">Strategy Type</Label>
                    <div className="grid grid-cols-2 gap-2">
                      {STRATEGY_TYPES.map((type) => (
                        <button
                          key={type.id}
                          onClick={() => setNewStrategyType(type.id)}
                          className={`p-3 rounded-lg border text-left transition-colors ${
                            newStrategyType === type.id
                              ? 'border-purple-500 bg-purple-500/10 text-purple-300'
                              : 'border-gray-700 hover:border-gray-600 text-gray-300'
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span>{type.icon}</span>
                            <span className="font-medium text-sm">{type.name}</span>
                          </div>
                          <p className="text-xs text-gray-500">{type.description}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  {/* Description */}
                  <div className="space-y-2">
                    <Label htmlFor="strategy-desc" className="text-gray-300">Description (optional)</Label>
                    <Textarea
                      id="strategy-desc"
                      value={newStrategyDescription}
                      onChange={(e) => setNewStrategyDescription(e.target.value)}
                      placeholder="What should this strategy do?"
                      className="bg-gray-900 border-gray-700 resize-none h-20"
                    />
                  </div>
                </div>
                
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setShowNewStrategyDialog(false)}
                    className="border-gray-700"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={() => createStrategy(
                      newStrategyName || 'New Strategy',
                      newStrategyType,
                      newStrategyDescription
                    )}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    <Sparkles className="w-4 h-4 mr-1.5" />
                    Create Strategy
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          <ScrollArea className="h-full">
            <div className="p-2 space-y-1">
              {strategies.map((strategy) => (
                <div
                  key={strategy.id}
                  className={`group flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer ${
                    activeStrategy.id === strategy.id
                      ? 'bg-purple-600/20 text-purple-400 border border-purple-500/30'
                      : 'hover:bg-gray-800 text-gray-300'
                  }`}
                  onClick={() => {
                    setActiveStrategy(strategy)
                    setCode(strategy.code)
                  }}
                >
                  <FileCode className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate flex-1">{strategy.name}</span>
                  {strategies.length > 1 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        deleteStrategy(strategy.id)
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded text-gray-500 hover:text-red-400 transition-all"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
              
              {/* Quick add button at bottom */}
              <button
                onClick={() => setShowNewStrategyDialog(true)}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-500 hover:text-purple-400 hover:bg-purple-500/10 border border-dashed border-gray-700 hover:border-purple-500/50 transition-colors mt-2"
              >
                <Plus className="w-4 h-4" />
                <span>New Strategy</span>
              </button>
            </div>
          </ScrollArea>
        </div>

        {/* Center: Code Editor */}
        <div 
          className="flex-1 flex flex-col relative"
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="h-10 border-b border-gray-800 flex items-center px-4 gap-2 bg-[#0d0d14]">
            <FileCode className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-400">{activeStrategy.name}.py</span>
            <div className="flex-1" />
            <span className="text-xs text-gray-600">{code.split('\n').length} lines</span>
          </div>
          <div className="flex-1 overflow-auto bg-[#0a0a0f]">
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-full p-4 bg-transparent text-gray-300 font-mono text-sm resize-none focus:outline-none"
              spellCheck={false}
              placeholder="# Write your trading strategy here...

def strategy(data, params):
    signals = []
    for i in range(len(data)):
        signals.append('HOLD')
    return signals
"
            />
          </div>
          
          {/* Drag overlay */}
          {dragActive && (
            <div className="absolute inset-0 bg-purple-600/20 backdrop-blur-sm flex items-center justify-center z-10 border-2 border-dashed border-purple-500 m-1 rounded-lg">
              <div className="text-center">
                <Upload className="w-12 h-12 mx-auto mb-3 text-purple-400 animate-bounce" />
                <p className="text-lg font-medium text-purple-300">Drop to Import</p>
                <p className="text-sm text-purple-400/70">Python, JSON, or Markdown files</p>
              </div>
            </div>
          )}
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
                    <div key={i} className="space-y-2">
                      <div className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                        {msg.role === 'assistant' && (
                          <div className="w-7 h-7 rounded-full bg-purple-600 flex items-center justify-center flex-shrink-0">
                            <Bot className="w-4 h-4" />
                          </div>
                        )}
                        <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                          msg.role === 'user' 
                            ? 'bg-purple-600 text-white' 
                            : 'bg-gray-800 text-gray-100'
                        }`}>
                          <div className="whitespace-pre-wrap">{msg.content}</div>
                          {msg.model && msg.role === 'assistant' && (
                            <div className="text-[9px] text-gray-500 mt-1.5 flex items-center gap-1">
                              <Sparkles className="w-2.5 h-2.5" />
                              {msg.model}
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* Action buttons for strategy creation */}
                      {msg.action === 'create_strategy' && msg.strategyData && (
                        <div className="ml-9 flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleCreateFromChat(msg.strategyData!)}
                            className="bg-green-600 hover:bg-green-700 text-xs"
                          >
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Create "{msg.strategyData.name}"
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowNewStrategyDialog(true)}
                            className="border-gray-700 text-xs"
                          >
                            <Code className="w-3 h-3 mr-1" />
                            Customize
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                  
                  {/* Thinking indicator */}
                  {isThinking && (
                    <div className="flex gap-2">
                      <div className="w-7 h-7 rounded-full bg-purple-600 flex items-center justify-center flex-shrink-0">
                        <Bot className="w-4 h-4" />
                      </div>
                      <div className="bg-gray-800 rounded-lg px-4 py-2 flex items-center gap-2">
                        <Loader2 className="w-3 h-3 animate-spin text-purple-400" />
                        <span className="text-xs text-gray-400">Thinking...</span>
                      </div>
                    </div>
                  )}
                </div>
              </ScrollArea>
              
              {/* Quick suggestions */}
              <div className="px-3 pb-2">
                <div className="flex flex-wrap gap-1">
                  {[
                    { label: 'Create strategy', icon: '✨', prompt: 'Create a trend following strategy' },
                    { label: 'Add RSI', icon: '📊', prompt: 'Add RSI indicator to my strategy' },
                    { label: 'Optimize', icon: '🚀', prompt: 'How can I optimize my strategy?' },
                    { label: 'Fix stops', icon: '🛡️', prompt: 'Help me improve my stop loss logic' },
                  ].map((action, i) => (
                    <button
                      key={i}
                      onClick={() => setChatInput(action.prompt)}
                      className="text-[10px] px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded-full text-gray-400 hover:text-white transition-colors flex items-center gap-1"
                    >
                      <span>{action.icon}</span>
                      <span>{action.label}</span>
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="p-3 border-t border-gray-800">
                <div className="flex gap-2">
                  <Input
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleChatSend()}
                    placeholder="Ask about your strategy or say 'create a scalping strategy'..."
                    className="flex-1 bg-gray-900 border-gray-700 text-sm"
                    disabled={isThinking}
                  />
                  <Button 
                    size="icon" 
                    onClick={handleChatSend} 
                    disabled={!chatInput.trim() || isThinking}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    {isThinking ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
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

