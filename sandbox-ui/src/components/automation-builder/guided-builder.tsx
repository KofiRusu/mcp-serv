'use client'

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import {
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
  Circle,
  Sparkles,
  Database,
  Activity,
  Bell,
  Shield,
  Rocket,
  TrendingUp,
  BarChart3,
  FileImage,
} from 'lucide-react'
import type { Block, BlockType } from './block-node'
import type { AutomationType } from './builder-canvas'

interface WizardStep {
  id: string
  title: string
  description: string
  icon: React.ElementType
}

const WIZARD_STEPS: WizardStep[] = [
  { id: 'type', title: 'Automation Type', description: 'What do you want to build?', icon: Sparkles },
  { id: 'source', title: 'Data Source', description: 'Where will data come from?', icon: Database },
  { id: 'logic', title: 'Logic & Signals', description: 'Define conditions and indicators', icon: Activity },
  { id: 'output', title: 'Output & Actions', description: 'What should happen?', icon: Bell },
  { id: 'review', title: 'Review & Create', description: 'Confirm your automation', icon: Rocket },
]

interface AutomationTypeOption {
  value: AutomationType
  label: string
  icon: React.ElementType
  description: string
  color: string
}

const AUTOMATION_TYPES: AutomationTypeOption[] = [
  { value: 'scraper', label: 'Data Scraper', icon: Database, description: 'Collect and store market data', color: 'emerald' },
  { value: 'trading_bot', label: 'Trading Bot', icon: TrendingUp, description: 'Automated order execution', color: 'cyan' },
  { value: 'alert', label: 'Alert System', icon: Bell, description: 'Notifications & webhooks', color: 'orange' },
  { value: 'signal', label: 'Signal Generator', icon: BarChart3, description: 'Generate trading signals', color: 'pink' },
  { value: 'risk', label: 'Risk Monitor', icon: Shield, description: 'Portfolio risk tracking', color: 'red' },
  { value: 'backtest', label: 'Backtest', icon: Activity, description: 'Test on historical data', color: 'purple' },
  { value: 'architecture', label: 'From Diagram', icon: FileImage, description: 'Upload architecture diagram', color: 'indigo' },
]

interface DataSourceOption {
  id: string
  name: string
  description: string
  config: Record<string, any>
  icon: React.ElementType
}

const DATA_SOURCES: DataSourceOption[] = [
  { id: 'binance-ws', name: 'Binance WebSocket', description: 'Real-time market data', config: { symbol: 'BTCUSDT', stream: 'btcusdt@aggTrade' }, icon: Database },
  { id: 'binance-rest', name: 'Binance REST', description: 'REST API endpoints', config: { symbol: 'BTC/USDT', endpoint: 'ticker' }, icon: Database },
  { id: 'coingecko', name: 'CoinGecko API', description: 'Market aggregator', config: { coins: ['bitcoin'], interval: 60 }, icon: Database },
  { id: 'custom', name: 'Custom API', description: 'Your own endpoint', config: { url: '', interval: 60 }, icon: Database },
]

interface LogicOption {
  id: string
  name: string
  description: string
  blockType: BlockType
  config: Record<string, any>
}

const LOGIC_OPTIONS: LogicOption[] = [
  { id: 'rsi', name: 'RSI', description: 'Relative Strength Index', blockType: 'indicator', config: { period: 14, overbought: 70, oversold: 30 } },
  { id: 'macd', name: 'MACD', description: 'Moving Average Convergence', blockType: 'indicator', config: { fast: 12, slow: 26, signal: 9 } },
  { id: 'ma', name: 'Moving Average', description: 'SMA/EMA calculation', blockType: 'indicator', config: { period: 20, type: 'SMA' } },
  { id: 'price-condition', name: 'Price Condition', description: 'Price threshold trigger', blockType: 'condition', config: { above: 0, below: 0 } },
  { id: 'volume-filter', name: 'Volume Filter', description: 'Filter by volume', blockType: 'filter', config: { minVolume: 1000 } },
]

interface OutputOption {
  id: string
  name: string
  description: string
  blockType: BlockType
  config: Record<string, any>
}

const OUTPUT_OPTIONS: Record<AutomationType, OutputOption[]> = {
  scraper: [
    { id: 'json-file', name: 'JSON File', description: 'Save data to file', blockType: 'output', config: { output_dir: '/app/data' } },
    { id: 'database', name: 'Database', description: 'Store in database', blockType: 'output', config: { connectionString: '' } },
    { id: 'websocket', name: 'WebSocket Broadcast', description: 'Stream to clients', blockType: 'output', config: { port: 8080 } },
  ],
  trading_bot: [
    { id: 'market-order', name: 'Market Order', description: 'Execute immediately', blockType: 'order', config: { exchange: 'binance', side: 'buy' } },
    { id: 'limit-order', name: 'Limit Order', description: 'Execute at price', blockType: 'order', config: { exchange: 'binance', side: 'buy', price: 0 } },
    { id: 'stop-loss', name: 'Stop Loss', description: 'Automatic risk limit', blockType: 'stop_loss', config: { type: 'percent', value: 2 } },
  ],
  alert: [
    { id: 'console', name: 'Console Alert', description: 'Log to console', blockType: 'notification', config: { type: 'console' } },
    { id: 'discord', name: 'Discord Webhook', description: 'Send to Discord', blockType: 'notification', config: { webhookUrl: '' } },
    { id: 'telegram', name: 'Telegram Alert', description: 'Send to Telegram', blockType: 'notification', config: { botToken: '', chatId: '' } },
    { id: 'webhook', name: 'Custom Webhook', description: 'HTTP webhook', blockType: 'webhook', config: { url: '' } },
  ],
  signal: [
    { id: 'signal-output', name: 'Signal Output', description: 'Emit trading signal', blockType: 'signal', config: {} },
    { id: 'json-file', name: 'JSON File', description: 'Save signals to file', blockType: 'output', config: { output_dir: '/app/signals' } },
  ],
  risk: [
    { id: 'risk-check', name: 'Risk Check', description: 'Validate risk limits', blockType: 'risk_check', config: { maxDrawdown: 10 } },
    { id: 'position-sizer', name: 'Position Sizer', description: 'Calculate size', blockType: 'position_size', config: { method: 'fixed', risk: 1 } },
    { id: 'alert', name: 'Alert', description: 'Send notification', blockType: 'notification', config: { type: 'console' } },
  ],
  backtest: [
    { id: 'entry', name: 'Entry Signal', description: 'Define entry point', blockType: 'entry', config: { type: 'market' } },
    { id: 'exit', name: 'Exit Signal', description: 'Define exit point', blockType: 'exit', config: { type: 'market' } },
    { id: 'report', name: 'Backtest Report', description: 'Generate results', blockType: 'output', config: { metrics: ['pnl', 'sharpe', 'drawdown'] } },
  ],
}

interface GuidedBuilderProps {
  onComplete: (blocks: Block[], automationType: AutomationType, name: string) => void
  onCancel: () => void
}

export function GuidedBuilder({ onComplete, onCancel }: GuidedBuilderProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [automationType, setAutomationType] = useState<AutomationType>('scraper')
  const [automationName, setAutomationName] = useState('')
  const [selectedSource, setSelectedSource] = useState<string>('')
  const [selectedLogic, setSelectedLogic] = useState<string[]>([])
  const [selectedOutputs, setSelectedOutputs] = useState<string[]>([])
  const [customConfigs, setCustomConfigs] = useState<Record<string, Record<string, any>>>({})

  const currentStep = WIZARD_STEPS[currentStepIndex]
  const isFirstStep = currentStepIndex === 0
  const isLastStep = currentStepIndex === WIZARD_STEPS.length - 1

  const canProceed = useCallback(() => {
    switch (currentStep.id) {
      case 'type':
        return automationType && automationName.trim().length > 0
      case 'source':
        return selectedSource !== ''
      case 'logic':
        return true // Optional step
      case 'output':
        return selectedOutputs.length > 0
      case 'review':
        return true
      default:
        return true
    }
  }, [currentStep.id, automationType, automationName, selectedSource, selectedOutputs])

  const handleNext = () => {
    if (isLastStep) {
      handleComplete()
    } else {
      setCurrentStepIndex(prev => prev + 1)
    }
  }

  const handleBack = () => {
    if (!isFirstStep) {
      setCurrentStepIndex(prev => prev - 1)
    }
  }

  const handleComplete = () => {
    // Generate blocks from selections
    const blocks: Block[] = []
    let yPos = 100

    // Add source block
    const source = DATA_SOURCES.find(s => s.id === selectedSource)
    if (source) {
      blocks.push({
        id: `block-${Date.now()}-source`,
        type: 'source',
        name: source.name,
        config: { ...source.config, ...customConfigs[source.id] },
        position: { x: 100, y: yPos },
        connections: [],
      })
      yPos += 120
    }

    // Add logic blocks
    selectedLogic.forEach((logicId, idx) => {
      const logic = LOGIC_OPTIONS.find(l => l.id === logicId)
      if (logic) {
        const blockId = `block-${Date.now()}-logic-${idx}`
        blocks.push({
          id: blockId,
          type: logic.blockType,
          name: logic.name,
          config: { ...logic.config, ...customConfigs[logicId] },
          position: { x: 100, y: yPos },
          connections: [],
        })
        // Connect to previous block
        if (blocks.length > 1) {
          blocks[blocks.length - 2].connections.push(blockId)
        }
        yPos += 120
      }
    })

    // Add output blocks
    const outputs = OUTPUT_OPTIONS[automationType] || []
    selectedOutputs.forEach((outputId, idx) => {
      const output = outputs.find(o => o.id === outputId)
      if (output) {
        const blockId = `block-${Date.now()}-output-${idx}`
        blocks.push({
          id: blockId,
          type: output.blockType,
          name: output.name,
          config: { ...output.config, ...customConfigs[outputId] },
          position: { x: 100, y: yPos },
          connections: [],
        })
        // Connect to previous block
        if (blocks.length > 1) {
          blocks[blocks.length - 2].connections.push(blockId)
        }
        yPos += 120
      }
    })

    onComplete(blocks, automationType, automationName)
  }

  const updateConfig = (id: string, key: string, value: any) => {
    setCustomConfigs(prev => ({
      ...prev,
      [id]: { ...prev[id], [key]: value }
    }))
  }

  const renderStepContent = () => {
    switch (currentStep.id) {
      case 'type':
        return (
          <div className="space-y-6">
            <div>
              <Label className="text-sm text-gray-300 mb-2 block">Automation Name</Label>
              <Input
                value={automationName}
                onChange={(e) => setAutomationName(e.target.value)}
                placeholder="My Awesome Automation"
                className="bg-gray-800 border-gray-700"
              />
            </div>

            <div>
              <Label className="text-sm text-gray-300 mb-3 block">What do you want to build?</Label>
              <div className="grid grid-cols-2 gap-3">
                {AUTOMATION_TYPES.map((type) => {
                  const Icon = type.icon
                  return (
                    <motion.button
                      key={type.value}
                      onClick={() => setAutomationType(type.value)}
                      className={cn(
                        'p-4 rounded-xl border-2 text-left transition-all',
                        automationType === type.value
                          ? `border-${type.color}-500 bg-${type.color}-500/10`
                          : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                      )}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <div className={cn('p-2 rounded-lg w-fit mb-2', `bg-${type.color}-500/20`)}>
                        <Icon className={cn('w-5 h-5', `text-${type.color}-400`)} />
                      </div>
                      <h4 className="font-medium text-white">{type.label}</h4>
                      <p className="text-xs text-gray-400 mt-1">{type.description}</p>
                    </motion.button>
                  )
                })}
              </div>
            </div>
          </div>
        )

      case 'source':
        return (
          <div className="space-y-4">
            <RadioGroup value={selectedSource} onValueChange={setSelectedSource}>
              {DATA_SOURCES.map((source) => {
                const Icon = source.icon
                return (
                  <motion.div
                    key={source.id}
                    className={cn(
                      'flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer',
                      selectedSource === source.id
                        ? 'border-emerald-500 bg-emerald-500/10'
                        : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                    )}
                    onClick={() => setSelectedSource(source.id)}
                    whileHover={{ scale: 1.01 }}
                  >
                    <RadioGroupItem value={source.id} id={source.id} className="mt-1" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Icon className="w-4 h-4 text-emerald-400" />
                        <Label htmlFor={source.id} className="font-medium text-white cursor-pointer">
                          {source.name}
                        </Label>
                      </div>
                      <p className="text-xs text-gray-400 mt-1">{source.description}</p>
                      
                      {selectedSource === source.id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          className="mt-3 pt-3 border-t border-gray-700 space-y-2"
                        >
                          {Object.entries(source.config).map(([key, value]) => (
                            <div key={key}>
                              <Label className="text-xs text-gray-400 capitalize">{key.replace(/_/g, ' ')}</Label>
                              <Input
                                value={customConfigs[source.id]?.[key] ?? (typeof value === 'object' ? JSON.stringify(value) : value)}
                                onChange={(e) => updateConfig(source.id, key, e.target.value)}
                                className="h-8 bg-gray-700 border-gray-600 text-sm"
                              />
                            </div>
                          ))}
                        </motion.div>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </RadioGroup>
          </div>
        )

      case 'logic':
        return (
          <div className="space-y-4">
            <p className="text-sm text-gray-400 mb-4">
              Select indicators and conditions (optional)
            </p>
            {LOGIC_OPTIONS.map((logic) => (
              <motion.div
                key={logic.id}
                className={cn(
                  'flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer',
                  selectedLogic.includes(logic.id)
                    ? 'border-pink-500 bg-pink-500/10'
                    : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                )}
                onClick={() => {
                  setSelectedLogic(prev =>
                    prev.includes(logic.id)
                      ? prev.filter(l => l !== logic.id)
                      : [...prev, logic.id]
                  )
                }}
                whileHover={{ scale: 1.01 }}
              >
                <Checkbox
                  checked={selectedLogic.includes(logic.id)}
                  className="mt-1"
                />
                <div className="flex-1">
                  <h4 className="font-medium text-white">{logic.name}</h4>
                  <p className="text-xs text-gray-400">{logic.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        )

      case 'output':
        const outputs = OUTPUT_OPTIONS[automationType] || []
        return (
          <div className="space-y-4">
            <p className="text-sm text-gray-400 mb-4">
              What should happen when conditions are met?
            </p>
            {outputs.map((output) => (
              <motion.div
                key={output.id}
                className={cn(
                  'flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer',
                  selectedOutputs.includes(output.id)
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                )}
                onClick={() => {
                  setSelectedOutputs(prev =>
                    prev.includes(output.id)
                      ? prev.filter(o => o !== output.id)
                      : [...prev, output.id]
                  )
                }}
                whileHover={{ scale: 1.01 }}
              >
                <Checkbox
                  checked={selectedOutputs.includes(output.id)}
                  className="mt-1"
                />
                <div className="flex-1">
                  <h4 className="font-medium text-white">{output.name}</h4>
                  <p className="text-xs text-gray-400">{output.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        )

      case 'review':
        const typeInfo = AUTOMATION_TYPES.find(t => t.value === automationType)
        const sourceInfo = DATA_SOURCES.find(s => s.id === selectedSource)
        const outputsInfo = (OUTPUT_OPTIONS[automationType] || []).filter(o => selectedOutputs.includes(o.id))
        const logicInfo = LOGIC_OPTIONS.filter(l => selectedLogic.includes(l.id))

        return (
          <div className="space-y-6">
            <div className="p-4 bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-xl border border-purple-500/30">
              <h3 className="font-semibold text-white text-lg mb-1">{automationName}</h3>
              <p className="text-sm text-gray-400">{typeInfo?.label} • {typeInfo?.description}</p>
            </div>

            <div className="space-y-4">
              <div>
                <Label className="text-xs text-gray-400 uppercase tracking-wider">Data Source</Label>
                <div className="mt-2 p-3 bg-gray-800/50 rounded-lg">
                  <p className="font-medium text-white">{sourceInfo?.name}</p>
                  <p className="text-xs text-gray-400">{sourceInfo?.description}</p>
                </div>
              </div>

              {logicInfo.length > 0 && (
                <div>
                  <Label className="text-xs text-gray-400 uppercase tracking-wider">Logic & Signals</Label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {logicInfo.map(l => (
                      <Badge key={l.id} variant="secondary">{l.name}</Badge>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <Label className="text-xs text-gray-400 uppercase tracking-wider">Outputs & Actions</Label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {outputsInfo.map(o => (
                    <Badge key={o.id} variant="secondary">{o.name}</Badge>
                  ))}
                </div>
              </div>
            </div>

            <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
              <p className="text-sm text-emerald-300">
                <CheckCircle2 className="w-4 h-4 inline mr-2" />
                Ready to create! Click "Create Automation" to build your blocks.
              </p>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="h-full flex flex-col bg-gray-900/95 backdrop-blur-sm">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <h2 className="text-lg font-semibold text-white">Guided Builder</h2>
        <p className="text-sm text-gray-400">Step-by-step automation creation</p>
      </div>

      {/* Progress */}
      <div className="px-4 py-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          {WIZARD_STEPS.map((step, idx) => {
            const Icon = step.icon
            const isActive = idx === currentStepIndex
            const isComplete = idx < currentStepIndex

            return (
              <div key={step.id} className="flex items-center">
                <div
                  className={cn(
                    'flex items-center justify-center w-8 h-8 rounded-full transition-colors',
                    isActive && 'bg-purple-500 text-white',
                    isComplete && 'bg-emerald-500 text-white',
                    !isActive && !isComplete && 'bg-gray-700 text-gray-400'
                  )}
                >
                  {isComplete ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : (
                    <Icon className="w-4 h-4" />
                  )}
                </div>
                {idx < WIZARD_STEPS.length - 1 && (
                  <div
                    className={cn(
                      'w-12 h-0.5 mx-1',
                      idx < currentStepIndex ? 'bg-emerald-500' : 'bg-gray-700'
                    )}
                  />
                )}
              </div>
            )
          })}
        </div>
        <div className="mt-2">
          <p className="text-sm font-medium text-white">{currentStep.title}</p>
          <p className="text-xs text-gray-400">{currentStep.description}</p>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1 p-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
          >
            {renderStepContent()}
          </motion.div>
        </AnimatePresence>
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800 flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={onCancel}
          className="text-gray-400"
        >
          Cancel
        </Button>
        
        <div className="flex gap-2">
          {!isFirstStep && (
            <Button
              variant="outline"
              onClick={handleBack}
              className="gap-1"
            >
              <ChevronLeft className="w-4 h-4" />
              Back
            </Button>
          )}
          <Button
            onClick={handleNext}
            disabled={!canProceed()}
            className="gap-1 bg-purple-600 hover:bg-purple-500"
          >
            {isLastStep ? (
              <>
                <Rocket className="w-4 h-4" />
                Create Automation
              </>
            ) : (
              <>
                Next
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default GuidedBuilder

