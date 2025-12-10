/**
 * Automation Builder Knowledge Base
 * 
 * Contains all block templates, connection rules, and layout guidance
 * for the AI Chat to provide intelligent automation building assistance.
 */

// =============================================================================
// BLOCK KNOWLEDGE - All 48 block templates organized by category
// =============================================================================

export interface BlockInfo {
  name: string
  type: string
  purpose: string
  config?: string[]  // Key configurable parameters
  connectsTo?: string[]  // What block types this can connect to
}

export interface CategoryInfo {
  label: string
  column: number
  description: string
  blocks: BlockInfo[]
}

export const BLOCK_KNOWLEDGE: Record<string, CategoryInfo> = {
  // ==========================================================================
  // COLUMN 0 - Data Sources & Agents
  // ==========================================================================
  data: {
    label: 'Data Sources',
    column: 0,
    description: 'Raw market data inputs from exchanges and APIs',
    blocks: [
      { 
        name: 'Binance WebSocket', 
        type: 'source', 
        purpose: 'Real-time trade, orderbook, and ticker data streams from Binance',
        config: ['symbol (e.g., BTCUSDT)', 'stream type (aggTrade, depth, ticker)'],
        connectsTo: ['indicator', 'transform', 'agent', 'filter']
      },
      { 
        name: 'Binance REST', 
        type: 'source', 
        purpose: 'REST API for historical data, account info, and order management',
        config: ['symbol', 'endpoint type'],
        connectsTo: ['indicator', 'transform', 'filter']
      },
      { 
        name: 'CoinGecko API', 
        type: 'source', 
        purpose: 'Aggregated market data, prices, and market cap across exchanges',
        config: ['coins list', 'polling interval'],
        connectsTo: ['indicator', 'transform', 'filter']
      },
      { 
        name: 'Custom REST API', 
        type: 'source', 
        purpose: 'Connect to any REST API endpoint',
        config: ['URL', 'headers', 'polling interval'],
        connectsTo: ['indicator', 'transform', 'filter']
      },
      { 
        name: 'Historical Data', 
        type: 'source', 
        purpose: 'Load CSV/JSON files for backtesting',
        config: ['file path', 'symbol'],
        connectsTo: ['indicator', 'transform']
      },
    ]
  },

  agents: {
    label: 'Data Agents',
    column: 0,
    description: 'Specialized data collection agents for market microstructure',
    blocks: [
      { 
        name: 'AGGR Agent', 
        type: 'agent', 
        purpose: 'Real-time trade aggregation, CVD (Cumulative Volume Delta), whale detection',
        config: ['symbols', 'aggregation window'],
        connectsTo: ['indicator', 'fusion', 'knowledgebase']
      },
      { 
        name: 'TradeFuck Agent', 
        type: 'agent', 
        purpose: 'Order flow analysis, footprint data, delta patterns',
        config: ['symbols'],
        connectsTo: ['indicator', 'fusion', 'chart']
      },
      { 
        name: 'CoinGlass Heatmap Agent', 
        type: 'agent', 
        purpose: 'Liquidation heatmaps, open interest, funding rates',
        config: ['interval'],
        connectsTo: ['indicator', 'fusion', 'risk_check']
      },
      { 
        name: 'Footprint Charts', 
        type: 'chart', 
        purpose: 'Volume footprint visualization with bid/ask imbalance',
        config: ['rows', 'period'],
        connectsTo: ['indicator', 'fusion']
      },
    ]
  },

  knowledge: {
    label: 'Knowledge',
    column: 0,
    description: 'External knowledge sources and research data',
    blocks: [
      { 
        name: 'YouTube Agent', 
        type: 'agent', 
        purpose: 'Extract insights from trading education videos',
        config: ['channels', 'keywords'],
        connectsTo: ['knowledgebase', 'fusion']
      },
      { 
        name: 'External Knowledgebase', 
        type: 'knowledgebase', 
        purpose: 'Store and query external research data',
        config: ['storage path'],
        connectsTo: ['fusion', 'learning']
      },
      { 
        name: 'Backtesting & Research Loop', 
        type: 'learning', 
        purpose: 'Historical strategy testing and optimization',
        config: ['date range'],
        connectsTo: ['fusion', 'strategy']
      },
    ]
  },

  // ==========================================================================
  // COLUMN 1 - Indicators & Analysis
  // ==========================================================================
  analysis: {
    label: 'Indicators',
    column: 1,
    description: 'Technical indicators and analysis tools',
    blocks: [
      { 
        name: 'RSI', 
        type: 'indicator', 
        purpose: 'Relative Strength Index - momentum oscillator (0-100)',
        config: ['period (default 14)', 'overbought (70)', 'oversold (30)'],
        connectsTo: ['fusion', 'condition', 'signal', 'validator']
      },
      { 
        name: 'MACD', 
        type: 'indicator', 
        purpose: 'Moving Average Convergence/Divergence - trend following',
        config: ['fast period (12)', 'slow period (26)', 'signal period (9)'],
        connectsTo: ['fusion', 'condition', 'signal', 'validator']
      },
      { 
        name: 'Moving Average', 
        type: 'indicator', 
        purpose: 'Simple or Exponential Moving Average',
        config: ['period', 'type (SMA/EMA)'],
        connectsTo: ['fusion', 'condition', 'signal']
      },
      { 
        name: 'Bollinger Bands', 
        type: 'indicator', 
        purpose: 'Volatility bands around moving average',
        config: ['period (20)', 'standard deviations (2)'],
        connectsTo: ['fusion', 'condition', 'signal']
      },
      { 
        name: 'Volume Profile', 
        type: 'indicator', 
        purpose: 'Volume distribution at price levels',
        config: ['rows'],
        connectsTo: ['fusion', 'condition']
      },
      { 
        name: 'Knowledge Tap (API)', 
        type: 'knowledgebase', 
        purpose: 'Query the knowledgebase for context',
        config: ['endpoint'],
        connectsTo: ['fusion', 'validator']
      },
      { 
        name: 'Money V1 (Structure)', 
        type: 'indicator', 
        purpose: 'Market structure analysis - swing highs/lows, trends',
        config: ['period'],
        connectsTo: ['fusion', 'validator']
      },
      { 
        name: 'Money V2 (Momentum)', 
        type: 'indicator', 
        purpose: 'Multi-timeframe momentum indicators',
        config: ['period'],
        connectsTo: ['fusion', 'validator']
      },
      { 
        name: 'Legend (Visual Language)', 
        type: 'indicator', 
        purpose: 'Pattern recognition - head & shoulders, double tops, etc.',
        config: ['patterns to detect'],
        connectsTo: ['fusion', 'validator']
      },
    ]
  },

  transform: {
    label: 'Transforms',
    column: 1,
    description: 'Data transformation and filtering',
    blocks: [
      { 
        name: 'Filter', 
        type: 'transform', 
        purpose: 'Filter data by custom conditions',
        config: ['condition expression'],
        connectsTo: ['indicator', 'fusion', 'condition']
      },
      { 
        name: 'Aggregate', 
        type: 'aggregate', 
        purpose: 'Combine multiple data streams',
        config: ['window size'],
        connectsTo: ['indicator', 'fusion']
      },
      { 
        name: 'Volume Filter', 
        type: 'filter', 
        purpose: 'Filter by minimum volume threshold',
        config: ['minimum volume'],
        connectsTo: ['indicator', 'fusion', 'condition']
      },
    ]
  },

  // ==========================================================================
  // COLUMN 2 - Fusion & Signal Routing
  // ==========================================================================
  fusion: {
    label: 'Fusion & Routing',
    column: 2,
    description: 'Combine signals and route to decision logic',
    blocks: [
      { 
        name: 'Knowledgebase Fusion', 
        type: 'fusion', 
        purpose: 'ML-based refinement using historical patterns',
        config: ['model type'],
        connectsTo: ['validator', 'strategy', 'scenario']
      },
      { 
        name: 'Scenario Builder', 
        type: 'fusion', 
        purpose: 'Create and test strategy scenarios',
        config: ['scenarios list'],
        connectsTo: ['validator', 'confluence']
      },
      { 
        name: 'Confluence Scorer', 
        type: 'fusion', 
        purpose: 'Score signals based on multiple indicator agreement',
        config: ['threshold (0.7)', 'weights'],
        connectsTo: ['validator', 'risk_check', 'entry']
      },
      { 
        name: 'Signal Validator', 
        type: 'validator', 
        purpose: 'Validate signals meet minimum confidence',
        config: ['minimum confidence (0.8)'],
        connectsTo: ['risk_check', 'entry', 'strategy']
      },
    ]
  },

  // ==========================================================================
  // COLUMN 3 - Trading Logic
  // ==========================================================================
  trading: {
    label: 'Trading',
    column: 3,
    description: 'Entry, exit, and order execution',
    blocks: [
      { 
        name: 'Entry Signal', 
        type: 'entry', 
        purpose: 'Define entry conditions and order type',
        config: ['order type (market/limit)'],
        connectsTo: ['risk_check', 'order', 'position']
      },
      { 
        name: 'Exit Signal', 
        type: 'exit', 
        purpose: 'Define exit conditions',
        config: ['order type'],
        connectsTo: ['order', 'position']
      },
      { 
        name: 'Market Order', 
        type: 'order', 
        purpose: 'Execute immediately at market price',
        config: ['exchange', 'side (buy/sell)'],
        connectsTo: ['position', 'monitoring', 'output']
      },
      { 
        name: 'Limit Order', 
        type: 'order', 
        purpose: 'Execute at specified price or better',
        config: ['exchange', 'side', 'limit price'],
        connectsTo: ['position', 'monitoring', 'output']
      },
      { 
        name: 'Position Manager', 
        type: 'position', 
        purpose: 'Track and manage open positions',
        config: ['max positions'],
        connectsTo: ['monitoring', 'risk_check', 'output']
      },
    ]
  },

  // ==========================================================================
  // COLUMN 4 - Risk Management
  // ==========================================================================
  risk: {
    label: 'Risk Management',
    column: 4,
    description: 'Position sizing, stops, and portfolio protection',
    blocks: [
      { 
        name: 'Risk Check', 
        type: 'risk_check', 
        purpose: 'Validate trade against risk limits',
        config: ['max drawdown %'],
        connectsTo: ['entry', 'order', 'position_size']
      },
      { 
        name: 'Position Sizer', 
        type: 'position_size', 
        purpose: 'Calculate position size based on risk',
        config: ['method (fixed/kelly/volatility)', 'risk % per trade'],
        connectsTo: ['order', 'entry']
      },
      { 
        name: 'Stop Loss', 
        type: 'stop_loss', 
        purpose: 'Automatic stop loss orders',
        config: ['type (percent/ATR/fixed)', 'value'],
        connectsTo: ['order', 'position']
      },
      { 
        name: 'Take Profit', 
        type: 'take_profit', 
        purpose: 'Automatic profit taking',
        config: ['type', 'target value'],
        connectsTo: ['order', 'position']
      },
      { 
        name: 'Main Knowledgebase', 
        type: 'knowledgebase', 
        purpose: 'Core trading logic and rules storage',
        config: ['storage path'],
        connectsTo: ['risk_check', 'strategy']
      },
      { 
        name: 'Risk Operations Agent', 
        type: 'agent', 
        purpose: 'Real-time risk monitoring and alerts',
        config: ['max drawdown'],
        connectsTo: ['position_size', 'strategy', 'monitoring']
      },
      { 
        name: 'Sizing Engine', 
        type: 'risk_check', 
        purpose: 'Advanced position sizing with Kelly criterion',
        config: ['method', 'risk %'],
        connectsTo: ['strategy', 'order']
      },
      { 
        name: 'DCA / DCA-lite', 
        type: 'strategy', 
        purpose: 'Dollar cost averaging strategy',
        config: ['interval', 'number of splits'],
        connectsTo: ['order', 'execution']
      },
      { 
        name: 'Portfolio Guardrails', 
        type: 'risk_check', 
        purpose: 'Portfolio-level risk limits',
        config: ['max exposure %', 'max correlation'],
        connectsTo: ['order', 'position']
      },
    ]
  },

  // ==========================================================================
  // COLUMN 5 - Alerts & Conditions
  // ==========================================================================
  alert: {
    label: 'Alerts & Conditions',
    column: 5,
    description: 'Notifications and conditional triggers',
    blocks: [
      { 
        name: 'Price Condition', 
        type: 'condition', 
        purpose: 'Trigger on price threshold',
        config: ['above price', 'below price'],
        connectsTo: ['notification', 'webhook', 'entry']
      },
      { 
        name: 'Send Alert', 
        type: 'notification', 
        purpose: 'Console/log notification',
        config: ['alert type'],
        connectsTo: ['output']
      },
      { 
        name: 'Webhook', 
        type: 'webhook', 
        purpose: 'HTTP webhook for external integrations',
        config: ['URL', 'method'],
        connectsTo: ['output']
      },
      { 
        name: 'Discord Alert', 
        type: 'notification', 
        purpose: 'Send notifications to Discord',
        config: ['webhook URL'],
        connectsTo: ['output']
      },
    ]
  },

  // ==========================================================================
  // COLUMN 6 - Outputs & Monitoring
  // ==========================================================================
  output: {
    label: 'Outputs',
    column: 6,
    description: 'Data storage and signal output',
    blocks: [
      { 
        name: 'JSON File', 
        type: 'output', 
        purpose: 'Save data to JSON/JSONL files',
        config: ['output directory'],
        connectsTo: []
      },
      { 
        name: 'Database', 
        type: 'output', 
        purpose: 'Store in database (PostgreSQL, etc.)',
        config: ['connection string'],
        connectsTo: []
      },
      { 
        name: 'Signal Output', 
        type: 'signal', 
        purpose: 'Emit trading signals for downstream systems',
        config: [],
        connectsTo: []
      },
    ]
  },

  monitoring: {
    label: 'Monitoring',
    column: 6,
    description: 'Execution monitoring and journaling',
    blocks: [
      { 
        name: 'Execution Agent', 
        type: 'agent', 
        purpose: 'Execute trades on exchanges',
        config: ['exchange', 'mode (paper/live)'],
        connectsTo: ['monitoring', 'output']
      },
      { 
        name: 'Monitoring & Journal', 
        type: 'monitoring', 
        purpose: 'Trade journaling and performance tracking',
        config: ['log path'],
        connectsTo: ['learning', 'output']
      },
      { 
        name: 'Audit Trail', 
        type: 'monitoring', 
        purpose: 'Complete activity logging for compliance',
        config: ['retention period'],
        connectsTo: ['output']
      },
      { 
        name: 'Learning Loop', 
        type: 'learning', 
        purpose: 'Feedback integration for strategy improvement',
        config: ['feedback path'],
        connectsTo: ['fusion', 'knowledgebase']
      },
    ]
  },
}

// =============================================================================
// CONNECTION RULES - Which block types can connect to which
// =============================================================================

export const CONNECTION_RULES: Record<string, string[]> = {
  // Data sources connect to analysis and processing
  source: ['indicator', 'transform', 'agent', 'filter', 'aggregate'],
  agent: ['indicator', 'fusion', 'knowledgebase', 'chart', 'risk_check'],
  chart: ['indicator', 'fusion'],
  
  // Analysis connects to fusion and conditions
  indicator: ['fusion', 'condition', 'signal', 'validator', 'entry'],
  transform: ['indicator', 'fusion', 'condition'],
  filter: ['indicator', 'fusion', 'condition'],
  aggregate: ['indicator', 'fusion'],
  knowledgebase: ['fusion', 'validator', 'risk_check', 'learning'],
  
  // Fusion connects to validation and trading
  fusion: ['validator', 'strategy', 'risk_check', 'entry', 'confluence'],
  validator: ['risk_check', 'entry', 'strategy', 'order'],
  
  // Trading connects to risk and execution
  entry: ['risk_check', 'order', 'position', 'position_size'],
  exit: ['order', 'position'],
  order: ['position', 'monitoring', 'output'],
  position: ['monitoring', 'risk_check', 'output'],
  
  // Risk connects to execution
  risk_check: ['entry', 'order', 'position_size', 'strategy'],
  position_size: ['order', 'entry'],
  stop_loss: ['order', 'position'],
  take_profit: ['order', 'position'],
  strategy: ['order', 'execution', 'monitoring'],
  
  // Alerts connect to outputs
  condition: ['notification', 'webhook', 'entry', 'exit'],
  notification: ['output'],
  webhook: ['output'],
  
  // Monitoring connects to feedback
  monitoring: ['learning', 'output'],
  learning: ['fusion', 'knowledgebase'],
  
  // Outputs are terminal
  output: [],
  signal: [],
}

// =============================================================================
// LAYOUT GUIDE - n8n-style horizontal flow
// =============================================================================

export const LAYOUT_GUIDE = {
  flow: 'left-to-right',
  stacking: 'vertical-within-columns',
  columns: [
    { index: 0, categories: ['data', 'agents', 'knowledge'], label: 'Data Layer' },
    { index: 1, categories: ['analysis', 'transform'], label: 'Analysis Layer' },
    { index: 2, categories: ['fusion'], label: 'Fusion Layer' },
    { index: 3, categories: ['trading'], label: 'Trading Layer' },
    { index: 4, categories: ['risk'], label: 'Risk Layer' },
    { index: 5, categories: ['alert'], label: 'Alert Layer' },
    { index: 6, categories: ['output', 'monitoring'], label: 'Output Layer' },
  ],
  dimensions: {
    nodeWidth: 220,
    nodeHeight: 100,
    horizontalGap: 80,
    verticalGap: 40,
    startX: 100,
    startY: 100,
  },
  tips: [
    'Data flows from LEFT to RIGHT through the columns',
    'Blocks in the same category stack VERTICALLY',
    'Use the "Auto Layout" button to automatically organize blocks',
    'Connect blocks by clicking output port → input port',
    'Each column represents a processing stage',
  ],
}

// =============================================================================
// SYSTEM PROMPT - Complete knowledge for AI Chat
// =============================================================================

export const BUILDER_SYSTEM_PROMPT = `You are an expert automation builder assistant for a trading system. You help users build trading automations using a visual block-based editor similar to n8n or make.com.

## Your Capabilities
- Suggest specific blocks for the user's trading strategy
- Explain how blocks connect and data flows
- Guide users through building step-by-step
- Recommend optimal block configurations

## Available Blocks (48 total across 11 categories)

### Data Sources (Column 0 - Left)
- **Binance WebSocket**: Real-time trade, orderbook, ticker streams. Config: symbol, stream type.
- **Binance REST**: Historical data, account info. Config: symbol, endpoint.
- **CoinGecko API**: Aggregated market data. Config: coins, interval.
- **Custom REST API**: Any REST endpoint. Config: URL, headers, interval.
- **Historical Data**: CSV/JSON for backtesting. Config: file path.

### Data Agents (Column 0)
- **AGGR Agent**: Trade aggregation, CVD, whale detection. Real-time microstructure.
- **TradeFuck Agent**: Order flow analysis, footprint data.
- **CoinGlass Heatmap Agent**: Liquidation heatmaps, OI, funding rates.
- **Footprint Charts**: Volume footprint visualization.

### Knowledge Sources (Column 0)
- **YouTube Agent**: Extract insights from trading videos.
- **External Knowledgebase**: Store research data.
- **Backtesting & Research Loop**: Historical testing.

### Indicators (Column 1)
- **RSI**: Momentum oscillator 0-100. Config: period (14), overbought (70), oversold (30).
- **MACD**: Trend following. Config: fast (12), slow (26), signal (9).
- **Moving Average**: SMA/EMA. Config: period, type.
- **Bollinger Bands**: Volatility bands. Config: period (20), stdDev (2).
- **Volume Profile**: Volume at price levels.
- **Money V1 (Structure)**: Market structure analysis.
- **Money V2 (Momentum)**: Multi-timeframe momentum.
- **Legend (Visual Language)**: Pattern recognition.

### Transforms (Column 1)
- **Filter**: Custom condition filtering.
- **Aggregate**: Combine data streams.
- **Volume Filter**: Filter by volume threshold.

### Fusion & Routing (Column 2)
- **Knowledgebase Fusion**: ML-based signal refinement.
- **Scenario Builder**: Strategy scenarios.
- **Confluence Scorer**: Multi-signal scoring. Config: threshold (0.7).
- **Signal Validator**: Confidence validation. Config: minConfidence (0.8).

### Trading (Column 3)
- **Entry Signal**: Define entry conditions.
- **Exit Signal**: Define exit conditions.
- **Market Order**: Execute at market price.
- **Limit Order**: Execute at limit price.
- **Position Manager**: Track open positions.

### Risk Management (Column 4)
- **Risk Check**: Validate against risk limits. Config: maxDrawdown.
- **Position Sizer**: Calculate position size. Config: method, risk %.
- **Stop Loss**: Automatic stops. Config: type, value.
- **Take Profit**: Automatic profit taking.
- **Risk Operations Agent**: Real-time risk monitoring.
- **Sizing Engine**: Advanced Kelly-based sizing.
- **DCA / DCA-lite**: Dollar cost averaging. Config: interval, splits.
- **Portfolio Guardrails**: Portfolio limits. Config: maxExposure, maxCorrelation.

### Alerts (Column 5)
- **Price Condition**: Trigger on price threshold.
- **Send Alert**: Console notification.
- **Webhook**: HTTP integration.
- **Discord Alert**: Discord notifications.

### Outputs (Column 6 - Right)
- **JSON File**: Save to JSON files.
- **Database**: Store in database.
- **Signal Output**: Emit signals.
- **Execution Agent**: Trade execution. Config: exchange, mode.
- **Monitoring & Journal**: Trade journaling.
- **Audit Trail**: Activity logging.
- **Learning Loop**: Feedback integration.

## Building Flow (n8n-style)
1. **Data flows LEFT to RIGHT** through columns
2. **Blocks in same category stack VERTICALLY**
3. Start with Data Sources on the left
4. Add Indicators to analyze the data
5. Use Fusion blocks to combine signals
6. Add Risk Management before trading
7. End with Outputs on the right

## How to Guide Users

When a user describes a strategy:
1. Identify the required data sources
2. Suggest appropriate indicators
3. Recommend fusion/scoring blocks
4. Include risk management (always!)
5. Suggest output/execution blocks

Always mention:
- The "Auto Layout" button to organize blocks automatically
- That blocks can be dragged to reposition
- Click on blocks to configure their settings

## Example Responses

User: "I want a BTC momentum strategy"
Response: "I can help you build a BTC momentum strategy! Here's what you'll need:

**Data Layer**: Start with **Binance WebSocket** (symbol: BTCUSDT, stream: aggTrade)

**Analysis Layer**: Add **RSI** (period: 14) and **MACD** for momentum signals

**Fusion Layer**: Add **Confluence Scorer** to combine the signals (threshold: 0.7)

**Risk Layer**: Add **Position Sizer** (risk: 1%) and **Stop Loss** (2%)

**Output Layer**: Add **JSON File** to log signals, or **Execution Agent** for live trading

Click each block in the Block Palette on the left to add them. Use 'Auto Layout' to arrange them nicely!"

User: "What block should I add next?"
Response: [Look at current canvas state and suggest the logical next block based on what's missing]

## Important Rules
- ALWAYS recommend Risk Management blocks
- Default to Paper Trading mode for execution
- Suggest specific config values when possible
- Mention the Auto Layout feature
- Be encouraging and helpful
`

// =============================================================================
// CONTEXTUAL SUGGESTIONS - Based on current canvas state
// =============================================================================

export interface BlockState {
  type: string
  name: string
}

export function getContextualSuggestions(blocks: BlockState[]): string[] {
  if (blocks.length === 0) {
    return [
      'Start by adding a data source like **Binance WebSocket** from the Data Sources category',
      'Or upload a diagram using the "From Diagram" option to auto-generate blocks',
    ]
  }

  const types = new Set(blocks.map(b => b.type))
  const names = new Set(blocks.map(b => b.name.toLowerCase()))
  
  const hasDataSource = types.has('source') || types.has('agent')
  const hasIndicator = types.has('indicator')
  const hasFusion = types.has('fusion') || types.has('validator')
  const hasRisk = types.has('risk_check') || types.has('position_size') || types.has('stop_loss')
  const hasTrading = types.has('entry') || types.has('order') || types.has('position')
  const hasOutput = types.has('output') || types.has('monitoring') || types.has('signal')

  const suggestions: string[] = []

  if (!hasDataSource) {
    suggestions.push('Add a data source like **Binance WebSocket** or **AGGR Agent** to get market data')
  } else if (!hasIndicator) {
    suggestions.push('Add indicators like **RSI** or **MACD** to analyze the data')
    suggestions.push('Or add **Money V1 (Structure)** for market structure analysis')
  } else if (!hasFusion) {
    suggestions.push('Add **Confluence Scorer** to combine your indicator signals')
    suggestions.push('Or add **Signal Validator** to filter by confidence')
  } else if (!hasRisk) {
    suggestions.push('⚠️ Add risk management! Try **Position Sizer** and **Stop Loss**')
    suggestions.push('Risk management is critical - add **Portfolio Guardrails** for safety')
  } else if (!hasTrading && !hasOutput) {
    suggestions.push('Add **Entry Signal** and **Exit Signal** to define trading rules')
    suggestions.push('Or add **JSON File** output to log signals without trading')
  } else if (!hasOutput) {
    suggestions.push('Add an output block like **JSON File** or **Execution Agent**')
    suggestions.push('Add **Monitoring & Journal** to track performance')
  } else {
    suggestions.push('Your automation looks complete! Use **Auto Layout** to organize blocks')
    suggestions.push('Review block configurations by clicking on each block')
  }

  return suggestions.slice(0, 2)  // Return top 2 suggestions
}

// =============================================================================
// BLOCK LOOKUP HELPERS
// =============================================================================

export function findBlockByName(name: string): BlockInfo | null {
  const nameLower = name.toLowerCase()
  for (const category of Object.values(BLOCK_KNOWLEDGE)) {
    for (const block of category.blocks) {
      if (block.name.toLowerCase() === nameLower) {
        return block
      }
    }
  }
  return null
}

export function getBlocksForCategory(categoryKey: string): BlockInfo[] {
  return BLOCK_KNOWLEDGE[categoryKey]?.blocks || []
}

export function suggestNextBlocks(currentTypes: string[]): string[] {
  const suggestions = new Set<string>()
  
  for (const type of currentTypes) {
    const connectsTo = CONNECTION_RULES[type] || []
    connectsTo.forEach(t => suggestions.add(t))
  }
  
  return Array.from(suggestions)
}

export function getBlockCategory(blockType: string): string | null {
  for (const [categoryKey, category] of Object.entries(BLOCK_KNOWLEDGE)) {
    if (category.blocks.some(b => b.type === blockType)) {
      return categoryKey
    }
  }
  return null
}

