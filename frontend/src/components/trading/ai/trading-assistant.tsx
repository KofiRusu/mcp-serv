'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useTradingStore } from '@/stores/trading-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { trainingDataLogger, MarketContext, TradeDecision } from '@/lib/trading/training-data-logger'
import { 
  Send, 
  Bot, 
  User, 
  Sparkles,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  X,
  Loader2
} from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  action?: TradingAction
  model?: string
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
  { label: 'Market analysis', prompt: "What's your take on BTC right now?" },
  { label: 'Trade idea', prompt: 'Got any good setups for ETH?' },
  { label: 'Portfolio review', prompt: "How are my positions looking?" },
  { label: 'Risk check', prompt: "Am I overexposed anywhere?" },
]

export function TradingAssistant() {
  const { currentSymbol, positions, portfolio, accounts, currentAccountId, addPosition, mode } = useTradingStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [sessionId] = useState(() => `session-${Date.now()}`)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Get current account balance
  const currentAccount = accounts.find(a => a.id === currentAccountId)
  const balance = currentAccount?.balance || portfolio.totalValue

  // Initialize with welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        id: '1',
        role: 'assistant',
        content: `Hey! I'm here to help with your trading. Currently watching **${currentSymbol}**.\n\nWhat would you like to know?`,
        timestamp: new Date(),
      }])
    }
  }, [currentSymbol, messages.length])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const parseTradeIntent = (text: string): TradingAction | null => {
    const lowerText = text.toLowerCase()
    
    // Detect trade intent
    const isLong = lowerText.includes('long') || (lowerText.includes('buy') && !lowerText.includes('why'))
    const isShort = lowerText.includes('short') || lowerText.includes('sell')
    
    if (!isLong && !isShort) return null

    // Extract symbol
    const symbols = ['btc', 'eth', 'sol', 'bnb', 'xrp', 'ada']
    const foundSymbol = symbols.find(s => lowerText.includes(s))
    const symbol = foundSymbol ? `${foundSymbol.toUpperCase()}USDT` : currentSymbol

    // Extract risk percentage
    const riskMatch = lowerText.match(/(\d+(?:\.\d+)?)\s*%?\s*risk/)
    const riskPercent = riskMatch ? parseFloat(riskMatch[1]) : 1

    return {
      type: 'trade',
      side: isLong ? 'long' : 'short',
      symbol,
      riskPercent,
      confirmed: false,
    }
  }

  const generateLocalResponse = useCallback((userMessage: string): { content: string; model?: string } => {
    const lowerMessage = userMessage.toLowerCase()
    
    // Market analysis keywords
    if (lowerMessage.includes('analyz') || lowerMessage.includes('trend') || lowerMessage.includes('market') || lowerMessage.includes('take') || lowerMessage.includes('btc') || lowerMessage.includes('eth')) {
      return {
        content: `Looking at **${currentSymbol}** - it's been consolidating lately. Key levels to watch:\n\n` +
          `• Support around the recent lows\n` +
          `• Resistance at the previous highs\n\n` +
          `Volume's been decent. I'd wait for a clear break either way before taking a position. What timeframe are you looking at?`,
        model: 'local',
      }
    }

    // Portfolio/position keywords
    if (lowerMessage.includes('portfolio') || lowerMessage.includes('position') || lowerMessage.includes('looking')) {
      if (positions.length === 0) {
        return {
          content: `You're flat right now - no open positions. Account sitting at **$${balance.toLocaleString()}**.\n\nAnything catching your eye?`,
          model: 'local',
        }
      }
      
      const totalPnl = positions.reduce((sum, p) => sum + p.pnl, 0)
      return {
        content: `Here's your position rundown:\n\n` +
          positions.map(p => 
            `• **${p.symbol}** ${p.side.toUpperCase()} - ${p.pnl >= 0 ? '🟢' : '🔴'} ${p.pnl >= 0 ? '+' : ''}$${p.pnl.toFixed(2)} (${p.pnlPercent.toFixed(1)}%)`
          ).join('\n') +
          `\n\nTotal P&L: **${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}**`,
        model: 'local',
      }
    }

    // Risk keywords
    if (lowerMessage.includes('risk') || lowerMessage.includes('overexposed')) {
      const totalRisk = positions.reduce((sum, p) => {
        if (p.stopLoss) {
          return sum + Math.abs(p.entryPrice - p.stopLoss) * p.size
        }
        return sum + (p.entryPrice * p.size * 0.05)
      }, 0)
      
      const riskPercent = (totalRisk / balance) * 100
      const positionsWithoutSL = positions.filter(p => !p.stopLoss).length

      return {
        content: `Risk check:\n\n` +
          `• Total at risk: **$${totalRisk.toFixed(2)}** (${riskPercent.toFixed(1)}% of account)\n` +
          `• Positions without stops: **${positionsWithoutSL}**\n\n` +
          `${riskPercent > 5 ? "⚠️ You're running a bit hot. Consider tightening stops or reducing size." : "✅ Looking reasonable. Keep those stops in place."}`,
        model: 'local',
      }
    }

    // Trade setup keywords
    if (lowerMessage.includes('setup') || lowerMessage.includes('trade idea') || lowerMessage.includes('entry')) {
      return {
        content: `For **${currentSymbol}**, I'd look for:\n\n` +
          `• A pullback to support before going long\n` +
          `• Clear rejection candles for confirmation\n` +
          `• 1-2% risk per trade max\n\n` +
          `What's your preferred timeframe? I can be more specific.`,
        model: 'local',
      }
    }

    // Help/greeting
    if (lowerMessage.includes('hello') || lowerMessage.includes('hi') || lowerMessage.includes('hey') || lowerMessage.includes('help')) {
      return {
        content: `Hey! I can help you with:\n\n` +
          `📊 **Market Analysis** - "What's your take on BTC?"\n` +
          `💼 **Portfolio Review** - "How are my positions?"\n` +
          `⚠️ **Risk Check** - "Am I overexposed?"\n` +
          `📈 **Trade Ideas** - "Got any setups for ETH?"\n\n` +
          `What would you like to know?`,
        model: 'local',
      }
    }

    // Default conversational response
    return {
      content: `I can help with market analysis, trade ideas, or review your positions. Just ask away!`,
      model: 'local',
    }
  }, [currentSymbol, positions, balance])

  const generateAIResponse = useCallback(async (userMessage: string): Promise<{ content: string; model?: string }> => {
    try {
      const response = await fetch('/api/trading-assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          sessionId,
          conversationHistory: messages.slice(-10).map(m => ({
            role: m.role,
            content: m.content,
            timestamp: m.timestamp.toISOString(),
          })),
          tradingContext: {
            currentSymbol,
            positions: positions.map(p => ({
              symbol: p.symbol,
              side: p.side,
              size: p.size,
              entryPrice: p.entryPrice,
              currentPrice: p.currentPrice,
              pnl: p.pnl,
              pnlPercent: p.pnlPercent,
            })),
            balance,
            mode,
          },
        }),
      })

      if (!response.ok) {
        console.error('API response not ok:', response.status)
        throw new Error('Failed to get response')
      }

      const data = await response.json()
      return {
        content: data.response,
        model: data.model,
      }
    } catch (error) {
      console.error('AI response error:', error)
      // Fallback to local response
      return generateLocalResponse(userMessage)
    }
  }, [messages, currentSymbol, positions, balance, mode, sessionId, generateLocalResponse])

  const handleSend = async () => {
    if (!input.trim() || isTyping) return

    const userInput = input.trim()
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: userInput,
      timestamp: new Date(),
    }

    // Update state immediately
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsTyping(true)

    // Check for trade intent
    const tradeAction = parseTradeIntent(userInput)

    try {
      // Get AI response
      const { content, model } = await generateAIResponse(userInput)
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content,
        timestamp: new Date(),
        action: tradeAction || undefined,
        model,
      }

      setMessages(prev => [...prev, assistantMessage])

      // Log conversation for PersRM training
      try {
        const marketContext: MarketContext = {
          symbol: currentSymbol,
          price: positions.find(p => p.symbol === currentSymbol)?.currentPrice || 0,
          change24h: 0,
          volume24h: 0,
          timestamp: new Date().toISOString(),
        }

        // Convert trade action to decision format if present
        let decision: TradeDecision | undefined
        if (tradeAction && tradeAction.type === 'trade') {
          decision = {
            action: tradeAction.side === 'long' ? 'LONG' : tradeAction.side === 'short' ? 'SHORT' : 'HOLD',
            symbol: tradeAction.symbol || currentSymbol,
            riskPercent: tradeAction.riskPercent,
            confidence: 0.7,
            reasoning: content,
          }
        }

        trainingDataLogger.logConversation(
          userInput,
          content,
          marketContext,
          model,
          decision
        )
      } catch (logError) {
        // Silent fail for logging
        console.debug('Training data log failed:', logError)
      }
    } catch (error) {
      console.error('handleSend error:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "Sorry, I'm having a moment. Try that again?",
        timestamp: new Date(),
        model: 'error',
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
    }
  }

  const handleConfirmTrade = (messageId: string) => {
    const message = messages.find(m => m.id === messageId)
    if (!message?.action || message.action.type !== 'trade') return

    if (mode === 'view') {
      alert('Switch to Paper or Live mode to execute trades')
      return
    }

    const action = message.action
    const price = 67500
    const riskAmount = balance * (action.riskPercent! / 100)
    const slDistance = price * 0.02
    const size = riskAmount / slDistance
    const stopLoss = action.side === 'long' ? price - slDistance : price + slDistance
    const takeProfit = action.side === 'long' ? price + slDistance * 3 : price - slDistance * 3
    
    const positionId = `pos-${Date.now()}`
    
    addPosition({
      symbol: action.symbol!,
      side: action.side!,
      size,
      entryPrice: price,
      currentPrice: price,
      pnl: 0,
      pnlPercent: 0,
      leverage: 1,
      stopLoss,
      takeProfit,
      strategy: 'AI Assistant',
      openedAt: new Date().toISOString(),
    })

    // Log trade decision for PersRM training
    try {
      const marketContext: MarketContext = {
        symbol: action.symbol!,
        price,
        change24h: 0,
        volume24h: 0,
        timestamp: new Date().toISOString(),
      }

      const decision: TradeDecision = {
        action: action.side === 'long' ? 'LONG' : 'SHORT',
        symbol: action.symbol!,
        entryPrice: price,
        stopLoss,
        takeProfit: [takeProfit],
        riskPercent: action.riskPercent,
        confidence: 0.7,
        reasoning: `User confirmed ${action.side} trade via AI Assistant`,
      }

      trainingDataLogger.logTradeDecision(
        decision,
        marketContext,
        message.content,
        { balance, openPositions: positions.length, unrealizedPnl: positions.reduce((sum, p) => sum + p.pnl, 0) },
        positionId
      )
    } catch (logError) {
      console.debug('Training data log failed:', logError)
    }

    setMessages(prev => prev.map(m => 
      m.id === messageId 
        ? { ...m, action: { ...m.action!, confirmed: true } }
        : m
    ))

    const confirmMessage: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: `Done! ${action.side?.toUpperCase()} ${action.symbol} is live. I've set a stop at $${stopLoss.toFixed(0)} and target at $${takeProfit.toFixed(0)}. Keep an eye on it! 👀`,
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
      content: "No worries, cancelled. Let me know if you want to try a different setup.",
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, rejectMessage])
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages Container */}
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto p-3 space-y-4"
      >
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
                {message.model && message.role === 'assistant' && (
                  <div className="text-[9px] text-gray-500 mt-1 flex items-center gap-1">
                    <Sparkles className="w-2.5 h-2.5" />
                    {message.model}
                  </div>
                )}
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
                    {message.action.riskPercent}% risk
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
                    Execute
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 text-xs border-gray-600"
                    onClick={() => handleRejectTrade(message.id)}
                  >
                    <X className="w-3 h-3 mr-1" />
                    Pass
                  </Button>
                </div>
              </div>
            )}

            {/* Confirmed trade */}
            {message.action?.confirmed && (
              <div className="ml-9 bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-2 flex items-center gap-2 text-xs text-green-400">
                <CheckCircle className="w-4 h-4" />
                Position opened
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
            <div className="bg-gray-800 rounded-lg px-4 py-2 flex items-center gap-2">
              <Loader2 className="w-3 h-3 animate-spin text-purple-400" />
              <span className="text-xs text-gray-400">Thinking...</span>
            </div>
          </div>
        )}
        
        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

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
            onKeyDown={handleKeyDown}
            placeholder="Ask about markets or place trades..."
            className="flex-1 bg-gray-900 border-gray-700 text-sm"
            disabled={isTyping}
          />
          <Button 
            size="icon" 
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="bg-purple-600 hover:bg-purple-700"
          >
            {isTyping ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
