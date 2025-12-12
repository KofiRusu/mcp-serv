'use client'

import { useState, useCallback, useEffect } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { 
  Save, 
  Loader2,
  ChevronLeft,
  Sparkles,
  List,
  Play,
  Square,
  Rocket,
  Code,
  AlertTriangle,
  LayoutGrid,
  MessageSquare,
  Wand2,
  PanelLeftClose,
  PanelLeft,
  HelpCircle,
} from 'lucide-react'
import { 
  BuilderCanvas, 
  AIBuilderChat, 
  BlockPalette,
  OnboardingTour,
  GuidedBuilder,
  ActivityIndicator,
} from '@/components/automation-builder'
import type { Block } from '@/components/automation-builder/block-node'
import type { AutomationType } from '@/components/automation-builder/builder-canvas'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { motion, AnimatePresence } from 'framer-motion'

interface Automation {
  id: string
  name: string
  description: string
  type: AutomationType
  deployment_type: string
  status: 'draft' | 'testing' | 'running' | 'deployed' | 'stopped' | 'error' | 'paused'
  blocks: Block[]
  config: Record<string, any>
  generated_code: string | null
  paper_trading?: boolean
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-500',
  testing: 'bg-yellow-500',
  running: 'bg-blue-500',
  deployed: 'bg-green-500',
  stopped: 'bg-gray-500',
  error: 'bg-red-500',
  paused: 'bg-orange-500',
}

type BuilderMode = 'ai' | 'manual' | 'guided'

export default function AutomationBuilderPage() {
  const [automation, setAutomation] = useState<Automation | null>(null)
  const [blocks, setBlocks] = useState<Block[]>([])
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null)
  const [automationName, setAutomationName] = useState('New Automation')
  const [automationType, setAutomationType] = useState<AutomationType>('scraper')
  const [generatedCode, setGeneratedCode] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [showConfigDialog, setShowConfigDialog] = useState(false)
  const [configBlockId, setConfigBlockId] = useState<string | null>(null)
  const [status, setStatus] = useState<Automation['status']>('draft')
  const [paperTrading, setPaperTrading] = useState(true)
  const [showCodeDialog, setShowCodeDialog] = useState(false)
  const [output, setOutput] = useState<string[]>([])
  
  // New UX states
  const [builderMode, setBuilderMode] = useState<BuilderMode>('ai')
  const [showBlockPalette, setShowBlockPalette] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [isFirstVisit, setIsFirstVisit] = useState(false)
  const [activity, setActivity] = useState<{ type: 'success' | 'error' | 'info' | 'loading'; message: string } | null>(null)
  const [triggerDiagramUpload, setTriggerDiagramUpload] = useState(false)

  // Check for first visit
  useEffect(() => {
    const hasVisited = localStorage.getItem('automation-builder-visited')
    if (!hasVisited) {
      setIsFirstVisit(true)
      setShowOnboarding(true)
      localStorage.setItem('automation-builder-visited', 'true')
    }
  }, [])

  // Load automation from URL if ID provided
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const id = params.get('id')
    if (id) {
      loadAutomation(id)
    }
  }, [])

  const showActivity = useCallback((type: 'success' | 'error' | 'info' | 'loading', message: string) => {
    setActivity({ type, message })
    if (type !== 'loading') {
      setTimeout(() => setActivity(null), 3000)
    }
  }, [])

  // Function to poll logs for a running automation
  const startLogPolling = useCallback((automationId: string) => {
    const pollLogs = async () => {
      try {
        const logsRes = await fetch(`http://localhost:8000/api/v1/automations/${automationId}`)
        if (logsRes.ok) {
          const data = await logsRes.json()
          setOutput(data.logs || [])
          setStatus(data.status)
          
          if (data.status === 'running' || data.status === 'testing') {
            setTimeout(pollLogs, 2000)
          } else {
            setIsRunning(false)
          }
        }
      } catch (e) {
        console.debug('Log polling error:', e)
      }
    }
    pollLogs()
  }, [])

  // Handler for upload diagram button from canvas
  const handleUploadDiagramFromCanvas = useCallback(() => {
    // Switch to AI mode if not already there
    setBuilderMode('ai')
    // Set the automation type to architecture (from diagram)
    setAutomationType('architecture')
    // Trigger the upload dialog in AIBuilderChat
    setTriggerDiagramUpload(true)
    // Reset after a brief moment to allow the trigger
    setTimeout(() => setTriggerDiagramUpload(false), 100)
    showActivity('info', 'Upload an architecture diagram to build automation')
  }, [showActivity])

  const loadAutomation = async (id: string) => {
    try {
      showActivity('loading', 'Loading automation...')
      
      // Try backend first
      let data = null
      try {
        const res = await fetch(`http://localhost:8000/api/v1/automations/${id}`)
        if (res.ok) {
          data = await res.json()
        }
      } catch (e) {
        console.debug('Backend unavailable, trying localStorage:', e)
      }
      
      // Fallback to localStorage if backend fails
      if (!data) {
        const storedAutomations = JSON.parse(localStorage.getItem('local-automations') || '[]')
        data = storedAutomations.find((a: any) => a.id === id)
      }
      
      if (data) {
        console.log('Loaded automation data:', data)
        console.log('Blocks to load:', data.blocks?.length || 0, data.blocks)
        setAutomation(data)
        setBlocks(data.blocks || [])
        setAutomationName(data.name)
        setAutomationType(data.type || 'scraper')
        setGeneratedCode(data.generated_code)
        setStatus(data.status)
        setPaperTrading(data.paper_trading ?? true)
        
        // Load existing logs
        if (data.logs && data.logs.length > 0) {
          setOutput(data.logs)
        }
        
        // If automation is running/testing, start polling for logs
        if (data.status === 'running' || data.status === 'testing') {
          setIsRunning(true)
          startLogPolling(id)
        }
        
        showActivity('success', `Automation loaded with ${data.blocks?.length || 0} blocks!`)
      } else {
        showActivity('error', 'Automation not found')
      }
    } catch (e) {
      console.debug('Failed to load automation:', e)
      showActivity('error', 'Failed to load automation')
    }
  }

  const handleGeneratedAutomation = useCallback((generated: any) => {
    setIsGenerating(true)
    showActivity('loading', 'Applying generated blocks...')
    
    setTimeout(() => {
      setAutomationName(generated.name)
      setGeneratedCode(generated.generated_code)
      setAutomationType(generated.type || automationType)
      setPaperTrading(generated.paper_trading ?? true)
      
      // Convert generated blocks to Block type
      const newBlocks: Block[] = (generated.blocks || []).map((b: any) => ({
        id: b.id || `block-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        type: b.type,
        name: b.name,
        config: b.config || {},
        position: b.position || { x: 100, y: 100 },
        connections: b.connections || []
      }))
      
      setBlocks(newBlocks)
      setIsGenerating(false)
      showActivity('success', `Generated: ${generated.name}`)
      toast.success(`Generated: ${generated.name}`)
    }, 500)
  }, [automationType, showActivity])

  // n8n-style layout constants
  const LAYOUT_CONFIG = {
    nodeWidth: 220,
    nodeHeight: 100,
    horizontalGap: 80,
    verticalGap: 40,
    startX: 100,
    startY: 100,
    maxNodesPerColumn: 4,
  }

  // Category order for n8n-style left-to-right flow
  const CATEGORY_ORDER: Record<string, number> = {
    'source': 0, 'data': 0,
    'indicator': 1, 'transform': 1, 'filter': 1, 'aggregate': 1, 'analysis': 1,
    'agent': 2, 'knowledgebase': 2, 'knowledge': 2,
    'fusion': 3, 'validator': 3,
    'entry': 4, 'exit': 4, 'order': 4, 'position': 4, 'trading': 4,
    'risk_check': 5, 'position_size': 5, 'stop_loss': 5, 'take_profit': 5, 'risk': 5, 'strategy': 5,
    'condition': 6, 'notification': 6, 'webhook': 6, 'alert': 6,
    'output': 7, 'signal': 7, 'monitoring': 7, 'learning': 7, 'chart': 7,
  }

  // Calculate optimal position for a new block (n8n style - left to right flow)
  const calculateBlockPosition = useCallback((blocks: Block[], newBlockType: BlockType): { x: number; y: number } => {
    if (blocks.length === 0) {
      return { x: LAYOUT_CONFIG.startX, y: LAYOUT_CONFIG.startY }
    }

    // Get category/column for new block
    const newColumn = CATEGORY_ORDER[newBlockType] ?? 0

    // Group existing blocks by their column
    const blocksByColumn: Record<number, Block[]> = {}
    blocks.forEach(block => {
      const col = CATEGORY_ORDER[block.type] ?? 0
      if (!blocksByColumn[col]) blocksByColumn[col] = []
      blocksByColumn[col].push(block)
    })

    // Find blocks in the same column
    const sameColumnBlocks = blocksByColumn[newColumn] || []
    
    // Calculate x position based on column
    const x = LAYOUT_CONFIG.startX + newColumn * (LAYOUT_CONFIG.nodeWidth + LAYOUT_CONFIG.horizontalGap)
    
    // Calculate y position - stack vertically within same column
    const y = LAYOUT_CONFIG.startY + sameColumnBlocks.length * (LAYOUT_CONFIG.nodeHeight + LAYOUT_CONFIG.verticalGap)

    return { x, y }
  }, [])

  // Auto-layout all blocks in n8n style (horizontal flow by category)
  const autoLayoutBlocks = useCallback(() => {
    if (blocks.length === 0) return

    // Group blocks by their category/column
    const blocksByColumn: Record<number, Block[]> = {}
    blocks.forEach(block => {
      const col = CATEGORY_ORDER[block.type] ?? 0
      if (!blocksByColumn[col]) blocksByColumn[col] = []
      blocksByColumn[col].push(block)
    })

    // Reposition all blocks
    const repositionedBlocks = blocks.map(block => {
      const col = CATEGORY_ORDER[block.type] ?? 0
      const columnBlocks = blocksByColumn[col]
      const indexInColumn = columnBlocks.findIndex(b => b.id === block.id)
      
      return {
        ...block,
        position: {
          x: LAYOUT_CONFIG.startX + col * (LAYOUT_CONFIG.nodeWidth + LAYOUT_CONFIG.horizontalGap),
          y: LAYOUT_CONFIG.startY + indexInColumn * (LAYOUT_CONFIG.nodeHeight + LAYOUT_CONFIG.verticalGap),
        }
      }
    })

    setBlocks(repositionedBlocks)
    showActivity('success', 'Blocks auto-arranged!')
    toast.success('Blocks arranged in workflow layout')
  }, [blocks, showActivity])

  const handleAddBlock = useCallback((blockData: Partial<Block> & { type: BlockType; name: string }) => {
    setBlocks(prev => {
      // Calculate n8n-style position based on block type/category
      const position = blockData.position || calculateBlockPosition(prev, blockData.type)
      
      // Generate complete block with defaults for missing properties
      const newBlock: Block = {
        id: blockData.id || `block-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        type: blockData.type,
        name: blockData.name,
        config: blockData.config || {},
        position,
        connections: blockData.connections || [],
      }
      return [...prev, newBlock]
    })
    showActivity('success', `Added: ${blockData.name}`)
    toast.success(`Added block: ${blockData.name}`)
  }, [showActivity, calculateBlockPosition])

  // Progressive block add for diagram analysis
  const handleProgressiveBlockAdd = useCallback((block: any, index: number, total: number) => {
    const newBlock: Block = {
      id: block.id || `block-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      type: block.type,
      name: block.name,
      config: block.config || {},
      position: block.position || { x: 100 + (index % 4) * 200, y: 100 + Math.floor(index / 4) * 150 },
      connections: block.connections || []
    }
    
    setBlocks(prev => {
      // Avoid duplicates
      if (prev.some(b => b.id === newBlock.id)) return prev
      return [...prev, newBlock]
    })
    
    // Only show activity for significant progress
    if (index === 0 || index === total - 1 || index % 5 === 0) {
      showActivity('info', `Building: ${block.name} (${index + 1}/${total})`)
    }
  }, [showActivity])

  // Add connection between blocks (for diagram analysis)
  const handleConnectionAdd = useCallback((fromId: string, toId: string) => {
    setBlocks(prev => prev.map(block => {
      if (block.id === fromId) {
        const connections = block.connections || []
        if (!connections.includes(toId)) {
          return { ...block, connections: [...connections, toId] }
        }
      }
      return block
    }))
  }, [])

  const handleGuidedComplete = useCallback((automation: any) => {
    handleGeneratedAutomation(automation)
    setBuilderMode('ai')
    showActivity('success', 'Automation created from wizard!')
  }, [handleGeneratedAutomation, showActivity])

  const handleSave = async () => {
    setIsSaving(true)
    showActivity('loading', 'Saving automation...')
    try {
      const payload = {
        name: automationName,
        description: '',
        type: automationType,
        blocks: blocks,
        config: {},
        generated_code: generatedCode,
        paper_trading: paperTrading,
      }

      let savedToBackend = false
      let savedData: Automation | null = null

      // Try backend first
      try {
        let res
        if (automation?.id) {
          res = await fetch(`http://localhost:8000/api/v1/automations/${automation.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          })
        } else {
          res = await fetch('http://localhost:8000/api/v1/automations/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          })
        }

        if (res.ok) {
          savedData = await res.json()
          savedToBackend = true
        }
      } catch {
        // Backend unavailable, will use localStorage fallback
        console.log('Backend unavailable, using localStorage fallback')
      }

      // Fallback to localStorage if backend failed
      if (!savedToBackend) {
        const id = automation?.id || `local-${Date.now()}-${Math.random().toString(36).slice(2)}`
        savedData = {
          id,
          name: automationName,
          description: '',
          type: automationType,
          deployment_type: 'local',
          status: 'draft',
          blocks: blocks,
          config: {},
          generated_code: generatedCode,
          paper_trading: paperTrading,
        }

        // Save to localStorage
        const existingAutomations = JSON.parse(localStorage.getItem('local-automations') || '[]')
        const existingIndex = existingAutomations.findIndex((a: Automation) => a.id === id)
        if (existingIndex >= 0) {
          existingAutomations[existingIndex] = savedData
        } else {
          existingAutomations.push(savedData)
        }
        localStorage.setItem('local-automations', JSON.stringify(existingAutomations))
      }

      if (savedData) {
        setAutomation(savedData)
        window.history.replaceState({}, '', `/editor?id=${savedData.id}`)
        showActivity('success', savedToBackend ? 'Automation saved!' : 'Saved locally (backend unavailable)')
        toast.success(savedToBackend ? 'Automation saved!' : 'Saved locally (backend unavailable)')
      }
    } catch (e) {
      showActivity('error', 'Failed to save')
      toast.error('Failed to save automation')
    } finally {
      setIsSaving(false)
    }
  }

  const handleRun = async () => {
    if (!automation?.id) {
      await handleSave()
    }
    
    const currentId = automation?.id
    if (!currentId) {
      toast.error('Please save the automation first')
      return
    }

    setIsRunning(true)
    setOutput([])
    showActivity('loading', 'Starting automation...')

    try {
      const res = await fetch(`http://localhost:8000/api/v1/automations/${currentId}/run`, {
        method: 'POST'
      })
      
      if (res.ok) {
        setStatus('running')
        showActivity('success', 'Automation started!')
        toast.success('Automation started!')
        
        // Start polling for logs
        startLogPolling(currentId)
      } else {
        const error = await res.json()
        throw new Error(error.detail || 'Run failed')
      }
    } catch (e: any) {
      setIsRunning(false)
      showActivity('error', 'Failed to start')
      toast.error(e.message || 'Failed to start automation')
    }
  }

  const handleStop = async () => {
    if (!automation?.id) return

    try {
      await fetch(`http://localhost:8000/api/v1/automations/${automation.id}/stop`, {
        method: 'POST'
      })
      setStatus('stopped')
      setIsRunning(false)
      showActivity('info', 'Automation stopped')
      toast.info('Automation stopped')
    } catch (e) {
      toast.error('Failed to stop automation')
    }
  }

  const handleDeploy = async () => {
    if (!automation?.id) {
      await handleSave()
    }

    const currentId = automation?.id
    if (!currentId) {
      toast.error('Please save the automation first')
      return
    }

    showActivity('loading', 'Deploying to Docker...')

    try {
      const res = await fetch(`http://localhost:8000/api/v1/automations/${currentId}/deploy`, {
        method: 'POST'
      })
      
      if (res.ok) {
        setStatus('deployed')
        showActivity('success', '🎉 Deployed successfully!')
        toast.success('Automation deployed to Docker!')
      } else {
        const error = await res.json()
        throw new Error(error.detail || 'Deploy failed')
      }
    } catch (e: any) {
      showActivity('error', 'Deploy failed')
      toast.error(e.message || 'Failed to deploy automation')
    }
  }

  const handleConfigureBlock = (blockId: string) => {
    setConfigBlockId(blockId)
    setShowConfigDialog(true)
  }

  const selectedBlock = configBlockId ? blocks.find(b => b.id === configBlockId) : null

  return (
    <div className="h-screen flex flex-col bg-[#0a0a0f] text-gray-100">
      {/* Onboarding Tour */}
      <OnboardingTour 
        isOpen={showOnboarding} 
        onComplete={() => setShowOnboarding(false)} 
      />

      {/* Activity Indicator */}
      <AnimatePresence>
        {activity && (
          <ActivityIndicator type={activity.type} message={activity.message} />
        )}
      </AnimatePresence>

      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-900/50">
        <div className="flex items-center gap-4">
          <Link href="/trading">
            <Button variant="ghost" size="sm" className="gap-2">
              <ChevronLeft className="h-4 w-4" />
              Back
            </Button>
          </Link>
          
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-400" />
            <span className="font-semibold">Automation Builder</span>
          </div>

          <Badge className={`${STATUS_COLORS[status]} text-white`}>
            {status.toUpperCase()}
          </Badge>

          {!paperTrading && automationType === 'trading_bot' && (
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3 w-3" />
              LIVE TRADING
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Mode Switcher */}
          <div className="flex items-center bg-gray-800 rounded-lg p-1 mr-2">
            <button
              onClick={() => setBuilderMode('ai')}
              className={cn(
                "flex items-center gap-1 px-3 py-1 rounded text-xs font-medium transition-colors",
                builderMode === 'ai' 
                  ? "bg-purple-600 text-white" 
                  : "text-gray-400 hover:text-gray-200"
              )}
            >
              <MessageSquare className="h-3 w-3" />
              AI Chat
            </button>
            <button
              onClick={() => setBuilderMode('manual')}
              className={cn(
                "flex items-center gap-1 px-3 py-1 rounded text-xs font-medium transition-colors",
                builderMode === 'manual' 
                  ? "bg-emerald-600 text-white" 
                  : "text-gray-400 hover:text-gray-200"
              )}
            >
              <LayoutGrid className="h-3 w-3" />
              Manual
            </button>
            <button
              onClick={() => setBuilderMode('guided')}
              className={cn(
                "flex items-center gap-1 px-3 py-1 rounded text-xs font-medium transition-colors",
                builderMode === 'guided' 
                  ? "bg-blue-600 text-white" 
                  : "text-gray-400 hover:text-gray-200"
              )}
            >
              <Wand2 className="h-3 w-3" />
              Guided
            </button>
          </div>

          <Input
            id="automation-name-input"
            value={automationName}
            onChange={(e) => setAutomationName(e.target.value)}
            onInput={(e) => setAutomationName((e.target as HTMLInputElement).value)}
            onBlur={(e) => setAutomationName(e.target.value)}
            className="w-64 bg-gray-800 border-gray-700 text-sm relative z-20"
            placeholder="Automation name..."
          />
          
          <Button
            variant="outline"
            size="sm"
            onClick={handleSave}
            disabled={isSaving}
            className="gap-2"
          >
            {isSaving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save
          </Button>

          {/* Run/Deploy buttons in header */}
          {status === 'running' || status === 'testing' ? (
            <Button
              size="sm"
              variant="destructive"
              onClick={handleStop}
              className="gap-2"
            >
              <Square className="h-4 w-4" />
              Stop
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={handleRun}
              disabled={isRunning}
              className="gap-2 bg-blue-600 hover:bg-blue-500"
            >
              {isRunning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Run
            </Button>
          )}
          <Button
            size="sm"
            onClick={handleDeploy}
            disabled={status === 'deployed'}
            className="gap-2 bg-emerald-600 hover:bg-emerald-500"
          >
            <Rocket className="h-4 w-4" />
            Deploy
          </Button>

          {blocks.length > 1 && (
            <Button
              variant="outline"
              size="sm"
              onClick={autoLayoutBlocks}
              className="gap-2"
              title="Auto-arrange blocks in n8n-style layout"
            >
              <LayoutGrid className="h-4 w-4" />
              Auto Layout
            </Button>
          )}

          {generatedCode && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowCodeDialog(true)}
              className="gap-2"
          >
              <Code className="h-4 w-4" />
              View Code
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowOnboarding(true)}
            className="gap-1"
          >
            <HelpCircle className="h-4 w-4" />
          </Button>

          <Link href="/trading/automations">
            <Button variant="ghost" size="sm" className="gap-2">
              <List className="h-4 w-4" />
              My Automations
          </Button>
        </Link>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Conditional based on mode */}
        <AnimatePresence mode="wait">
          {builderMode === 'ai' && (
            <motion.div
              key="ai-chat"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="w-80 flex-shrink-0 border-r border-gray-800"
            >
              <AIBuilderChat
                onGeneratedAutomation={handleGeneratedAutomation}
                onProgressiveBlockAdd={handleProgressiveBlockAdd}
                onConnectionAdd={handleConnectionAdd}
                isGenerating={isGenerating}
                automationType={automationType}
                onAutomationTypeChange={setAutomationType}
                triggerDiagramUpload={triggerDiagramUpload}
                currentBlocks={blocks.map(b => ({ type: b.type, name: b.name }))}
              />
            </motion.div>
          )}

          {builderMode === 'manual' && (
            <motion.div
              key="block-palette"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="w-72 flex-shrink-0 border-r border-gray-800 h-full overflow-hidden"
            >
              <BlockPalette
                automationType={automationType}
                onAddBlock={handleAddBlock}
                isCollapsed={false}
                onToggleCollapse={() => {}}
              />
            </motion.div>
          )}

          {builderMode === 'guided' && (
            <motion.div
              key="guided-builder"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="w-96 flex-shrink-0 border-r border-gray-800"
            >
              <GuidedBuilder
                onComplete={handleGuidedComplete}
                onCancel={() => setBuilderMode('ai')}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Center: Canvas + Preview */}
        <div className="flex-1 flex flex-col">
          <BuilderCanvas
            blocks={blocks}
            onBlocksChange={setBlocks}
            selectedBlockId={selectedBlockId}
            onSelectBlock={setSelectedBlockId}
            onConfigureBlock={handleConfigureBlock}
            automationType={automationType}
            onUploadDiagram={handleUploadDiagramFromCanvas}
            onRun={handleRun}
            onDeploy={handleDeploy}
            isRunning={isRunning}
            status={status}
          />
          
          {/* Bottom Action Bar */}
          <div className="h-56 border-t border-gray-800 bg-gray-900/30 flex flex-col flex-shrink-0">
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 flex-shrink-0 min-h-[52px]">
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="text-sm font-medium text-white">Output</span>
                {output.length > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    {output.length} lines
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {status === 'running' || status === 'testing' ? (
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={handleStop}
                    className="gap-2"
                  >
                    <Square className="h-4 w-4" />
                    Stop
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    onClick={handleRun}
                    disabled={isRunning}
                    className="gap-2 bg-blue-600 hover:bg-blue-500"
                  >
                    {isRunning ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                    Run
                  </Button>
                )}
                
                <Button
                  size="sm"
                  onClick={handleDeploy}
                  disabled={status === 'deployed'}
                  className="gap-2 bg-emerald-600 hover:bg-emerald-500"
                >
                  <Rocket className="h-4 w-4" />
                  Deploy
                </Button>
              </div>
            </div>
            
            <ScrollArea className="flex-1 p-3 font-mono text-sm">
              {output.length === 0 ? (
                <div className="text-gray-500 italic">
                  Output will appear here when you run the automation...
                </div>
              ) : (
                output.map((line, i) => {
                  // Parse and format output for user-friendly display
                  const isPriceOutput = line.includes('$') && !line.includes('[')
                  const isError = line.toLowerCase().includes('error')
                  const isConnected = line.toLowerCase().includes('connected')
                  
                  if (isPriceOutput) {
                    // Price output - show prominently
                    return (
                      <div key={i} className="py-1 text-green-400 font-semibold text-base">
                        📈 {line}
                      </div>
                    )
                  } else if (isError) {
                    return (
                      <div key={i} className="py-0.5 text-red-400">
                        ❌ {line}
                      </div>
                    )
                  } else if (isConnected) {
                    return (
                      <div key={i} className="py-0.5 text-blue-400">
                        ✅ {line}
                      </div>
                    )
                  } else {
                    // Filter out verbose timestamp logs, show only meaningful output
                    const cleanLine = line.replace(/\[\d{4}-\d{2}-\d{2}T[\d:.]+\]\s*/g, '')
                    if (cleanLine.includes('Received') && !cleanLine.includes('$')) {
                      return null // Skip verbose "Received" logs without price
                    }
                    return (
                      <div key={i} className="py-0.5 text-gray-400 text-xs">
                        {cleanLine}
                      </div>
                    )
                  }
                }).filter(Boolean)
              )}
            </ScrollArea>
          </div>
        </div>
      </div>

      {/* Block Config Dialog */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-lg">
          <DialogHeader>
            <DialogTitle>Configure Block</DialogTitle>
            <DialogDescription className="text-gray-400">
              {selectedBlock?.name} ({selectedBlock?.type})
            </DialogDescription>
          </DialogHeader>
          
          {selectedBlock && (
            <div className="space-y-4 py-4">
              {Object.entries(selectedBlock.config).map(([key, value]) => (
                <div key={key}>
                  <label className="text-sm text-gray-400 mb-1 block capitalize">
                    {key.replace(/_/g, ' ')}
                  </label>
                  <Input
                    value={typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    onChange={(e) => {
                      let newValue: any = e.target.value
                      // Try to parse as JSON for arrays/objects
                      if (e.target.value.startsWith('[') || e.target.value.startsWith('{')) {
                        try {
                          newValue = JSON.parse(e.target.value)
                        } catch {
                          // Keep as string
                        }
                      }
                      setBlocks(blocks.map(b => 
                        b.id === selectedBlock.id 
                          ? { ...b, config: { ...b.config, [key]: newValue } }
                          : b
                      ))
                    }}
                    className="bg-gray-800 border-gray-700"
                  />
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowConfigDialog(false)}>
              Cancel
            </Button>
            <Button onClick={() => setShowConfigDialog(false)}>
              Apply
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Code View Dialog */}
      <Dialog open={showCodeDialog} onOpenChange={setShowCodeDialog}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-4xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>Generated Code</DialogTitle>
            <DialogDescription className="text-gray-400">
              {automationName}
            </DialogDescription>
          </DialogHeader>
          
          <ScrollArea className="h-[60vh]">
            <pre className="p-4 bg-gray-950 rounded-lg text-sm font-mono text-gray-300 overflow-x-auto">
              {generatedCode || '// No code generated yet'}
            </pre>
          </ScrollArea>

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => {
                navigator.clipboard.writeText(generatedCode || '')
                toast.success('Code copied to clipboard!')
              }}
            >
              Copy Code
            </Button>
            <Button onClick={() => setShowCodeDialog(false)}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
