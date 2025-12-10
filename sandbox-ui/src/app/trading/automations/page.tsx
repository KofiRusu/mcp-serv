'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Plus,
  Search,
  Play,
  Square,
  Rocket,
  Trash2,
  MoreVertical,
  RefreshCw,
  Code,
  Terminal,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  Clock,
  ChevronLeft,
  Sparkles,
  ExternalLink,
  Database
} from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

interface Automation {
  id: string
  name: string
  description: string
  type: string
  deployment_type: string
  status: 'draft' | 'testing' | 'running' | 'deployed' | 'stopped' | 'error' | 'paused'
  blocks: any[]
  config: Record<string, any>
  generated_code: string | null
  docker_image: string | null
  container_id: string | null
  paper_trading: boolean
  symbols: string[]
  exchange: string | null
  created_at: string
  updated_at: string
  last_run: string | null
  run_count: number
  total_pnl: number
  win_rate: number | null
  total_trades: number
  error_message: string | null
  logs: string[]
}

const STATUS_CONFIG = {
  draft: { icon: AlertCircle, color: 'text-gray-400', bg: 'bg-gray-500/10', label: 'Draft' },
  testing: { icon: Loader2, color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Testing' },
  running: { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Running' },
  deployed: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Deployed' },
  stopped: { icon: Square, color: 'text-gray-400', bg: 'bg-gray-500/10', label: 'Stopped' },
  error: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Error' },
  paused: { icon: AlertCircle, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Paused' },
}

const TYPE_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
  scraper: { icon: '📊', label: 'Scraper', color: 'text-emerald-400' },
  trading_bot: { icon: '🤖', label: 'Trading Bot', color: 'text-cyan-400' },
  alert: { icon: '🔔', label: 'Alert', color: 'text-orange-400' },
  signal: { icon: '📈', label: 'Signal', color: 'text-pink-400' },
  risk: { icon: '🛡️', label: 'Risk Monitor', color: 'text-red-400' },
  backtest: { icon: '📜', label: 'Backtest', color: 'text-purple-400' },
}

export default function AutomationsPage() {
  const router = useRouter()
  const [automations, setAutomations] = useState<Automation[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedAutomation, setSelectedAutomation] = useState<Automation | null>(null)
  const [showLogsDialog, setShowLogsDialog] = useState(false)
  const [logs, setLogs] = useState<string>('')

  // Load automations from backend and localStorage
  const loadAutomations = useCallback(async () => {
    try {
      let backendAutomations: Automation[] = []
      let localAutomations: Automation[] = []

      // Try to load from backend
      try {
        const res = await fetch('http://localhost:8000/api/v1/automations/')
        if (res.ok) {
          backendAutomations = await res.json()
        }
      } catch {
        console.debug('Backend unavailable, loading from localStorage only')
      }

      // Always load from localStorage
      try {
        const stored = localStorage.getItem('local-automations')
        if (stored) {
          localAutomations = JSON.parse(stored)
        }
      } catch {
        console.debug('Failed to load from localStorage')
      }

      // Merge: backend automations take priority, add local-only ones
      const backendIds = new Set(backendAutomations.map(a => a.id))
      const mergedAutomations = [
        ...backendAutomations,
        ...localAutomations.filter(a => !backendIds.has(a.id))
      ]

      setAutomations(mergedAutomations)
    } catch (e) {
      console.debug('Failed to load automations:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAutomations()
    // Poll for updates
    const interval = setInterval(loadAutomations, 5000)
    return () => clearInterval(interval)
  }, [loadAutomations])

  // Actions
  const handleRun = async (id: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/automations/${id}/run`, {
        method: 'POST'
      })
      if (res.ok) {
        toast.success('Automation started')
        loadAutomations()
      } else {
        const error = await res.json()
        toast.error(error.detail || 'Failed to start')
      }
    } catch (e) {
      toast.error('Failed to start automation')
    }
  }

  const handleStop = async (id: string) => {
    try {
      await fetch(`http://localhost:8000/api/v1/automations/${id}/stop`, { method: 'POST' })
      toast.info('Automation stopped')
      loadAutomations()
    } catch (e) {
      toast.error('Failed to stop automation')
    }
  }

  const handleDeploy = async (id: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/automations/${id}/deploy`, {
        method: 'POST'
      })
      if (res.ok) {
        toast.success('Deployed to Docker!')
        loadAutomations()
      } else {
        const error = await res.json()
        toast.error(error.detail || 'Deploy failed')
      }
    } catch (e) {
      toast.error('Failed to deploy')
    }
  }

  const handleUndeploy = async (id: string) => {
    try {
      await fetch(`http://localhost:8000/api/v1/automations/${id}/undeploy`, { method: 'POST' })
      toast.info('Container stopped')
      loadAutomations()
    } catch (e) {
      toast.error('Failed to undeploy')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this automation?')) return
    
    try {
      // Check if it's a local automation
      if (id.startsWith('local-')) {
        // Delete from localStorage
        const stored = localStorage.getItem('local-automations')
        if (stored) {
          const localAutomations = JSON.parse(stored)
          const filtered = localAutomations.filter((a: Automation) => a.id !== id)
          localStorage.setItem('local-automations', JSON.stringify(filtered))
        }
        toast.success('Automation deleted')
      } else {
        // Delete from backend
        await fetch(`http://localhost:8000/api/v1/automations/${id}`, { method: 'DELETE' })
        toast.success('Automation deleted')
      }
      loadAutomations()
    } catch (e) {
      toast.error('Failed to delete')
    }
  }

  const handleViewLogs = async (automation: Automation) => {
    setSelectedAutomation(automation)
    setShowLogsDialog(true)
    
    try {
      // Try container logs first
      let res = await fetch(`http://localhost:8000/api/v1/automations/${automation.id}/container-logs?lines=100`)
      if (res.ok) {
        const data = await res.json()
        if (data.logs) {
          setLogs(data.logs)
          return
        }
      }
      
      // Fall back to dev mode output
      res = await fetch(`http://localhost:8000/api/v1/automations/${automation.id}/output?lines=100`)
      if (res.ok) {
        const data = await res.json()
        setLogs(data.output?.join('\n') || 'No logs available')
      }
    } catch (e) {
      setLogs('Failed to fetch logs')
    }
  }

  // Filter automations
  const filteredAutomations = automations.filter(a =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Group by status
  const deployed = filteredAutomations.filter(a => a.status === 'deployed')
  const running = filteredAutomations.filter(a => a.status === 'testing' || a.status === 'running')
  const others = filteredAutomations.filter(a => !['deployed', 'testing', 'running'].includes(a.status))

  const renderAutomationCard = (automation: Automation) => {
    const statusConfig = STATUS_CONFIG[automation.status] || STATUS_CONFIG.draft
    const StatusIcon = statusConfig.icon
    const typeConfig = TYPE_CONFIG[automation.type] || { icon: '📊', label: automation.type, color: 'text-gray-400' }

    return (
      <Card 
        key={automation.id} 
        className="bg-gray-900/50 border-gray-800 hover:border-gray-700 transition-colors cursor-pointer"
        onClick={() => router.push(`/editor?id=${automation.id}`)}
      >
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <div className={cn('p-2 rounded-lg text-lg', statusConfig.bg)}>
                {typeConfig.icon}
              </div>
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  {automation.name}
                  {!automation.paper_trading && automation.type === 'trading_bot' && (
                    <Badge variant="destructive" className="text-[10px] px-1 py-0">
                      LIVE
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription className="text-xs flex items-center gap-1">
                  <span className={typeConfig.color}>{typeConfig.label}</span>
                  <span className="text-gray-600">•</span>
                  {new Date(automation.created_at).toLocaleDateString()}
                  {automation.symbols?.length > 0 && (
                    <>
                      <span className="text-gray-600">•</span>
                      <span className="text-gray-400">{automation.symbols.slice(0, 2).join(', ')}</span>
                    </>
                  )}
                </CardDescription>
              </div>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => e.stopPropagation()}>
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-gray-900 border-gray-700">
                <DropdownMenuItem asChild>
                  <Link href={`/editor?id=${automation.id}`} className="cursor-pointer">
                    <Code className="h-4 w-4 mr-2" />
                    Edit
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleViewLogs(automation)} className="cursor-pointer">
                  <Terminal className="h-4 w-4 mr-2" />
                  View Logs
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-gray-700" />
                <DropdownMenuItem
                  onClick={() => handleDelete(automation.id)}
                  className="text-red-400 cursor-pointer"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge className={cn('gap-1', statusConfig.bg, statusConfig.color, 'border-0')}>
                <StatusIcon className={cn('h-3 w-3', (automation.status === 'testing' || automation.status === 'running') && 'animate-spin')} />
                {statusConfig.label}
              </Badge>
              
              {/* Trading stats for trading bots */}
              {automation.type === 'trading_bot' && automation.total_trades > 0 && (
                <span className="text-xs text-gray-400">
                  {automation.total_trades} trades
                  {automation.win_rate !== null && ` • ${automation.win_rate.toFixed(0)}% win`}
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-1">
              {automation.status === 'testing' || automation.status === 'running' ? (
                <Button size="sm" variant="destructive" onClick={() => handleStop(automation.id)}>
                  <Square className="h-3 w-3 mr-1" />
                  Stop
                </Button>
              ) : automation.status === 'deployed' ? (
                <Button size="sm" variant="outline" onClick={() => handleUndeploy(automation.id)}>
                  <Square className="h-3 w-3 mr-1" />
                  Stop
                </Button>
              ) : (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRun(automation.id)}
                    disabled={!automation.generated_code}
                  >
                    <Play className="h-3 w-3 mr-1" />
                    Test
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleDeploy(automation.id)}
                    disabled={!automation.generated_code}
                    className="bg-purple-600 hover:bg-purple-500"
                  >
                    <Rocket className="h-3 w-3 mr-1" />
                    Deploy
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* PnL for trading bots */}
          {automation.type === 'trading_bot' && automation.total_pnl !== 0 && (
            <div className={cn(
              'mt-2 text-sm font-medium',
              automation.total_pnl > 0 ? 'text-emerald-400' : 'text-red-400'
            )}>
              PnL: {automation.total_pnl > 0 ? '+' : ''}{automation.total_pnl.toFixed(2)} USD
            </div>
          )}

          {automation.error_message && (
            <p className="mt-2 text-xs text-red-400 truncate">
              Error: {automation.error_message}
            </p>
          )}

          {automation.last_run && (
            <p className="mt-2 text-xs text-gray-500 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Last run: {new Date(automation.last_run).toLocaleString()}
            </p>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/trading">
                <Button variant="ghost" size="sm">
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Trading
                </Button>
              </Link>
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-purple-400" />
                <h1 className="text-xl font-bold">My Automations</h1>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search automations..."
                  className="pl-9 w-64 bg-gray-800 border-gray-700"
                />
              </div>
              <Button onClick={loadAutomations} variant="outline" size="icon">
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Link href="/editor">
                <Button className="bg-emerald-600 hover:bg-emerald-500">
                  <Plus className="h-4 w-4 mr-2" />
                  New Automation
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : automations.length === 0 ? (
          <div className="text-center py-20">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-800 mb-4">
              <Sparkles className="h-8 w-8 text-purple-400" />
            </div>
            <h2 className="text-xl font-semibold mb-2">No automations yet</h2>
            <p className="text-gray-400 mb-6">
              Create your first automation to start collecting data
            </p>
            <Link href="/editor">
              <Button className="bg-emerald-600 hover:bg-emerald-500">
                <Plus className="h-4 w-4 mr-2" />
                Create Automation
              </Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Deployed */}
            {deployed.length > 0 && (
              <section>
                <h2 className="text-sm font-medium text-emerald-400 mb-3 flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Deployed ({deployed.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {deployed.map(renderAutomationCard)}
                </div>
              </section>
            )}

            {/* Running */}
            {running.length > 0 && (
              <section>
                <h2 className="text-sm font-medium text-amber-400 mb-3 flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running ({running.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {running.map(renderAutomationCard)}
                </div>
              </section>
            )}

            {/* Others */}
            {others.length > 0 && (
              <section>
                <h2 className="text-sm font-medium text-gray-400 mb-3">
                  All Automations ({others.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {others.map(renderAutomationCard)}
                </div>
              </section>
            )}
          </div>
        )}
      </div>

      {/* Logs Dialog */}
      <Dialog open={showLogsDialog} onOpenChange={setShowLogsDialog}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-3xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Terminal className="h-5 w-5" />
              {selectedAutomation?.name} - Logs
            </DialogTitle>
            <DialogDescription className="text-gray-400">
              Recent output from the automation
            </DialogDescription>
          </DialogHeader>
          
          <ScrollArea className="h-96 mt-4">
            <pre className="font-mono text-xs text-gray-300 whitespace-pre-wrap p-4 bg-black/50 rounded-lg">
              {logs || 'No logs available'}
            </pre>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  )
}

