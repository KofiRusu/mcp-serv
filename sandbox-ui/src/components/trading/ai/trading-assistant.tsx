'use client'

import { useState, useRef, useEffect } from 'react'
import { useTradingStore } from '@/stores/trading-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { 
  Send, 
  Bot, 
  User, 
  Sparkles,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  X,
  Zap
} from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  action?: TradingAction
}

interface TradingAction {
  type: 'trade' | 'analysis' | 'alert'
  side?: 'long' | 'short'
  symbol?: string
  size?: number
  stopLoss?: number
  takeProfit?: number
  riskPercent?: number
  confirmed?: boolean
}

// Quick action suggestions
const quickActions = [
  { label: 'Market analysis', prompt: 'Analyze the current BTC market structure' },
  { label: 'Trade idea', prompt: 'Give me a trade idea for ETH with proper risk management' },
  { label: 'Portfolio review', prompt: 'Review my current positions and suggest adjustments' },
  { label: 'Risk check', prompt: 'What is my current risk exposure?' },
]

export function TradingAssistant() {
  const { currentSymbol, positions, portfolio, addPosition, mode } = useTradingStore()
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Welcome to the Trading Assistant! I can help you analyze markets, place trades, and manage risk. Currently viewing **${currentSymbol}**.\n\nTry asking me:\n- "What's the trend on BTC?"\n- "Long ETH with 1% risk"\n- "Summarize my portfolio"`,
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const parseTradeIntent = (text: string): TradingAction | null => {
    const lowerText = text.toLowerCase()
    
    // Detect trade intent
    const isLong = lowerText.includes('long') || lowerText.includes('buy')
    const isShort = lowerText.includes('short') || lowerText.includes('sell')
    
    if (!isLong && !isShort) return null

    // Extract symbol
    const symbols = ['btc', 'eth', 'sol', 'bnb', 'xrp', 'ada']
    const foundSymbol = symbols.find(s => lowerText.includes(s))
    const symbol = foundSymbol ? `${foundSymbol.toUpperCase()}USDT` : currentSymbol

    // Extract risk percentage
    const riskMatch = lowerText.match(/(\d+(?:\.\d+)?)\s*%?\s*risk/)
    const riskPercent = riskMatch ? parseFloat(riskMatch[1]) : 1

    // Extract R multiple for TP
    const rMultipleMatch = lowerText.match(/(\d+(?:\.\d+)?)\s*r/i)
    const rMultiple = rMultipleMatch ? parseFloat(rMultipleMatch[1]) : 3

    return {
      type: 'trade',
      side: isLong ? 'long' : 'short',
      symbol,
      riskPercent,
      confirmed: false,
    }
  }

  const generateResponse = async (userMessage: string): Promise<{ content: string; action?: TradingAction }> => {
    // Check for trade intent
    const tradeAction = parseTradeIntent(userMessage)
    
    if (tradeAction) {
      const price = 67500 // Mock price, would come from market data
      const accountValue = portfolio.totalValue
      const riskAmount = accountValue * (tradeAction.riskPercent! / 100)
      const slDistance = price * 0.02 // 2% SL
      const size = riskAmount / slDistance
      const stopLoss = tradeAction.side === 'long' ? price - slDistance : price + slDistance
      const takeProfit = tradeAction.side === 'long' ? price + slDistance * 3 : price - slDistance * 3

      tradeAction.size = size
      tradeAction.stopLoss = stopLoss
      tradeAction.takeProfit = takeProfit

      return {
        content: `I've prepared a **${tradeAction.side?.toUpperCase()}** order for **${tradeAction.symbol}**:\n\n` +
          `📊 **Order Details**\n` +
          `- Entry: ~$${price.toLocaleString()}\n` +
          `- Size: ${size.toFixed(4)} ${tradeAction.symbol?.replace('USDT', '')}\n` +
          `- Stop Loss: $${stopLoss.toFixed(2)}\n` +
          `- Take Profit: $${takeProfit.toFixed(2)}\n` +
          `- Risk: $${riskAmount.toFixed(2)} (${tradeAction.riskPercent}% of account)\n` +
          `- R:R: 1:3\n\n` +
          `${mode === 'paper' ? '📝 Paper trading mode' : mode === 'live' ? '⚠️ LIVE trading mode' : '👁️ View only mode'}`,
        action: tradeAction,
      }
    }

    // Analysis responses
    const lowerMessage = userMessage.toLowerCase()
    
    if (lowerMessage.includes('analyz') || lowerMessage.includes('trend') || lowerMessage.includes('market')) {
      return {
        content: `**${currentSymbol} Market Analysis** 📊\n\n` +
          `**Trend:** Bullish on higher timeframes, consolidating on 4H\n\n` +
          `**Key Levels:**\n` +
          `- Resistance: $68,500 / $70,000\n` +
          `- Support: $65,000 / $62,500\n\n` +
          `**Indicators:**\n` +
          `- RSI(14): 58 (neutral)\n` +
          `- MACD: Bullish crossover forming\n` +
          `- 200 EMA: Price above, bullish\n\n` +
          `**Suggestion:** Look for long entries on pullbacks to $65-66k zone with invalidation below $64k.`,
        action: { type: 'analysis' },
      }
    }

    if (lowerMessage.includes('portfolio') || lowerMessage.includes('position')) {
      const positionSummary = positions.length > 0
        ? positions.map(p => `- ${p.symbol}: ${p.side} ${p.size.toFixed(4)} @ $${p.entryPrice.toLocaleString()} (${p.pnl >= 0 ? '+' : ''}${p.pnlPercent.toFixed(2)}%)`).join('\n')
        : 'No open positions'

      return {
        content: `**Portfolio Summary** 💼\n\n` +
          `**Account Value:** $${portfolio.totalValue.toLocaleString()}\n` +
          `**Today's PnL:** ${portfolio.dayPnl >= 0 ? '+' : ''}$${portfolio.dayPnl.toFixed(2)} (${portfolio.dayPnlPercent >= 0 ? '+' : ''}${portfolio.dayPnlPercent.toFixed(2)}%)\n` +
          `**Win Rate:** ${portfolio.winRate}%\n\n` +
          `**Open Positions:**\n${positionSummary}`,
      }
    }

    if (lowerMessage.includes('risk')) {
      const totalRisk = positions.reduce((sum, p) => {
        if (p.stopLoss) {
          const riskPerPosition = Math.abs(p.entryPrice - p.stopLoss) * p.size
          return sum + riskPerPosition
        }
        return sum
      }, 0)
      
      const riskPercent = (totalRisk / portfolio.totalValue) * 100

      return {
        content: `**Risk Analysis** ⚠️\n\n` +
          `**Total Risk:** $${totalRisk.toFixed(2)} (${riskPercent.toFixed(2)}% of account)\n` +
          `**Open Positions:** ${positions.length}\n` +
          `**Positions without SL:** ${positions.filter(p => !p.stopLoss).length}\n\n` +
          `${riskPercent > 5 ? '⚠️ **Warning:** Risk exceeds 5% recommendation' : '✅ Risk within acceptable limits'}`,
      }
    }

    // Default response
    return {
      content: `I can help you with:\n\n` +
        `🔍 **Analysis:** "Analyze BTC", "What's the trend on ETH?"\n` +
        `📈 **Trading:** "Long BTC with 1% risk", "Short ETH 2x leverage"\n` +
        `💼 **Portfolio:** "Review my positions", "What's my PnL?"\n` +
        `⚠️ **Risk:** "What's my current risk?", "Am I overexposed?"\n\n` +
        `Currently viewing: **${currentSymbol}**`,
    }
  }

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsTyping(true)

    // Simulate AI thinking
    await new Promise(resolve => setTimeout(resolve, 1000))

    const response = await generateResponse(input)
    
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: response.content,
      timestamp: new Date(),
      action: response.action,
    }

    setMessages(prev => [...prev, assistantMessage])
    setIsTyping(false)
  }

  const handleConfirmTrade = (messageId: string) => {
    const message = messages.find(m => m.id === messageId)
    if (!message?.action || message.action.type !== 'trade') return

    if (mode === 'view') {
      alert('Switch to Paper or Live mode to execute trades')
      return
    }

    const action = message.action
    
    // Add position
    addPosition({
      symbol: action.symbol!,
      side: action.side!,
      size: action.size!,
      entryPrice: 67500, // Mock price
      currentPrice: 67500,
      pnl: 0,
      pnlPercent: 0,
      leverage: 1,
      stopLoss: action.stopLoss,
      takeProfit: action.takeProfit,
      strategy: 'AI Assistant',
      openedAt: new Date().toISOString(),
    })

    // Update message to show confirmed
    setMessages(prev => prev.map(m => 
      m.id === messageId 
        ? { ...m, action: { ...m.action!, confirmed: true } }
        : m
    ))

    // Add confirmation message
    const confirmMessage: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: `✅ **Order Executed!**\n\n${action.side?.toUpperCase()} ${action.symbol} position opened.\nCheck the Positions panel to monitor your trade.`,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, confirmMessage])
  }

  const handleRejectTrade = (messageId: string) => {
    setMessages(prev => prev.map(m => 
      m.id === messageId 
        ? { ...m, action: undefined }
        : m
    ))

    const rejectMessage: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: `Order cancelled. Let me know if you'd like to adjust the parameters or try a different trade.`,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, rejectMessage])
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <ScrollArea className="flex-1 p-3" ref={scrollRef}>
        <div className="space-y-4">
          {messages.map((message) => (
            <div key={message.id} className="space-y-2">
              <div className={`flex gap-2 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {message.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-full bg-purple-600 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                    message.role === 'user'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-800 text-gray-100'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{message.content}</div>
                </div>
                {message.role === 'user' && (
                  <div className="w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>

              {/* Trade Action Card */}
              {message.action?.type === 'trade' && !message.action.confirmed && (
                <div className="ml-9 bg-gray-900 border border-gray-700 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-2">
                    {message.action.side === 'long' ? (
                      <TrendingUp className="w-4 h-4 text-green-400" />
                    ) : (
                      <TrendingDown className="w-4 h-4 text-red-400" />
                    )}
                    <span className="font-medium">
                      {message.action.side?.toUpperCase()} {message.action.symbol}
                    </span>
                    <Badge variant="outline" className="text-[10px]">
                      {mode === 'paper' ? 'Paper' : mode === 'live' ? 'Live' : 'View'}
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      className="flex-1 bg-green-600 hover:bg-green-700 text-xs"
                      onClick={() => handleConfirmTrade(message.id)}
                      disabled={mode === 'view'}
                    >
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Confirm
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1 text-xs border-gray-600"
                      onClick={() => handleRejectTrade(message.id)}
                    >
                      <X className="w-3 h-3 mr-1" />
                      Cancel
                    </Button>
                  </div>
                </div>
              )}

              {/* Confirmed trade */}
              {message.action?.confirmed && (
                <div className="ml-9 bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-2 flex items-center gap-2 text-xs text-green-400">
                  <CheckCircle className="w-4 h-4" />
                  Trade executed successfully
                </div>
              )}
            </div>
          ))}

          {/* Typing indicator */}
          {isTyping && (
            <div className="flex gap-2">
              <div className="w-7 h-7 rounded-full bg-purple-600 flex items-center justify-center">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-gray-800 rounded-lg px-4 py-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Quick Actions */}
      <div className="px-3 pb-2">
        <div className="flex flex-wrap gap-1">
          {quickActions.map((action, i) => (
            <button
              key={i}
              onClick={() => setInput(action.prompt)}
              className="text-[10px] px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded-full text-gray-400 hover:text-white transition-colors"
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="p-3 border-t border-gray-800">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about markets or place trades..."
            className="flex-1 bg-gray-900 border-gray-700 text-sm"
          />
          <Button 
            size="icon" 
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="bg-purple-600 hover:bg-purple-700"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

