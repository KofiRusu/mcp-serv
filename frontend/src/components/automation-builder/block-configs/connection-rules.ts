/**
 * Connection Rules for Automation Blocks
 * Defines which block types can connect to each other
 */

import type { BlockType } from '../block-node'

// Output types that each block category produces
export const BLOCK_OUTPUT_TYPES: Record<string, string[]> = {
  // Data Sources - produce market data
  source: ['market-data', 'historical-data', 'custom-data'],
  
  // Indicators - produce indicator values
  indicator: ['indicator-value', 'pattern-signal'],
  
  // Transforms - produce filtered/aggregated data
  transform: ['filtered-data', 'aggregated-data'],
  filter: ['filtered-data'],
  aggregate: ['aggregated-data'],
  
  // Trading signals
  entry: ['trade-signal'],
  exit: ['trade-signal'],
  signal: ['signal-emitted'],
  
  // Orders
  order: ['order-result'],
  position: ['position-data'],
  
  // Risk management
  risk_check: ['risk-status', 'position-size'],
  position_size: ['position-size'],
  stop_loss: ['stop-order'],
  take_profit: ['tp-order'],
  strategy: ['dca-signal'],
  
  // Alerts
  condition: ['condition-result'],
  notification: ['notification-sent'],
  webhook: ['webhook-response'],
  
  // Outputs
  output: ['file-written', 'db-written'],
  
  // Agents
  agent: ['aggr-data', 'orderflow-data', 'heatmap-data', 'research-data', 'execution-result', 'risk-status'],
  chart: ['footprint-data'],
  
  // Knowledge
  knowledgebase: ['kb-data', 'kb-query-result'],
  learning: ['backtest-result', 'learning-feedback'],
  
  // Fusion
  fusion: ['fusion-signal', 'scenario-signal', 'confluence-score'],
  validator: ['validated-signal'],
  
  // Monitoring
  monitoring: ['journal-entry', 'audit-log'],
}

// Input types that each block category accepts
export const BLOCK_INPUT_TYPES: Record<string, string[]> = {
  // Data Sources - no inputs (they are sources)
  source: [],
  
  // Indicators - accept market data
  indicator: ['market-data', 'historical-data', 'filtered-data', 'aggregated-data'],
  
  // Transforms - accept various data types
  transform: ['market-data', 'indicator-value', 'custom-data', 'filtered-data'],
  filter: ['market-data', 'indicator-value'],
  aggregate: ['market-data', 'indicator-value', 'filtered-data'],
  
  // Trading - accept signals and indicators
  entry: ['indicator-value', 'pattern-signal', 'fusion-signal', 'confluence-score', 'validated-signal'],
  exit: ['indicator-value', 'pattern-signal', 'position-data'],
  signal: ['trade-signal', 'fusion-signal'],
  
  // Orders - accept trade signals
  order: ['trade-signal', 'validated-signal', 'dca-signal'],
  position: ['order-result', 'market-data'],
  
  // Risk management - accept signals and positions
  risk_check: ['trade-signal', 'position-data', 'execution-result'],
  position_size: ['trade-signal', 'risk-status'],
  stop_loss: ['trade-signal', 'position-data', 'order-result'],
  take_profit: ['trade-signal', 'position-data', 'order-result'],
  strategy: ['trade-signal', 'market-data'],
  
  // Alerts - accept conditions and signals
  condition: ['market-data', 'indicator-value'],
  notification: ['condition-result', 'trade-signal', 'indicator-value', 'execution-result'],
  webhook: ['condition-result', 'trade-signal', 'indicator-value'],
  
  // Outputs - accept various data
  output: ['market-data', 'indicator-value', 'trade-signal', 'aggregated-data', 'fusion-signal'],
  
  // Agents - some are sources, some accept data
  agent: ['position-data', 'trade-signal', 'execution-result', 'dca-signal'],
  chart: ['market-data', 'aggr-data'],
  
  // Knowledge
  knowledgebase: ['research-data', 'market-data', 'indicator-value', 'pattern-signal'],
  learning: ['historical-data', 'trade-signal', 'journal-entry', 'backtest-result'],
  
  // Fusion - accept multiple signal types
  fusion: ['indicator-value', 'kb-data', 'pattern-signal', 'fusion-signal', 'confluence-score'],
  validator: ['trade-signal', 'fusion-signal', 'confluence-score'],
  
  // Monitoring - accept execution results
  monitoring: ['execution-result', 'order-result', 'risk-status', 'journal-entry'],
}

// Valid connection matrix - which block types can connect to which
export const CONNECTION_MATRIX: Record<BlockType, BlockType[]> = {
  // Data Sources → Indicators, Transforms, Outputs, Charts, Knowledge
  source: ['indicator', 'transform', 'filter', 'aggregate', 'output', 'chart', 'knowledgebase', 'condition'],
  
  // Indicators → Fusion, Risk, Trading, Outputs, Alerts, Knowledge
  indicator: ['fusion', 'validator', 'risk_check', 'position_size', 'entry', 'exit', 'output', 'notification', 'webhook', 'condition', 'knowledgebase'],
  
  // Transforms → Indicators, Outputs
  transform: ['indicator', 'output', 'fusion'],
  filter: ['indicator', 'output', 'aggregate'],
  aggregate: ['indicator', 'output', 'fusion'],
  
  // Trading Signals → Orders, Risk, Outputs, Alerts
  entry: ['order', 'risk_check', 'position_size', 'stop_loss', 'take_profit', 'output', 'notification', 'webhook', 'validator', 'agent'],
  exit: ['order', 'output', 'notification', 'webhook'],
  signal: ['output', 'notification', 'webhook'],
  
  // Orders → Position, Monitoring, Outputs
  order: ['position', 'stop_loss', 'take_profit', 'monitoring', 'output'],
  position: ['risk_check', 'exit', 'agent', 'monitoring', 'output'],
  
  // Risk → Trading, Outputs
  risk_check: ['order', 'entry', 'position_size', 'output', 'notification'],
  position_size: ['order', 'output'],
  stop_loss: ['order', 'output'],
  take_profit: ['order', 'output'],
  strategy: ['order', 'agent', 'output'],
  
  // Conditions → Notifications, Webhooks
  condition: ['notification', 'webhook', 'entry', 'exit'],
  notification: ['output'],
  webhook: ['output'],
  
  // Outputs (terminal nodes)
  output: [],
  
  // Agents → Various based on type
  agent: ['indicator', 'fusion', 'risk_check', 'monitoring', 'output', 'order', 'notification'],
  chart: ['indicator', 'fusion', 'output'],
  
  // Knowledge → Fusion, Indicators
  knowledgebase: ['fusion', 'indicator', 'learning'],
  learning: ['knowledgebase', 'output', 'monitoring'],
  
  // Fusion → Trading, Risk, Outputs
  fusion: ['entry', 'exit', 'validator', 'risk_check', 'output', 'notification'],
  validator: ['entry', 'order', 'output'],
  
  // Monitoring (mostly terminal)
  monitoring: ['learning', 'output'],
  
  // Legacy/other
  loop: ['source', 'indicator', 'transform'],
}

// Get color for connection based on data type
export function getConnectionColor(outputType: string): string {
  const colorMap: Record<string, string> = {
    'market-data': '#10b981',      // Emerald
    'historical-data': '#10b981',
    'indicator-value': '#ec4899',  // Pink
    'pattern-signal': '#ec4899',
    'trade-signal': '#06b6d4',     // Cyan
    'fusion-signal': '#eab308',    // Yellow
    'validated-signal': '#eab308',
    'order-result': '#06b6d4',
    'position-data': '#06b6d4',
    'risk-status': '#ef4444',      // Red
    'stop-order': '#ef4444',
    'tp-order': '#22c55e',         // Green
    'condition-result': '#a855f7', // Purple
    'notification-sent': '#f97316',// Orange
  }
  return colorMap[outputType] || '#64748b' // Slate default
}

// Check if a connection is valid between two block types
export function isValidConnection(fromType: BlockType, toType: BlockType): boolean {
  const validTargets = CONNECTION_MATRIX[fromType]
  return validTargets?.includes(toType) || false
}

// Get all valid connection targets for a block type
export function getValidTargets(fromType: BlockType): BlockType[] {
  return CONNECTION_MATRIX[fromType] || []
}

// Get reason why connection is invalid
export function getConnectionError(fromType: BlockType, toType: BlockType): string | null {
  if (isValidConnection(fromType, toType)) return null
  
  const fromOutputs = BLOCK_OUTPUT_TYPES[fromType] || []
  const toInputs = BLOCK_INPUT_TYPES[toType] || []
  
  if (fromOutputs.length === 0) {
    return `${fromType} blocks don't produce outputs`
  }
  
  if (toInputs.length === 0) {
    return `${toType} blocks don't accept inputs`
  }
  
  return `${fromType} outputs (${fromOutputs.join(', ')}) are not compatible with ${toType} inputs (${toInputs.join(', ')})`
}

// Validate entire automation flow
export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

export interface BlockData {
  id: string
  type: BlockType
  name: string
  connections: string[]
  config: Record<string, any>
}

export function validateAutomationFlow(blocks: BlockData[]): ValidationResult {
  const errors: string[] = []
  const warnings: string[] = []
  
  // Create lookup map
  const blockMap = new Map(blocks.map(b => [b.id, b]))
  
  // Check for orphan blocks (no connections in or out, except sources)
  blocks.forEach(block => {
    const hasOutput = block.connections.length > 0
    const hasInput = blocks.some(b => b.connections.includes(block.id))
    
    if (!hasOutput && !hasInput) {
      if (block.type === 'source' || block.type === 'agent') {
        // Sources without outputs are warnings
        if (!hasOutput) {
          warnings.push(`${block.name} has no outgoing connections`)
        }
      } else {
        errors.push(`${block.name} is not connected to anything`)
      }
    }
  })
  
  // Check for invalid connections
  blocks.forEach(block => {
    block.connections.forEach(targetId => {
      const targetBlock = blockMap.get(targetId)
      if (targetBlock) {
        if (!isValidConnection(block.type, targetBlock.type)) {
          errors.push(
            `Invalid connection: ${block.name} (${block.type}) → ${targetBlock.name} (${targetBlock.type})`
          )
        }
      } else {
        errors.push(`${block.name} has connection to non-existent block`)
      }
    })
  })
  
  // Check for circular dependencies
  const visited = new Set<string>()
  const stack = new Set<string>()
  
  function hasCycle(blockId: string): boolean {
    if (stack.has(blockId)) return true
    if (visited.has(blockId)) return false
    
    visited.add(blockId)
    stack.add(blockId)
    
    const block = blockMap.get(blockId)
    if (block) {
      for (const targetId of block.connections) {
        if (hasCycle(targetId)) return true
      }
    }
    
    stack.delete(blockId)
    return false
  }
  
  for (const block of blocks) {
    if (hasCycle(block.id)) {
      errors.push('Circular dependency detected in automation flow')
      break
    }
  }
  
  // Check for required source blocks
  const hasSource = blocks.some(b => 
    b.type === 'source' || 
    (b.type === 'agent' && BLOCK_INPUT_TYPES['agent'].length === 0)
  )
  if (!hasSource) {
    warnings.push('Automation has no data source blocks')
  }
  
  // Check for output blocks
  const hasOutput = blocks.some(b => 
    b.type === 'output' || 
    b.type === 'notification' || 
    b.type === 'webhook' ||
    b.type === 'order'
  )
  if (!hasOutput) {
    warnings.push('Automation has no output or action blocks')
  }
  
  return {
    valid: errors.length === 0,
    errors,
    warnings
  }
}

// Get suggested next blocks based on current block type
export function getSuggestedNextBlocks(fromType: BlockType): { type: BlockType; reason: string }[] {
  const suggestions: { type: BlockType; reason: string }[] = []
  const validTargets = getValidTargets(fromType)
  
  // Prioritize common patterns
  const patterns: Record<BlockType, { type: BlockType; reason: string }[]> = {
    source: [
      { type: 'indicator', reason: 'Add technical analysis' },
      { type: 'transform', reason: 'Filter or aggregate data' },
      { type: 'output', reason: 'Save raw data' },
    ],
    indicator: [
      { type: 'entry', reason: 'Create entry signal' },
      { type: 'fusion', reason: 'Combine with other indicators' },
      { type: 'condition', reason: 'Set alert condition' },
    ],
    entry: [
      { type: 'risk_check', reason: 'Validate risk limits' },
      { type: 'position_size', reason: 'Calculate position size' },
      { type: 'order', reason: 'Execute trade' },
    ],
    order: [
      { type: 'position', reason: 'Track position' },
      { type: 'stop_loss', reason: 'Add stop loss' },
      { type: 'take_profit', reason: 'Add take profit' },
    ],
    fusion: [
      { type: 'validator', reason: 'Validate signal' },
      { type: 'entry', reason: 'Generate entry' },
    ],
    condition: [
      { type: 'notification', reason: 'Send alert' },
      { type: 'webhook', reason: 'Call webhook' },
    ],
    agent: [
      { type: 'indicator', reason: 'Analyze agent data' },
      { type: 'fusion', reason: 'Combine with other data' },
    ],
    // Add defaults for other types
    transform: [{ type: 'indicator', reason: 'Add analysis' }],
    filter: [{ type: 'indicator', reason: 'Analyze filtered data' }],
    aggregate: [{ type: 'indicator', reason: 'Analyze aggregated data' }],
    exit: [{ type: 'order', reason: 'Execute exit order' }],
    signal: [{ type: 'output', reason: 'Save signal' }],
    position: [{ type: 'monitoring', reason: 'Track position' }],
    risk_check: [{ type: 'order', reason: 'Execute if approved' }],
    position_size: [{ type: 'order', reason: 'Execute with size' }],
    stop_loss: [{ type: 'order', reason: 'Create stop order' }],
    take_profit: [{ type: 'order', reason: 'Create TP order' }],
    strategy: [{ type: 'order', reason: 'Execute strategy' }],
    notification: [],
    webhook: [],
    output: [],
    knowledgebase: [{ type: 'fusion', reason: 'Use in fusion' }],
    learning: [{ type: 'output', reason: 'Save results' }],
    validator: [{ type: 'entry', reason: 'Generate validated entry' }],
    monitoring: [{ type: 'learning', reason: 'Feed learning loop' }],
    chart: [{ type: 'fusion', reason: 'Use chart data' }],
    loop: [],
  }
  
  return patterns[fromType] || validTargets.slice(0, 3).map(t => ({ type: t, reason: 'Compatible connection' }))
}

