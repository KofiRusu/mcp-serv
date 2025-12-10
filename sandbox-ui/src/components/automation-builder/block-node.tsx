'use client'

import { memo, useState, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'
import { 
  Database, 
  Zap, 
  FileOutput, 
  GitBranch, 
  Settings, 
  MoreVertical,
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
  ArrowRightLeft,
  Link2,
  Play,
  GripVertical,
  // New icons for trading system architecture
  Bot,
  Brain,
  GitMerge,
  CheckCircle2,
  Gauge,
  Eye,
  RefreshCw,
  CandlestickChart
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

// Expanded block types
export type BlockType = 
  | 'source' 
  | 'transform' 
  | 'output' 
  | 'condition'
  | 'loop'
  | 'entry'
  | 'exit'
  | 'order'
  | 'position'
  | 'indicator'
  | 'signal'
  | 'filter'
  | 'aggregate'
  | 'notification'
  | 'webhook'
  | 'risk_check'
  | 'position_size'
  | 'stop_loss'
  | 'take_profit'
  // New block types for trading system architecture
  | 'agent'          // For AGGR, YouTube, TradeFuck, CoinGlass, Risk Ops, Execution agents
  | 'knowledgebase'  // For External KB, Main KB
  | 'fusion'         // For KB Fusion, Scenario Builder
  | 'validator'      // For Signal Validator
  | 'strategy'       // For DCA/DCA-lite
  | 'monitoring'     // For Monitoring & Journal, Audit Trail
  | 'learning'       // For Learning Loop, Backtesting
  | 'chart'          // For Footprint Charts

export interface BlockConfig {
  [key: string]: any
}

export interface Block {
  id: string
  type: BlockType
  name: string
  config: BlockConfig
  position: { x: number; y: number }
  connections: string[]
}

interface BlockNodeProps {
  block: Block
  selected: boolean
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onConfigure: (id: string) => void
  onDragStart: (e: React.DragEvent, id: string) => void
  onConnect?: (fromId: string, toId: string) => void
  allBlocks?: Block[]
}

// Icons for each block type
const BLOCK_ICONS: Record<BlockType, React.ElementType> = {
  source: Database,
  transform: Zap,
  output: FileOutput,
  condition: GitBranch,
  loop: ArrowRightLeft,
  entry: TrendingUp,
  exit: TrendingUp,
  order: DollarSign,
  position: Layers,
  indicator: Activity,
  signal: BarChart3,
  filter: Filter,
  aggregate: Layers,
  notification: Bell,
  webhook: Webhook,
  risk_check: Shield,
  position_size: Target,
  stop_loss: Shield,
  take_profit: Target,
  // New block type icons
  agent: Bot,
  knowledgebase: Brain,
  fusion: GitMerge,
  validator: CheckCircle2,
  strategy: Gauge,
  monitoring: Eye,
  learning: RefreshCw,
  chart: CandlestickChart,
}

// Color schemes for block types (grouped by category)
const BLOCK_COLORS: Record<BlockType, string> = {
  // Data (green)
  source: 'border-emerald-500/50 bg-emerald-500/10',
  
  // Transform (amber)
  transform: 'border-amber-500/50 bg-amber-500/10',
  filter: 'border-amber-500/50 bg-amber-500/10',
  aggregate: 'border-amber-500/50 bg-amber-500/10',
  
  // Output (blue)
  output: 'border-blue-500/50 bg-blue-500/10',
  
  // Conditions (purple)
  condition: 'border-purple-500/50 bg-purple-500/10',
  loop: 'border-purple-500/50 bg-purple-500/10',
  
  // Trading (cyan)
  entry: 'border-cyan-500/50 bg-cyan-500/10',
  exit: 'border-cyan-400/50 bg-cyan-400/10',
  order: 'border-cyan-500/50 bg-cyan-500/10',
  position: 'border-cyan-500/50 bg-cyan-500/10',
  
  // Indicators/Signals (pink)
  indicator: 'border-pink-500/50 bg-pink-500/10',
  signal: 'border-pink-500/50 bg-pink-500/10',
  
  // Alerts (orange)
  notification: 'border-orange-500/50 bg-orange-500/10',
  webhook: 'border-orange-500/50 bg-orange-500/10',
  
  // Risk (red)
  risk_check: 'border-red-500/50 bg-red-500/10',
  position_size: 'border-red-400/50 bg-red-400/10',
  stop_loss: 'border-red-500/50 bg-red-500/10',
  take_profit: 'border-green-500/50 bg-green-500/10',
  
  // Agents (violet)
  agent: 'border-violet-500/50 bg-violet-500/10',
  
  // Knowledge (orange)
  knowledgebase: 'border-orange-500/50 bg-orange-500/10',
  
  // Fusion & Routing (yellow)
  fusion: 'border-yellow-500/50 bg-yellow-500/10',
  validator: 'border-yellow-400/50 bg-yellow-400/10',
  
  // Strategy (indigo)
  strategy: 'border-indigo-500/50 bg-indigo-500/10',
  
  // Monitoring (slate)
  monitoring: 'border-slate-400/50 bg-slate-400/10',
  
  // Learning (teal)
  learning: 'border-teal-500/50 bg-teal-500/10',
  
  // Charts (rose)
  chart: 'border-rose-500/50 bg-rose-500/10',
}

const BLOCK_ICON_COLORS: Record<BlockType, string> = {
  source: 'text-emerald-400',
  transform: 'text-amber-400',
  filter: 'text-amber-400',
  aggregate: 'text-amber-400',
  output: 'text-blue-400',
  condition: 'text-purple-400',
  loop: 'text-purple-400',
  entry: 'text-cyan-400',
  exit: 'text-cyan-300',
  order: 'text-cyan-400',
  position: 'text-cyan-400',
  indicator: 'text-pink-400',
  signal: 'text-pink-400',
  notification: 'text-orange-400',
  webhook: 'text-orange-400',
  risk_check: 'text-red-400',
  position_size: 'text-red-300',
  stop_loss: 'text-red-400',
  take_profit: 'text-green-400',
  // New block type icon colors
  agent: 'text-violet-400',
  knowledgebase: 'text-orange-400',
  fusion: 'text-yellow-400',
  validator: 'text-yellow-300',
  strategy: 'text-indigo-400',
  monitoring: 'text-slate-300',
  learning: 'text-teal-400',
  chart: 'text-rose-400',
}

// Category labels for display
const BLOCK_CATEGORY: Record<BlockType, string> = {
  source: 'DATA',
  transform: 'TRANSFORM',
  filter: 'FILTER',
  aggregate: 'AGGREGATE',
  output: 'OUTPUT',
  condition: 'CONDITION',
  loop: 'LOOP',
  entry: 'ENTRY',
  exit: 'EXIT',
  order: 'ORDER',
  position: 'POSITION',
  indicator: 'INDICATOR',
  signal: 'SIGNAL',
  notification: 'ALERT',
  webhook: 'WEBHOOK',
  risk_check: 'RISK',
  position_size: 'SIZING',
  stop_loss: 'STOP LOSS',
  take_profit: 'TAKE PROFIT',
  // New block type categories
  agent: 'AGENT',
  knowledgebase: 'KNOWLEDGE',
  fusion: 'FUSION',
  validator: 'VALIDATOR',
  strategy: 'STRATEGY',
  monitoring: 'MONITORING',
  learning: 'LEARNING',
  chart: 'CHART',
}

export const BlockNode = memo(function BlockNode({
  block,
  selected,
  onSelect,
  onDelete,
  onConfigure,
  onDragStart,
  onConnect,
  allBlocks = [],
}: BlockNodeProps) {
  const Icon = BLOCK_ICONS[block.type] || Zap
  const [isHovering, setIsHovering] = useState(false)
  const [isOutputHovered, setIsOutputHovered] = useState(false)
  const [isInputHovered, setIsInputHovered] = useState(false)
  
  // Get available blocks to connect to (excluding self and already connected)
  const connectableBlocks = allBlocks.filter(b => 
    b.id !== block.id && !block.connections.includes(b.id)
  )

  // Handle quick connect from output port
  const handleOutputClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    if (connectableBlocks.length === 1 && onConnect) {
      onConnect(block.id, connectableBlocks[0].id)
    }
  }, [block.id, connectableBlocks, onConnect])
  
  return (
    <TooltipProvider delayDuration={300}>
      <motion.div
        className={cn(
          'absolute w-52 rounded-lg border-2 p-3 cursor-move backdrop-blur-sm',
          'hover:shadow-lg hover:shadow-black/30',
          BLOCK_COLORS[block.type] || BLOCK_COLORS.transform,
          selected && 'ring-2 ring-white/50 shadow-xl'
        )}
        style={{
          left: block.position.x,
          top: block.position.y,
        }}
        draggable
        onDragStart={(e) => onDragStart(e, block.id)}
        onClick={(e) => {
          e.stopPropagation()
          onSelect(block.id)
        }}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
        whileHover={{ scale: 1.02 }}
        transition={{ duration: 0.15 }}
      >
        {/* Drag handle indicator */}
        <div className={cn(
          "absolute -top-1 left-1/2 -translate-x-1/2 opacity-0 transition-opacity",
          isHovering && "opacity-100"
        )}>
          <GripVertical className="w-4 h-4 text-gray-500" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className={cn(
              'p-1.5 rounded-md bg-black/30', 
              BLOCK_ICON_COLORS[block.type] || BLOCK_ICON_COLORS.transform
            )}>
              <Icon className="w-4 h-4" />
            </div>
            <span className="text-[10px] font-medium uppercase tracking-wider text-gray-400">
              {BLOCK_CATEGORY[block.type] || block.type}
            </span>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-6 w-6 hover:bg-white/10" 
                onClick={(e) => e.stopPropagation()}
              >
                <MoreVertical className="h-3 w-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="bg-gray-900 border-gray-700 min-w-[160px]">
              <DropdownMenuItem 
                onClick={() => onConfigure(block.id)} 
                className="cursor-pointer"
              >
                <Settings className="h-4 w-4 mr-2" />
                Configure
              </DropdownMenuItem>
              
              {connectableBlocks.length > 0 && onConnect && (
                <>
                  <DropdownMenuSeparator className="bg-gray-700" />
                  <DropdownMenuLabel className="text-xs text-gray-500">Connect to</DropdownMenuLabel>
                  {connectableBlocks.slice(0, 5).map(b => (
                    <DropdownMenuItem 
                      key={b.id}
                      onClick={() => onConnect(block.id, b.id)} 
                      className="cursor-pointer text-xs"
                    >
                      <Link2 className="h-3 w-3 mr-2" />
                      {b.name}
                    </DropdownMenuItem>
                  ))}
                  {connectableBlocks.length > 5 && (
                    <DropdownMenuItem disabled className="text-xs text-gray-500">
                      +{connectableBlocks.length - 5} more...
                    </DropdownMenuItem>
                  )}
                </>
              )}
              
              <DropdownMenuSeparator className="bg-gray-700" />
              <DropdownMenuItem 
                onClick={() => onDelete(block.id)} 
                className="text-red-400 cursor-pointer"
              >
                Delete Block
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        
        {/* Name */}
        <h4 className="text-sm font-semibold text-white truncate">{block.name}</h4>
        
        {/* Config preview */}
        {Object.keys(block.config).length > 0 && (
          <div className="mt-2 space-y-1">
            {Object.entries(block.config).slice(0, 2).map(([key, value]) => (
              <div key={key} className="flex items-center gap-1 text-xs text-gray-400">
                <span className="truncate">{key}:</span>
                <span className="text-gray-300 truncate">
                  {typeof value === 'object' 
                    ? JSON.stringify(value).slice(0, 15) + '...'
                    : String(value).slice(0, 12)}
                </span>
              </div>
            ))}
            {Object.keys(block.config).length > 2 && (
              <div className="text-[10px] text-gray-500">
                +{Object.keys(block.config).length - 2} more
              </div>
            )}
          </div>
        )}
        
        {/* Connection indicators */}
        {block.connections.length > 0 && (
          <div className="mt-2 pt-2 border-t border-white/10">
            <div className="text-[10px] text-gray-500 flex items-center gap-1">
              <Play className="w-3 h-3 fill-current" />
              {block.connections.length} output{block.connections.length !== 1 ? 's' : ''}
            </div>
          </div>
        )}
        
        {/* Connection points - input (left) */}
        <Tooltip>
          <TooltipTrigger asChild>
            <motion.div 
              className={cn(
                "absolute -left-3 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full",
                "bg-gray-900 border-2 cursor-pointer z-10",
                "flex items-center justify-center",
                isInputHovered 
                  ? "border-blue-400 shadow-lg shadow-blue-500/30" 
                  : "border-gray-600 hover:border-blue-400"
              )}
              onMouseEnter={() => setIsInputHovered(true)}
              onMouseLeave={() => setIsInputHovered(false)}
              whileHover={{ scale: 1.3 }}
              transition={{ duration: 0.15 }}
            >
              <div className={cn(
                "w-2 h-2 rounded-full transition-colors",
                isInputHovered ? "bg-blue-400" : "bg-gray-600"
              )} />
            </motion.div>
          </TooltipTrigger>
          <TooltipContent side="left" className="bg-gray-900 border-gray-700">
            <p className="text-xs">Input - receives data</p>
          </TooltipContent>
        </Tooltip>
        
        {/* Connection points - output (right) */}
        <Tooltip>
          <TooltipTrigger asChild>
            <motion.div 
              className={cn(
                "absolute -right-3 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full",
                "bg-gray-900 border-2 cursor-pointer z-10",
                "flex items-center justify-center",
                isOutputHovered 
                  ? "border-emerald-400 shadow-lg shadow-emerald-500/30" 
                  : "border-emerald-500/60 hover:border-emerald-400"
              )}
              onMouseEnter={() => setIsOutputHovered(true)}
              onMouseLeave={() => setIsOutputHovered(false)}
              onClick={handleOutputClick}
              whileHover={{ scale: 1.3 }}
              transition={{ duration: 0.15 }}
            >
              <motion.div 
                className={cn(
                  "w-2 h-2 rounded-full",
                  isOutputHovered ? "bg-emerald-400" : "bg-emerald-500/60"
                )}
                animate={isOutputHovered ? { scale: [1, 1.2, 1] } : {}}
                transition={{ duration: 0.5, repeat: Infinity }}
              />
            </motion.div>
          </TooltipTrigger>
          <TooltipContent side="right" className="bg-gray-900 border-gray-700">
            <p className="text-xs">
              {connectableBlocks.length === 1 
                ? `Click to connect to ${connectableBlocks[0].name}` 
                : `Output - ${connectableBlocks.length} available connections`}
            </p>
          </TooltipContent>
        </Tooltip>

        {/* Pulse animation when selected */}
        {selected && (
          <motion.div
            className="absolute inset-0 rounded-lg border-2 border-white/30 pointer-events-none"
            initial={{ scale: 1, opacity: 0.5 }}
            animate={{ scale: 1.05, opacity: 0 }}
            transition={{ duration: 1, repeat: Infinity }}
          />
        )}
      </motion.div>
    </TooltipProvider>
  )
})

export default BlockNode
