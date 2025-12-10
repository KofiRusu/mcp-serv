'use client'

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import {
  Search,
  ChevronRight,
  ChevronDown,
  Database,
  Zap,
  FileOutput,
  GitBranch,
  TrendingUp,
  Bell,
  Shield,
  Target,
  DollarSign,
  Activity,
  Webhook,
  BarChart3,
  Filter,
  Layers,
  GripVertical,
  Clock,
  Star,
  // New icons for trading system architecture
  Bot,
  Brain,
  GitMerge,
  CheckCircle2,
  Gauge,
  Eye,
  RefreshCw,
  CandlestickChart,
  Youtube,
  BookOpen,
  FlaskConical,
  Cpu,
  LineChart,
  Sparkles,
  Merge,
  Calculator,
  Scale,
  Wallet,
  ClipboardCheck,
  History,
  GraduationCap,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { Block, BlockType } from './block-node'
import type { AutomationType } from './builder-canvas'

interface BlockTemplate {
  type: BlockType
  name: string
  description: string
  defaultConfig: Record<string, any>
  category: string
  icon: React.ElementType
  color: string
}

const BLOCK_TEMPLATES: BlockTemplate[] = [
  // Data Sources
  { type: 'source', name: 'Binance WebSocket', description: 'Real-time market data', defaultConfig: { symbol: 'BTCUSDT', stream: 'btcusdt@aggTrade' }, category: 'data', icon: Database, color: 'emerald' },
  { type: 'source', name: 'Binance REST', description: 'REST API endpoints', defaultConfig: { symbol: 'BTC/USDT', endpoint: 'ticker' }, category: 'data', icon: Database, color: 'emerald' },
  { type: 'source', name: 'CoinGecko API', description: 'Market data aggregator', defaultConfig: { coins: ['bitcoin'], interval: 60 }, category: 'data', icon: Database, color: 'emerald' },
  { type: 'source', name: 'Custom REST API', description: 'Your own API endpoint', defaultConfig: { url: '', interval: 60 }, category: 'data', icon: Database, color: 'emerald' },
  { type: 'source', name: 'Historical Data', description: 'CSV/JSON file input', defaultConfig: { file: '', symbol: 'BTC/USDT' }, category: 'data', icon: Database, color: 'emerald' },
  
  // Indicators
  { type: 'indicator', name: 'RSI', description: 'Relative Strength Index', defaultConfig: { period: 14, overbought: 70, oversold: 30 }, category: 'analysis', icon: Activity, color: 'pink' },
  { type: 'indicator', name: 'MACD', description: 'Moving Average Convergence', defaultConfig: { fast: 12, slow: 26, signal: 9 }, category: 'analysis', icon: Activity, color: 'pink' },
  { type: 'indicator', name: 'Moving Average', description: 'SMA/EMA calculation', defaultConfig: { period: 20, type: 'SMA' }, category: 'analysis', icon: Activity, color: 'pink' },
  { type: 'indicator', name: 'Bollinger Bands', description: 'Volatility bands', defaultConfig: { period: 20, stdDev: 2 }, category: 'analysis', icon: Activity, color: 'pink' },
  { type: 'indicator', name: 'Volume Profile', description: 'Volume distribution', defaultConfig: { rows: 24 }, category: 'analysis', icon: BarChart3, color: 'pink' },
  
  // Transforms
  { type: 'transform', name: 'Filter', description: 'Filter data by condition', defaultConfig: { condition: '' }, category: 'transform', icon: Filter, color: 'amber' },
  { type: 'aggregate', name: 'Aggregate', description: 'Combine multiple inputs', defaultConfig: { window: '1m' }, category: 'transform', icon: Layers, color: 'amber' },
  { type: 'filter', name: 'Volume Filter', description: 'Filter by volume', defaultConfig: { minVolume: 1000 }, category: 'transform', icon: Filter, color: 'amber' },
  
  // Trading
  { type: 'entry', name: 'Entry Signal', description: 'Define entry conditions', defaultConfig: { type: 'market' }, category: 'trading', icon: TrendingUp, color: 'cyan' },
  { type: 'exit', name: 'Exit Signal', description: 'Define exit conditions', defaultConfig: { type: 'market' }, category: 'trading', icon: TrendingUp, color: 'cyan' },
  { type: 'order', name: 'Market Order', description: 'Execute at market price', defaultConfig: { exchange: 'binance', side: 'buy' }, category: 'trading', icon: DollarSign, color: 'cyan' },
  { type: 'order', name: 'Limit Order', description: 'Execute at limit price', defaultConfig: { exchange: 'binance', side: 'buy', price: 0 }, category: 'trading', icon: DollarSign, color: 'cyan' },
  { type: 'position', name: 'Position Manager', description: 'Track open positions', defaultConfig: { maxPosition: 1 }, category: 'trading', icon: Layers, color: 'cyan' },
  
  // Risk
  { type: 'risk_check', name: 'Risk Check', description: 'Validate risk limits', defaultConfig: { maxDrawdown: 10 }, category: 'risk', icon: Shield, color: 'red' },
  { type: 'position_size', name: 'Position Sizer', description: 'Calculate position size', defaultConfig: { method: 'fixed', risk: 1 }, category: 'risk', icon: Target, color: 'red' },
  { type: 'stop_loss', name: 'Stop Loss', description: 'Automatic stop loss', defaultConfig: { type: 'percent', value: 2 }, category: 'risk', icon: Shield, color: 'red' },
  { type: 'take_profit', name: 'Take Profit', description: 'Automatic take profit', defaultConfig: { type: 'percent', value: 4 }, category: 'risk', icon: Target, color: 'green' },
  
  // Alerts
  { type: 'condition', name: 'Price Condition', description: 'Price threshold check', defaultConfig: { above: 0, below: 0 }, category: 'alert', icon: GitBranch, color: 'purple' },
  { type: 'notification', name: 'Send Alert', description: 'Console/log notification', defaultConfig: { type: 'console' }, category: 'alert', icon: Bell, color: 'orange' },
  { type: 'webhook', name: 'Webhook', description: 'HTTP webhook call', defaultConfig: { url: '' }, category: 'alert', icon: Webhook, color: 'orange' },
  { type: 'notification', name: 'Discord Alert', description: 'Discord webhook', defaultConfig: { webhookUrl: '' }, category: 'alert', icon: Bell, color: 'orange' },
  
  // Outputs
  { type: 'output', name: 'JSON File', description: 'Save to JSON file', defaultConfig: { output_dir: '/app/data' }, category: 'output', icon: FileOutput, color: 'blue' },
  { type: 'output', name: 'Database', description: 'Store in database', defaultConfig: { connectionString: '' }, category: 'output', icon: FileOutput, color: 'blue' },
  { type: 'signal', name: 'Signal Output', description: 'Emit trading signal', defaultConfig: {}, category: 'output', icon: BarChart3, color: 'blue' },

  // ========== NEW: Trading System Architecture Blocks ==========

  // L1 Market Microstructure (agents category)
  { type: 'agent', name: 'AGGR Agent', description: 'Real-time trade aggregation', defaultConfig: { symbols: ['BTCUSDT'], stream: 'aggTrade' }, category: 'agents', icon: Bot, color: 'violet' },
  { type: 'agent', name: 'TradeFuck Agent', description: 'Order flow analysis', defaultConfig: { symbols: ['BTCUSDT'] }, category: 'agents', icon: Bot, color: 'violet' },
  { type: 'agent', name: 'CoinGlass Heatmap Agent', description: 'Liquidation heatmaps', defaultConfig: { interval: '1h' }, category: 'agents', icon: Bot, color: 'violet' },
  { type: 'chart', name: 'Footprint Charts', description: 'Volume footprint visualization', defaultConfig: { rows: 24, period: '1m' }, category: 'agents', icon: CandlestickChart, color: 'violet' },

  // External Knowledge (knowledge category)
  { type: 'agent', name: 'YouTube Agent', description: 'Research video extraction', defaultConfig: { channels: [], keywords: [] }, category: 'knowledge', icon: Youtube, color: 'orange' },
  { type: 'knowledgebase', name: 'External Knowledgebase', description: 'External data store', defaultConfig: { path: '/data/external' }, category: 'knowledge', icon: BookOpen, color: 'orange' },
  { type: 'learning', name: 'Backtesting & Research Loop', description: 'Historical testing', defaultConfig: { startDate: '', endDate: '' }, category: 'knowledge', icon: FlaskConical, color: 'orange' },

  // L2 Indicator Layer (analysis category - extends existing)
  { type: 'knowledgebase', name: 'Knowledge Tap (API)', description: 'KB query interface', defaultConfig: { endpoint: '/api/kb' }, category: 'analysis', icon: Cpu, color: 'pink' },
  { type: 'indicator', name: 'Money V1 (Structure)', description: 'Market structure analysis', defaultConfig: { period: 20 }, category: 'analysis', icon: LineChart, color: 'pink' },
  { type: 'indicator', name: 'Money V2 (Momentum)', description: 'Momentum indicators', defaultConfig: { period: 14 }, category: 'analysis', icon: LineChart, color: 'pink' },
  { type: 'indicator', name: 'Legend (Visual Language)', description: 'Pattern recognition', defaultConfig: { patterns: ['head_shoulders', 'double_top'] }, category: 'analysis', icon: Sparkles, color: 'pink' },

  // L3 Fusion & Signal Router (fusion category)
  { type: 'fusion', name: 'Knowledgebase Fusion', description: 'ML refinement', defaultConfig: { model: 'ensemble' }, category: 'fusion', icon: Merge, color: 'yellow' },
  { type: 'fusion', name: 'Scenario Builder', description: 'Strategy scenarios', defaultConfig: { scenarios: [] }, category: 'fusion', icon: GitMerge, color: 'yellow' },
  { type: 'fusion', name: 'Confluence Scorer', description: 'Multi-signal scoring', defaultConfig: { threshold: 0.7 }, category: 'fusion', icon: Calculator, color: 'yellow' },
  { type: 'validator', name: 'Signal Validator', description: 'Signal validation', defaultConfig: { minConfidence: 0.8 }, category: 'fusion', icon: CheckCircle2, color: 'yellow' },

  // L4 Risk Management (risk category - extends existing)
  { type: 'knowledgebase', name: 'Main Knowledgebase', description: 'Core bot logic store', defaultConfig: { path: '/data/main' }, category: 'risk', icon: Brain, color: 'red' },
  { type: 'agent', name: 'Risk Operations Agent', description: 'Risk monitoring', defaultConfig: { maxDrawdown: 10 }, category: 'risk', icon: Shield, color: 'red' },
  { type: 'risk_check', name: 'Sizing Engine', description: 'Position sizing', defaultConfig: { method: 'kelly', risk: 1 }, category: 'risk', icon: Calculator, color: 'red' },
  { type: 'strategy', name: 'DCA / DCA-lite', description: 'Dollar cost averaging', defaultConfig: { interval: '4h', splits: 4 }, category: 'risk', icon: Scale, color: 'red' },
  { type: 'risk_check', name: 'Portfolio Guardrails', description: 'Portfolio limits', defaultConfig: { maxExposure: 50, maxCorrelation: 0.7 }, category: 'risk', icon: Shield, color: 'red' },

  // L5 Execution & Monitoring (monitoring category)
  { type: 'agent', name: 'Execution Agent', description: 'Trade execution', defaultConfig: { exchange: 'binance', mode: 'paper' }, category: 'monitoring', icon: Wallet, color: 'slate' },
  { type: 'monitoring', name: 'Monitoring & Journal', description: 'Trade journaling', defaultConfig: { logPath: '/logs/trades' }, category: 'monitoring', icon: ClipboardCheck, color: 'slate' },
  { type: 'monitoring', name: 'Audit Trail', description: 'Activity logging', defaultConfig: { retention: '90d' }, category: 'monitoring', icon: History, color: 'slate' },
  { type: 'learning', name: 'Learning Loop', description: 'Feedback integration', defaultConfig: { feedbackPath: '/data/feedback' }, category: 'monitoring', icon: GraduationCap, color: 'slate' },
]

const CATEGORY_CONFIG: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  data: { label: 'Data Sources', icon: Database, color: 'emerald' },
  analysis: { label: 'Indicators', icon: Activity, color: 'pink' },
  transform: { label: 'Transforms', icon: Zap, color: 'amber' },
  trading: { label: 'Trading', icon: TrendingUp, color: 'cyan' },
  risk: { label: 'Risk Management', icon: Shield, color: 'red' },
  alert: { label: 'Alerts & Conditions', icon: Bell, color: 'orange' },
  output: { label: 'Outputs', icon: FileOutput, color: 'blue' },
  // New categories for trading system architecture
  agents: { label: 'Data Agents', icon: Bot, color: 'violet' },
  knowledge: { label: 'Knowledge', icon: Brain, color: 'orange' },
  fusion: { label: 'Fusion & Routing', icon: GitMerge, color: 'yellow' },
  monitoring: { label: 'Monitoring', icon: Eye, color: 'slate' },
}

interface BlockPaletteProps {
  automationType: AutomationType
  onAddBlock: (block: Omit<Block, 'id' | 'position' | 'connections'>) => void
  recentBlocks?: string[]
  isCollapsed?: boolean
  onToggleCollapse?: () => void
}

export function BlockPalette({
  automationType,
  onAddBlock,
  recentBlocks = [],
  isCollapsed = false,
  onToggleCollapse,
}: BlockPaletteProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedCategories, setExpandedCategories] = useState<string[]>(['data'])
  const [draggedTemplate, setDraggedTemplate] = useState<BlockTemplate | null>(null)

  // Filter templates based on automation type
  // Note: For now, showing all categories to enable manual building of complex diagrams
  const getRelevantCategories = () => {
    // Always show all categories in manual mode for maximum flexibility
    return Object.keys(CATEGORY_CONFIG)
  }

  const relevantCategories = getRelevantCategories()

  // Filter templates by search and category
  const filteredTemplates = BLOCK_TEMPLATES.filter(t => {
    if (!relevantCategories.includes(t.category)) return false
    if (!searchQuery) return true
    return (
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase())
    )
  })

  // Group by category
  const templatesByCategory = filteredTemplates.reduce((acc, t) => {
    if (!acc[t.category]) acc[t.category] = []
    acc[t.category].push(t)
    return acc
  }, {} as Record<string, BlockTemplate[]>)

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev =>
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    )
  }

  const handleDragStart = useCallback((e: React.DragEvent, template: BlockTemplate) => {
    setDraggedTemplate(template)
    e.dataTransfer.setData('application/json', JSON.stringify({
      type: 'new-block',
      template: {
        type: template.type,
        name: template.name,
        config: template.defaultConfig,
      }
    }))
    e.dataTransfer.effectAllowed = 'copy'
  }, [])

  const handleDragEnd = () => {
    setDraggedTemplate(null)
  }

  const handleAddBlock = (template: BlockTemplate) => {
    onAddBlock({
      type: template.type,
      name: template.name,
      config: { ...template.defaultConfig },
    })
  }

  // Get recently used blocks
  const recentTemplates = recentBlocks
    .map(name => BLOCK_TEMPLATES.find(t => t.name === name))
    .filter(Boolean) as BlockTemplate[]

  if (isCollapsed) {
    return (
      <div className="w-12 h-full bg-gray-900/50 border-r border-gray-800 flex flex-col items-center py-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          className="mb-4"
        >
          <ChevronRight className="w-4 h-4" />
        </Button>
        {Object.entries(CATEGORY_CONFIG)
          .filter(([key]) => relevantCategories.includes(key))
          .map(([key, config]) => (
            <Button
              key={key}
              variant="ghost"
              size="icon"
              className="mb-2"
              title={config.label}
              onClick={() => {
                if (onToggleCollapse) onToggleCollapse()
                setExpandedCategories([key])
              }}
            >
              <config.icon className={cn('w-4 h-4', `text-${config.color}-400`)} />
            </Button>
          ))}
      </div>
    )
  }

  return (
    <div className="w-64 h-full bg-gray-900/50 border-r border-gray-800 flex flex-col overflow-hidden">
      {/* Header - fixed at top */}
      <div className="p-3 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white">Block Palette</h3>
          {onToggleCollapse && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleCollapse}
              className="h-6 w-6"
            >
              <ChevronDown className="w-4 h-4 rotate-90" />
            </Button>
          )}
        </div>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search blocks..."
            className="pl-8 h-8 bg-gray-800 border-gray-700 text-sm"
          />
        </div>
      </div>

      {/* Scrollable block list */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-2">
          {/* Recently used */}
          {recentTemplates.length > 0 && !searchQuery && (
            <div className="mb-4">
              <div className="flex items-center gap-2 px-2 py-1.5 text-xs text-gray-400">
                <Clock className="w-3 h-3" />
                <span>Recently Used</span>
              </div>
              <div className="space-y-1">
                {recentTemplates.slice(0, 3).map((template, idx) => (
                  <PaletteBlock
                    key={`recent-${idx}`}
                    template={template}
                    onAdd={() => handleAddBlock(template)}
                    onDragStart={handleDragStart}
                    onDragEnd={handleDragEnd}
                    isDragging={draggedTemplate?.name === template.name}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Categories */}
          {Object.entries(templatesByCategory).map(([category, templates]) => {
            const config = CATEGORY_CONFIG[category]
            const isExpanded = expandedCategories.includes(category)

            return (
              <div key={category} className="mb-2">
                <button
                  onClick={() => toggleCategory(category)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-medium text-gray-300 hover:text-white hover:bg-gray-800/50 rounded-md transition-colors"
                >
                  <motion.div
                    animate={{ rotate: isExpanded ? 90 : 0 }}
                    transition={{ duration: 0.15 }}
                  >
                    <ChevronRight className="w-3 h-3" />
                  </motion.div>
                  <config.icon className={cn('w-3.5 h-3.5', `text-${config.color}-400`)} />
                  <span className="flex-1 text-left">{config.label}</span>
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                    {templates.length}
                  </Badge>
                </button>

                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="pl-4 space-y-1 mt-1">
                        {templates.map((template, idx) => (
                          <PaletteBlock
                            key={`${category}-${idx}`}
                            template={template}
                            onAdd={() => handleAddBlock(template)}
                            onDragStart={handleDragStart}
                            onDragEnd={handleDragEnd}
                            isDragging={draggedTemplate?.name === template.name}
                          />
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )
          })}

          {filteredTemplates.length === 0 && (
            <div className="text-center py-8 text-gray-500 text-sm">
              No blocks match "{searchQuery}"
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer hint - fixed at bottom */}
      <div className="p-2 border-t border-gray-800 flex-shrink-0">
        <p className="text-[10px] text-gray-500 text-center">
          Drag blocks to canvas or click to add
        </p>
      </div>
    </div>
  )
}

// Individual palette block component
interface PaletteBlockProps {
  template: BlockTemplate
  onAdd: () => void
  onDragStart: (e: React.DragEvent, template: BlockTemplate) => void
  onDragEnd: () => void
  isDragging?: boolean
}

function PaletteBlock({ template, onAdd, onDragStart, onDragEnd, isDragging }: PaletteBlockProps) {
  const Icon = template.icon

  return (
    <motion.div
      draggable
      tabIndex={0}
      role="button"
      aria-label={`Add ${template.name} block: ${template.description}`}
      onDragStart={(e) => onDragStart(e as unknown as React.DragEvent, template)}
      onDragEnd={onDragEnd}
      onClick={onAdd}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onAdd()
        }
      }}
      className={cn(
        'flex items-center gap-2 px-2 py-2 rounded-md cursor-grab active:cursor-grabbing',
        'bg-gray-800/30 hover:bg-gray-800/60 border border-transparent hover:border-gray-700',
        'transition-all duration-150 group focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50',
        isDragging && 'opacity-50 scale-95'
      )}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <GripVertical className="w-3 h-3 text-gray-600 group-hover:text-gray-400 flex-shrink-0" />
      <div className={cn(
        'p-1.5 rounded',
        `bg-${template.color}-500/10`
      )}>
        <Icon className={cn('w-3.5 h-3.5', `text-${template.color}-400`)} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-gray-200 truncate">{template.name}</p>
        <p className="text-[10px] text-gray-500 truncate">{template.description}</p>
      </div>
    </motion.div>
  )
}

export default BlockPalette

