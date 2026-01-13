/**
 * Block Execution Simulator
 * 
 * Simulates automation execution by processing blocks in topological order
 * and passing data from outputs to connected inputs.
 */

import type { Block, BlockType } from '../block-node'

export interface BlockOutput {
  blockId: string
  blockName: string
  blockType: BlockType
  timestamp: Date
  data: any
  status: 'pending' | 'running' | 'success' | 'error'
  error?: string
  duration?: number
}

export interface ExecutionState {
  status: 'idle' | 'running' | 'completed' | 'error'
  currentBlockId: string | null
  outputs: BlockOutput[]
  startTime?: Date
  endTime?: Date
}

/**
 * Get blocks in topological order (respecting connections)
 */
export function getTopologicalOrder(blocks: Block[]): Block[] {
  const blockMap = new Map(blocks.map(b => [b.id, b]))
  const visited = new Set<string>()
  const result: Block[] = []
  
  // Build reverse connection map (who connects TO this block)
  const incomingConnections = new Map<string, string[]>()
  blocks.forEach(block => {
    block.connections.forEach(targetId => {
      const existing = incomingConnections.get(targetId) || []
      existing.push(block.id)
      incomingConnections.set(targetId, existing)
    })
  })
  
  // Find root blocks (no incoming connections)
  const roots = blocks.filter(b => !incomingConnections.has(b.id) || incomingConnections.get(b.id)!.length === 0)
  
  // BFS from roots
  const queue = [...roots]
  while (queue.length > 0) {
    const block = queue.shift()!
    if (visited.has(block.id)) continue
    
    visited.add(block.id)
    result.push(block)
    
    // Add connected blocks
    block.connections.forEach(connId => {
      const connBlock = blockMap.get(connId)
      if (connBlock && !visited.has(connId)) {
        queue.push(connBlock)
      }
    })
  }
  
  // Add any unvisited blocks (disconnected)
  blocks.forEach(b => {
    if (!visited.has(b.id)) {
      result.push(b)
    }
  })
  
  return result
}

/**
 * Simulate a single block's execution based on its type and config
 */
export function simulateBlockExecution(
  block: Block,
  inputData: any[] // Data from connected source blocks
): { output: any; displayText: string } {
  const timestamp = new Date().toISOString()
  
  switch (block.type) {
    case 'source': {
      // Data source blocks generate market data
      const symbol = block.config.symbol || 'BTCUSDT'
      const price = 95000 + Math.random() * 1000 // Simulated price
      const volume = Math.floor(1000 + Math.random() * 5000)
      return {
        output: {
          symbol,
          price: price.toFixed(2),
          volume,
          timestamp,
          open: (price - 50).toFixed(2),
          high: (price + 100).toFixed(2),
          low: (price - 150).toFixed(2),
          close: price.toFixed(2),
        },
        displayText: `📊 ${symbol}: $${price.toFixed(2)} (Vol: ${volume})`
      }
    }
    
    case 'indicator': {
      const indicatorName = block.name.toLowerCase()
      const prices = inputData.map(d => parseFloat(d?.price || d?.close || '95000'))
      const latestPrice = prices[0] || 95000
      
      if (indicatorName.includes('rsi')) {
        const period = block.config.period || 14
        const rsiValue = 30 + Math.random() * 40 // Simulated RSI
        const overbought = block.config.overbought || 70
        const oversold = block.config.oversold || 30
        const signal = rsiValue > overbought ? 'OVERBOUGHT' : rsiValue < oversold ? 'OVERSOLD' : 'NEUTRAL'
        return {
          output: { rsi: rsiValue.toFixed(1), period, signal, price: latestPrice },
          displayText: `📈 RSI(${period}): ${rsiValue.toFixed(1)} → ${signal}`
        }
      }
      
      if (indicatorName.includes('macd')) {
        const fast = block.config.fast || 12
        const slow = block.config.slow || 26
        const signalPeriod = block.config.signal || 9
        const macdValue = -50 + Math.random() * 100
        const signalLine = macdValue + (-10 + Math.random() * 20)
        const histogram = macdValue - signalLine
        const trend = histogram > 0 ? 'BULLISH' : 'BEARISH'
        return {
          output: { macd: macdValue.toFixed(2), signal: signalLine.toFixed(2), histogram: histogram.toFixed(2), trend },
          displayText: `📈 MACD(${fast},${slow},${signalPeriod}): ${macdValue.toFixed(2)} → ${trend}`
        }
      }
      
      if (indicatorName.includes('moving') || indicatorName.includes('ma')) {
        const period = block.config.period || 20
        const maType = block.config.type || 'SMA'
        const maValue = latestPrice + (-200 + Math.random() * 400)
        const trend = latestPrice > maValue ? 'ABOVE (Bullish)' : 'BELOW (Bearish)'
        return {
          output: { ma: maValue.toFixed(2), type: maType, period, trend },
          displayText: `📈 ${maType}(${period}): $${maValue.toFixed(2)} → ${trend}`
        }
      }
      
      if (indicatorName.includes('bollinger')) {
        const period = block.config.period || 20
        const stdDev = block.config.stdDev || 2
        const middle = latestPrice
        const upper = middle + stdDev * 500
        const lower = middle - stdDev * 500
        const position = latestPrice > upper ? 'ABOVE UPPER' : latestPrice < lower ? 'BELOW LOWER' : 'WITHIN BANDS'
        return {
          output: { upper: upper.toFixed(2), middle: middle.toFixed(2), lower: lower.toFixed(2), position },
          displayText: `📈 BB(${period},${stdDev}): ${position}`
        }
      }
      
      if (indicatorName.includes('money') || indicatorName.includes('structure')) {
        const period = block.config.period || 20
        const structure = ['Higher High', 'Lower Low', 'Range Bound', 'Break of Structure'][Math.floor(Math.random() * 4)]
        return {
          output: { structure, period, price: latestPrice },
          displayText: `🏗️ Market Structure: ${structure}`
        }
      }
      
      // Generic indicator
      return {
        output: { value: (50 + Math.random() * 50).toFixed(2), name: block.name },
        displayText: `📊 ${block.name}: Calculated`
      }
    }
    
    case 'stop_loss': {
      const type = block.config.type || 'percent'
      const value = block.config.value || 2
      const inputPrice = inputData[0]?.price || 95000
      const stopPrice = type === 'percent' 
        ? (parseFloat(inputPrice) * (1 - value / 100)).toFixed(2)
        : (parseFloat(inputPrice) - value).toFixed(2)
      return {
        output: { stopPrice, type, value, entryPrice: inputPrice },
        displayText: `🛡️ Stop Loss: $${stopPrice} (-${value}${type === 'percent' ? '%' : ''})`
      }
    }
    
    case 'take_profit': {
      const type = block.config.type || 'percent'
      const value = block.config.value || 4
      const inputPrice = inputData[0]?.price || 95000
      const targetPrice = type === 'percent' 
        ? (parseFloat(inputPrice) * (1 + value / 100)).toFixed(2)
        : (parseFloat(inputPrice) + value).toFixed(2)
      return {
        output: { targetPrice, type, value, entryPrice: inputPrice },
        displayText: `🎯 Take Profit: $${targetPrice} (+${value}${type === 'percent' ? '%' : ''})`
      }
    }
    
    case 'entry': {
      const type = block.config.type || 'market'
      const signals = inputData.filter(d => d?.signal || d?.rsi || d?.macd)
      const bullishSignals = signals.filter(s => 
        s.signal === 'OVERSOLD' || s.trend === 'BULLISH' || s.position === 'BELOW LOWER'
      ).length
      const shouldEnter = bullishSignals >= 2
      return {
        output: { 
          action: shouldEnter ? 'ENTER_LONG' : 'WAIT', 
          type, 
          bullishSignals,
          reason: shouldEnter ? 'Multiple bullish signals detected' : 'Insufficient signals'
        },
        displayText: shouldEnter 
          ? `🟢 ENTRY SIGNAL: ${bullishSignals} bullish indicators confirm` 
          : `⏳ Wait: Only ${bullishSignals} bullish signals`
      }
    }
    
    case 'exit': {
      const type = block.config.type || 'market'
      const signals = inputData.filter(d => d?.signal || d?.rsi || d?.macd)
      const bearishSignals = signals.filter(s => 
        s.signal === 'OVERBOUGHT' || s.trend === 'BEARISH' || s.position === 'ABOVE UPPER'
      ).length
      const shouldExit = bearishSignals >= 2
      return {
        output: { 
          action: shouldExit ? 'EXIT' : 'HOLD', 
          type, 
          bearishSignals,
          reason: shouldExit ? 'Multiple bearish signals detected' : 'Position looks safe'
        },
        displayText: shouldExit 
          ? `🔴 EXIT SIGNAL: ${bearishSignals} bearish indicators warn` 
          : `✅ Hold: Position stable`
      }
    }
    
    case 'order': {
      const exchange = block.config.exchange || 'binance'
      const side = block.config.side || 'buy'
      const orderType = block.name.toLowerCase().includes('limit') ? 'limit' : 'market'
      const price = inputData[0]?.price || '95000'
      return {
        output: { 
          orderId: `sim_${Date.now()}`,
          exchange, 
          side: side.toUpperCase(), 
          type: orderType,
          price,
          status: 'SIMULATED'
        },
        displayText: `📝 ${side.toUpperCase()} ${orderType.toUpperCase()} @ $${price} (simulated)`
      }
    }
    
    case 'risk_check': {
      const maxDrawdown = block.config.maxDrawdown || 10
      const currentDrawdown = Math.random() * 15
      const passed = currentDrawdown < maxDrawdown
      return {
        output: { passed, currentDrawdown: currentDrawdown.toFixed(2), maxDrawdown },
        displayText: passed 
          ? `✅ Risk Check Passed: ${currentDrawdown.toFixed(1)}% < ${maxDrawdown}%` 
          : `⚠️ Risk Warning: ${currentDrawdown.toFixed(1)}% exceeds ${maxDrawdown}%`
      }
    }
    
    case 'position_size': {
      const method = block.config.method || 'fixed'
      const risk = block.config.risk || 1
      const accountSize = 10000
      const positionSize = (accountSize * risk / 100).toFixed(2)
      return {
        output: { positionSize, method, riskPercent: risk },
        displayText: `📐 Position Size: $${positionSize} (${risk}% risk)`
      }
    }
    
    case 'notification': {
      const notifType = block.config.type || 'console'
      const message = `Signal at ${timestamp}`
      return {
        output: { sent: true, type: notifType, message },
        displayText: `🔔 Notification: ${notifType.toUpperCase()} alert sent`
      }
    }
    
    case 'webhook': {
      const url = block.config.url || 'https://example.com/webhook'
      return {
        output: { called: true, url, status: 200 },
        displayText: `🌐 Webhook: Called ${url.substring(0, 30)}...`
      }
    }
    
    case 'output': {
      const outputDir = block.config.output_dir || '/app/data'
      return {
        output: { saved: true, path: outputDir, records: inputData.length },
        displayText: `💾 Output: Saved ${inputData.length} records to ${outputDir}`
      }
    }
    
    case 'filter':
    case 'transform': {
      const condition = block.config.condition || 'pass all'
      const inputCount = inputData.length
      const outputCount = Math.floor(inputCount * 0.7) || 1
      return {
        output: { filtered: inputData.slice(0, outputCount), inputCount, outputCount },
        displayText: `🔀 ${block.name}: ${inputCount} → ${outputCount} records`
      }
    }
    
    case 'aggregate': {
      const window = block.config.window || '1m'
      return {
        output: { aggregated: inputData, window, count: inputData.length },
        displayText: `📦 Aggregate: Combined ${inputData.length} inputs (${window} window)`
      }
    }
    
    case 'agent': {
      const agentName = block.name.toLowerCase()
      if (agentName.includes('aggr')) {
        return {
          output: { trades: 150, cvd: '+$1.2M', whales: 3, volume: '45.2 BTC' },
          displayText: `🤖 AGGR: 150 trades, CVD +$1.2M, 3 whale alerts`
        }
      }
      if (agentName.includes('coinglass')) {
        return {
          output: { openInterest: '+2.5%', fundingRate: '0.01%', liquidations: '$15M' },
          displayText: `📊 CoinGlass: OI +2.5%, Funding 0.01%, $15M liquidated`
        }
      }
      if (agentName.includes('youtube')) {
        return {
          output: { videos: 5, sentiment: 'bullish', confidence: 0.72 },
          displayText: `📺 YouTube: 5 videos analyzed, sentiment bullish (72%)`
        }
      }
      return {
        output: { status: 'active', name: block.name },
        displayText: `🤖 ${block.name}: Active`
      }
    }
    
    case 'fusion': {
      const signals = inputData.filter(d => d?.signal || d?.trend || d?.action)
      const bullish = signals.filter(s => 
        ['OVERSOLD', 'BULLISH', 'ENTER_LONG'].includes(s?.signal || s?.trend || s?.action)
      ).length
      const total = signals.length || 1
      const confluenceScore = (bullish / total * 100).toFixed(0)
      return {
        output: { confluenceScore, bullish, total, recommendation: bullish > total / 2 ? 'BUY' : 'WAIT' },
        displayText: `🔗 Fusion: ${confluenceScore}% confluence (${bullish}/${total} bullish)`
      }
    }
    
    case 'validator': {
      const minConfidence = block.config.minConfidence || 0.8
      const inputScore = Math.random()
      const valid = inputScore >= minConfidence
      return {
        output: { valid, confidence: inputScore.toFixed(2), threshold: minConfidence },
        displayText: valid 
          ? `✅ Validated: ${(inputScore * 100).toFixed(0)}% confidence` 
          : `❌ Rejected: ${(inputScore * 100).toFixed(0)}% < ${(minConfidence * 100).toFixed(0)}% threshold`
      }
    }
    
    case 'condition': {
      const above = block.config.above || 0
      const below = block.config.below || 999999
      const price = parseFloat(inputData[0]?.price || '95000')
      const passed = price > above && price < below
      return {
        output: { passed, price, above, below },
        displayText: passed 
          ? `✅ Condition Met: $${price} in range` 
          : `❌ Condition Failed: $${price} out of range`
      }
    }
    
    case 'monitoring': {
      return {
        output: { logged: true, timestamp, inputs: inputData.length },
        displayText: `📋 Journal: Logged ${inputData.length} events at ${timestamp}`
      }
    }
    
    case 'learning': {
      const feedbackPath = block.config.feedbackPath || '/data/feedback'
      return {
        output: { learned: true, path: feedbackPath, samplesProcessed: inputData.length },
        displayText: `🎓 Learning: Processed ${inputData.length} samples for improvement`
      }
    }
    
    case 'strategy': {
      const interval = block.config.interval || '4h'
      const splits = block.config.splits || 4
      return {
        output: { strategy: 'DCA', interval, splits, nextBuy: 'in 4 hours' },
        displayText: `📈 DCA Strategy: ${splits} splits every ${interval}`
      }
    }
    
    case 'chart': {
      const rows = block.config.rows || 24
      return {
        output: { rendered: true, rows, period: block.config.period || '1m' },
        displayText: `📊 Chart: Footprint rendered (${rows} rows)`
      }
    }
    
    case 'knowledgebase': {
      const path = block.config.path || '/data/kb'
      return {
        output: { queried: true, path, results: 15 },
        displayText: `📚 Knowledge: 15 relevant entries retrieved`
      }
    }
    
    default:
      return {
        output: { processed: true, type: block.type, name: block.name },
        displayText: `⚙️ ${block.name}: Processed`
      }
  }
}

/**
 * Execute all blocks in order and return outputs
 */
export async function executeAutomation(
  blocks: Block[],
  onProgress?: (output: BlockOutput) => void
): Promise<ExecutionState> {
  const state: ExecutionState = {
    status: 'running',
    currentBlockId: null,
    outputs: [],
    startTime: new Date()
  }
  
  const orderedBlocks = getTopologicalOrder(blocks)
  const outputMap = new Map<string, any>() // Store outputs by block ID
  
  for (const block of orderedBlocks) {
    state.currentBlockId = block.id
    
    // Emit pending status
    const pendingOutput: BlockOutput = {
      blockId: block.id,
      blockName: block.name,
      blockType: block.type,
      timestamp: new Date(),
      data: null,
      status: 'running'
    }
    onProgress?.(pendingOutput)
    
    // Small delay for visual effect
    await new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 200))
    
    try {
      // Gather inputs from connected source blocks
      const inputData: any[] = []
      
      // Find blocks that connect TO this block
      blocks.forEach(sourceBlock => {
        if (sourceBlock.connections.includes(block.id)) {
          const sourceOutput = outputMap.get(sourceBlock.id)
          if (sourceOutput) {
            inputData.push(sourceOutput)
          }
        }
      })
      
      // Execute block
      const startTime = Date.now()
      const { output, displayText } = simulateBlockExecution(block, inputData)
      const duration = Date.now() - startTime
      
      // Store output for downstream blocks
      outputMap.set(block.id, output)
      
      // Emit success
      const successOutput: BlockOutput = {
        blockId: block.id,
        blockName: block.name,
        blockType: block.type,
        timestamp: new Date(),
        data: { output, displayText, inputsReceived: inputData.length },
        status: 'success',
        duration
      }
      state.outputs.push(successOutput)
      onProgress?.(successOutput)
      
    } catch (error: any) {
      const errorOutput: BlockOutput = {
        blockId: block.id,
        blockName: block.name,
        blockType: block.type,
        timestamp: new Date(),
        data: null,
        status: 'error',
        error: error.message
      }
      state.outputs.push(errorOutput)
      onProgress?.(errorOutput)
    }
  }
  
  state.status = 'completed'
  state.currentBlockId = null
  state.endTime = new Date()
  
  return state
}

/**
 * Format execution output for display
 */
export function formatExecutionOutput(outputs: BlockOutput[]): string[] {
  const lines: string[] = [
    '═══════════════════════════════════════════════════════════',
    '  🚀 AUTOMATION EXECUTION STARTED',
    '═══════════════════════════════════════════════════════════',
    ''
  ]
  
  outputs.forEach((output, index) => {
    const statusIcon = output.status === 'success' ? '✓' : output.status === 'error' ? '✗' : '⏳'
    const typeIcon = getTypeIcon(output.blockType)
    
    lines.push(`┌─ Block ${index + 1}: ${output.blockName} [${output.blockType.toUpperCase()}]`)
    lines.push(`│  ${statusIcon} Status: ${output.status.toUpperCase()}${output.duration ? ` (${output.duration}ms)` : ''}`)
    
    if (output.status === 'success' && output.data?.displayText) {
      lines.push(`│  ${typeIcon} ${output.data.displayText}`)
      if (output.data.inputsReceived > 0) {
        lines.push(`│  📥 Received data from ${output.data.inputsReceived} connected block(s)`)
      }
    }
    
    if (output.status === 'error') {
      lines.push(`│  ❌ Error: ${output.error}`)
    }
    
    lines.push('└───────────────────────────────────────────────────────────')
    lines.push('')
  })
  
  lines.push('═══════════════════════════════════════════════════════════')
  lines.push('  ✅ AUTOMATION EXECUTION COMPLETED')
  lines.push('═══════════════════════════════════════════════════════════')
  
  return lines
}

function getTypeIcon(type: BlockType): string {
  const icons: Partial<Record<BlockType, string>> = {
    source: '📊',
    indicator: '📈',
    transform: '🔀',
    filter: '🔍',
    aggregate: '📦',
    entry: '🟢',
    exit: '🔴',
    order: '📝',
    position: '📊',
    risk_check: '🛡️',
    position_size: '📐',
    stop_loss: '🛑',
    take_profit: '🎯',
    notification: '🔔',
    webhook: '🌐',
    output: '💾',
    agent: '🤖',
    fusion: '🔗',
    validator: '✅',
    condition: '❓',
    monitoring: '📋',
    learning: '🎓',
    strategy: '📈',
    chart: '📊',
    knowledgebase: '📚',
  }
  return icons[type] || '⚙️'
}

