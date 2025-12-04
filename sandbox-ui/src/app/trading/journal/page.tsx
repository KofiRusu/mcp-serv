'use client'

import { useState } from 'react'
import { useTradingStore } from '@/stores/trading-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { 
  ArrowLeft, 
  BookOpen, 
  Plus, 
  Search,
  Filter,
  TrendingUp,
  TrendingDown,
  MessageSquare,
  BarChart3,
  Calendar,
  Tag
} from 'lucide-react'
import Link from 'next/link'

export default function JournalPage() {
  const { journal, addJournalEntry } = useTradingStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [showNewEntry, setShowNewEntry] = useState(false)
  const [newEntry, setNewEntry] = useState({
    type: 'note' as const,
    title: '',
    content: '',
    symbols: [] as string[],
    tags: [] as string[],
  })

  // Filter journal entries
  const filteredJournal = journal.filter((entry) => {
    const matchesSearch = 
      entry.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      entry.content.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = filterType === 'all' || entry.type === filterType
    return matchesSearch && matchesType
  })

  const handleCreateEntry = () => {
    if (!newEntry.title.trim()) return
    
    addJournalEntry({
      type: newEntry.type,
      title: newEntry.title,
      content: newEntry.content,
      symbols: newEntry.symbols,
      tags: newEntry.tags,
    })
    
    setNewEntry({ type: 'note', title: '', content: '', symbols: [], tags: [] })
    setShowNewEntry(false)
  }

  // Group by date
  const groupedJournal = filteredJournal.reduce((acc, entry) => {
    const date = new Date(entry.createdAt).toLocaleDateString()
    if (!acc[date]) acc[date] = []
    acc[date].push(entry)
    return acc
  }, {} as Record<string, typeof journal>)

  return (
    <div className="flex flex-col h-screen bg-[#0a0a0f] text-gray-100">
      {/* Header */}
      <header className="h-12 border-b border-gray-800 bg-[#0d0d14] flex items-center px-4 gap-4">
        <Link href="/trading">
          <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
            <ArrowLeft className="w-4 h-4 mr-1.5" />
            Back to Trading
          </Button>
        </Link>
        
        <div className="w-px h-6 bg-gray-700" />
        
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-purple-400" />
          <span className="font-semibold">Trading Journal</span>
        </div>

        <div className="flex-1" />

        <Button size="sm" onClick={() => setShowNewEntry(true)} className="bg-purple-600 hover:bg-purple-700">
          <Plus className="w-4 h-4 mr-1.5" />
          New Entry
        </Button>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-64 border-r border-gray-800 bg-[#0d0d14] p-4 space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search journal..."
              className="pl-9 bg-gray-900 border-gray-700"
            />
          </div>

          {/* Filters */}
          <div>
            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">Filter by Type</div>
            <div className="space-y-1">
              {[
                { value: 'all', label: 'All Entries', icon: BookOpen },
                { value: 'trade', label: 'Trades', icon: TrendingUp },
                { value: 'note', label: 'Notes', icon: MessageSquare },
                { value: 'analysis', label: 'Analysis', icon: BarChart3 },
              ].map((filter) => (
                <button
                  key={filter.value}
                  onClick={() => setFilterType(filter.value)}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                    filterType === filter.value
                      ? 'bg-purple-600/20 text-purple-400'
                      : 'text-gray-400 hover:bg-gray-800'
                  }`}
                >
                  <filter.icon className="w-4 h-4" />
                  {filter.label}
                </button>
              ))}
            </div>
          </div>

          {/* Stats */}
          <div className="bg-gray-900/50 rounded-lg p-3 space-y-2">
            <div className="text-xs font-semibold text-gray-500 uppercase">Statistics</div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Total Entries</span>
              <span>{journal.length}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Trades Logged</span>
              <span>{journal.filter(e => e.type === 'trade').length}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Notes</span>
              <span>{journal.filter(e => e.type === 'note').length}</span>
            </div>
          </div>
        </div>

        {/* Journal Entries */}
        <div className="flex-1">
          <ScrollArea className="h-full">
            <div className="p-6 space-y-6">
              {Object.keys(groupedJournal).length === 0 ? (
                <div className="text-center py-12">
                  <BookOpen className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                  <h3 className="text-lg font-medium mb-2">No journal entries yet</h3>
                  <p className="text-gray-500 mb-4">Start documenting your trading journey</p>
                  <Button onClick={() => setShowNewEntry(true)} className="bg-purple-600 hover:bg-purple-700">
                    <Plus className="w-4 h-4 mr-1.5" />
                    Create First Entry
                  </Button>
                </div>
              ) : (
                Object.entries(groupedJournal).map(([date, entries]) => (
                  <div key={date}>
                    <div className="flex items-center gap-2 mb-3">
                      <Calendar className="w-4 h-4 text-gray-500" />
                      <span className="text-sm font-medium text-gray-400">{date}</span>
                    </div>
                    <div className="space-y-3">
                      {entries.map((entry) => (
                        <JournalEntryCard key={entry.id} entry={entry} />
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </div>
      </div>

      {/* New Entry Modal */}
      <Dialog open={showNewEntry} onOpenChange={setShowNewEntry}>
        <DialogContent className="bg-[#0d0d14] border-gray-800 text-white sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>New Journal Entry</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm text-gray-400">Type</label>
              <Select value={newEntry.type} onValueChange={(v) => setNewEntry({ ...newEntry, type: v as any })}>
                <SelectTrigger className="bg-gray-900 border-gray-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-gray-700">
                  <SelectItem value="note">Note</SelectItem>
                  <SelectItem value="analysis">Analysis</SelectItem>
                  <SelectItem value="trade">Trade Log</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-400">Title</label>
              <Input
                value={newEntry.title}
                onChange={(e) => setNewEntry({ ...newEntry, title: e.target.value })}
                placeholder="Entry title..."
                className="bg-gray-900 border-gray-700"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-400">Content</label>
              <Textarea
                value={newEntry.content}
                onChange={(e) => setNewEntry({ ...newEntry, content: e.target.value })}
                placeholder="Write your thoughts..."
                rows={6}
                className="bg-gray-900 border-gray-700"
              />
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowNewEntry(false)} className="flex-1 border-gray-700">
                Cancel
              </Button>
              <Button onClick={handleCreateEntry} disabled={!newEntry.title.trim()} className="flex-1 bg-purple-600 hover:bg-purple-700">
                Create Entry
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function JournalEntryCard({ entry }: { entry: ReturnType<typeof useTradingStore>['journal'][0] }) {
  const typeConfig = {
    trade: { icon: TrendingUp, color: 'text-green-400', bg: 'bg-green-400/10' },
    note: { icon: MessageSquare, color: 'text-blue-400', bg: 'bg-blue-400/10' },
    analysis: { icon: BarChart3, color: 'text-purple-400', bg: 'bg-purple-400/10' },
  }

  const config = typeConfig[entry.type as keyof typeof typeConfig]
  const Icon = config.icon

  return (
    <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-800 hover:border-gray-700 transition-colors">
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg ${config.bg}`}>
          <Icon className={`w-4 h-4 ${config.color}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-medium truncate">{entry.title}</h3>
            <span className="text-xs text-gray-500">
              {new Date(entry.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <p className="text-sm text-gray-400 line-clamp-2 mb-2">{entry.content}</p>
          <div className="flex items-center gap-2">
            {entry.symbols.map((symbol) => (
              <Badge key={symbol} variant="outline" className="text-[10px]">
                {symbol}
              </Badge>
            ))}
            {entry.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="text-[10px]">
                <Tag className="w-2 h-2 mr-1" />
                {tag}
              </Badge>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

