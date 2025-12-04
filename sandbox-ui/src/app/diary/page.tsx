"use client"

import { useState, useEffect, useCallback } from "react"
import { NoteDBList } from "@/components/notes/note-db-list"
import { NoteDBEditor } from "@/components/notes/note-db-editor"
import { AudioUploader } from "@/components/notes/audio-uploader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import Link from "next/link"
import {
  Plus,
  Search,
  FileText,
  Mic,
  ArrowLeft,
  Sparkles,
  MessageSquare,
  Home,
  FolderCode,
  Code2,
  Menu,
  X,
  Loader2,
  Brain,
  FileAudio,
} from "lucide-react"
import {
  listNotesDB,
  createNoteDB,
  searchAll,
  getNoteDB,
  type NoteDB,
  type SearchResult,
  type SearchResponse,
} from "@/lib/notes-db-api"
import { cn } from "@/lib/utils"
import { useRouter } from "next/navigation"
import { queueChatMessage, formatNoteForChat, formatSearchResultForChat } from "@/lib/chat-integration"

const NAV_ITEMS = [
  { href: "/", label: "Chat", icon: MessageSquare },
  { href: "/notes", label: "Notes", icon: FileText },
  { href: "/diary", label: "Diary", icon: Mic },
  { href: "/editor", label: "Editor", icon: FolderCode },
  { href: "/sandbox", label: "VSCode", icon: Code2 },
]

export default function DiaryPage() {
  const router = useRouter()
  const [notes, setNotes] = useState<NoteDB[]>([])
  const [selectedNote, setSelectedNote] = useState<NoteDB | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [showUploader, setShowUploader] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  
  // Global search state
  const [showGlobalSearch, setShowGlobalSearch] = useState(false)
  const [globalSearchQuery, setGlobalSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null)
  const [isSearching, setIsSearching] = useState(false)

  const fetchNotes = useCallback(async () => {
    try {
      setIsLoading(true)
      const response = await listNotesDB({
        query: searchQuery || undefined,
      })
      setNotes(response.notes)
    } catch (error) {
      console.error("Failed to fetch notes:", error)
    } finally {
      setIsLoading(false)
    }
  }, [searchQuery])

  useEffect(() => {
    fetchNotes()
  }, [fetchNotes])

  const handleCreateNote = async () => {
    try {
      setIsCreating(true)
      const note = await createNoteDB({
        title: "Untitled Note",
        content: "",
        tags: [],
      })
      setNotes((prev) => [note, ...prev])
      setSelectedNote(note)
    } catch (error) {
      console.error("Failed to create note:", error)
    } finally {
      setIsCreating(false)
    }
  }

  const handleNoteSelect = (note: NoteDB) => {
    setSelectedNote(note)
    setShowUploader(false)
  }

  const handleNoteUpdate = (updatedNote: NoteDB) => {
    setNotes((prev) =>
      prev.map((n) => (n.id === updatedNote.id ? updatedNote : n))
    )
    setSelectedNote(updatedNote)
  }

  const handleNoteDelete = (noteId: number) => {
    setNotes((prev) => prev.filter((n) => n.id !== noteId))
    if (selectedNote?.id === noteId) {
      setSelectedNote(null)
    }
  }

  const handleBack = () => {
    setSelectedNote(null)
    setShowUploader(false)
  }

  const handleTranscriptComplete = () => {
    // Refresh notes list when a transcript is processed
    fetchNotes()
  }

  const handleSendToChat = (content: string) => {
    // Queue the message for the chat page
    queueChatMessage({
      content,
      source: 'diary',
      sourceId: selectedNote?.id,
      sourceTitle: selectedNote?.title,
    })
    
    // Navigate to chat page
    router.push('/')
  }

  const handleGlobalSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!globalSearchQuery.trim() || globalSearchQuery.length < 2) return

    try {
      setIsSearching(true)
      const results = await searchAll(globalSearchQuery)
      setSearchResults(results)
    } catch (error) {
      console.error("Search failed:", error)
    } finally {
      setIsSearching(false)
    }
  }

  const handleSearchResultClick = async (result: SearchResult) => {
    if (result.type === 'note' && typeof result.id === 'number') {
      try {
        const note = await getNoteDB(result.id)
        setSelectedNote(note)
        setShowGlobalSearch(false)
        setSearchResults(null)
      } catch (error) {
        console.error("Failed to load note:", error)
      }
    } else if (result.type === 'transcript') {
      // For transcripts, try to find the associated note
      if (result.note_id) {
        try {
          const note = await getNoteDB(result.note_id)
          setSelectedNote(note)
          setShowGlobalSearch(false)
          setSearchResults(null)
        } catch (error) {
          console.error("Failed to load note for transcript:", error)
        }
      }
    } else if (result.type === 'memory' || result.type === 'chat_history') {
      // For memory/chat results, send to chat as context
      const formatted = formatSearchResultForChat(result.type, result.title, result.snippet)
      queueChatMessage({
        content: formatted,
        source: 'search',
        sourceTitle: result.title,
      })
      setShowGlobalSearch(false)
      setSearchResults(null)
      router.push('/')
    }
  }

  return (
    <div className="flex h-screen bg-[var(--bg-primary)]">
      {/* Mobile sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="md:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)]"
      >
        {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Sidebar */}
      <aside className={cn(
        "w-72 border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex flex-col",
        "fixed md:relative inset-y-0 left-0 z-40 transition-transform duration-300",
        sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}>
        {/* Header */}
        <div className="p-4 border-b border-[var(--border-color)]">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-gradient-to-br from-[var(--accent-primary)]/20 to-[var(--accent-secondary)]/20">
                <Mic className="h-5 w-5 text-[var(--accent-primary)]" />
              </div>
              <div>
                <h1 className="font-semibold text-[var(--text-primary)]">Diary</h1>
                <p className="text-xs text-[var(--text-muted)]">
                  {notes.length} notes
                </p>
              </div>
            </div>
            <Button
              size="icon"
              variant="ghost"
              onClick={handleCreateNote}
              disabled={isCreating}
              className="hover:bg-[var(--bg-tertiary)]"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          {/* Local Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)]" />
            <Input
              placeholder="Filter notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-[var(--bg-tertiary)] border-[var(--border-color)]"
            />
          </div>

          {/* Global Search Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowGlobalSearch(true)}
            className="w-full mt-2 justify-start gap-2 text-[var(--text-muted)]"
          >
            <Brain className="h-4 w-4" />
            <span>Search All (Notes, Transcripts, Memory)</span>
          </Button>
        </div>

        {/* Quick Actions */}
        <div className="p-2 border-b border-[var(--border-color)] space-y-1">
          <button
            onClick={() => {
              setShowUploader(true)
              setSelectedNote(null)
            }}
            className={cn(
              "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors",
              showUploader
                ? "bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
                : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
            )}
          >
            <Mic className="h-4 w-4" />
            <span>Upload Audio</span>
          </button>
          <button
            onClick={handleCreateNote}
            disabled={isCreating}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <FileText className="h-4 w-4" />
            <span>New Note</span>
          </button>
        </div>

        {/* Notes List */}
        <div className="flex-1 overflow-y-auto">
          <NoteDBList
            notes={notes}
            selectedId={selectedNote?.id}
            onSelect={handleNoteSelect}
            isLoading={isLoading}
          />
        </div>

        {/* Navigation */}
        <nav className="p-2 border-t border-[var(--border-color)]">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors",
                item.href === "/diary"
                  ? "bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
              )}
            >
              <item.icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        {selectedNote ? (
          <>
            {/* Back button for mobile */}
            <div className="md:hidden p-2 border-b border-[var(--border-color)]">
              <Button variant="ghost" size="sm" onClick={handleBack}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to list
              </Button>
            </div>
            <NoteDBEditor
              note={selectedNote}
              onUpdate={handleNoteUpdate}
              onDelete={handleNoteDelete}
              onSendToChat={handleSendToChat}
            />
          </>
        ) : showUploader ? (
          <div className="flex-1 flex flex-col p-6 overflow-y-auto">
            {/* Back button for mobile */}
            <div className="md:hidden mb-4">
              <Button variant="ghost" size="sm" onClick={handleBack}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to list
              </Button>
            </div>
            
            <div className="max-w-2xl mx-auto w-full">
              <div className="text-center mb-8">
                <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--accent-primary)]/20 to-[var(--accent-secondary)]/20 flex items-center justify-center mb-4">
                  <Mic className="h-8 w-8 text-[var(--accent-primary)]" />
                </div>
                <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
                  Upload Audio Recording
                </h2>
                <p className="text-sm text-[var(--text-muted)] mt-2">
                  Upload audio files to transcribe and automatically generate summaries with action items
                </p>
              </div>

              <AudioUploader
                onTranscriptComplete={() => {}}
                onNoteCreated={handleTranscriptComplete}
              />

              <div className="mt-8 p-4 rounded-xl bg-[var(--bg-tertiary)] border border-[var(--border-color)]">
                <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2 flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-[var(--accent-primary)]" />
                  How it works
                </h3>
                <ol className="text-sm text-[var(--text-secondary)] space-y-2">
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] flex items-center justify-center text-xs flex-shrink-0">1</span>
                    <span>Upload an audio file (meeting recording, voice memo, lecture)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] flex items-center justify-center text-xs flex-shrink-0">2</span>
                    <span>AI transcribes the audio and generates a summary</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] flex items-center justify-center text-xs flex-shrink-0">3</span>
                    <span>Action items are automatically extracted</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] flex items-center justify-center text-xs flex-shrink-0">4</span>
                    <span>A new note is created with the summary and action items</span>
                  </li>
                </ol>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4">
              <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--accent-primary)]/20 to-[var(--accent-secondary)]/20 flex items-center justify-center">
                <Mic className="h-8 w-8 text-[var(--accent-primary)]" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-[var(--text-primary)]">
                  Voice-First Notes
                </h2>
                <p className="text-sm text-[var(--text-muted)] mt-1">
                  Upload audio recordings to create AI-powered summaries
                </p>
              </div>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button
                  onClick={() => setShowUploader(true)}
                  className="bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-[var(--bg-primary)]"
                >
                  <Mic className="h-4 w-4 mr-2" />
                  Upload Audio
                </Button>
                <Button
                  onClick={handleCreateNote}
                  disabled={isCreating}
                  variant="outline"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create Note
                </Button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Global Search Modal */}
      {showGlobalSearch && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-start justify-center pt-20">
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-color)] w-full max-w-2xl mx-4 shadow-2xl">
            {/* Search Header */}
            <div className="p-4 border-b border-[var(--border-color)]">
              <form onSubmit={handleGlobalSearch} className="flex gap-2">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)]" />
                  <Input
                    placeholder="Search notes, transcripts, and memory..."
                    value={globalSearchQuery}
                    onChange={(e) => setGlobalSearchQuery(e.target.value)}
                    className="pl-9 bg-[var(--bg-tertiary)] border-[var(--border-color)]"
                    autoFocus
                  />
                </div>
                <Button type="submit" disabled={isSearching}>
                  {isSearching ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Search"
                  )}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setShowGlobalSearch(false)
                    setSearchResults(null)
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
              </form>
            </div>

            {/* Search Results */}
            <div className="max-h-96 overflow-y-auto">
              {searchResults ? (
                searchResults.total > 0 ? (
                  <div className="p-4 space-y-4">
                    {/* Notes Results */}
                    {searchResults.by_type.notes.length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase mb-2 flex items-center gap-2">
                          <FileText className="h-3 w-3" />
                          Notes ({searchResults.by_type.notes.length})
                        </h3>
                        <div className="space-y-2">
                          {searchResults.by_type.notes.map((result) => (
                            <button
                              key={`note-${result.id}`}
                              onClick={() => handleSearchResultClick(result)}
                              className="w-full text-left p-3 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-elevated)] transition-colors"
                            >
                              <div className="font-medium text-[var(--text-primary)]">
                                {result.title}
                              </div>
                              <div className="text-sm text-[var(--text-muted)] mt-1 line-clamp-2">
                                {result.snippet}
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Transcripts Results */}
                    {searchResults.by_type.transcripts.length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase mb-2 flex items-center gap-2">
                          <FileAudio className="h-3 w-3" />
                          Transcripts ({searchResults.by_type.transcripts.length})
                        </h3>
                        <div className="space-y-2">
                          {searchResults.by_type.transcripts.map((result) => (
                            <button
                              key={`transcript-${result.id}`}
                              onClick={() => handleSearchResultClick(result)}
                              className="w-full text-left p-3 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-elevated)] transition-colors"
                            >
                              <div className="font-medium text-[var(--text-primary)]">
                                {result.title}
                              </div>
                              <div className="text-sm text-[var(--text-muted)] mt-1 line-clamp-2">
                                {result.snippet}
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Memory Results */}
                    {searchResults.by_type.memory.length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase mb-2 flex items-center gap-2">
                          <Brain className="h-3 w-3" />
                          Memory ({searchResults.by_type.memory.length})
                        </h3>
                        <div className="space-y-2">
                          {searchResults.by_type.memory.map((result) => (
                            <button
                              key={`memory-${result.id}`}
                              onClick={() => handleSearchResultClick(result)}
                              className="w-full text-left p-3 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-elevated)] transition-colors"
                            >
                              <div className="font-medium text-[var(--text-primary)]">
                                {result.title}
                              </div>
                              <div className="text-sm text-[var(--text-muted)] mt-1 line-clamp-2">
                                {result.snippet}
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-8 text-center text-[var(--text-muted)]">
                    <p>No results found for "{searchResults.query}"</p>
                  </div>
                )
              ) : (
                <div className="p-8 text-center text-[var(--text-muted)]">
                  <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Search across all your notes, transcripts, and memories</p>
                  <p className="text-xs mt-2">Enter at least 2 characters to search</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

