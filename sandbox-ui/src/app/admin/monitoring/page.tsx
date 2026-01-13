'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { 
  Activity,
  ArrowLeft,
  RefreshCw,
  TrendingUp,
  Clock,
  AlertTriangle,
  CheckCircle2,
  BarChart3,
  Zap
} from 'lucide-react'

interface APIUsageStats {
  total_requests: number
  requests_today: number
  requests_this_hour: number
  avg_response_time_ms: number | null
  error_rate: number
  top_endpoints: Array<{
    endpoint: string
    count: number
    avg_response_ms: number | null
  }>
  requests_by_hour: Array<{
    hour: string
    count: number
  }>
}

interface FeatureUsageStats {
  total_actions: number
  actions_today: number
  top_features: Array<{
    feature: string
    count: number
  }>
}

interface SystemHealth {
  status: string
  active_sessions: number
  requests_last_hour: number
  error_rate_last_hour: number
  database_connected: boolean
  timestamp: string
}

export default function MonitoringPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [apiUsage, setApiUsage] = useState<APIUsageStats | null>(null)
  const [featureUsage, setFeatureUsage] = useState<FeatureUsageStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      
      const [healthRes, apiRes, featureRes] = await Promise.all([
        fetch('/api/v1/admin/monitoring/health'),
        fetch('/api/v1/admin/monitoring/api-usage'),
        fetch('/api/v1/admin/monitoring/feature-usage'),
      ])
      
      if (healthRes.ok) setHealth(await healthRes.json())
      if (apiRes.ok) setApiUsage(await apiRes.json())
      if (featureRes.ok) setFeatureUsage(await featureRes.json())
      
      setError(null)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-emerald-400 bg-emerald-500/10'
      case 'degraded': return 'text-yellow-400 bg-yellow-500/10'
      case 'critical': return 'text-red-400 bg-red-500/10'
      default: return 'text-gray-400 bg-gray-500/10'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle2 className="w-5 h-5" />
      case 'degraded': return <AlertTriangle className="w-5 h-5" />
      case 'critical': return <AlertTriangle className="w-5 h-5" />
      default: return <Activity className="w-5 h-5" />
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-[#0d0d14]">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link 
                href="/admin"
                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-700 flex items-center justify-center">
                  <Activity className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">System Monitoring</h1>
                  <p className="text-sm text-gray-500">Real-time system health and usage</p>
                </div>
              </div>
            </div>
            <button
              onClick={fetchData}
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
            <Activity className="w-5 h-5 text-blue-500" />
            System Health
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Status */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
              <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full ${health ? getStatusColor(health.status) : 'bg-gray-500/10'}`}>
                {health ? getStatusIcon(health.status) : <Activity className="w-5 h-5" />}
                <span className="font-medium capitalize">{health?.status || 'Loading...'}</span>
              </div>
              <div className="text-sm text-gray-500 mt-2">Overall Status</div>
            </div>
            
            {/* Active Sessions */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
              <div className="text-2xl font-bold text-white">{health?.active_sessions || 0}</div>
              <div className="text-sm text-gray-500">Active Sessions</div>
            </div>
            
            {/* Requests/Hour */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
              <div className="text-2xl font-bold text-white">{health?.requests_last_hour || 0}</div>
              <div className="text-sm text-gray-500">Requests (Last Hour)</div>
            </div>
            
            {/* Error Rate */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
              <div className={`text-2xl font-bold ${(health?.error_rate_last_hour || 0) > 5 ? 'text-red-400' : 'text-emerald-400'}`}>
                {health?.error_rate_last_hour?.toFixed(1) || 0}%
              </div>
              <div className="text-sm text-gray-500">Error Rate</div>
            </div>
          </div>
        </section>

        {/* API Usage Stats */}
        <section>
          <h2 className="text-lg font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-500" />
            API Usage (Last 24 Hours)
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
              <div className="text-2xl font-bold text-white">{apiUsage?.total_requests?.toLocaleString() || 0}</div>
              <div className="text-sm text-gray-500">Total Requests</div>
            </div>
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
              <div className="text-2xl font-bold text-white">{apiUsage?.requests_today?.toLocaleString() || 0}</div>
              <div className="text-sm text-gray-500">Today</div>
            </div>
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
              <div className="text-2xl font-bold text-white">{apiUsage?.avg_response_time_ms?.toFixed(0) || '-'} ms</div>
              <div className="text-sm text-gray-500">Avg Response Time</div>
            </div>
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
              <div className={`text-2xl font-bold ${(apiUsage?.error_rate || 0) > 5 ? 'text-red-400' : 'text-emerald-400'}`}>
                {apiUsage?.error_rate?.toFixed(1) || 0}%
              </div>
              <div className="text-sm text-gray-500">Error Rate</div>
            </div>
          </div>

          {/* Top Endpoints */}
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800">
              <h3 className="font-medium text-white">Top Endpoints</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-800/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Endpoint</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase">Requests</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase">Avg Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {apiUsage?.top_endpoints?.map((endpoint, i) => (
                    <tr key={i} className="hover:bg-gray-800/30">
                      <td className="px-6 py-3">
                        <code className="text-violet-400 text-sm">{endpoint.endpoint}</code>
                      </td>
                      <td className="px-6 py-3 text-right text-gray-300">{endpoint.count}</td>
                      <td className="px-6 py-3 text-right text-gray-400">
                        {endpoint.avg_response_ms?.toFixed(0) || '-'} ms
                      </td>
                    </tr>
                  )) || (
                    <tr>
                      <td colSpan={3} className="px-6 py-4 text-center text-gray-500">No data</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Feature Usage */}
        <section>
          <h2 className="text-lg font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-blue-500" />
            Feature Usage
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
              <div className="text-2xl font-bold text-white">{featureUsage?.total_actions?.toLocaleString() || 0}</div>
              <div className="text-sm text-gray-500">Total Actions</div>
            </div>
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
              <div className="text-2xl font-bold text-white">{featureUsage?.actions_today?.toLocaleString() || 0}</div>
              <div className="text-sm text-gray-500">Today</div>
            </div>
          </div>

          {/* Top Features */}
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden mt-4">
            <div className="px-6 py-4 border-b border-gray-800">
              <h3 className="font-medium text-white">Most Used Features</h3>
            </div>
            <div className="p-6">
              <div className="space-y-3">
                {featureUsage?.top_features?.map((feature, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <div className="flex-1">
                      <div className="flex justify-between mb-1">
                        <span className="text-gray-300">{feature.feature}</span>
                        <span className="text-gray-500">{feature.count}</span>
                      </div>
                      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-blue-500 rounded-full"
                          style={{ 
                            width: `${Math.min(100, (feature.count / (featureUsage?.top_features?.[0]?.count || 1)) * 100)}%` 
                          }}
                        />
                      </div>
                    </div>
                  </div>
                )) || (
                  <div className="text-center text-gray-500">No data</div>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Quick Links */}
        <section className="flex gap-4">
          <Link
            href="/admin/sessions"
            className="flex-1 bg-gray-900/50 border border-gray-800 rounded-xl p-5 hover:border-blue-500/50 transition-colors"
          >
            <div className="font-medium text-white mb-1">Manage Sessions</div>
            <div className="text-sm text-gray-500">View and terminate user sessions</div>
          </Link>
          <Link
            href="/admin/ip-whitelist"
            className="flex-1 bg-gray-900/50 border border-gray-800 rounded-xl p-5 hover:border-blue-500/50 transition-colors"
          >
            <div className="font-medium text-white mb-1">IP Whitelist</div>
            <div className="text-sm text-gray-500">Manage allowed IP addresses</div>
          </Link>
        </section>
      </main>
    </div>
  )
}
