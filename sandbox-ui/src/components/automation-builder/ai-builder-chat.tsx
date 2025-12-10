'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  Send, 
  Bot, 
  User, 
  Sparkles, 
  Loader2, 
  ChevronDown,
  RotateCcw,
  Wand2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Blocks,
  Settings2,
  Mic,
  MicOff,
  Image as ImageIcon,
  Upload,
  X,
  FileImage,
  Cpu,
  Network,
  Layers,
  ArrowRight,
  Zap,
  RefreshCw,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import { motion, AnimatePresence } from 'framer-motion'
import { Progress } from '@/components/ui/progress'
import { 
  BUILDER_SYSTEM_PROMPT, 
  getContextualSuggestions, 
  BlockState,
  BLOCK_KNOWLEDGE,
  LAYOUT_GUIDE 
} from '@/lib/automation-builder-knowledge'

export type AutomationType = 
  | 'scraper' 
  | 'trading_bot' 
  | 'alert' 
  | 'signal' 
  | 'risk' 
  | 'backtest'
  | 'architecture' // New type for full system architecture

interface DiagramAnalysis {
  layers: {
    name: string
    components: string[]
  }[]
  totalComponents: number
  connections: number
  estimatedBlocks: number
}

interface BuildProgress {
  stage: 'analyzing' | 'extracting' | 'building' | 'connecting' | 'complete'
  currentLayer?: string
  currentComponent?: string
  progress: number
  blocksBuilt: number
  totalBlocks: number
  message: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  automation?: any
  isTyping?: boolean
  status?: 'pending' | 'success' | 'error'
  image?: string // Base64 or URL
  diagramAnalysis?: DiagramAnalysis
  buildProgress?: BuildProgress
}

interface AIBuilderChatProps {
  onGeneratedAutomation: (automation: any) => void
  onProgressiveBlockAdd?: (block: any, index: number, total: number) => void
  onConnectionAdd?: (from: string, to: string) => void
  isGenerating: boolean
  automationType: AutomationType
  onAutomationTypeChange: (type: AutomationType) => void
  triggerDiagramUpload?: boolean
  /** Current blocks on the canvas for context-aware suggestions */
  currentBlocks?: BlockState[]
}

const AUTOMATION_TYPES = [
  { value: 'architecture', label: 'From Diagram', icon: '🏗️', description: 'Upload architecture diagram', color: 'from-violet-500/20 to-indigo-500/20' },
  { value: 'scraper', label: 'Data Scraper', icon: '📊', description: 'Collect data from exchanges/APIs', color: 'from-blue-500/20 to-cyan-500/20' },
  { value: 'trading_bot', label: 'Trading Bot', icon: '🤖', description: 'Automated order execution', color: 'from-emerald-500/20 to-green-500/20' },
  { value: 'alert', label: 'Alert System', icon: '🔔', description: 'Price & indicator notifications', color: 'from-yellow-500/20 to-orange-500/20' },
  { value: 'signal', label: 'Signal Generator', icon: '📈', description: 'Multi-factor trading signals', color: 'from-purple-500/20 to-pink-500/20' },
  { value: 'risk', label: 'Risk Monitor', icon: '🛡️', description: 'Portfolio risk tracking', color: 'from-red-500/20 to-rose-500/20' },
  { value: 'backtest', label: 'Backtest', icon: '📜', description: 'Test strategies on history', color: 'from-indigo-500/20 to-violet-500/20' },
] as const

const SUGGESTIONS: Record<AutomationType, string[]> = {
  architecture: [
    "Upload a system architecture diagram to auto-generate blocks",
    "I'll analyze any flowchart, block diagram, or system design",
    "Supports PNG, JPG diagrams with components and connections",
  ],
  scraper: [
    "Create a scraper that gets BTC orderbook from Binance every 30 seconds",
    "Track ETH and SOL prices from CoinGecko every minute",
    "Stream real-time trades for BTCUSDT from Binance",
  ],
  trading_bot: [
    "Create a DCA bot that buys $100 of BTC every day",
    "Build a grid trading bot for ETH between $2000-$3000",
    "Make a momentum bot that trades based on RSI signals",
  ],
  alert: [
    "Alert me when BTC goes above $100,000 or below $50,000",
    "Send notification when RSI drops below 30 on ETH",
    "Notify when trading volume spikes 3x average",
  ],
  signal: [
    "Generate signals combining RSI, MACD, and volume",
    "Create a confluence scorer for BTC with multiple indicators",
    "Build a multi-timeframe signal generator",
  ],
  risk: [
    "Monitor portfolio drawdown and alert at 10%",
    "Track position exposure across all assets",
    "Create a risk dashboard with real-time metrics",
  ],
  backtest: [
    "Backtest a moving average crossover strategy on BTC",
    "Test RSI-based entry/exit on ETH with 1-year data",
    "Compare DCA vs lump sum over 2023",
  ],
}

const REFINE_OPTIONS = [
  { label: 'More aggressive', prompt: 'Make this more aggressive with tighter parameters' },
  { label: 'More conservative', prompt: 'Make this more conservative with safer parameters' },
  { label: 'Add more blocks', prompt: 'Add more logic blocks and conditions' },
  { label: 'Simplify', prompt: 'Simplify and reduce the number of blocks' },
]

// Typing animation hook
function useTypingAnimation(text: string, speed: number = 20, enabled: boolean = true) {
  const [displayedText, setDisplayedText] = useState('')
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    if (!enabled) {
      setDisplayedText(text)
      setIsComplete(true)
      return
    }

    setDisplayedText('')
    setIsComplete(false)
    
    let currentIndex = 0
    const interval = setInterval(() => {
      if (currentIndex < text.length) {
        setDisplayedText(text.slice(0, currentIndex + 1))
        currentIndex++
      } else {
        setIsComplete(true)
        clearInterval(interval)
      }
    }, speed)

    return () => clearInterval(interval)
  }, [text, speed, enabled])

  return { displayedText, isComplete }
}

// Block preview component
function BlockPreview({ block, index }: { block: any; index: number }) {
  const blockColors: Record<string, string> = {
    data_source: 'bg-blue-500/20 border-blue-500/40 text-blue-300',
    processor: 'bg-purple-500/20 border-purple-500/40 text-purple-300',
    condition: 'bg-yellow-500/20 border-yellow-500/40 text-yellow-300',
    action: 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300',
    output: 'bg-orange-500/20 border-orange-500/40 text-orange-300',
    agent: 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300',
    fusion: 'bg-amber-500/20 border-amber-500/40 text-amber-300',
    risk: 'bg-red-500/20 border-red-500/40 text-red-300',
    execution: 'bg-green-500/20 border-green-500/40 text-green-300',
  }
  
  const color = blockColors[block.type] || 'bg-gray-500/20 border-gray-500/40 text-gray-300'
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className={cn(
        "flex items-center gap-2 px-2 py-1 rounded-md border text-xs",
        color
      )}
    >
      <Blocks className="w-3 h-3 flex-shrink-0" />
      <span className="truncate max-w-[100px]">{block.name}</span>
    </motion.div>
  )
}

// Typing message component
function TypingMessage({ content, onComplete }: { content: string; onComplete?: () => void }) {
  const { displayedText, isComplete } = useTypingAnimation(content, 15, true)
  
  useEffect(() => {
    if (isComplete && onComplete) {
      onComplete()
    }
  }, [isComplete, onComplete])

  return (
    <p className="whitespace-pre-wrap">
      {displayedText}
      {!isComplete && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.5, repeat: Infinity }}
          className="inline-block w-2 h-4 bg-purple-400 ml-1 align-middle"
        />
      )}
    </p>
  )
}

// Build Progress Component
function BuildProgressIndicator({ progress }: { progress: BuildProgress }) {
  const stageIcons = {
    analyzing: <Cpu className="w-4 h-4" />,
    extracting: <Layers className="w-4 h-4" />,
    building: <Blocks className="w-4 h-4" />,
    connecting: <Network className="w-4 h-4" />,
    complete: <CheckCircle2 className="w-4 h-4" />,
  }

  const stageColors = {
    analyzing: 'text-purple-400',
    extracting: 'text-blue-400',
    building: 'text-emerald-400',
    connecting: 'text-amber-400',
    complete: 'text-green-400',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 p-3 bg-gray-800/50 rounded-lg border border-gray-700 space-y-3"
    >
      {/* Stage indicator */}
      <div className="flex items-center gap-2">
        <motion.div 
          className={cn("p-1.5 rounded-lg bg-gray-700/50", stageColors[progress.stage])}
          animate={progress.stage !== 'complete' ? { scale: [1, 1.1, 1] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
        >
          {stageIcons[progress.stage]}
        </motion.div>
        <div className="flex-1">
          <div className="text-sm font-medium text-gray-200">{progress.message}</div>
          {progress.currentLayer && (
            <div className="text-xs text-gray-400 flex items-center gap-1">
              <Layers className="w-3 h-3" />
              {progress.currentLayer}
              {progress.currentComponent && (
                <>
                  <ArrowRight className="w-3 h-3" />
                  <span className="text-cyan-400">{progress.currentComponent}</span>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-gray-400">
          <span>Building blocks</span>
          <span>{progress.blocksBuilt} / {progress.totalBlocks}</span>
        </div>
        <Progress value={progress.progress} className="h-2 bg-gray-700" />
      </div>

      {/* Stage dots */}
      <div className="flex justify-between px-2">
        {['analyzing', 'extracting', 'building', 'connecting', 'complete'].map((stage, i) => {
          const isActive = stage === progress.stage
          const isPast = ['analyzing', 'extracting', 'building', 'connecting', 'complete'].indexOf(progress.stage) > i
          return (
            <div key={stage} className="flex flex-col items-center gap-1">
              <motion.div
                className={cn(
                  "w-2 h-2 rounded-full transition-colors",
                  isActive && "bg-purple-400",
                  isPast && "bg-emerald-400",
                  !isActive && !isPast && "bg-gray-600"
                )}
                animate={isActive ? { scale: [1, 1.3, 1] } : {}}
                transition={{ duration: 0.5, repeat: Infinity }}
              />
              <span className={cn(
                "text-[10px] capitalize",
                isActive && "text-purple-400",
                isPast && "text-emerald-400",
                !isActive && !isPast && "text-gray-500"
              )}>
                {stage.slice(0, 4)}
              </span>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}

// Diagram Analysis Preview
function DiagramAnalysisPreview({ analysis }: { analysis: DiagramAnalysis }) {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      className="mt-3 p-3 bg-gradient-to-br from-purple-500/10 to-blue-500/10 rounded-lg border border-purple-500/30"
    >
      <div className="flex items-center gap-2 mb-3">
        <Cpu className="w-4 h-4 text-purple-400" />
        <span className="text-sm font-medium text-purple-300">Diagram Analysis</span>
      </div>
      
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center p-2 bg-gray-800/50 rounded">
          <div className="text-lg font-bold text-cyan-400">{analysis.totalComponents}</div>
          <div className="text-xs text-gray-400">Components</div>
        </div>
        <div className="text-center p-2 bg-gray-800/50 rounded">
          <div className="text-lg font-bold text-amber-400">{analysis.connections}</div>
          <div className="text-xs text-gray-400">Connections</div>
        </div>
        <div className="text-center p-2 bg-gray-800/50 rounded">
          <div className="text-lg font-bold text-emerald-400">{analysis.estimatedBlocks}</div>
          <div className="text-xs text-gray-400">Blocks</div>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-xs text-gray-400 flex items-center gap-1">
          <Layers className="w-3 h-3" />
          Detected Layers:
        </div>
        {analysis.layers.map((layer, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className="flex items-start gap-2 text-xs"
          >
            <div className="w-4 h-4 rounded bg-gray-700 flex items-center justify-center text-[10px] font-bold text-gray-400 flex-shrink-0">
              {i + 1}
            </div>
            <div className="flex-1">
              <div className="font-medium text-gray-300">{layer.name}</div>
              <div className="text-gray-500 truncate">
                {layer.components.slice(0, 3).join(', ')}
                {layer.components.length > 3 && ` +${layer.components.length - 3} more`}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}

// Image Upload Zone Component
function ImageUploadZone({ 
  onImageUpload, 
  isDragging, 
  uploadedImage,
  onClear 
}: { 
  onImageUpload: (file: File) => void
  isDragging: boolean
  uploadedImage: string | null
  onClear: () => void
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  if (uploadedImage) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative rounded-lg overflow-hidden border-2 border-purple-500/50 bg-gray-800/50"
      >
        <img 
          src={uploadedImage} 
          alt="Uploaded diagram" 
          className="w-full h-40 object-contain bg-gray-900"
        />
        <button
          onClick={onClear}
          className="absolute top-2 right-2 p-1 bg-red-500/80 hover:bg-red-500 rounded-full transition-colors"
        >
          <X className="w-4 h-4 text-white" />
        </button>
        <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-gray-900 to-transparent">
          <div className="flex items-center gap-1 text-xs text-purple-300">
            <FileImage className="w-3 h-3" />
            <span>Ready to analyze</span>
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn(
        "relative border-2 border-dashed rounded-lg p-4 transition-all cursor-pointer",
        isDragging 
          ? "border-purple-400 bg-purple-500/10" 
          : "border-gray-600 hover:border-gray-500 bg-gray-800/30"
      )}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onImageUpload(file)
        }}
      />
      
      <div className="flex flex-col items-center gap-2 text-center">
        <motion.div
          animate={isDragging ? { scale: 1.1 } : { scale: 1 }}
          className="p-3 bg-gray-700/50 rounded-full"
        >
          <Upload className={cn(
            "w-6 h-6 transition-colors",
            isDragging ? "text-purple-400" : "text-gray-400"
          )} />
        </motion.div>
        <div>
          <p className="text-sm font-medium text-gray-300">
            {isDragging ? "Drop your diagram here" : "Upload Architecture Diagram"}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            PNG, JPG, or any image format
          </p>
        </div>
      </div>
    </motion.div>
  )
}

export function AIBuilderChat({ 
  onGeneratedAutomation,
  onProgressiveBlockAdd,
  onConnectionAdd,
  isGenerating,
  automationType,
  onAutomationTypeChange,
  triggerDiagramUpload,
  currentBlocks = [],
}: AIBuilderChatProps) {
  const currentType = AUTOMATION_TYPES.find(t => t.value === automationType)
  
  // Get contextual suggestions based on current canvas state
  const contextSuggestions = getContextualSuggestions(currentBlocks)
  
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Hi! I'm your automation builder assistant. I can help you create **${currentType?.label || 'automations'}**.\n\nDescribe what you want to build, or select a different automation type above.`,
      timestamp: new Date(),
    }
  ])
  const [input, setInput] = useState('')
  const [typingMessageId, setTypingMessageId] = useState<string | null>(null)
  const [isListening, setIsListening] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedImage, setUploadedImage] = useState<string | null>(null)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [typeDropdownOpen, setTypeDropdownOpen] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const mainFileInputRef = useRef<HTMLInputElement>(null)

  // Handle external trigger for diagram upload
  useEffect(() => {
    if (triggerDiagramUpload && mainFileInputRef.current) {
      // Switch to architecture type
      onAutomationTypeChange('architecture')
      // Short delay to ensure type change is processed
      setTimeout(() => {
        mainFileInputRef.current?.click()
      }, 50)
    }
  }, [triggerDiagramUpload, onAutomationTypeChange])
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const dropZoneRef = useRef<HTMLDivElement>(null)

  // Update intro message when type changes
  useEffect(() => {
    const newType = AUTOMATION_TYPES.find(t => t.value === automationType)
    
    // Get available categories for the layout guide
    const categoryList = Object.keys(BLOCK_KNOWLEDGE).slice(0, 5).map(k => BLOCK_KNOWLEDGE[k].label).join(', ')
    
    const introMessage = automationType === 'architecture'
      ? `Hi! I'm your **automation builder assistant** with knowledge of **48 blocks** across **11 categories**.

📸 **Upload a diagram** below, and I'll:
1. Identify all components and layers
2. Detect connections between nodes
3. Build each block progressively
4. Connect everything together

Or describe what you want to build and I'll suggest the right blocks!`
      : `Hi! I'm your **automation builder assistant**. I can help you create **${newType?.label || 'automations'}**.

I have knowledge of **48 blocks** across categories like: ${categoryList}, and more.

**How I can help:**
• Suggest specific blocks for your strategy
• Explain how blocks connect (left-to-right flow)
• Guide you step-by-step through building
• Recommend optimal configurations

${newType?.description ? `\n📌 *${newType.description}*\n` : ''}
Describe what you want to build, or try the suggestions below!`
    
    setMessages([{
      id: '1',
      role: 'assistant',
      content: introMessage,
      timestamp: new Date(),
    }])
    setUploadedImage(null)
    setUploadedFile(null)
  }, [automationType])

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) {
      handleImageUpload(file)
    }
  }, [])

  const handleImageUpload = useCallback((file: File) => {
    setUploadedFile(file)
    const reader = new FileReader()
    reader.onload = (e) => {
      setUploadedImage(e.target?.result as string)
    }
    reader.readAsDataURL(file)
  }, [])

  const clearImage = useCallback(() => {
    setUploadedImage(null)
    setUploadedFile(null)
  }, [])

  // Process diagram with streaming updates
  const processDiagram = useCallback(async () => {
    if (!uploadedImage || !uploadedFile) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: 'Analyze this architecture diagram and build the automation blocks',
      timestamp: new Date(),
      image: uploadedImage,
    }
    setMessages(prev => [...prev, userMessage])

    // Initial response
    const responseId = (Date.now() + 1).toString()
    const initialResponse: Message = {
      id: responseId,
      role: 'assistant',
      content: '🔍 **Analyzing your architecture diagram...**\n\nI\'m processing the image to identify components, layers, and connections.',
      timestamp: new Date(),
      isTyping: true,
      status: 'pending',
      buildProgress: {
        stage: 'analyzing',
        progress: 5,
        blocksBuilt: 0,
        totalBlocks: 0,
        message: 'Scanning diagram structure...',
      }
    }
    setMessages(prev => [...prev, initialResponse])

    try {
      // Create form data
      const formData = new FormData()
      formData.append('image', uploadedFile)
      formData.append('type', automationType)

      // Call the diagram analysis endpoint
      const response = await fetch('http://localhost:8000/api/v1/automations/analyze-diagram', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Diagram analysis failed')
      }

      // Check if it's a streaming response
      const contentType = response.headers.get('content-type')
      
      if (contentType?.includes('text/event-stream')) {
        // Handle SSE streaming
        const reader = response.body?.getReader()
        const decoder = new TextDecoder()
        
        if (!reader) throw new Error('No response body')

        let diagramAnalysis: DiagramAnalysis | null = null
        let automation: any = null
        let currentProgress: BuildProgress = {
          stage: 'analyzing',
          progress: 10,
          blocksBuilt: 0,
          totalBlocks: 0,
          message: 'Analyzing diagram...',
        }

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                
                if (data.type === 'analysis') {
                  diagramAnalysis = data.analysis
                  currentProgress = {
                    stage: 'extracting',
                    progress: 20,
                    blocksBuilt: 0,
                    totalBlocks: diagramAnalysis?.estimatedBlocks || 0,
                    message: `Found ${diagramAnalysis?.totalComponents} components across ${diagramAnalysis?.layers.length} layers`,
                  }
                } else if (data.type === 'progress') {
                  currentProgress = {
                    ...currentProgress,
                    ...data.progress,
                  }
                  
                  // Progressive block add
                  if (data.block && onProgressiveBlockAdd) {
                    onProgressiveBlockAdd(data.block, currentProgress.blocksBuilt, currentProgress.totalBlocks)
                  }
                } else if (data.type === 'connection' && onConnectionAdd) {
                  onConnectionAdd(data.from, data.to)
                } else if (data.type === 'complete') {
                  automation = data.automation
                  currentProgress = {
                    stage: 'complete',
                    progress: 100,
                    blocksBuilt: automation.blocks.length,
                    totalBlocks: automation.blocks.length,
                    message: 'All blocks built successfully!',
                  }
                }

                // Update message with current progress
                setMessages(prev => prev.map(m => 
                  m.id === responseId 
                    ? {
                        ...m,
                        content: getProgressMessage(currentProgress, diagramAnalysis),
                        buildProgress: currentProgress,
                        diagramAnalysis: diagramAnalysis || undefined,
                        isTyping: currentProgress.stage !== 'complete',
                        status: currentProgress.stage === 'complete' ? 'success' : 'pending',
                        automation: automation || undefined,
                      }
                    : m
                ))
              } catch (e) {
                // Skip malformed JSON
              }
            }
          }
        }
      } else {
        // Non-streaming response
        const data = await response.json()
        
        // Simulate progressive building for non-streaming response
        await simulateProgressiveBuild(responseId, data, onProgressiveBlockAdd, onConnectionAdd)
        
        setMessages(prev => prev.map(m => 
          m.id === responseId 
            ? {
                ...m,
                content: `✅ **Architecture Built Successfully!**\n\nI've analyzed your diagram and created **${data.blocks?.length || 0} blocks** with all connections.\n\nThe automation is now ready on your canvas.`,
                isTyping: false,
                status: 'success',
                automation: data,
                diagramAnalysis: data.analysis,
                buildProgress: {
                  stage: 'complete',
                  progress: 100,
                  blocksBuilt: data.blocks?.length || 0,
                  totalBlocks: data.blocks?.length || 0,
                  message: 'All blocks built!',
                },
              }
            : m
        ))
        
        if (data) {
          onGeneratedAutomation(data)
        }
      }

      clearImage()

    } catch (error) {
      console.error('Diagram processing error:', error)
      
      // Fallback: Generate mock response for demo
      const mockData = generateMockDiagramResponse()
      await simulateProgressiveBuild(responseId, mockData, onProgressiveBlockAdd, onConnectionAdd)
      
      setMessages(prev => prev.map(m => 
        m.id === responseId 
          ? {
              ...m,
              content: `✅ **Architecture Built Successfully!**\n\nI've analyzed your diagram and created **${mockData.blocks.length} blocks** across **${mockData.analysis.layers.length} layers**.\n\n*Note: Using demo mode - backend not available*`,
              isTyping: false,
              status: 'success',
              automation: mockData,
              diagramAnalysis: mockData.analysis,
              buildProgress: {
                stage: 'complete',
                progress: 100,
                blocksBuilt: mockData.blocks.length,
                totalBlocks: mockData.blocks.length,
                message: 'All blocks built!',
              },
            }
          : m
      ))
      
      onGeneratedAutomation(mockData)
      clearImage()
    }
  }, [uploadedImage, uploadedFile, automationType, onGeneratedAutomation, onProgressiveBlockAdd, onConnectionAdd, clearImage])

  // Simulate progressive building for demo
  async function simulateProgressiveBuild(
    messageId: string, 
    data: any,
    onBlockAdd?: (block: any, index: number, total: number) => void,
    onConnectionAdd?: (from: string, to: string) => void
  ) {
    const blocks = data.blocks || []
    const analysis = data.analysis || { layers: [], totalComponents: blocks.length, connections: 0, estimatedBlocks: blocks.length }
    
    // Phase 1: Analysis
    setMessages(prev => prev.map(m => 
      m.id === messageId 
        ? {
            ...m,
            content: '🔍 **Analyzing diagram...**\n\nIdentifying components and structure.',
            buildProgress: {
              stage: 'analyzing',
              progress: 15,
              blocksBuilt: 0,
              totalBlocks: blocks.length,
              message: 'Scanning diagram structure...',
            },
            diagramAnalysis: analysis,
          }
        : m
    ))
    await sleep(800)

    // Phase 2: Extracting
    setMessages(prev => prev.map(m => 
      m.id === messageId 
        ? {
            ...m,
            content: `📊 **Found ${analysis.totalComponents} components!**\n\nDetected ${analysis.layers.length} layers. Starting extraction...`,
            buildProgress: {
              stage: 'extracting',
              progress: 25,
              blocksBuilt: 0,
              totalBlocks: blocks.length,
              message: `Extracting ${analysis.totalComponents} components...`,
            },
          }
        : m
    ))
    await sleep(600)

    // Phase 3: Building blocks progressively
    for (let i = 0; i < blocks.length; i++) {
      const block = blocks[i]
      const progress = 25 + ((i + 1) / blocks.length) * 60
      
      if (onBlockAdd) {
        onBlockAdd(block, i, blocks.length)
      }

      setMessages(prev => prev.map(m => 
        m.id === messageId 
          ? {
              ...m,
              content: `🔨 **Building blocks...**\n\nCreating: **${block.name}**`,
              buildProgress: {
                stage: 'building',
                currentComponent: block.name,
                currentLayer: block.layer || '',
                progress,
                blocksBuilt: i + 1,
                totalBlocks: blocks.length,
                message: `Building ${block.name}...`,
              },
            }
          : m
      ))
      
      await sleep(150 + Math.random() * 200)
    }

    // Phase 4: Connecting
    setMessages(prev => prev.map(m => 
      m.id === messageId 
        ? {
            ...m,
            content: '🔗 **Connecting blocks...**\n\nEstablishing data flows and relationships.',
            buildProgress: {
              stage: 'connecting',
              progress: 90,
              blocksBuilt: blocks.length,
              totalBlocks: blocks.length,
              message: 'Drawing connections...',
            },
          }
        : m
    ))
    
    // Simulate connection drawing
    for (const block of blocks) {
      if (block.connections?.length && onConnectionAdd) {
        for (const conn of block.connections) {
          onConnectionAdd(block.id, conn)
          await sleep(100)
        }
      }
    }
    
    await sleep(500)
  }

  function getProgressMessage(progress: BuildProgress, analysis: DiagramAnalysis | null): string {
    switch (progress.stage) {
      case 'analyzing':
        return '🔍 **Analyzing your architecture diagram...**\n\nScanning for components and structure.'
      case 'extracting':
        return `📊 **Found ${analysis?.totalComponents || 0} components!**\n\nDetected ${analysis?.layers.length || 0} layers with ${analysis?.connections || 0} connections.`
      case 'building':
        return `🔨 **Building blocks...**\n\nCreating: **${progress.currentComponent}**`
      case 'connecting':
        return '🔗 **Connecting blocks...**\n\nEstablishing data flows between components.'
      case 'complete':
        return `✅ **Architecture Built Successfully!**\n\nCreated **${progress.blocksBuilt} blocks** with all connections.`
      default:
        return 'Processing...'
    }
  }

  // Generate mock response for demo when backend unavailable
  function generateMockDiagramResponse() {
    const layers = [
      { 
        name: 'L1 Market Microstructure', 
        components: ['AGGR Agent', 'TradeFuck Agent', 'CoinGlass Heatmap Agent', 'Footprint Charts'] 
      },
      { 
        name: 'L2 Indicator Layer', 
        components: ['Money V1 (Structure)', 'Money V2 (Momentum)', 'Legend (Visual Language)'] 
      },
      { 
        name: 'L3 Fusion & Signal Router', 
        components: ['Knowledgebase Fusion', 'Scenario Builder', 'Confluence Scorer', 'Signal Validator'] 
      },
      { 
        name: 'L4 Risk Management', 
        components: ['Risk Operations Agent', 'Sizing Engine', 'DCA / DCA-lite', 'Portfolio Guardrails'] 
      },
      { 
        name: 'L5 Execution & Monitoring', 
        components: ['Execution Agent', 'Monitoring & Journal', 'Audit Trail', 'Learning Loop'] 
      },
      {
        name: 'External Knowledge Cluster',
        components: ['YouTube Agent', 'External Knowledgebase', 'Backtesting & Research Loop']
      }
    ]

    const blocks = layers.flatMap((layer, layerIndex) => 
      layer.components.map((component, compIndex) => ({
        id: `block-${layerIndex}-${compIndex}`,
        type: getBlockType(layer.name),
        name: component,
        layer: layer.name,
        config: {},
        position: { 
          x: 300 + compIndex * 180, 
          y: 100 + layerIndex * 150 
        },
        connections: getConnections(layerIndex, compIndex, layers),
      }))
    )

    return {
      name: 'Trading System Architecture',
      type: 'architecture',
      description: 'Full trading system from market data to execution',
      blocks,
      analysis: {
        layers,
        totalComponents: blocks.length,
        connections: blocks.reduce((acc, b) => acc + (b.connections?.length || 0), 0),
        estimatedBlocks: blocks.length,
      },
    }
  }

  function getBlockType(layerName: string): string {
    if (layerName.includes('Microstructure')) return 'agent'
    if (layerName.includes('Indicator')) return 'processor'
    if (layerName.includes('Fusion')) return 'fusion'
    if (layerName.includes('Risk')) return 'risk'
    if (layerName.includes('Execution')) return 'execution'
    return 'data_source'
  }

  function getConnections(layerIndex: number, compIndex: number, layers: any[]): string[] {
    // Connect to next layer components
    if (layerIndex < layers.length - 2) {
      const nextLayer = layers[layerIndex + 1]
      if (nextLayer && nextLayer.components.length > 0) {
        const nextCompIndex = Math.min(compIndex, nextLayer.components.length - 1)
        return [`block-${layerIndex + 1}-${nextCompIndex}`]
      }
    }
    return []
  }

  function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  const handleSend = async (customPrompt?: string) => {
    // If we have an uploaded image and we're in architecture mode, process the diagram
    if (uploadedImage && automationType === 'architecture') {
      await processDiagram()
      return
    }

    const messageContent = customPrompt || input.trim()
    if (!messageContent || isGenerating) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageContent,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    if (!customPrompt) setInput('')

    // Add thinking message
    const thinkingId = (Date.now() + 1).toString()
    const thinkingMessage: Message = {
      id: thinkingId,
      role: 'assistant',
      content: '...',
      timestamp: new Date(),
      isTyping: true,
      status: 'pending',
    }
    setMessages(prev => [...prev, thinkingMessage])

    try {
      // Build context-aware prompt with current canvas state
      const canvasContext = currentBlocks.length > 0 
        ? `\n\nCurrent canvas has ${currentBlocks.length} blocks:\n${currentBlocks.map(b => `- ${b.name} (${b.type})`).join('\n')}`
        : '\n\nCanvas is empty - starting fresh.'
      
      const enhancedPrompt = `${messageContent}${canvasContext}`
      
      const response = await fetch('http://localhost:8000/api/v1/automations/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: enhancedPrompt,
          type: automationType,
          system_prompt: BUILDER_SYSTEM_PROMPT,  // Include comprehensive system knowledge
        })
      })

      if (!response.ok) throw new Error('Generation failed')

      const data = await response.json()

      // Format response based on automation type
      let responseContent = `I've created **${data.name}** for you!\n\n`
      responseContent += `**Type:** ${AUTOMATION_TYPES.find(t => t.value === data.type)?.label || data.type}\n`
      responseContent += `**Description:** ${data.description}\n`
      
      if (data.paper_trading !== undefined) {
        responseContent += `\n⚠️ **Paper Trading:** ${data.paper_trading ? 'Enabled (Safe Mode)' : 'DISABLED - Real Money!'}\n`
      }
      
      responseContent += `\nI've generated ${data.blocks?.length || 0} blocks. Click below to apply them to your canvas.`

      const assistantMessage: Message = {
        id: thinkingId,
        role: 'assistant',
        content: responseContent,
        timestamp: new Date(),
        automation: data,
        status: 'success',
      }

      setTypingMessageId(thinkingId)
      setMessages(prev => prev.map(m => m.id === thinkingId ? assistantMessage : m))
      onGeneratedAutomation(data)

    } catch (error) {
      // Generate helpful AI response even when backend is unavailable
      const helpfulSuggestions = getContextualSuggestions(currentBlocks)
      const fallbackContent = currentBlocks.length === 0
        ? `I'm having trouble connecting to the backend, but I can still help!

**To get started manually:**
1. Click **"Manual"** mode in the toolbar
2. Open **"Data Sources"** category in the Block Palette
3. Click **"Binance WebSocket"** to add your first block

**Suggested flow for "${messageContent.slice(0, 50)}${messageContent.length > 50 ? '...' : ''}":**
• Start with a data source (Binance WebSocket or AGGR Agent)
• Add indicators (RSI, MACD, or Moving Average)
• Add Confluence Scorer to combine signals
• Add risk management (Position Sizer, Stop Loss)
• End with an output (JSON File or Execution Agent)

Use **"Auto Layout"** to organize your blocks!`
        : `I'm having trouble connecting to the backend, but based on your current canvas:

${helpfulSuggestions.map(s => `• ${s}`).join('\n')}

**Your next step:** ${helpfulSuggestions[0] || 'Review your block configurations'}`

      const errorMessage: Message = {
        id: thinkingId,
        role: 'assistant',
        content: fallbackContent,
        timestamp: new Date(),
        status: 'error',
      }
      setMessages(prev => prev.map(m => m.id === thinkingId ? errorMessage : m))
    }
  }

  const handleRefine = (option: typeof REFINE_OPTIONS[0], automation: any) => {
    const refinePrompt = `For the automation "${automation.name}": ${option.prompt}`
    handleSend(refinePrompt)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSuggestion = (suggestion: string) => {
    setInput(suggestion)
    textareaRef.current?.focus()
  }

  // Voice input (Web Speech API)
  const toggleVoiceInput = useCallback(() => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Voice input is not supported in this browser')
      return
    }

    if (isListening) {
      setIsListening(false)
      return
    }

    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'

    recognition.onstart = () => setIsListening(true)
    recognition.onend = () => setIsListening(false)
    recognition.onerror = () => setIsListening(false)
    
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript
      setInput(prev => prev + ' ' + transcript)
      textareaRef.current?.focus()
    }

    recognition.start()
  }, [isListening])

  // Use contextual suggestions if there are blocks on canvas, otherwise use type-based suggestions
  const suggestions = currentBlocks.length > 0 
    ? contextSuggestions  // Dynamic suggestions based on canvas state
    : SUGGESTIONS[automationType] || SUGGESTIONS.scraper

  return (
    <div 
      ref={dropZoneRef}
      className="flex flex-col h-full bg-gray-900/50 border-r border-gray-800"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Hidden file input for external trigger (from canvas Upload Diagram button) */}
      <input
        ref={mainFileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) {
            handleImageUpload(file)
          }
          e.target.value = ''
        }}
      />
      
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <motion.div 
            className="p-2 bg-gradient-to-br from-purple-500/30 to-pink-500/30 rounded-lg"
            animate={{ 
              boxShadow: isGenerating 
                ? ['0 0 0 rgba(168,85,247,0)', '0 0 20px rgba(168,85,247,0.4)', '0 0 0 rgba(168,85,247,0)']
                : '0 0 0 rgba(168,85,247,0)'
            }}
            transition={{ duration: 1.5, repeat: isGenerating ? Infinity : 0 }}
          >
            <Sparkles className="w-4 h-4 text-purple-400" />
          </motion.div>
          <div>
            <h3 className="text-sm font-semibold text-white">AI Builder</h3>
            <p className="text-xs text-gray-400">
              {isGenerating ? 'Generating...' : 'Describe your automation'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {isGenerating && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="flex items-center gap-1 px-2 py-1 bg-purple-500/20 rounded-full"
            >
              <Loader2 className="w-3 h-3 animate-spin text-purple-400" />
              <span className="text-xs text-purple-300">Working</span>
            </motion.div>
          )}
        </div>
      </div>

      {/* Type Selector */}
      <div className="p-3 border-b border-gray-800">
        <DropdownMenu open={typeDropdownOpen} onOpenChange={setTypeDropdownOpen}>
          <DropdownMenuTrigger asChild>
            <Button 
              variant="outline" 
              className={cn(
                "w-full justify-between border-gray-700 hover:bg-gray-700 transition-all",
                `bg-gradient-to-r ${currentType?.color || 'from-gray-800 to-gray-800'}`
              )}
              aria-haspopup="listbox"
              aria-expanded={typeDropdownOpen}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  setTypeDropdownOpen(!typeDropdownOpen)
                }
              }}
            >
              <span className="flex items-center gap-2">
                <span className="text-lg">{currentType?.icon}</span>
                <span className="font-medium">{currentType?.label}</span>
              </span>
              <ChevronDown className={cn(
                "w-4 h-4 transition-transform duration-200",
                typeDropdownOpen ? "rotate-180" : ""
              )} />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-64 bg-gray-900 border-gray-700" role="listbox">
            <DropdownMenuLabel className="text-gray-400">Select Automation Type</DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-gray-700" />
            {AUTOMATION_TYPES.map((type) => (
              <DropdownMenuItem
                key={type.value}
                onClick={() => {
                  onAutomationTypeChange(type.value as AutomationType)
                  setTypeDropdownOpen(false)
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onAutomationTypeChange(type.value as AutomationType)
                    setTypeDropdownOpen(false)
                  }
                }}
                className={cn(
                  "cursor-pointer transition-colors focus:bg-gray-800 focus:outline-none",
                  automationType === type.value && "bg-gray-800"
                )}
                role="option"
                aria-selected={automationType === type.value}
                tabIndex={0}
              >
                <span className="flex items-center gap-3 w-full py-1">
                  <span className="text-xl">{type.icon}</span>
                  <div className="flex-1">
                    <div className="font-medium text-gray-100">{type.label}</div>
                    <div className="text-xs text-gray-400">{type.description}</div>
                  </div>
                  {automationType === type.value && (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  )}
                </span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-3" ref={scrollRef}>
        <div className="space-y-4">
          <AnimatePresence mode="popLayout">
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={cn(
                  'flex gap-2',
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                )}
              >
                {message.role === 'assistant' && (
                  <div className={cn(
                    "p-1.5 rounded-lg h-fit flex-shrink-0 transition-colors",
                    message.status === 'error' 
                      ? 'bg-red-500/20' 
                      : message.status === 'success'
                      ? 'bg-emerald-500/20'
                      : 'bg-purple-500/20'
                  )}>
                    {message.isTyping ? (
                      <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                    ) : message.status === 'error' ? (
                      <AlertCircle className="w-4 h-4 text-red-400" />
                    ) : message.status === 'success' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <Bot className="w-4 h-4 text-purple-400" />
                    )}
                  </div>
                )}
                <div
                  className={cn(
                    'max-w-[85%] rounded-lg px-3 py-2 text-sm transition-all',
                    message.role === 'user'
                      ? 'bg-emerald-600 text-white'
                      : message.status === 'error'
                      ? 'bg-red-900/30 border border-red-500/30 text-gray-200'
                      : 'bg-gray-800 text-gray-200'
                  )}
                >
                  {/* User uploaded image */}
                  {message.image && message.role === 'user' && (
                    <div className="mb-2 rounded overflow-hidden">
                      <img 
                        src={message.image} 
                        alt="Uploaded diagram" 
                        className="max-h-32 w-auto"
                      />
                    </div>
                  )}

                  {message.isTyping && !message.buildProgress ? (
                    <div className="flex items-center gap-2">
                      <motion.div className="flex gap-1">
                        {[0, 1, 2].map(i => (
                          <motion.span
                            key={i}
                            className="w-2 h-2 bg-purple-400 rounded-full"
                            animate={{ y: [0, -4, 0] }}
                            transition={{ 
                              duration: 0.6, 
                              repeat: Infinity, 
                              delay: i * 0.15 
                            }}
                          />
                        ))}
                      </motion.div>
                      <span className="text-gray-400 text-xs">Thinking...</span>
                    </div>
                  ) : typingMessageId === message.id && !message.buildProgress ? (
                    <TypingMessage 
                      content={message.content} 
                      onComplete={() => setTypingMessageId(null)}
                    />
                  ) : (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  )}
                  
                  {/* Error Action Buttons */}
                  {message.status === 'error' && message.role === 'assistant' && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-3 pt-3 border-t border-red-500/30 flex flex-wrap gap-2"
                    >
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-gray-600 hover:bg-gray-800 text-xs h-7"
                        onClick={() => {
                          // Switch to manual mode and focus on block palette
                          const manualButton = document.querySelector('[data-builder-mode="manual"]') as HTMLButtonElement
                          manualButton?.click()
                        }}
                      >
                        <Layers className="w-3 h-3 mr-1" />
                        Try Manual Mode
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-gray-600 hover:bg-gray-800 text-xs h-7"
                        onClick={() => {
                          // Switch to guided mode
                          const guidedButton = document.querySelector('[data-builder-mode="guided"]') as HTMLButtonElement
                          guidedButton?.click()
                        }}
                      >
                        <Sparkles className="w-3 h-3 mr-1" />
                        Use Template
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-emerald-500/50 hover:bg-emerald-500/20 text-xs h-7 text-emerald-400"
                        onClick={() => handleSend(input || 'Create a simple data scraper')}
                      >
                        <RefreshCw className="w-3 h-3 mr-1" />
                        Retry
                      </Button>
                    </motion.div>
                  )}

                  {/* Build Progress */}
                  {message.buildProgress && (
                    <BuildProgressIndicator progress={message.buildProgress} />
                  )}

                  {/* Diagram Analysis */}
                  {message.diagramAnalysis && message.status === 'success' && (
                    <DiagramAnalysisPreview analysis={message.diagramAnalysis} />
                  )}
                  
                  {/* Automation Result */}
                  {message.automation && !message.isTyping && message.status === 'success' && !message.diagramAnalysis && (
                    <motion.div 
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="mt-3 pt-3 border-t border-gray-700 space-y-3"
                    >
                      {/* Block Previews */}
                      <div className="space-y-2">
                        <div className="flex items-center gap-1 text-xs text-gray-400">
                          <Blocks className="w-3 h-3" />
                          <span>Generated Blocks:</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {message.automation.blocks?.slice(0, 6).map((block: any, i: number) => (
                            <BlockPreview key={i} block={block} index={i} />
                          ))}
                          {(message.automation.blocks?.length || 0) > 6 && (
                            <span className="text-xs px-2 py-1 bg-gray-700 rounded-md text-gray-400">
                              +{message.automation.blocks.length - 6} more
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          className="flex-1 bg-purple-600 hover:bg-purple-500"
                          onClick={() => onGeneratedAutomation(message.automation)}
                        >
                          <Sparkles className="w-3 h-3 mr-1" />
                          Apply to Canvas
                        </Button>
                      </div>

                      {/* Refine Options */}
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-1 text-xs text-gray-400">
                          <Settings2 className="w-3 h-3" />
                          <span>Quick Refinements:</span>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {REFINE_OPTIONS.map((option, i) => (
                            <button
                              key={i}
                              onClick={() => handleRefine(option, message.automation)}
                              disabled={isGenerating}
                              className="text-xs px-2 py-1 rounded bg-gray-700/50 text-gray-300 hover:bg-gray-600 transition-colors disabled:opacity-50"
                            >
                              <Wand2 className="w-3 h-3 inline mr-1" />
                              {option.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
                {message.role === 'user' && (
                  <div className="p-1.5 bg-emerald-500/20 rounded-lg h-fit flex-shrink-0">
                    <User className="w-4 h-4 text-emerald-400" />
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </ScrollArea>

      {/* Image Upload Zone (for architecture mode) */}
      <AnimatePresence>
        {automationType === 'architecture' && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-3 pb-2"
          >
            <ImageUploadZone
              onImageUpload={handleImageUpload}
              isDragging={isDragging}
              uploadedImage={uploadedImage}
              onClear={clearImage}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Suggestions - Show contextual or type-based suggestions */}
      <AnimatePresence>
        {(messages.length <= 1 || currentBlocks.length > 0) && !uploadedImage && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="px-3 pb-2"
          >
            <p className="text-xs text-gray-500 mb-2 flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              {currentBlocks.length > 0 
                ? `Next steps (${currentBlocks.length} blocks on canvas):`
                : automationType === 'architecture' 
                  ? 'Tips:' 
                  : 'Try one of these:'}
            </p>
            <div className="flex flex-col gap-1.5">
              {suggestions.slice(0, 3).map((suggestion, i) => (
                <motion.button
                  key={`${currentBlocks.length}-${i}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  onClick={() => !suggestion.startsWith('Your automation') && handleSuggestion(suggestion.replace(/\*\*/g, ''))}
                  className={cn(
                    "text-xs text-left px-3 py-2 rounded-lg bg-gray-800/80 text-gray-300 transition-all border border-gray-700/50",
                    !suggestion.startsWith('Your automation') && "hover:bg-gray-700 hover:translate-x-1 cursor-pointer",
                    currentBlocks.length > 0 && "border-emerald-500/30 bg-emerald-500/10"
                  )}
                >
                  {/* Render markdown bold as actual bold */}
                  {suggestion.split(/\*\*(.*?)\*\*/).map((part, j) => 
                    j % 2 === 1 ? <strong key={j} className="text-emerald-400">{part}</strong> : part
                  )}
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input */}
      <div className="p-3 border-t border-gray-800">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                automationType === 'architecture' && uploadedImage
                  ? "Add instructions or click 'Analyze' to process..."
                  : automationType === 'architecture'
                  ? "Upload a diagram above or describe your system..."
                  : `Describe your ${currentType?.label.toLowerCase() || 'automation'}...`
              }
              className="min-h-[60px] max-h-[120px] resize-none bg-gray-800 border-gray-700 text-sm pr-20"
              disabled={isGenerating}
            />
            <div className="absolute right-2 bottom-2 flex items-center gap-1">
              {automationType !== 'architecture' && (
                <label className="p-1.5 rounded bg-gray-700/50 text-gray-400 hover:text-gray-300 cursor-pointer transition-colors">
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      if (file) {
                        handleImageUpload(file)
                        onAutomationTypeChange('architecture')
                      }
                    }}
                  />
                  <ImageIcon className="w-4 h-4" />
                </label>
              )}
              <button
                onClick={toggleVoiceInput}
                disabled={isGenerating}
                className={cn(
                  "p-1.5 rounded transition-colors",
                  isListening 
                    ? "bg-red-500/20 text-red-400" 
                    : "bg-gray-700/50 text-gray-400 hover:text-gray-300"
                )}
              >
                {isListening ? (
                  <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ repeat: Infinity }}>
                    <MicOff className="w-4 h-4" />
                  </motion.div>
                ) : (
                  <Mic className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
          <Button
            onClick={() => handleSend()}
            disabled={(!input.trim() && !uploadedImage) || isGenerating}
            className={cn(
              "self-end transition-all",
              uploadedImage 
                ? "bg-purple-600 hover:bg-purple-500" 
                : "bg-emerald-600 hover:bg-emerald-500"
            )}
          >
            {isGenerating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : uploadedImage ? (
              <>
                <Zap className="w-4 h-4 mr-1" />
                Analyze
              </>
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
        
        {/* Quick Actions */}
        <div className="flex items-center gap-2 mt-2">
          <span className="text-xs text-gray-500">Quick:</span>
          <button
            onClick={() => {
              setMessages([{
                id: '1',
                role: 'assistant',
                content: automationType === 'architecture'
                  ? `Hi! Upload an architecture diagram and I'll build it for you!`
                  : `Hi! I'm ready to create a new ${currentType?.label}.\n\nDescribe what you want to build.`,
                timestamp: new Date(),
              }])
              clearImage()
            }}
            className="text-xs text-gray-400 hover:text-gray-300 flex items-center gap-1"
          >
            <RotateCcw className="w-3 h-3" />
            Clear chat
          </button>
        </div>
      </div>

      {/* Drag overlay */}
      <AnimatePresence>
        {isDragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-purple-500/10 backdrop-blur-sm border-2 border-dashed border-purple-400 rounded-lg flex items-center justify-center z-50"
          >
            <div className="text-center">
              <Upload className="w-12 h-12 text-purple-400 mx-auto mb-2" />
              <p className="text-lg font-medium text-purple-300">Drop your diagram here</p>
              <p className="text-sm text-purple-400/70">I'll analyze and build the blocks</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default AIBuilderChat
