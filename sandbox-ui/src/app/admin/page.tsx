'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { 
  Activity, 
  Database, 
  Newspaper, 
  TrendingUp, 
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Settings,
  Shield,
  Monitor,
  Cpu,
  HardDrive,
  Zap,
  Users,
  Globe,
  BarChart3
} from 'lucide-react'

interface ScraperStatus {
  marketData: {
    available: boolean
    lastUpdate: string | null
    files: number
  }
  news: {
    available: boolean
    lastUpdate: string | null
    count: number
  }
  sentiment: {
    available: boolean
    lastUpdate: string | null
  }
}

export default function AdminDashboard() {
  const [status, setStatus] = useState<ScraperStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/scraped-data?type=status')
      if (!response.ok) throw new Error('Failed to fetch status')
      const data = await response.json()
      setStatus(data)
      setError(null)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // Refresh status every 30 seconds
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const formatTimestamp = (ts: string | null) => {
    if (!ts) return 'Never'
    const date = new Date(ts)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-[#0d0d14]">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-purple-700 flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Admin Dashboard</h1>
                <p className="text-sm text-gray-500">System monitoring & configuration</p>
              </div>
            </div>
            <button
              onClick={fetchStatus}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* System Health Overview */}
        <section>
          <h2 className="text-lg font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-violet-500" />
            System Health
          </h2>
          
          {error ? (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
              {error}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Market Data Status */}
              <StatusCard
                title="Market Data Scraper"
                icon={<TrendingUp className="w-5 h-5" />}
                status={status?.marketData.available ? 'online' : 'offline'}
                loading={loading}
                details={[
                  { label: 'Symbols tracked', value: status?.marketData.files?.toString() || '0' },
                  { label: 'Last update', value: formatTimestamp(status?.marketData.lastUpdate || null) },
                ]}
              />

              {/* News Scraper Status */}
              <StatusCard
                title="News Scraper"
                icon={<Newspaper className="w-5 h-5" />}
                status={status?.news.available ? 'online' : 'offline'}
                loading={loading}
                details={[
                  { label: 'Articles today', value: status?.news.count?.toString() || '0' },
                  { label: 'Last update', value: formatTimestamp(status?.news.lastUpdate || null) },
                ]}
              />

              {/* Sentiment Scraper Status */}
              <StatusCard
                title="Sentiment Analyzer"
                icon={<Zap className="w-5 h-5" />}
                status={status?.sentiment.available ? 'online' : 'offline'}
                loading={loading}
                details={[
                  { label: 'Status', value: status?.sentiment.available ? 'Active' : 'Inactive' },
                  { label: 'Last update', value: formatTimestamp(status?.sentiment.lastUpdate || null) },
                ]}
              />
            </div>
          )}
        </section>

        {/* Quick Actions */}
        <section>
          <h2 className="text-lg font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5 text-violet-500" />
            Quick Actions
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <QuickActionCard
              title="Trading Dashboard"
              description="View live market data and trading interface"
              href="/trading"
              icon={<TrendingUp className="w-6 h-6" />}
            />
            <QuickActionCard
              title="Trading Lab"
              description="Backtest strategies and analyze performance"
              href="/trading/lab"
              icon={<Cpu className="w-6 h-6" />}
            />
            <QuickActionCard
              title="Trading Journal"
              description="Review trade history and notes"
              href="/trading/journal"
              icon={<Database className="w-6 h-6" />}
            />
            <QuickActionCard
              title="Automations"
              description="Configure automated trading rules"
              href="/trading/automations"
              icon={<Zap className="w-6 h-6" />}
            />
          </div>
        </section>

        {/* Admin Tools */}
        <section>
          <h2 className="text-lg font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-violet-500" />
            Admin Tools
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <QuickActionCard
              title="System Monitoring"
              description="View API usage, health metrics, and analytics"
              href="/admin/monitoring"
              icon={<BarChart3 className="w-6 h-6" />}
            />
            <QuickActionCard
              title="IP Whitelist"
              description="Manage allowed IP addresses for access control"
              href="/admin/ip-whitelist"
              icon={<Globe className="w-6 h-6" />}
            />
            <QuickActionCard
              title="Session Management"
              description="View and terminate active user sessions"
              href="/admin/sessions"
              icon={<Users className="w-6 h-6" />}
            />
          </div>
        </section>

        {/* Data Storage Info */}
        <section>
          <h2 className="text-lg font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <HardDrive className="w-5 h-5 text-violet-500" />
            Data Sources
          </h2>
          
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3">Market History</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Location</span>
                    <code className="text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded">data/market-history/</code>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Format</span>
                    <span className="text-gray-300">JSON (tickers, orderbooks, trades, ohlcv)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Update Frequency</span>
                    <span className="text-gray-300">~1 minute</span>
                  </div>
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3">News & Sentiment</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">News Location</span>
                    <code className="text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded">data/news/</code>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Sentiment Location</span>
                    <code className="text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded">data/sentiment/</code>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Update Frequency</span>
                    <span className="text-gray-300">~5 minutes</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* System Info */}
        <section>
          <h2 className="text-lg font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <Monitor className="w-5 h-5 text-violet-500" />
            System Information
          </h2>
          
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
              <div>
                <span className="text-gray-500 block mb-1">Environment</span>
                <span className="text-gray-300 font-medium">{process.env.NODE_ENV || 'development'}</span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">Data Source</span>
                <span className="text-gray-300 font-medium">Local Scrapers</span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">API Status</span>
                <span className="text-green-400 font-medium flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-400"></span>
                  Operational
                </span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">Last Checked</span>
                <span className="text-gray-300 font-medium">{new Date().toLocaleTimeString()}</span>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

interface StatusCardProps {
  title: string
  icon: React.ReactNode
  status: 'online' | 'offline' | 'warning'
  loading: boolean
  details: Array<{ label: string; value: string }>
}

function StatusCard({ title, icon, status, loading, details }: StatusCardProps) {
  const statusColors = {
    online: 'bg-green-500',
    offline: 'bg-red-500',
    warning: 'bg-yellow-500',
  }

  const statusIcons = {
    online: <CheckCircle2 className="w-4 h-4 text-green-400" />,
    offline: <XCircle className="w-4 h-4 text-red-400" />,
    warning: <Clock className="w-4 h-4 text-yellow-400" />,
  }

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-violet-500/10 text-violet-400 flex items-center justify-center">
            {icon}
          </div>
          <div>
            <h3 className="font-medium text-white">{title}</h3>
            <div className="flex items-center gap-2 mt-1">
              {loading ? (
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse" />
              ) : (
                <div className={`w-2 h-2 rounded-full ${statusColors[status]}`} />
              )}
              <span className="text-xs text-gray-500 capitalize">
                {loading ? 'Checking...' : status}
              </span>
            </div>
          </div>
        </div>
        {!loading && statusIcons[status]}
      </div>
      
      <div className="space-y-2">
        {details.map((detail, i) => (
          <div key={i} className="flex justify-between text-sm">
            <span className="text-gray-500">{detail.label}</span>
            <span className="text-gray-300">{loading ? '...' : detail.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

interface QuickActionCardProps {
  title: string
  description: string
  href: string
  icon: React.ReactNode
}

function QuickActionCard({ title, description, href, icon }: QuickActionCardProps) {
  return (
    <Link
      href={href}
      className="block bg-gray-900/50 border border-gray-800 rounded-xl p-5 hover:border-violet-500/50 hover:bg-gray-800/50 transition-all group"
    >
      <div className="w-12 h-12 rounded-xl bg-violet-500/10 text-violet-400 flex items-center justify-center mb-4 group-hover:bg-violet-500/20 transition-colors">
        {icon}
      </div>
      <h3 className="font-medium text-white mb-1">{title}</h3>
      <p className="text-sm text-gray-500">{description}</p>
    </Link>
  )
}


