/**
 * Centralized Interaction Logger
 * 
 * Logs all user interactions for analytics and PersRM training:
 * - Backtest runs and results
 * - Chat conversations
 * - Trade executions
 * - Errors and failures
 * - UI interactions
 */

export type InteractionType = 
  | 'backtest_started'
  | 'backtest_completed'
  | 'backtest_error'
  | 'chat_message'
  | 'chat_response'
  | 'trade_opened'
  | 'trade_closed'
  | 'trade_modified'
  | 'order_placed'
  | 'order_cancelled'
  | 'exchange_connected'
  | 'exchange_disconnected'
  | 'error'
  | 'ui_action'

export interface InteractionLog {
  id: string
  type: InteractionType
  timestamp: string
  sessionId: string
  data: Record<string, any>
  metadata?: {
    symbol?: string
    accountId?: string
    mode?: string
    duration?: number
    error?: string
  }
}

// Generate unique session ID
const SESSION_ID = typeof window !== 'undefined' 
  ? `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  : 'server'

// In-memory buffer for batch sending
let logBuffer: InteractionLog[] = []
let flushTimeout: NodeJS.Timeout | null = null
const FLUSH_INTERVAL = 5000 // Flush every 5 seconds
const MAX_BUFFER_SIZE = 50 // Flush if buffer exceeds this

/**
 * Log an interaction
 */
export async function logInteraction(
  type: InteractionType,
  data: Record<string, any>,
  metadata?: InteractionLog['metadata']
): Promise<void> {
  const log: InteractionLog = {
    id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
    type,
    timestamp: new Date().toISOString(),
    sessionId: SESSION_ID,
    data,
    metadata,
  }
  
  // Add to buffer
  logBuffer.push(log)
  
  // Also log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Interaction] ${type}:`, data)
  }
  
  // Flush if buffer is full
  if (logBuffer.length >= MAX_BUFFER_SIZE) {
    await flushLogs()
  } else if (!flushTimeout) {
    // Schedule flush
    flushTimeout = setTimeout(flushLogs, FLUSH_INTERVAL)
  }
}

/**
 * Flush logs to backend
 */
export async function flushLogs(): Promise<void> {
  if (flushTimeout) {
    clearTimeout(flushTimeout)
    flushTimeout = null
  }
  
  if (logBuffer.length === 0) return
  
  const logsToSend = [...logBuffer]
  logBuffer = []
  
  try {
    await fetch('/api/interactions/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ logs: logsToSend }),
    })
  } catch (error) {
    console.error('Failed to flush interaction logs:', error)
    // Put logs back in buffer on failure
    logBuffer = [...logsToSend, ...logBuffer]
  }
}

// Convenience functions for common interaction types

/**
 * Log backtest started
 */
export function logBacktestStarted(config: Record<string, any>): void {
  logInteraction('backtest_started', { config }, {
    symbol: config.symbols?.join(', '),
  })
}

/**
 * Log backtest completed
 */
export function logBacktestCompleted(
  backtestId: string,
  config: Record<string, any>,
  metrics: Record<string, any>,
  duration: number
): void {
  logInteraction('backtest_completed', {
    backtestId,
    config,
    metrics,
  }, {
    symbol: config.symbols?.join(', '),
    duration,
  })
}

/**
 * Log backtest error
 */
export function logBacktestError(
  backtestId: string,
  error: string,
  config?: Record<string, any>
): void {
  logInteraction('backtest_error', {
    backtestId,
    config,
  }, {
    error,
  })
}

/**
 * Log chat message sent
 */
export function logChatMessage(
  message: string,
  context: Record<string, any>
): void {
  logInteraction('chat_message', {
    message,
    context,
  }, {
    symbol: context.symbol,
    mode: context.mode,
  })
}

/**
 * Log chat response received
 */
export function logChatResponse(
  response: string,
  model: string,
  context: Record<string, any>
): void {
  logInteraction('chat_response', {
    response,
    model,
    context,
  }, {
    symbol: context.symbol,
  })
}

/**
 * Log trade opened
 */
export function logTradeOpened(trade: Record<string, any>): void {
  logInteraction('trade_opened', trade, {
    symbol: trade.symbol,
    accountId: trade.accountId,
    mode: trade.mode,
  })
}

/**
 * Log trade closed
 */
export function logTradeClosed(trade: Record<string, any>): void {
  logInteraction('trade_closed', trade, {
    symbol: trade.symbol,
    accountId: trade.accountId,
    duration: trade.duration,
  })
}

/**
 * Log order placed
 */
export function logOrderPlaced(order: Record<string, any>): void {
  logInteraction('order_placed', order, {
    symbol: order.symbol,
    accountId: order.accountId,
  })
}

/**
 * Log exchange connection
 */
export function logExchangeConnected(
  exchange: string,
  accountId: string,
  network?: string
): void {
  logInteraction('exchange_connected', {
    exchange,
    accountId,
    network,
  }, {
    accountId,
  })
}

/**
 * Log exchange disconnection
 */
export function logExchangeDisconnected(
  exchange: string,
  accountId: string
): void {
  logInteraction('exchange_disconnected', {
    exchange,
    accountId,
  }, {
    accountId,
  })
}

/**
 * Log error
 */
export function logError(
  error: string,
  context?: Record<string, any>
): void {
  logInteraction('error', {
    error,
    context,
  }, {
    error,
  })
}

/**
 * Log UI action (button clicks, tab changes, etc.)
 */
export function logUIAction(
  action: string,
  details?: Record<string, any>
): void {
  logInteraction('ui_action', {
    action,
    details,
  })
}

// Flush logs before page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    // Use sendBeacon for reliable delivery on page close
    if (logBuffer.length > 0 && navigator.sendBeacon) {
      navigator.sendBeacon(
        '/api/interactions/log',
        JSON.stringify({ logs: logBuffer })
      )
    }
  })
}

// Export session ID for linking logs
export { SESSION_ID }

