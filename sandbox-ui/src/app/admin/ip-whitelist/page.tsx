'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { 
  Shield,
  Plus,
  Trash2,
  RefreshCw,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Upload,
  Globe
} from 'lucide-react'

interface WhitelistEntry {
  id: string
  ip_address: string
  description: string | null
  cidr_notation: string | null
  is_active: boolean
  expires_at: string | null
  created_at: string
}

interface WhitelistData {
  entries: WhitelistEntry[]
  total: number
  active_count: number
}

export default function IPWhitelistPage() {
  const [data, setData] = useState<WhitelistData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [myIp, setMyIp] = useState<string>('')
  
  // Form state
  const [newIp, setNewIp] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [adding, setAdding] = useState(false)

  const fetchData = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/v1/admin/whitelist')
      if (!response.ok) throw new Error('Failed to fetch whitelist')
      const result = await response.json()
      setData(result)
      setError(null)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchMyIp = async () => {
    try {
      const response = await fetch('/api/v1/admin/whitelist/my-ip')
      if (response.ok) {
        const result = await response.json()
        setMyIp(result.ip_address)
      }
    } catch {
      // Ignore errors
    }
  }

  useEffect(() => {
    fetchData()
    fetchMyIp()
  }, [])

  const addIp = async () => {
    if (!newIp.trim()) return
    
    try {
      setAdding(true)
      const response = await fetch('/api/v1/admin/whitelist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ip_address: newIp.trim(),
          description: newDescription.trim() || null,
        }),
      })
      
      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Failed to add IP')
      }
      
      setNewIp('')
      setNewDescription('')
      fetchData()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setAdding(false)
    }
  }

  const removeIp = async (id: string) => {
    if (!confirm('Are you sure you want to remove this IP?')) return
    
    try {
      const response = await fetch(`/api/v1/admin/whitelist/${id}`, {
        method: 'DELETE',
      })
      
      if (!response.ok) throw new Error('Failed to remove IP')
      fetchData()
    } catch (err: any) {
      setError(err.message)
    }
  }

  const addMyIp = () => {
    if (myIp) {
      setNewIp(myIp)
      setNewDescription('My current IP')
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
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-green-700 flex items-center justify-center">
                  <Shield className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">IP Whitelist</h1>
                  <p className="text-sm text-gray-500">Manage allowed IP addresses</p>
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
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
            <div className="text-2xl font-bold text-white">{data?.total || 0}</div>
            <div className="text-sm text-gray-500">Total Entries</div>
          </div>
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
            <div className="text-2xl font-bold text-emerald-400">{data?.active_count || 0}</div>
            <div className="text-sm text-gray-500">Active</div>
          </div>
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
            <div className="text-sm font-mono text-violet-400">{myIp || '...'}</div>
            <div className="text-sm text-gray-500">Your IP Address</div>
          </div>
        </div>

        {/* Add IP Form */}
        <section className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Plus className="w-5 h-5 text-emerald-500" />
            Add IP Address
          </h2>
          
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <input
                type="text"
                placeholder="IP Address or CIDR (e.g., 192.168.1.1 or 10.0.0.0/24)"
                value={newIp}
                onChange={(e) => setNewIp(e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div className="flex-1">
              <input
                type="text"
                placeholder="Description (optional)"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <button
              onClick={addMyIp}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors flex items-center gap-2"
            >
              <Globe className="w-4 h-4" />
              Use My IP
            </button>
            <button
              onClick={addIp}
              disabled={adding || !newIp.trim()}
              className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add
            </button>
          </div>
        </section>

        {/* Error Display */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
            {error}
          </div>
        )}

        {/* Whitelist Table */}
        <section className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800">
            <h2 className="text-lg font-semibold text-white">Whitelisted IPs</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">IP Address</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Description</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Added</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      Loading...
                    </td>
                  </tr>
                ) : data?.entries.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      No IP addresses whitelisted yet
                    </td>
                  </tr>
                ) : (
                  data?.entries.map((entry) => (
                    <tr key={entry.id} className="hover:bg-gray-800/30">
                      <td className="px-6 py-4">
                        <code className="text-violet-400 bg-violet-500/10 px-2 py-1 rounded">
                          {entry.cidr_notation || entry.ip_address}
                        </code>
                      </td>
                      <td className="px-6 py-4 text-gray-300">
                        {entry.description || '-'}
                      </td>
                      <td className="px-6 py-4">
                        {entry.is_active ? (
                          <span className="flex items-center gap-1 text-emerald-400">
                            <CheckCircle2 className="w-4 h-4" />
                            Active
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-red-400">
                            <XCircle className="w-4 h-4" />
                            Inactive
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-gray-400 text-sm">
                        {new Date(entry.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => removeIp(entry.id)}
                          className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
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
