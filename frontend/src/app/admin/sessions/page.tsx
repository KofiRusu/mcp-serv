'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { 
  Users,
  ArrowLeft,
  RefreshCw,
  LogOut,
  AlertTriangle,
  Clock,
  Globe,
  User,
  Shield
} from 'lucide-react'

interface Session {
  id: string
  keycloak_user_id: string
  username: string
  email: string | null
  roles: string[]
  login_time: string
  logout_time: string | null
  last_activity: string | null
  ip_address: string | null
  is_active: boolean
  duration_minutes: number | null
}

interface SessionData {
  sessions: Session[]
  total: number
  active_count: number
}

export default function SessionsPage() {
  const [data, setData] = useState<SessionData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [terminating, setTerminating] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/v1/admin/monitoring/sessions?active_only=false')
      if (!response.ok) throw new Error('Failed to fetch sessions')
      const result = await response.json()
      setData(result)
      setError(null)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  const terminateSession = async (sessionId: string, username: string) => {
    if (!confirm(`Are you sure you want to terminate the session for "${username}"?`)) return
    
    try {
      setTerminating(sessionId)
      const response = await fetch(`/api/v1/admin/monitoring/sessions/${sessionId}/terminate`, {
        method: 'POST',
      })
      
      if (!response.ok) throw new Error('Failed to terminate session')
      fetchData()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setTerminating(null)
    }
  }

  const terminateAll = async () => {
    if (!confirm('Are you sure you want to terminate ALL active sessions? This will log out everyone except you.')) return
    
    try {
      setTerminating('all')
      const response = await fetch('/api/v1/admin/monitoring/sessions/terminate-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exclude_current: true }),
      })
      
      if (!response.ok) throw new Error('Failed to terminate sessions')
      const result = await response.json()
      alert(`Terminated ${result.terminated} sessions`)
      fetchData()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setTerminating(null)
    }
  }

  const formatDuration = (minutes: number | null) => {
    if (minutes === null) return '-'
    if (minutes < 60) return `${minutes}m`
    if (minutes < 1440) return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
    return `${Math.floor(minutes / 1440)}d ${Math.floor((minutes % 1440) / 60)}h`
  }

  const formatTime = (isoString: string | null) => {
    if (!isoString) return '-'
    const date = new Date(isoString)
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
            <div className="flex items-center gap-4">
              <Link 
                href="/admin"
                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-600 to-red-700 flex items-center justify-center">
                  <Users className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Session Management</h1>
                  <p className="text-sm text-gray-500">View and manage user sessions</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={terminateAll}
                disabled={terminating === 'all' || (data?.active_count || 0) === 0}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-lg transition-colors"
              >
                <AlertTriangle className="w-4 h-4" />
                Terminate All
              </button>
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
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
            <div className="text-2xl font-bold text-white">{data?.total || 0}</div>
            <div className="text-sm text-gray-500">Total Sessions</div>
          </div>
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
            <div className="text-2xl font-bold text-emerald-400">{data?.active_count || 0}</div>
            <div className="text-sm text-gray-500">Active Now</div>
          </div>
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
            <div className="text-2xl font-bold text-gray-400">{(data?.total || 0) - (data?.active_count || 0)}</div>
            <div className="text-sm text-gray-500">Ended</div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
            {error}
          </div>
        )}

        {/* Sessions Table */}
        <section className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800">
            <h2 className="text-lg font-semibold text-white">User Sessions</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">User</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">IP Address</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Roles</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Last Active</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Duration</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                      Loading...
                    </td>
                  </tr>
                ) : data?.sessions.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                      No sessions found
                    </td>
                  </tr>
                ) : (
                  data?.sessions.map((session) => (
                    <tr key={session.id} className="hover:bg-gray-800/30">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                            <User className="w-4 h-4 text-gray-400" />
                          </div>
                          <div>
                            <div className="font-medium text-white">{session.username}</div>
                            <div className="text-xs text-gray-500">{session.email || '-'}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <Globe className="w-4 h-4 text-gray-500" />
                          <code className="text-sm text-gray-400">{session.ip_address || '-'}</code>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1">
                          {session.roles?.map((role, i) => (
                            <span 
                              key={i}
                              className={`px-2 py-0.5 rounded text-xs ${
                                role.includes('admin') 
                                  ? 'bg-violet-500/20 text-violet-400' 
                                  : 'bg-gray-700 text-gray-400'
                              }`}
                            >
                              {role}
                            </span>
                          )) || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2 text-gray-400">
                          <Clock className="w-4 h-4" />
                          <span className="text-sm">{formatTime(session.last_activity)}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-gray-400 text-sm">
                        {formatDuration(session.duration_minutes)}
                      </td>
                      <td className="px-6 py-4">
                        {session.is_active ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-500/10 text-gray-400 text-xs">
                            <span className="w-2 h-2 rounded-full bg-gray-400" />
                            Ended
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {session.is_active && (
                          <button
                            onClick={() => terminateSession(session.id, session.username)}
                            disabled={terminating === session.id}
                            className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50"
                          >
                            <LogOut className="w-4 h-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  )
}
