/**
 * Block Configuration Schemas
 * Typed schemas for all 48 block types with validation rules
 */

export type FieldType = 
  | 'text' 
  | 'number' 
  | 'select' 
  | 'multi-select' 
  | 'symbol' 
  | 'interval' 
  | 'slider' 
  | 'toggle' 
  | 'json' 
  | 'condition'
  | 'url'
  | 'file'

export interface FieldSchema {
  name: string
  label: string
  type: FieldType
  description?: string
  required?: boolean
  default?: any
  // For number fields
  min?: number
  max?: number
  step?: number
  // For select fields
  options?: { value: string; label: string }[]
  // For multi-select
  allowCustom?: boolean
  // For symbol fields
  exchange?: string
  // For slider
  showValue?: boolean
  // Validation
  validate?: (value: any) => string | null
}

export interface BlockConfigSchema {
  blockType: string
  blockName: string
  category: string
  description: string
  fields: FieldSchema[]
  // Connection rules
  acceptsInput: boolean
  outputType: string // What data type this block outputs
  acceptedInputTypes: string[] // What input types this block can receive
}

// Common field definitions for reuse
const COMMON_FIELDS = {
  symbol: (defaultValue = 'BTCUSDT'): FieldSchema => ({
    name: 'symbol',
    label: 'Trading Pair',
    type: 'symbol',
    description: 'Select trading pair',
    required: true,
    default: defaultValue,
    exchange: 'binance',
  }),
  interval: (defaultValue = '1m'): FieldSchema => ({
    name: 'interval',
    label: 'Time Interval',
    type: 'interval',
    description: 'Data collection interval',
    required: true,
    default: defaultValue,
    options: [
      { value: '1s', label: '1 Second' },
      { value: '5s', label: '5 Seconds' },
      { value: '15s', label: '15 Seconds' },
      { value: '30s', label: '30 Seconds' },
      { value: '1m', label: '1 Minute' },
      { value: '5m', label: '5 Minutes' },
      { value: '15m', label: '15 Minutes' },
      { value: '30m', label: '30 Minutes' },
      { value: '1h', label: '1 Hour' },
      { value: '4h', label: '4 Hours' },
      { value: '1d', label: '1 Day' },
    ],
  }),
  period: (defaultValue = 14, min = 1, max = 200): FieldSchema => ({
    name: 'period',
    label: 'Period',
    type: 'slider',
    description: 'Calculation period',
    required: true,
    default: defaultValue,
    min,
    max,
    step: 1,
    showValue: true,
  }),
}

// ============ DATA SOURCES ============
export const DATA_SOURCE_SCHEMAS: BlockConfigSchema[] = [
  {
    blockType: 'source',
    blockName: 'Binance WebSocket',
    category: 'data',
    description: 'Real-time market data from Binance',
    acceptsInput: false,
    outputType: 'market-data',
    acceptedInputTypes: [],
    fields: [
      COMMON_FIELDS.symbol('BTCUSDT'),
      {
        name: 'stream',
        label: 'Stream Type',
        type: 'select',
        description: 'Type of data stream',
        required: true,
        default: 'aggTrade',
        options: [
          { value: 'aggTrade', label: 'Aggregated Trades' },
          { value: 'trade', label: 'Individual Trades' },
          { value: 'kline_1m', label: 'Kline/Candlestick 1m' },
          { value: 'kline_5m', label: 'Kline/Candlestick 5m' },
          { value: 'kline_15m', label: 'Kline/Candlestick 15m' },
          { value: 'kline_1h', label: 'Kline/Candlestick 1h' },
          { value: 'depth', label: 'Partial Order Book' },
          { value: 'depth@100ms', label: 'Order Book Updates' },
          { value: 'ticker', label: '24hr Ticker' },
          { value: 'bookTicker', label: 'Best Bid/Ask' },
        ],
      },
    ],
  },
  {
    blockType: 'source',
    blockName: 'Binance REST',
    category: 'data',
    description: 'REST API endpoints from Binance',
    acceptsInput: false,
    outputType: 'market-data',
    acceptedInputTypes: [],
    fields: [
      COMMON_FIELDS.symbol('BTC/USDT'),
      {
        name: 'endpoint',
        label: 'API Endpoint',
        type: 'select',
        description: 'REST API endpoint',
        required: true,
        default: 'ticker',
        options: [
          { value: 'ticker', label: 'Price Ticker' },
          { value: 'orderbook', label: 'Order Book' },
          { value: 'trades', label: 'Recent Trades' },
          { value: 'klines', label: 'Historical Klines' },
          { value: 'ticker24h', label: '24h Statistics' },
        ],
      },
      COMMON_FIELDS.interval('60'),
    ],
  },
  {
    blockType: 'source',
    blockName: 'CoinGecko API',
    category: 'data',
    description: 'Market data aggregator',
    acceptsInput: false,
    outputType: 'market-data',
    acceptedInputTypes: [],
    fields: [
      {
        name: 'coins',
        label: 'Coins',
        type: 'multi-select',
        description: 'Select coins to track',
        required: true,
        default: ['bitcoin'],
        allowCustom: true,
        options: [
          { value: 'bitcoin', label: 'Bitcoin (BTC)' },
          { value: 'ethereum', label: 'Ethereum (ETH)' },
          { value: 'solana', label: 'Solana (SOL)' },
          { value: 'binancecoin', label: 'BNB' },
          { value: 'ripple', label: 'XRP' },
          { value: 'cardano', label: 'Cardano (ADA)' },
          { value: 'dogecoin', label: 'Dogecoin (DOGE)' },
        ],
      },
      {
        name: 'interval',
        label: 'Poll Interval (seconds)',
        type: 'number',
        description: 'How often to fetch data',
        required: true,
        default: 60,
        min: 10,
        max: 3600,
      },
    ],
  },
  {
    blockType: 'source',
    blockName: 'Custom REST API',
    category: 'data',
    description: 'Your own API endpoint',
    acceptsInput: false,
    outputType: 'custom-data',
    acceptedInputTypes: [],
    fields: [
      {
        name: 'url',
        label: 'API URL',
        type: 'url',
        description: 'Full URL of the API endpoint',
        required: true,
        default: '',
      },
      {
        name: 'method',
        label: 'HTTP Method',
        type: 'select',
        description: 'Request method',
        default: 'GET',
        options: [
          { value: 'GET', label: 'GET' },
          { value: 'POST', label: 'POST' },
        ],
      },
      {
        name: 'headers',
        label: 'Headers (JSON)',
        type: 'json',
        description: 'Custom headers',
        default: '{}',
      },
      {
        name: 'interval',
        label: 'Poll Interval (seconds)',
        type: 'number',
        default: 60,
        min: 1,
        max: 86400,
      },
    ],
  },
  {
    blockType: 'source',
    blockName: 'Historical Data',
    category: 'data',
    description: 'CSV/JSON file input',
    acceptsInput: false,
    outputType: 'historical-data',
    acceptedInputTypes: [],
    fields: [
      {
        name: 'file',
        label: 'Data File',
        type: 'file',
        description: 'Upload CSV or JSON file',
        required: true,
      },
      COMMON_FIELDS.symbol('BTC/USDT'),
      {
        name: 'dateColumn',
        label: 'Date Column',
        type: 'text',
        description: 'Name of timestamp column',
        default: 'timestamp',
      },
    ],
  },
]

// ============ INDICATORS ============
export const INDICATOR_SCHEMAS: BlockConfigSchema[] = [
  {
    blockType: 'indicator',
    blockName: 'RSI',
    category: 'analysis',
    description: 'Relative Strength Index',
    acceptsInput: true,
    outputType: 'indicator-value',
    acceptedInputTypes: ['market-data', 'historical-data'],
    fields: [
      COMMON_FIELDS.period(14, 2, 100),
      {
        name: 'overbought',
        label: 'Overbought Level',
        type: 'slider',
        description: 'RSI level considered overbought',
        required: true,
        default: 70,
        min: 50,
        max: 100,
        step: 1,
        showValue: true,
      },
      {
        name: 'oversold',
        label: 'Oversold Level',
        type: 'slider',
        description: 'RSI level considered oversold',
        required: true,
        default: 30,
        min: 0,
        max: 50,
        step: 1,
        showValue: true,
      },
    ],
  },
  {
    blockType: 'indicator',
    blockName: 'MACD',
    category: 'analysis',
    description: 'Moving Average Convergence Divergence',
    acceptsInput: true,
    outputType: 'indicator-value',
    acceptedInputTypes: ['market-data', 'historical-data'],
    fields: [
      {
        name: 'fast',
        label: 'Fast Period',
        type: 'number',
        description: 'Fast EMA period',
        required: true,
        default: 12,
        min: 1,
        max: 100,
      },
      {
        name: 'slow',
        label: 'Slow Period',
        type: 'number',
        description: 'Slow EMA period',
        required: true,
        default: 26,
        min: 1,
        max: 200,
      },
      {
        name: 'signal',
        label: 'Signal Period',
        type: 'number',
        description: 'Signal line period',
        required: true,
        default: 9,
        min: 1,
        max: 50,
      },
    ],
  },
  {
    blockType: 'indicator',
    blockName: 'Moving Average',
    category: 'analysis',
    description: 'SMA/EMA calculation',
    acceptsInput: true,
    outputType: 'indicator-value',
    acceptedInputTypes: ['market-data', 'historical-data'],
    fields: [
      COMMON_FIELDS.period(20, 1, 500),
      {
        name: 'type',
        label: 'MA Type',
        type: 'select',
        description: 'Type of moving average',
        required: true,
        default: 'SMA',
        options: [
          { value: 'SMA', label: 'Simple (SMA)' },
          { value: 'EMA', label: 'Exponential (EMA)' },
          { value: 'WMA', label: 'Weighted (WMA)' },
          { value: 'DEMA', label: 'Double Exp (DEMA)' },
          { value: 'TEMA', label: 'Triple Exp (TEMA)' },
        ],
      },
      {
        name: 'source',
        label: 'Price Source',
        type: 'select',
        default: 'close',
        options: [
          { value: 'close', label: 'Close' },
          { value: 'open', label: 'Open' },
          { value: 'high', label: 'High' },
          { value: 'low', label: 'Low' },
          { value: 'hl2', label: 'HL/2' },
          { value: 'hlc3', label: 'HLC/3' },
          { value: 'ohlc4', label: 'OHLC/4' },
        ],
      },
    ],
  },
  {
    blockType: 'indicator',
    blockName: 'Bollinger Bands',
    category: 'analysis',
    description: 'Volatility bands',
    acceptsInput: true,
    outputType: 'indicator-value',
    acceptedInputTypes: ['market-data', 'historical-data'],
    fields: [
      COMMON_FIELDS.period(20, 5, 100),
      {
        name: 'stdDev',
        label: 'Standard Deviations',
        type: 'slider',
        description: 'Number of standard deviations',
        required: true,
        default: 2,
        min: 0.5,
        max: 4,
        step: 0.1,
        showValue: true,
      },
    ],
  },
  {
    blockType: 'indicator',
    blockName: 'Volume Profile',
    category: 'analysis',
    description: 'Volume distribution analysis',
    acceptsInput: true,
    outputType: 'indicator-value',
    acceptedInputTypes: ['market-data', 'historical-data'],
    fields: [
      {
        name: 'rows',
        label: 'Number of Rows',
        type: 'number',
        description: 'Price level divisions',
        required: true,
        default: 24,
        min: 10,
        max: 100,
      },
      {
        name: 'valueArea',
        label: 'Value Area %',
        type: 'slider',
        default: 70,
        min: 50,
        max: 90,
        step: 1,
        showValue: true,
      },
    ],
  },
  {
    blockType: 'indicator',
    blockName: 'Money V1 (Structure)',
    category: 'analysis',
    description: 'Market structure analysis',
    acceptsInput: true,
    outputType: 'indicator-value',
    acceptedInputTypes: ['market-data', 'historical-data'],
    fields: [
      COMMON_FIELDS.period(20, 5, 100),
      {
        name: 'sensitivity',
        label: 'Sensitivity',
        type: 'slider',
        default: 50,
        min: 10,
        max: 100,
        step: 5,
        showValue: true,
      },
    ],
  },
  {
    blockType: 'indicator',
    blockName: 'Money V2 (Momentum)',
    category: 'analysis',
    description: 'Momentum indicators',
    acceptsInput: true,
    outputType: 'indicator-value',
    acceptedInputTypes: ['market-data', 'historical-data'],
    fields: [
      COMMON_FIELDS.period(14, 5, 50),
      {
        name: 'smoothing',
        label: 'Smoothing',
        type: 'number',
        default: 3,
        min: 1,
        max: 10,
      },
    ],
  },
  {
    blockType: 'indicator',
    blockName: 'Legend (Visual Language)',
    category: 'analysis',
    description: 'Pattern recognition',
    acceptsInput: true,
    outputType: 'pattern-signal',
    acceptedInputTypes: ['market-data', 'historical-data'],
    fields: [
      {
        name: 'patterns',
        label: 'Patterns to Detect',
        type: 'multi-select',
        default: ['head_shoulders', 'double_top'],
        options: [
          { value: 'head_shoulders', label: 'Head & Shoulders' },
          { value: 'double_top', label: 'Double Top' },
          { value: 'double_bottom', label: 'Double Bottom' },
          { value: 'triangle', label: 'Triangle' },
          { value: 'wedge', label: 'Wedge' },
          { value: 'flag', label: 'Flag/Pennant' },
          { value: 'channel', label: 'Channel' },
        ],
      },
      {
        name: 'minConfidence',
        label: 'Min Confidence %',
        type: 'slider',
        default: 70,
        min: 50,
        max: 100,
        step: 5,
        showValue: true,
      },
    ],
  },
]

// ============ TRANSFORMS ============
export const TRANSFORM_SCHEMAS: BlockConfigSchema[] = [
  {
    blockType: 'transform',
    blockName: 'Filter',
    category: 'transform',
    description: 'Filter data by condition',
    acceptsInput: true,
    outputType: 'filtered-data',
    acceptedInputTypes: ['market-data', 'indicator-value', 'custom-data'],
    fields: [
      {
        name: 'condition',
        label: 'Filter Condition',
        type: 'condition',
        description: 'JavaScript expression',
        required: true,
        default: 'value > 0',
      },
    ],
  },
  {
    blockType: 'aggregate',
    blockName: 'Aggregate',
    category: 'transform',
    description: 'Combine multiple inputs',
    acceptsInput: true,
    outputType: 'aggregated-data',
    acceptedInputTypes: ['market-data', 'indicator-value', 'filtered-data'],
    fields: [
      {
        name: 'window',
        label: 'Time Window',
        type: 'interval',
        default: '1m',
      },
      {
        name: 'method',
        label: 'Aggregation Method',
        type: 'select',
        default: 'last',
        options: [
          { value: 'last', label: 'Last Value' },
          { value: 'first', label: 'First Value' },
          { value: 'mean', label: 'Average' },
          { value: 'sum', label: 'Sum' },
          { value: 'min', label: 'Minimum' },
          { value: 'max', label: 'Maximum' },
        ],
      },
    ],
  },
  {
    blockType: 'filter',
    blockName: 'Volume Filter',
    category: 'transform',
    description: 'Filter by volume threshold',
    acceptsInput: true,
    outputType: 'filtered-data',
    acceptedInputTypes: ['market-data'],
    fields: [
      {
        name: 'minVolume',
        label: 'Minimum Volume',
        type: 'number',
        description: 'Filter out trades below this volume',
        required: true,
        default: 1000,
        min: 0,
      },
      {
        name: 'volumeField',
        label: 'Volume Field',
        type: 'text',
        default: 'volume',
      },
    ],
  },
]

// ============ TRADING ============
export const TRADING_SCHEMAS: BlockConfigSchema[] = [
  {
    blockType: 'entry',
    blockName: 'Entry Signal',
    category: 'trading',
    description: 'Define entry conditions',
    acceptsInput: true,
    outputType: 'trade-signal',
    acceptedInputTypes: ['indicator-value', 'pattern-signal', 'fusion-signal'],
    fields: [
      {
        name: 'type',
        label: 'Order Type',
        type: 'select',
        default: 'market',
        options: [
          { value: 'market', label: 'Market Order' },
          { value: 'limit', label: 'Limit Order' },
          { value: 'stop', label: 'Stop Order' },
        ],
      },
      {
        name: 'side',
        label: 'Side',
        type: 'select',
        default: 'buy',
        options: [
          { value: 'buy', label: 'Buy/Long' },
          { value: 'sell', label: 'Sell/Short' },
          { value: 'both', label: 'Both (Signal-based)' },
        ],
      },
      {
        name: 'conditions',
        label: 'Entry Conditions',
        type: 'condition',
        description: 'When to enter',
        default: 'rsi < 30 && macd_histogram > 0',
      },
    ],
  },
  {
    blockType: 'exit',
    blockName: 'Exit Signal',
    category: 'trading',
    description: 'Define exit conditions',
    acceptsInput: true,
    outputType: 'trade-signal',
    acceptedInputTypes: ['indicator-value', 'pattern-signal', 'position-data'],
    fields: [
      {
        name: 'type',
        label: 'Order Type',
        type: 'select',
        default: 'market',
        options: [
          { value: 'market', label: 'Market Order' },
          { value: 'limit', label: 'Limit Order' },
        ],
      },
      {
        name: 'conditions',
        label: 'Exit Conditions',
        type: 'condition',
        description: 'When to exit',
        default: 'rsi > 70 || profit > 5',
      },
    ],
  },
  {
    blockType: 'order',
    blockName: 'Market Order',
    category: 'trading',
    description: 'Execute at market price',
    acceptsInput: true,
    outputType: 'order-result',
    acceptedInputTypes: ['trade-signal'],
    fields: [
      {
        name: 'exchange',
        label: 'Exchange',
        type: 'select',
        default: 'binance',
        options: [
          { value: 'binance', label: 'Binance' },
          { value: 'bybit', label: 'Bybit' },
          { value: 'okx', label: 'OKX' },
          { value: 'paper', label: 'Paper Trading' },
        ],
      },
      {
        name: 'side',
        label: 'Side',
        type: 'select',
        default: 'buy',
        options: [
          { value: 'buy', label: 'Buy' },
          { value: 'sell', label: 'Sell' },
          { value: 'signal', label: 'From Signal' },
        ],
      },
      {
        name: 'amount',
        label: 'Amount',
        type: 'text',
        description: 'Fixed amount or % of balance',
        default: '100%',
      },
    ],
  },
  {
    blockType: 'order',
    blockName: 'Limit Order',
    category: 'trading',
    description: 'Execute at limit price',
    acceptsInput: true,
    outputType: 'order-result',
    acceptedInputTypes: ['trade-signal'],
    fields: [
      {
        name: 'exchange',
        label: 'Exchange',
        type: 'select',
        default: 'binance',
        options: [
          { value: 'binance', label: 'Binance' },
          { value: 'bybit', label: 'Bybit' },
          { value: 'okx', label: 'OKX' },
          { value: 'paper', label: 'Paper Trading' },
        ],
      },
      {
        name: 'side',
        label: 'Side',
        type: 'select',
        default: 'buy',
        options: [
          { value: 'buy', label: 'Buy' },
          { value: 'sell', label: 'Sell' },
        ],
      },
      {
        name: 'price',
        label: 'Limit Price',
        type: 'text',
        description: 'Price or expression (e.g., bid - 10)',
        default: '0',
      },
      {
        name: 'amount',
        label: 'Amount',
        type: 'text',
        default: '100%',
      },
    ],
  },
  {
    blockType: 'position',
    blockName: 'Position Manager',
    category: 'trading',
    description: 'Track open positions',
    acceptsInput: true,
    outputType: 'position-data',
    acceptedInputTypes: ['order-result', 'market-data'],
    fields: [
      {
        name: 'maxPosition',
        label: 'Max Positions',
        type: 'number',
        default: 1,
        min: 1,
        max: 10,
      },
      {
        name: 'trackPnL',
        label: 'Track P&L',
        type: 'toggle',
        default: true,
      },
    ],
  },
]

// ============ RISK MANAGEMENT ============
export const RISK_SCHEMAS: BlockConfigSchema[] = [
  {
    blockType: 'risk_check',
    blockName: 'Risk Check',
    category: 'risk',
    description: 'Validate risk limits',
    acceptsInput: true,
    outputType: 'risk-status',
    acceptedInputTypes: ['trade-signal', 'position-data'],
    fields: [
      {
        name: 'maxDrawdown',
        label: 'Max Drawdown %',
        type: 'slider',
        default: 10,
        min: 1,
        max: 50,
        step: 1,
        showValue: true,
      },
      {
        name: 'maxDailyLoss',
        label: 'Max Daily Loss %',
        type: 'slider',
        default: 5,
        min: 1,
        max: 25,
        step: 0.5,
        showValue: true,
      },
      {
        name: 'cooldownMinutes',
        label: 'Loss Cooldown (min)',
        type: 'number',
        default: 30,
        min: 0,
        max: 1440,
      },
    ],
  },
  {
    blockType: 'position_size',
    blockName: 'Position Sizer',
    category: 'risk',
    description: 'Calculate position size',
    acceptsInput: true,
    outputType: 'position-size',
    acceptedInputTypes: ['trade-signal', 'risk-status'],
    fields: [
      {
        name: 'method',
        label: 'Sizing Method',
        type: 'select',
        default: 'fixed',
        options: [
          { value: 'fixed', label: 'Fixed Amount' },
          { value: 'percent', label: 'Percent of Balance' },
          { value: 'risk', label: 'Risk-based' },
          { value: 'kelly', label: 'Kelly Criterion' },
        ],
      },
      {
        name: 'risk',
        label: 'Risk per Trade %',
        type: 'slider',
        default: 1,
        min: 0.1,
        max: 10,
        step: 0.1,
        showValue: true,
      },
      {
        name: 'maxSize',
        label: 'Max Position Size',
        type: 'text',
        default: '10000',
      },
    ],
  },
  {
    blockType: 'stop_loss',
    blockName: 'Stop Loss',
    category: 'risk',
    description: 'Automatic stop loss',
    acceptsInput: true,
    outputType: 'stop-order',
    acceptedInputTypes: ['trade-signal', 'position-data'],
    fields: [
      {
        name: 'type',
        label: 'Stop Type',
        type: 'select',
        default: 'percent',
        options: [
          { value: 'percent', label: 'Percentage' },
          { value: 'fixed', label: 'Fixed Amount' },
          { value: 'atr', label: 'ATR-based' },
          { value: 'trailing', label: 'Trailing Stop' },
        ],
      },
      {
        name: 'value',
        label: 'Stop Value',
        type: 'number',
        default: 2,
        min: 0.1,
        max: 50,
        step: 0.1,
      },
      {
        name: 'trailingActivation',
        label: 'Trailing Activation %',
        type: 'number',
        description: 'Start trailing after this profit %',
        default: 1,
        min: 0,
        max: 20,
      },
    ],
  },
  {
    blockType: 'take_profit',
    blockName: 'Take Profit',
    category: 'risk',
    description: 'Automatic take profit',
    acceptsInput: true,
    outputType: 'tp-order',
    acceptedInputTypes: ['trade-signal', 'position-data'],
    fields: [
      {
        name: 'type',
        label: 'TP Type',
        type: 'select',
        default: 'percent',
        options: [
          { value: 'percent', label: 'Percentage' },
          { value: 'fixed', label: 'Fixed Amount' },
          { value: 'rr', label: 'Risk:Reward Ratio' },
          { value: 'scaled', label: 'Scaled Exit' },
        ],
      },
      {
        name: 'value',
        label: 'TP Value',
        type: 'number',
        default: 4,
        min: 0.1,
        max: 100,
        step: 0.1,
      },
      {
        name: 'partialClose',
        label: 'Partial Close %',
        type: 'slider',
        description: 'Close this % at TP1',
        default: 50,
        min: 0,
        max: 100,
        step: 10,
        showValue: true,
      },
    ],
  },
  {
    blockType: 'risk_check',
    blockName: 'Portfolio Guardrails',
    category: 'risk',
    description: 'Portfolio-level limits',
    acceptsInput: true,
    outputType: 'risk-status',
    acceptedInputTypes: ['position-data'],
    fields: [
      {
        name: 'maxExposure',
        label: 'Max Portfolio Exposure %',
        type: 'slider',
        default: 50,
        min: 10,
        max: 100,
        step: 5,
        showValue: true,
      },
      {
        name: 'maxCorrelation',
        label: 'Max Correlation',
        type: 'slider',
        default: 0.7,
        min: 0,
        max: 1,
        step: 0.05,
        showValue: true,
      },
      {
        name: 'maxAssets',
        label: 'Max Concurrent Assets',
        type: 'number',
        default: 5,
        min: 1,
        max: 20,
      },
    ],
  },
  {
    blockType: 'risk_check',
    blockName: 'Sizing Engine',
    category: 'risk',
    description: 'Advanced position sizing',
    acceptsInput: true,
    outputType: 'position-size',
    acceptedInputTypes: ['trade-signal', 'risk-status'],
    fields: [
      {
        name: 'method',
        label: 'Method',
        type: 'select',
        default: 'kelly',
        options: [
          { value: 'kelly', label: 'Kelly Criterion' },
          { value: 'halfKelly', label: 'Half Kelly' },
          { value: 'optimalF', label: 'Optimal F' },
          { value: 'fixedFractional', label: 'Fixed Fractional' },
        ],
      },
      {
        name: 'risk',
        label: 'Base Risk %',
        type: 'slider',
        default: 1,
        min: 0.1,
        max: 5,
        step: 0.1,
        showValue: true,
      },
    ],
  },
  {
    blockType: 'strategy',
    blockName: 'DCA / DCA-lite',
    category: 'risk',
    description: 'Dollar cost averaging strategy',
    acceptsInput: true,
    outputType: 'dca-signal',
    acceptedInputTypes: ['trade-signal', 'market-data'],
    fields: [
      {
        name: 'interval',
        label: 'DCA Interval',
        type: 'interval',
        default: '4h',
      },
      {
        name: 'splits',
        label: 'Number of Splits',
        type: 'number',
        default: 4,
        min: 2,
        max: 20,
      },
      {
        name: 'priceDropTrigger',
        label: 'Price Drop Trigger %',
        type: 'slider',
        description: 'Buy more when price drops by this %',
        default: 5,
        min: 1,
        max: 20,
        step: 0.5,
        showValue: true,
      },
    ],
  },
]

// ============ ALERTS & CONDITIONS ============
export const ALERT_SCHEMAS: BlockConfigSchema[] = [
  {
    blockType: 'condition',
    blockName: 'Price Condition',
    category: 'alert',
    description: 'Price threshold check',
    acceptsInput: true,
    outputType: 'condition-result',
    acceptedInputTypes: ['market-data'],
    fields: [
      {
        name: 'above',
        label: 'Price Above',
        type: 'number',
        description: 'Trigger when price goes above',
        default: 0,
        min: 0,
      },
      {
        name: 'below',
        label: 'Price Below',
        type: 'number',
        description: 'Trigger when price goes below',
        default: 0,
        min: 0,
      },
      {
        name: 'crossOnly',
        label: 'Trigger on Cross Only',
        type: 'toggle',
        default: true,
      },
    ],
  },
  {
    blockType: 'notification',
    blockName: 'Send Alert',
    category: 'alert',
    description: 'Console/log notification',
    acceptsInput: true,
    outputType: 'notification-sent',
    acceptedInputTypes: ['condition-result', 'trade-signal', 'indicator-value'],
    fields: [
      {
        name: 'type',
        label: 'Alert Type',
        type: 'select',
        default: 'console',
        options: [
          { value: 'console', label: 'Console Log' },
          { value: 'toast', label: 'UI Toast' },
          { value: 'sound', label: 'Sound Alert' },
        ],
      },
      {
        name: 'message',
        label: 'Message Template',
        type: 'text',
        default: 'Alert: ${condition} triggered at ${price}',
      },
    ],
  },
  {
    blockType: 'webhook',
    blockName: 'Webhook',
    category: 'alert',
    description: 'HTTP webhook call',
    acceptsInput: true,
    outputType: 'webhook-response',
    acceptedInputTypes: ['condition-result', 'trade-signal', 'indicator-value'],
    fields: [
      {
        name: 'url',
        label: 'Webhook URL',
        type: 'url',
        required: true,
        default: '',
      },
      {
        name: 'method',
        label: 'Method',
        type: 'select',
        default: 'POST',
        options: [
          { value: 'POST', label: 'POST' },
          { value: 'GET', label: 'GET' },
        ],
      },
      {
        name: 'headers',
        label: 'Headers (JSON)',
        type: 'json',
        default: '{"Content-Type": "application/json"}',
      },
    ],
  },
  {
    blockType: 'notification',
    blockName: 'Discord Alert',
    category: 'alert',
    description: 'Discord webhook notification',
    acceptsInput: true,
    outputType: 'notification-sent',
    acceptedInputTypes: ['condition-result', 'trade-signal'],
    fields: [
      {
        name: 'webhookUrl',
        label: 'Discord Webhook URL',
        type: 'url',
        required: true,
        default: '',
      },
      {
        name: 'username',
        label: 'Bot Username',
        type: 'text',
        default: 'Trading Bot',
      },
      {
        name: 'embedColor',
        label: 'Embed Color',
        type: 'select',
        default: '#00ff00',
        options: [
          { value: '#00ff00', label: 'Green (Success)' },
          { value: '#ff0000', label: 'Red (Alert)' },
          { value: '#ffff00', label: 'Yellow (Warning)' },
          { value: '#0000ff', label: 'Blue (Info)' },
        ],
      },
    ],
  },
]

// ============ OUTPUTS ============
export const OUTPUT_SCHEMAS: BlockConfigSchema[] = [
  {
    blockType: 'output',
    blockName: 'JSON File',
    category: 'output',
    description: 'Save to JSON file',
    acceptsInput: true,
    outputType: 'file-written',
    acceptedInputTypes: ['market-data', 'indicator-value', 'trade-signal', 'aggregated-data'],
    fields: [
      {
        name: 'output_dir',
        label: 'Output Directory',
        type: 'text',
        default: '/app/data',
      },
      {
        name: 'filename',
        label: 'Filename Pattern',
        type: 'text',
        description: 'Use ${date}, ${symbol}, etc.',
        default: '${symbol}_${date}.json',
      },
      {
        name: 'append',
        label: 'Append Mode',
        type: 'toggle',
        default: true,
      },
    ],
  },
  {
    blockType: 'output',
    blockName: 'Database',
    category: 'output',
    description: 'Store in database',
    acceptsInput: true,
    outputType: 'db-written',
    acceptedInputTypes: ['market-data', 'indicator-value', 'trade-signal', 'aggregated-data'],
    fields: [
      {
        name: 'connectionString',
        label: 'Connection String',
        type: 'text',
        required: true,
        default: '',
      },
      {
        name: 'table',
        label: 'Table/Collection Name',
        type: 'text',
        default: 'trades',
      },
      {
        name: 'batchSize',
        label: 'Batch Size',
        type: 'number',
        default: 100,
        min: 1,
        max: 10000,
      },
    ],
  },
  {
    blockType: 'signal',
    blockName: 'Signal Output',
    category: 'output',
    description: 'Emit trading signal',
    acceptsInput: true,
    outputType: 'signal-emitted',
    acceptedInputTypes: ['trade-signal', 'fusion-signal'],
    fields: [
      {
        name: 'format',
        label: 'Output Format',
        type: 'select',
        default: 'json',
        options: [
          { value: 'json', label: 'JSON' },
          { value: 'tradingview', label: 'TradingView Format' },
          { value: 'mt4', label: 'MT4 Format' },
        ],
      },
    ],
  },
]

// ============ AGENTS ============
export const AGENT_SCHEMAS: BlockConfigSchema[] = [
  {
    blockType: 'agent',
    blockName: 'AGGR Agent',
    category: 'agents',
    description: 'Real-time trade aggregation',
    acceptsInput: false,
    outputType: 'aggr-data',
    acceptedInputTypes: [],
    fields: [
      {
        name: 'symbols',
        label: 'Symbols',
        type: 'multi-select',
        default: ['BTCUSDT'],
        options: [
          { value: 'BTCUSDT', label: 'BTC/USDT' },
          { value: 'ETHUSDT', label: 'ETH/USDT' },
          { value: 'SOLUSDT', label: 'SOL/USDT' },
          { value: 'BNBUSDT', label: 'BNB/USDT' },
        ],
        allowCustom: true,
      },
      {
        name: 'stream',
        label: 'Stream Type',
        type: 'select',
        default: 'aggTrade',
        options: [
          { value: 'aggTrade', label: 'Aggregated Trades' },
          { value: 'trade', label: 'Raw Trades' },
        ],
      },
      {
        name: 'cvdEnabled',
        label: 'Calculate CVD',
        type: 'toggle',
        default: true,
      },
    ],
  },
  {
    blockType: 'agent',
    blockName: 'TradeFuck Agent',
    category: 'agents',
    description: 'Order flow analysis',
    acceptsInput: false,
    outputType: 'orderflow-data',
    acceptedInputTypes: [],
    fields: [
      {
        name: 'symbols',
        label: 'Symbols',
        type: 'multi-select',
        default: ['BTCUSDT'],
        allowCustom: true,
      },
      {
        name: 'deltaThreshold',
        label: 'Delta Threshold',
        type: 'number',
        default: 100,
        min: 10,
      },
    ],
  },
  {
    blockType: 'agent',
    blockName: 'CoinGlass Heatmap Agent',
    category: 'agents',
    description: 'Liquidation heatmaps',
    acceptsInput: false,
    outputType: 'heatmap-data',
    acceptedInputTypes: [],
    fields: [
      {
        name: 'interval',
        label: 'Update Interval',
        type: 'interval',
        default: '1h',
      },
      {
        name: 'range',
        label: 'Price Range %',
        type: 'slider',
        default: 10,
        min: 5,
        max: 50,
        step: 1,
        showValue: true,
      },
    ],
  },
  {
    blockType: 'chart',
    blockName: 'Footprint Charts',
    category: 'agents',
    description: 'Volume footprint visualization',
    acceptsInput: true,
    outputType: 'footprint-data',
    acceptedInputTypes: ['market-data', 'aggr-data'],
    fields: [
      {
        name: 'rows',
        label: 'Price Rows',
        type: 'number',
        default: 24,
        min: 10,
        max: 100,
      },
      {
        name: 'period',
        label: 'Candle Period',
        type: 'interval',
        default: '1m',
      },
      {
        name: 'imbalanceThreshold',
        label: 'Imbalance Threshold %',
        type: 'slider',
        default: 200,
        min: 100,
        max: 500,
        step: 10,
        showValue: true,
      },
    ],
  },
  {
    blockType: 'agent',
    blockName: 'YouTube Agent',
    category: 'knowledge',
    description: 'Research video extraction',
    acceptsInput: false,
    outputType: 'research-data',
    acceptedInputTypes: [],
    fields: [
      {
        name: 'channels',
        label: 'YouTube Channels',
        type: 'multi-select',
        default: [],
        allowCustom: true,
      },
      {
        name: 'keywords',
        label: 'Search Keywords',
        type: 'multi-select',
        default: ['bitcoin', 'crypto analysis'],
        allowCustom: true,
      },
      {
        name: 'maxVideos',
        label: 'Max Videos per Search',
        type: 'number',
        default: 5,
        min: 1,
        max: 50,
      },
    ],
  },
  {
    blockType: 'agent',
    blockName: 'Execution Agent',
    category: 'monitoring',
    description: 'Trade execution',
    acceptsInput: true,
    outputType: 'execution-result',
    acceptedInputTypes: ['trade-signal', 'dca-signal'],
    fields: [
      {
        name: 'exchange',
        label: 'Exchange',
        type: 'select',
        default: 'binance',
        options: [
          { value: 'binance', label: 'Binance' },
          { value: 'bybit', label: 'Bybit' },
          { value: 'okx', label: 'OKX' },
        ],
      },
      {
        name: 'mode',
        label: 'Trading Mode',
        type: 'select',
        default: 'paper',
        options: [
          { value: 'paper', label: 'Paper Trading' },
          { value: 'live', label: 'Live Trading' },
        ],
      },
      {
        name: 'slippage',
        label: 'Max Slippage %',
        type: 'slider',
        default: 0.5,
        min: 0.1,
        max: 5,
        step: 0.1,
        showValue: true,
      },
    ],
  },
  {
    blockType: 'agent',
    blockName: 'Risk Operations Agent',
    category: 'risk',
    description: 'Risk monitoring',
    acceptsInput: true,
    outputType: 'risk-status',
    acceptedInputTypes: ['position-data', 'execution-result'],
    fields: [
      {
        name: 'maxDrawdown',
        label: 'Max Drawdown %',
        type: 'slider',
        default: 10,
        min: 1,
        max: 50,
        step: 1,
        showValue: true,
      },
      {
        name: 'alertThreshold',
        label: 'Alert at Drawdown %',
        type: 'slider',
        default: 5,
        min: 1,
        max: 25,
        step: 0.5,
        showValue: true,
      },
    ],
  },
]

// ============ KNOWLEDGE & FUSION ============
export const KNOWLEDGE_SCHEMAS: BlockConfigSchema[] = [
  {
    blockType: 'knowledgebase',
    blockName: 'External Knowledgebase',
    category: 'knowledge',
    description: 'External data store',
    acceptsInput: true,
    outputType: 'kb-data',
    acceptedInputTypes: ['research-data', 'market-data'],
    fields: [
      {
        name: 'path',
        label: 'Storage Path',
        type: 'text',
        default: '/data/external',
      },
      {
        name: 'format',
        label: 'Storage Format',
        type: 'select',
        default: 'json',
        options: [
          { value: 'json', label: 'JSON Files' },
          { value: 'sqlite', label: 'SQLite' },
          { value: 'vector', label: 'Vector DB' },
        ],
      },
    ],
  },
  {
    blockType: 'knowledgebase',
    blockName: 'Main Knowledgebase',
    category: 'risk',
    description: 'Core bot logic store',
    acceptsInput: true,
    outputType: 'kb-data',
    acceptedInputTypes: ['indicator-value', 'pattern-signal', 'research-data'],
    fields: [
      {
        name: 'path',
        label: 'Storage Path',
        type: 'text',
        default: '/data/main',
      },
    ],
  },
  {
    blockType: 'knowledgebase',
    blockName: 'Knowledge Tap (API)',
    category: 'analysis',
    description: 'KB query interface',
    acceptsInput: false,
    outputType: 'kb-query-result',
    acceptedInputTypes: [],
    fields: [
      {
        name: 'endpoint',
        label: 'API Endpoint',
        type: 'text',
        default: '/api/kb',
      },
      {
        name: 'queryType',
        label: 'Query Type',
        type: 'select',
        default: 'semantic',
        options: [
          { value: 'semantic', label: 'Semantic Search' },
          { value: 'exact', label: 'Exact Match' },
          { value: 'hybrid', label: 'Hybrid' },
        ],
      },
    ],
  },
  {
    blockType: 'learning',
    blockName: 'Backtesting & Research Loop',
    category: 'knowledge',
    description: 'Historical testing',
    acceptsInput: true,
    outputType: 'backtest-result',
    acceptedInputTypes: ['historical-data', 'trade-signal'],
    fields: [
      {
        name: 'startDate',
        label: 'Start Date',
        type: 'text',
        default: '',
      },
      {
        name: 'endDate',
        label: 'End Date',
        type: 'text',
        default: '',
      },
      {
        name: 'initialCapital',
        label: 'Initial Capital',
        type: 'number',
        default: 10000,
        min: 100,
      },
    ],
  },
]

// ============ FUSION & ROUTING ============
export const FUSION_SCHEMAS: BlockConfigSchema[] = [
  {
    blockType: 'fusion',
    blockName: 'Knowledgebase Fusion',
    category: 'fusion',
    description: 'ML refinement',
    acceptsInput: true,
    outputType: 'fusion-signal',
    acceptedInputTypes: ['indicator-value', 'kb-data', 'pattern-signal'],
    fields: [
      {
        name: 'model',
        label: 'Fusion Model',
        type: 'select',
        default: 'ensemble',
        options: [
          { value: 'ensemble', label: 'Ensemble Average' },
          { value: 'weighted', label: 'Weighted Average' },
          { value: 'ml', label: 'ML Model' },
          { value: 'voting', label: 'Voting' },
        ],
      },
      {
        name: 'weights',
        label: 'Input Weights (JSON)',
        type: 'json',
        default: '{}',
      },
    ],
  },
  {
    blockType: 'fusion',
    blockName: 'Scenario Builder',
    category: 'fusion',
    description: 'Strategy scenarios',
    acceptsInput: true,
    outputType: 'scenario-signal',
    acceptedInputTypes: ['indicator-value', 'pattern-signal'],
    fields: [
      {
        name: 'scenarios',
        label: 'Scenario Rules (JSON)',
        type: 'json',
        default: '[]',
      },
      {
        name: 'defaultAction',
        label: 'Default Action',
        type: 'select',
        default: 'hold',
        options: [
          { value: 'hold', label: 'Hold' },
          { value: 'exit', label: 'Exit Position' },
        ],
      },
    ],
  },
  {
    blockType: 'fusion',
    blockName: 'Confluence Scorer',
    category: 'fusion',
    description: 'Multi-signal scoring',
    acceptsInput: true,
    outputType: 'confluence-score',
    acceptedInputTypes: ['indicator-value', 'pattern-signal', 'fusion-signal'],
    fields: [
      {
        name: 'threshold',
        label: 'Signal Threshold',
        type: 'slider',
        default: 0.7,
        min: 0.1,
        max: 1,
        step: 0.05,
        showValue: true,
      },
      {
        name: 'minSignals',
        label: 'Min Confirming Signals',
        type: 'number',
        default: 2,
        min: 1,
        max: 10,
      },
    ],
  },
  {
    blockType: 'validator',
    blockName: 'Signal Validator',
    category: 'fusion',
    description: 'Signal validation',
    acceptsInput: true,
    outputType: 'validated-signal',
    acceptedInputTypes: ['trade-signal', 'fusion-signal', 'confluence-score'],
    fields: [
      {
        name: 'minConfidence',
        label: 'Min Confidence',
        type: 'slider',
        default: 0.8,
        min: 0.5,
        max: 1,
        step: 0.05,
        showValue: true,
      },
      {
        name: 'requireVolume',
        label: 'Require Volume Confirmation',
        type: 'toggle',
        default: true,
      },
      {
        name: 'cooldown',
        label: 'Signal Cooldown (sec)',
        type: 'number',
        default: 60,
        min: 0,
        max: 3600,
      },
    ],
  },
]

// ============ MONITORING ============
export const MONITORING_SCHEMAS: BlockConfigSchema[] = [
  {
    blockType: 'monitoring',
    blockName: 'Monitoring & Journal',
    category: 'monitoring',
    description: 'Trade journaling',
    acceptsInput: true,
    outputType: 'journal-entry',
    acceptedInputTypes: ['execution-result', 'order-result'],
    fields: [
      {
        name: 'logPath',
        label: 'Log Path',
        type: 'text',
        default: '/logs/trades',
      },
      {
        name: 'includeScreenshot',
        label: 'Include Chart Screenshot',
        type: 'toggle',
        default: false,
      },
      {
        name: 'metrics',
        label: 'Track Metrics',
        type: 'multi-select',
        default: ['pnl', 'winRate', 'sharpe'],
        options: [
          { value: 'pnl', label: 'P&L' },
          { value: 'winRate', label: 'Win Rate' },
          { value: 'sharpe', label: 'Sharpe Ratio' },
          { value: 'maxDrawdown', label: 'Max Drawdown' },
          { value: 'avgHoldTime', label: 'Avg Hold Time' },
        ],
      },
    ],
  },
  {
    blockType: 'monitoring',
    blockName: 'Audit Trail',
    category: 'monitoring',
    description: 'Activity logging',
    acceptsInput: true,
    outputType: 'audit-log',
    acceptedInputTypes: ['execution-result', 'order-result', 'risk-status'],
    fields: [
      {
        name: 'retention',
        label: 'Log Retention',
        type: 'select',
        default: '90d',
        options: [
          { value: '7d', label: '7 Days' },
          { value: '30d', label: '30 Days' },
          { value: '90d', label: '90 Days' },
          { value: '365d', label: '1 Year' },
          { value: 'forever', label: 'Forever' },
        ],
      },
      {
        name: 'logLevel',
        label: 'Log Level',
        type: 'select',
        default: 'info',
        options: [
          { value: 'debug', label: 'Debug (All)' },
          { value: 'info', label: 'Info' },
          { value: 'warn', label: 'Warnings Only' },
          { value: 'error', label: 'Errors Only' },
        ],
      },
    ],
  },
  {
    blockType: 'learning',
    blockName: 'Learning Loop',
    category: 'monitoring',
    description: 'Feedback integration',
    acceptsInput: true,
    outputType: 'learning-feedback',
    acceptedInputTypes: ['journal-entry', 'backtest-result'],
    fields: [
      {
        name: 'feedbackPath',
        label: 'Feedback Storage',
        type: 'text',
        default: '/data/feedback',
      },
      {
        name: 'autoAdjust',
        label: 'Auto-adjust Parameters',
        type: 'toggle',
        default: false,
      },
      {
        name: 'minSamples',
        label: 'Min Samples for Adjustment',
        type: 'number',
        default: 50,
        min: 10,
        max: 1000,
      },
    ],
  },
]

// ============ EXPORT ALL SCHEMAS ============
export const ALL_BLOCK_SCHEMAS: BlockConfigSchema[] = [
  ...DATA_SOURCE_SCHEMAS,
  ...INDICATOR_SCHEMAS,
  ...TRANSFORM_SCHEMAS,
  ...TRADING_SCHEMAS,
  ...RISK_SCHEMAS,
  ...ALERT_SCHEMAS,
  ...OUTPUT_SCHEMAS,
  ...AGENT_SCHEMAS,
  ...KNOWLEDGE_SCHEMAS,
  ...FUSION_SCHEMAS,
  ...MONITORING_SCHEMAS,
]

// Helper to get schema by block name
export function getBlockSchema(blockName: string): BlockConfigSchema | undefined {
  return ALL_BLOCK_SCHEMAS.find(s => s.blockName === blockName)
}

// Helper to get schemas by category
export function getSchemasByCategory(category: string): BlockConfigSchema[] {
  return ALL_BLOCK_SCHEMAS.filter(s => s.category === category)
}

// Helper to check if connection is valid
export function isValidConnection(fromSchema: BlockConfigSchema, toSchema: BlockConfigSchema): boolean {
  return toSchema.acceptedInputTypes.includes(fromSchema.outputType)
}

