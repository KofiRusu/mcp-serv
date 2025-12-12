'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { BlockNode, Block, BlockType } from './block-node'
import { 
  Plus, 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  Sparkles,
  MousePointer,
  ArrowRight,
  Layers,
  Database,
  TrendingUp,
  Bell,
  Shield,
  FileOutput,
  ImageIcon,
  Upload,
  Play,
  Square,
  Rocket,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'

export type AutomationType = 
  | 'scraper' 
  | 'trading_bot' 
  | 'alert' 
  | 'signal' 
  | 'risk' 
  | 'backtest'
  | 'architecture'

interface BuilderCanvasProps {
  blocks: Block[]
  onBlocksChange: (blocks: Block[]) => void
  selectedBlockId: string | null
  onSelectBlock: (id: string | null) => void
  onConfigureBlock: (id: string) => void
  automationType?: AutomationType
  onExternalDrop?: (template: BlockTemplate, position: { x: number; y: number }) => void
  onUploadDiagram?: () => void
  onRun?: () => void
  onDeploy?: () => void
  isRunning?: boolean
  status?: string
}

export interface BlockTemplate {
  type: BlockType
  name: string
  defaultConfig: Record<string, any>
  category: 'data' | 'trading' | 'analysis' | 'alert' | 'risk' | 'output'
}

// Expanded block templates for all automation types
export const BLOCK_TEMPLATES: BlockTemplate[] = [
  // === DATA SOURCES ===
  { type: 'source', name: 'Binance WebSocket', defaultConfig: { symbol: 'BTCUSDT', stream: 'btcusdt@aggTrade' }, category: 'data' },
  { type: 'source', name: 'Binance REST', defaultConfig: { symbol: 'BTC/USDT', endpoint: 'ticker' }, category: 'data' },
  { type: 'source', name: 'CoinGecko API', defaultConfig: { coins: ['bitcoin'], interval: 60 }, category: 'data' },
  { type: 'source', name: 'Custom REST API', defaultConfig: { url: '', interval: 60 }, category: 'data' },
  { type: 'source', name: 'Historical Data', defaultConfig: { file: '', symbol: 'BTC/USDT' }, category: 'data' },
  { type: 'source', name: 'Portfolio Feed', defaultConfig: { exchange: 'binance' }, category: 'data' },
  
  // === ANALYSIS & INDICATORS ===
  { type: 'indicator', name: 'RSI', defaultConfig: { period: 14, overbought: 70, oversold: 30 }, category: 'analysis' },
  { type: 'indicator', name: 'MACD', defaultConfig: { fast: 12, slow: 26, signal: 9 }, category: 'analysis' },
  { type: 'indicator', name: 'Moving Average', defaultConfig: { period: 20, type: 'SMA' }, category: 'analysis' },
  { type: 'indicator', name: 'Bollinger Bands', defaultConfig: { period: 20, stdDev: 2 }, category: 'analysis' },
  { type: 'indicator', name: 'Volume Profile', defaultConfig: { rows: 24 }, category: 'analysis' },
  { type: 'indicator', name: 'Momentum', defaultConfig: { period: 20 }, category: 'analysis' },
  
  // === TRANSFORMS ===
  { type: 'transform', name: 'Filter', defaultConfig: { condition: '' }, category: 'analysis' },
  { type: 'aggregate', name: 'Aggregate', defaultConfig: { window: '1m' }, category: 'analysis' },
  { type: 'aggregate', name: 'Confluence Score', defaultConfig: { weights: {} }, category: 'analysis' },
  { type: 'filter', name: 'Volume Filter', defaultConfig: { minVolume: 1000 }, category: 'analysis' },
  
  // === TRADING ===
  { type: 'entry', name: 'Entry Signal', defaultConfig: { type: 'market' }, category: 'trading' },
  { type: 'exit', name: 'Exit Signal', defaultConfig: { type: 'market' }, category: 'trading' },
  { type: 'order', name: 'Market Order', defaultConfig: { exchange: 'binance', side: 'buy' }, category: 'trading' },
  { type: 'order', name: 'Limit Order', defaultConfig: { exchange: 'binance', side: 'buy', price: 0 }, category: 'trading' },
  { type: 'position', name: 'Position Manager', defaultConfig: { maxPosition: 1 }, category: 'trading' },
  
  // === RISK MANAGEMENT ===
  { type: 'risk_check', name: 'Risk Check', defaultConfig: { maxDrawdown: 10 }, category: 'risk' },
  { type: 'position_size', name: 'Position Sizer', defaultConfig: { method: 'fixed', risk: 1 }, category: 'risk' },
  { type: 'stop_loss', name: 'Stop Loss', defaultConfig: { type: 'percent', value: 2 }, category: 'risk' },
  { type: 'take_profit', name: 'Take Profit', defaultConfig: { type: 'percent', value: 4 }, category: 'risk' },
  
  // === CONDITIONS ===
  { type: 'condition', name: 'Price Condition', defaultConfig: { above: 0, below: 0 }, category: 'alert' },
  { type: 'condition', name: 'If/Else', defaultConfig: { condition: '' }, category: 'alert' },
  { type: 'condition', name: 'Time Filter', defaultConfig: { startHour: 9, endHour: 17 }, category: 'alert' },
  
  // === ALERTS ===
  { type: 'notification', name: 'Send Alert', defaultConfig: { type: 'console' }, category: 'alert' },
  { type: 'webhook', name: 'Webhook', defaultConfig: { url: '' }, category: 'alert' },
  { type: 'notification', name: 'Discord Alert', defaultConfig: { webhookUrl: '' }, category: 'alert' },
  { type: 'notification', name: 'Telegram Alert', defaultConfig: { botToken: '', chatId: '' }, category: 'alert' },
  
  // === OUTPUTS ===
  { type: 'output', name: 'JSON File', defaultConfig: { output_dir: '/app/data' }, category: 'output' },
  { type: 'output', name: 'Database', defaultConfig: { connectionString: '' }, category: 'output' },
  { type: 'output', name: 'WebSocket Broadcast', defaultConfig: { port: 8080 }, category: 'output' },
  { type: 'signal', name: 'Signal Output', defaultConfig: {}, category: 'output' },
]

const CATEGORY_INFO: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  data: { label: 'Data Sources', icon: Database, color: 'text-blue-400' },
  analysis: { label: 'Analysis & Indicators', icon: TrendingUp, color: 'text-indigo-400' },
  trading: { label: 'Trading', icon: Layers, color: 'text-cyan-400' },
  risk: { label: 'Risk Management', icon: Shield, color: 'text-red-400' },
  alert: { label: 'Conditions & Alerts', icon: Bell, color: 'text-yellow-400' },
  output: { label: 'Outputs', icon: FileOutput, color: 'text-green-400' },
}

// Starter templates for quick start
const STARTER_TEMPLATES = {
  scraper: {
    title: 'Data Scraper',
    description: 'Fetch and process market data',
    blocks: [
      { type: 'source', name: 'Binance WebSocket', x: 100, y: 150 },
      { type: 'transform', name: 'Filter', x: 350, y: 150 },
      { type: 'output', name: 'JSON File', x: 600, y: 150 },
    ],
  },
  trading_bot: {
    title: 'Trading Bot',
    description: 'Build an automated trading strategy',
    blocks: [
      { type: 'source', name: 'Binance WebSocket', x: 100, y: 100 },
      { type: 'indicator', name: 'RSI', x: 350, y: 100 },
      { type: 'entry', name: 'Entry Signal', x: 600, y: 100 },
      { type: 'risk_check', name: 'Risk Check', x: 600, y: 250 },
      { type: 'order', name: 'Market Order', x: 850, y: 175 },
    ],
  },
  alert: {
    title: 'Alert System',
    description: 'Monitor conditions and send notifications',
    blocks: [
      { type: 'source', name: 'Binance REST', x: 100, y: 150 },
      { type: 'condition', name: 'Price Condition', x: 350, y: 150 },
      { type: 'notification', name: 'Discord Alert', x: 600, y: 150 },
    ],
  },
  signal: {
    title: 'Signal Generator',
    description: 'Generate trading signals based on analysis',
    blocks: [
      { type: 'source', name: 'Binance WebSocket', x: 100, y: 150 },
      { type: 'indicator', name: 'MACD', x: 350, y: 100 },
      { type: 'indicator', name: 'RSI', x: 350, y: 220 },
      { type: 'signal', name: 'Signal Output', x: 600, y: 160 },
    ],
  },
  risk: {
    title: 'Risk Monitor',
    description: 'Monitor portfolio and manage risk',
    blocks: [
      { type: 'source', name: 'Portfolio Feed', x: 100, y: 150 },
      { type: 'risk_check', name: 'Risk Check', x: 350, y: 150 },
      { type: 'notification', name: 'Send Alert', x: 600, y: 150 },
    ],
  },
  backtest: {
    title: 'Backtest Runner',
    description: 'Test strategies on historical data',
    blocks: [
      { type: 'source', name: 'Historical Data', x: 100, y: 150 },
      { type: 'indicator', name: 'Moving Average', x: 350, y: 100 },
      { type: 'entry', name: 'Entry Signal', x: 350, y: 220 },
      { type: 'output', name: 'JSON File', x: 600, y: 160 },
    ],
  },
}

export function BuilderCanvas({
  blocks,
  onBlocksChange,
  selectedBlockId,
  onSelectBlock,
  onConfigureBlock,
  onRun,
  onDeploy,
  isRunning = false,
  status = 'draft',
  automationType = 'scraper',
  onExternalDrop,
  onUploadDiagram,
}: BuilderCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [draggedBlockId, setDraggedBlockId] = useState<string | null>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [isDraggingOver, setIsDraggingOver] = useState(false)
  const [dropPosition, setDropPosition] = useState<{ x: number; y: number } | null>(null)
  const [showConnectionHint, setShowConnectionHint] = useState<string | null>(null)
  const [showStarterOptions, setShowStarterOptions] = useState(true)
  const [addBlockDropdownOpen, setAddBlockDropdownOpen] = useState(false)

  // Hide starter options when blocks exist
  useEffect(() => {
    if (blocks.length > 0) {
      setShowStarterOptions(false)
    }
  }, [blocks.length])

  // Handle block drag start
  const handleDragStart = useCallback((e: React.DragEvent, blockId: string) => {
    const block = blocks.find(b => b.id === blockId)
    if (!block) return
    
    const rect = (e.target as HTMLElement).getBoundingClientRect()
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    })
    setDraggedBlockId(blockId)
    e.dataTransfer.effectAllowed = 'move'
  }, [blocks])

  // Handle drag over with visual feedback
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setIsDraggingOver(true)
    
    if (canvasRef.current) {
      const canvasRect = canvasRef.current.getBoundingClientRect()
      const x = (e.clientX - canvasRect.left - pan.x) / zoom
      const y = (e.clientY - canvasRect.top - pan.y) / zoom
      setDropPosition({ x, y })
    }
  }, [pan, zoom])

  const handleDragLeave = useCallback(() => {
    setIsDraggingOver(false)
    setDropPosition(null)
  }, [])

  // Handle drop on canvas
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDraggingOver(false)
    setDropPosition(null)

    if (!canvasRef.current) return

    const canvasRect = canvasRef.current.getBoundingClientRect()
    const x = (e.clientX - canvasRect.left - pan.x) / zoom
    const y = (e.clientY - canvasRect.top - pan.y) / zoom

    // Check for palette drag data
    const templateData = e.dataTransfer.getData('application/json')
    if (templateData) {
      try {
        const template = JSON.parse(templateData) as BlockTemplate
        const newBlock: Block = {
          id: `block-${Date.now()}`,
          type: template.type,
          name: template.name,
          config: { ...template.defaultConfig },
          position: { x: Math.max(50, x - 96), y: Math.max(50, y - 40) },
          connections: [],
        }
        onBlocksChange([...blocks, newBlock])
        
        // Auto-connect to previous block if nearby
        const nearbyBlock = blocks.find(b => {
          const dist = Math.sqrt(
            Math.pow(b.position.x + 192 - newBlock.position.x, 2) +
            Math.pow(b.position.y + 40 - newBlock.position.y, 2)
          )
          return dist < 150
        })
        if (nearbyBlock) {
          setTimeout(() => {
            onBlocksChange(prev => prev.map(b =>
              b.id === nearbyBlock.id
                ? { ...b, connections: [...b.connections, newBlock.id] }
                : b
            ))
          }, 50)
        }
        return
      } catch (err) {
        // Not palette data
      }
    }

    // Handle internal block drag
    if (draggedBlockId) {
      onBlocksChange(
        blocks.map(b =>
          b.id === draggedBlockId
            ? { ...b, position: { x: Math.max(0, x - dragOffset.x), y: Math.max(0, y - dragOffset.y) } }
            : b
        )
      )
      setDraggedBlockId(null)
    }
  }, [draggedBlockId, blocks, pan, zoom, dragOffset, onBlocksChange])

  // Add new block
  const addBlock = useCallback((template: BlockTemplate) => {
    const newBlock: Block = {
      id: `block-${Date.now()}`,
      type: template.type,
      name: template.name,
      config: { ...template.defaultConfig },
      position: { x: 100 + blocks.length * 50, y: 100 + blocks.length * 30 },
      connections: [],
    }
    onBlocksChange([...blocks, newBlock])
  }, [blocks, onBlocksChange])

  // Load starter template
  const loadStarterTemplate = useCallback((type: AutomationType) => {
    const template = STARTER_TEMPLATES[type]
    if (!template) return

    const newBlocks: Block[] = template.blocks.map((b, idx) => {
      const fullTemplate = BLOCK_TEMPLATES.find(t => t.type === b.type && t.name === b.name)
      return {
        id: `block-${Date.now()}-${idx}`,
        type: b.type as BlockType,
        name: b.name,
        config: fullTemplate?.defaultConfig || {},
        position: { x: b.x, y: b.y },
        connections: [],
      }
    })

    // Auto-connect sequential blocks
    const connectedBlocks = newBlocks.map((block, idx) => {
      if (idx < newBlocks.length - 1) {
        return { ...block, connections: [newBlocks[idx + 1].id] }
      }
      return block
    })

    onBlocksChange(connectedBlocks)
    setShowStarterOptions(false)
  }, [onBlocksChange])

  // Delete block
  const deleteBlock = useCallback((id: string) => {
    onBlocksChange(
      blocks
        .filter(b => b.id !== id)
        .map(b => ({
          ...b,
          connections: b.connections.filter(c => c !== id)
        }))
    )
    if (selectedBlockId === id) {
      onSelectBlock(null)
    }
  }, [blocks, selectedBlockId, onBlocksChange, onSelectBlock])

  // Connect two blocks
  const connectBlocks = useCallback((fromId: string, toId: string) => {
    onBlocksChange(
      blocks.map(b =>
        b.id === fromId && !b.connections.includes(toId)
          ? { ...b, connections: [...b.connections, toId] }
          : b
      )
    )
  }, [blocks, onBlocksChange])

  // Draw connections with animations
  const renderConnections = () => {
    const lines: JSX.Element[] = []
    
    blocks.forEach(block => {
      // Guard against undefined connections
      const connections = block.connections || []
      connections.forEach(targetId => {
        const target = blocks.find(b => b.id === targetId)
        if (!target) return
        
        const startX = block.position.x + 192
        const startY = block.position.y + 40
        const endX = target.position.x
        const endY = target.position.y + 40
        
        const midX = (startX + endX) / 2
        const isHighlighted = selectedBlockId === block.id || selectedBlockId === targetId
        
        lines.push(
          <g key={`${block.id}-${targetId}`}>
            <motion.path
              d={`M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`}
              stroke={isHighlighted ? 'rgba(16, 185, 129, 0.8)' : 'rgba(16, 185, 129, 0.4)'}
              strokeWidth={isHighlighted ? '3' : '2'}
              fill="none"
              markerEnd="url(#arrowhead)"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
            {/* Animated flow dots */}
            <motion.circle
              r="4"
              fill="rgba(16, 185, 129, 0.8)"
              initial={{ offsetDistance: '0%' }}
              animate={{ offsetDistance: '100%' }}
              transition={{ 
                duration: 2, 
                repeat: Infinity, 
                ease: 'linear',
              }}
              style={{
                offsetPath: `path("M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}")`,
              }}
            />
          </g>
        )
      })
    })
    
    return (
      <svg
        className="absolute inset-0 pointer-events-none"
        style={{ width: '100%', height: '100%' }}
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon
              points="0 0, 10 3.5, 0 7"
              fill="rgba(16, 185, 129, 0.6)"
            />
          </marker>
          <linearGradient id="dropZoneGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(16, 185, 129, 0.1)" />
            <stop offset="100%" stopColor="rgba(59, 130, 246, 0.1)" />
          </linearGradient>
        </defs>
        {lines}
      </svg>
    )
  }

  // Get relevant templates based on automation type
  const getRelevantCategories = () => {
    switch (automationType) {
      case 'scraper':
        return ['data', 'analysis', 'output']
      case 'trading_bot':
        return ['data', 'analysis', 'trading', 'risk', 'output']
      case 'alert':
        return ['data', 'analysis', 'alert', 'output']
      case 'signal':
        return ['data', 'analysis', 'output']
      case 'risk':
        return ['data', 'risk', 'alert', 'output']
      case 'backtest':
        return ['data', 'analysis', 'trading', 'output']
      default:
        return ['data', 'analysis', 'trading', 'risk', 'alert', 'output']
    }
  }

  const relevantCategories = getRelevantCategories()
  const categories = [...new Set(BLOCK_TEMPLATES.map(t => t.category))]
    .filter(c => relevantCategories.includes(c))

  return (
    <div className="relative flex-1 bg-[#0a0a0f] overflow-hidden">
      {/* Run/Deploy buttons - top right */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-2">
        {onRun && (
          status === 'running' || status === 'testing' ? (
            <Button
              size="sm"
              variant="destructive"
              onClick={onRun}
              className="gap-2 shadow-lg"
            >
              <Square className="h-4 w-4" />
              Stop
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={onRun}
              disabled={isRunning}
              className="gap-2 bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-500/20"
            >
              {isRunning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Run
            </Button>
          )
        )}
        {onDeploy && (
          <Button
            size="sm"
            onClick={onDeploy}
            disabled={status === 'deployed'}
            className="gap-2 bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-500/20"
          >
            <Rocket className="h-4 w-4" />
            Deploy
          </Button>
        )}
      </div>
      
      {/* Add Block toolbar */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <DropdownMenu open={addBlockDropdownOpen} onOpenChange={setAddBlockDropdownOpen}>
          <DropdownMenuTrigger asChild>
            <Button 
              size="sm" 
              className="gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-lg shadow-emerald-500/20"
              data-tour="add-block"
              aria-haspopup="menu"
              aria-expanded={addBlockDropdownOpen}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  setAddBlockDropdownOpen(!addBlockDropdownOpen)
                }
              }}
            >
              <Plus className={cn(
                "w-4 h-4 transition-transform duration-200",
                addBlockDropdownOpen ? "rotate-45" : ""
              )} />
              Add Block
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="bg-gray-900/95 backdrop-blur-sm border-gray-700 w-56 max-h-[70vh] overflow-y-auto" role="menu">
            {categories.map((category, idx) => {
              const CategoryIcon = CATEGORY_INFO[category]?.icon || Layers
              return (
                <div key={category}>
                  {idx > 0 && <DropdownMenuSeparator className="bg-gray-700" />}
                  <DropdownMenuLabel className={cn(
                    "text-xs flex items-center gap-2",
                    CATEGORY_INFO[category]?.color || 'text-gray-400'
                  )}>
                    <CategoryIcon className="w-3 h-3" />
                    {CATEGORY_INFO[category]?.label || category}
                  </DropdownMenuLabel>
                  {BLOCK_TEMPLATES.filter(t => t.category === category).map(t => (
                    <DropdownMenuItem 
                      key={`${t.type}-${t.name}`} 
                      onClick={() => {
                        addBlock(t)
                        setAddBlockDropdownOpen(false)
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          addBlock(t)
                          setAddBlockDropdownOpen(false)
                        }
                      }}
                      className="cursor-pointer hover:bg-gray-800 focus:bg-gray-800 focus:outline-none text-gray-300"
                      role="menuitem"
                      tabIndex={0}
                    >
                      {t.name}
                    </DropdownMenuItem>
                  ))}
                </div>
              )
            })}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Type indicator */}
        <div className="px-3 py-1.5 bg-gray-800/80 rounded-md text-xs text-gray-400 font-medium">
          {automationType.replace('_', ' ').toUpperCase()}
        </div>
      </div>

      {/* Zoom controls */}
      <div className="absolute bottom-3 right-3 z-10 flex items-center gap-1 bg-gray-900/90 backdrop-blur-sm rounded-lg p-1 border border-gray-800">
        <Button
          size="icon"
          variant="ghost"
          className="h-8 w-8"
          onClick={() => setZoom(z => Math.max(0.25, z - 0.25))}
        >
          <ZoomOut className="h-4 w-4" />
        </Button>
        <span className="text-xs text-gray-400 w-12 text-center">{Math.round(zoom * 100)}%</span>
        <Button
          size="icon"
          variant="ghost"
          className="h-8 w-8"
          onClick={() => setZoom(z => Math.min(2, z + 0.25))}
        >
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button
          size="icon"
          variant="ghost"
          className="h-8 w-8"
          onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}
        >
          <Maximize2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Canvas */}
      <div
        ref={canvasRef}
        className={cn(
          "w-full h-full transition-colors duration-200",
          isDraggingOver && "bg-emerald-900/10"
        )}
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: `${20 * zoom}px ${20 * zoom}px`,
          backgroundPosition: `${pan.x}px ${pan.y}px`,
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => onSelectBlock(null)}
        data-tour="canvas"
      >
        {/* Drop zone indicator */}
        <AnimatePresence>
          {isDraggingOver && dropPosition && (
            <motion.div
              className="absolute pointer-events-none"
              style={{
                left: dropPosition.x * zoom + pan.x - 50,
                top: dropPosition.y * zoom + pan.y - 30,
              }}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
            >
              <div className="w-[200px] h-[80px] border-2 border-dashed border-emerald-500/50 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <span className="text-emerald-400 text-sm font-medium">Drop here</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div
          className="relative"
          style={{
            transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
            transformOrigin: '0 0',
            width: '3000px',
            height: '2000px',
          }}
        >
          {renderConnections()}
          
          {/* Block nodes with staggered animations - z-10 to render above empty state */}
          <div className="relative z-10">
            {blocks.map((block, index) => (
              <motion.div
                key={block.id}
                initial={{ opacity: 0, scale: 0.8, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ 
                  duration: 0.3, 
                  delay: index * 0.05,
                  ease: 'easeOut' 
                }}
              >
                <BlockNode
                  block={block}
                  selected={selectedBlockId === block.id}
                  onSelect={onSelectBlock}
                  onDelete={deleteBlock}
                  onConfigure={onConfigureBlock}
                  onDragStart={handleDragStart}
                  onConnect={connectBlocks}
                  allBlocks={blocks}
                />
              </motion.div>
            ))}
          </div>

          {/* Enhanced Empty state with starter templates - z-0 so blocks render above */}
          <AnimatePresence>
            {blocks.length === 0 && showStarterOptions && (
              <motion.div 
                className="absolute inset-0 flex items-center justify-center z-0"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <div className="text-center max-w-2xl">
                  {/* Main heading */}
                  <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="mb-8"
                  >
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 text-emerald-400 text-sm mb-4">
                      <Sparkles className="w-4 h-4" />
                      <span>Let&apos;s build something awesome</span>
                    </div>
                    <h2 className="text-2xl font-semibold text-gray-200 mb-2">
                      Start Building Your {STARTER_TEMPLATES[automationType]?.title || 'Automation'}
                    </h2>
                    <p className="text-gray-500">
                      {STARTER_TEMPLATES[automationType]?.description || 'Create powerful automations with no code'}
                    </p>
                  </motion.div>

                  {/* Quick start options */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="grid grid-cols-2 gap-4 mb-6"
                  >
                    {/* Use template */}
                    <button
                      onClick={() => loadStarterTemplate(automationType)}
                      className="group p-6 rounded-xl border border-gray-700 bg-gray-900/50 hover:bg-gray-800/50 hover:border-emerald-500/50 transition-all text-left"
                    >
                      <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20 transition-colors">
                          <Layers className="w-5 h-5" />
                        </div>
                        <span className="font-medium text-gray-200">Use Template</span>
                      </div>
                      <p className="text-sm text-gray-500">
                        Start with a pre-built template for {automationType.replace('_', ' ')}
                      </p>
                    </button>

                    {/* Start from scratch */}
                    <button
                      onClick={() => {
                        setShowStarterOptions(false)
                        addBlock(BLOCK_TEMPLATES[0])
                      }}
                      className="group p-6 rounded-xl border border-gray-700 bg-gray-900/50 hover:bg-gray-800/50 hover:border-blue-500/50 transition-all text-left"
                    >
                      <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 group-hover:bg-blue-500/20 transition-colors">
                          <Plus className="w-5 h-5" />
                        </div>
                        <span className="font-medium text-gray-200">Start Fresh</span>
                      </div>
                      <p className="text-sm text-gray-500">
                        Build your automation from scratch
                      </p>
                    </button>

                    {/* Upload Diagram - fallback for dropdown issues */}
                    {onUploadDiagram && (
                      <button
                        onClick={onUploadDiagram}
                        className="group p-6 rounded-xl border border-gray-700 bg-gray-900/50 hover:bg-gray-800/50 hover:border-purple-500/50 transition-all text-left col-span-2"
                      >
                        <div className="flex items-center gap-3 mb-3">
                          <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 group-hover:bg-purple-500/20 transition-colors">
                            <ImageIcon className="w-5 h-5" />
                          </div>
                          <span className="font-medium text-gray-200">Upload Architecture Diagram</span>
                          <span className="text-xs bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full">AI Vision</span>
                        </div>
                        <p className="text-sm text-gray-500">
                          Upload a system diagram and let AI automatically build all blocks
                        </p>
                      </button>
                    )}
                  </motion.div>

                  {/* Flow explanation */}
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="flex items-center justify-center gap-3 text-sm text-gray-500"
                  >
                    <div className="flex items-center gap-2">
                      <Database className="w-4 h-4 text-blue-400" />
                      <span>Data</span>
                    </div>
                    <ArrowRight className="w-4 h-4" />
                    <div className="flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-indigo-400" />
                      <span>Process</span>
                    </div>
                    <ArrowRight className="w-4 h-4" />
                    <div className="flex items-center gap-2">
                      <FileOutput className="w-4 h-4 text-green-400" />
                      <span>Output</span>
                    </div>
                  </motion.div>

                  {/* Hint */}
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.6 }}
                    className="mt-6 text-xs text-gray-600 flex items-center justify-center gap-2"
                  >
                    <MousePointer className="w-3 h-3" />
                    Drag blocks from the palette or describe what you want to the AI
                  </motion.p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Simple empty state when user dismissed starter but no blocks - z-0 */}
          {blocks.length === 0 && !showStarterOptions && (
            <div className="absolute inset-0 flex items-center justify-center z-0">
              <div className="text-center text-gray-500 p-8 rounded-xl border border-dashed border-gray-700 bg-gray-900/30">
                <p className="text-lg mb-2">Canvas is empty</p>
                <p className="text-sm mb-4">
                  Add blocks or describe what you want to build
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  <Button 
                    onClick={() => setShowStarterOptions(true)} 
                    variant="outline"
                    className="border-gray-600"
                  >
                    Show Templates
                  </Button>
                  <Button 
                    onClick={() => addBlock(BLOCK_TEMPLATES[0])} 
                    className="bg-emerald-600 hover:bg-emerald-500"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Block
                  </Button>
                  {onUploadDiagram && (
                    <Button 
                      onClick={onUploadDiagram}
                      className="bg-purple-600 hover:bg-purple-500"
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      Upload Diagram
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default BuilderCanvas
