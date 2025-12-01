"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { File, Folder, ChevronRight, ChevronDown, Plus, FolderPlus, Trash2, RefreshCw, Upload, FolderInput, FileUp } from "lucide-react"
import { cn } from "@/lib/utils"
import { getFileTree, writeFile, deleteFile, createDirectory, getFileIcon, importDirectory, uploadFile, type FileInfo } from "@/lib/api"
import { Button } from "@/components/ui/button"

interface FileTreeProps {
  selectedFile: string | null
  onSelectFile: (file: string) => void
  onRefresh?: () => void
}

interface TreeNodeProps {
  node: FileInfo
  selectedFile: string | null
  onSelectFile: (file: string) => void
  onDelete: (path: string, isDir: boolean) => void
  level?: number
}

function TreeNode({
  node,
  selectedFile,
  onSelectFile,
  onDelete,
  level = 0,
}: TreeNodeProps) {
  const [isOpen, setIsOpen] = useState(level === 0)

  if (!node.is_directory) {
    const icon = getFileIcon(node.name)
    return (
      <div
        onClick={() => onSelectFile(node.path)}
        className={cn(
          "group flex w-full items-center gap-2 px-2 py-1.5 text-sm transition-colors hover:bg-[var(--bg-tertiary)] cursor-pointer",
          selectedFile === node.path && "bg-[var(--bg-tertiary)] text-[var(--accent-primary)]"
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        <span className="text-base">{icon}</span>
        <span className="flex-1 truncate text-[var(--text-primary)]">{node.name}</span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete(node.path, false)
          }}
          className="opacity-0 group-hover:opacity-100 p-1 hover:text-[var(--error)] transition-opacity"
        >
          <Trash2 className="h-3 w-3" />
        </button>
      </div>
    )
  }

  return (
    <div>
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="group flex w-full items-center gap-2 px-2 py-1.5 text-sm transition-colors hover:bg-[var(--bg-tertiary)] cursor-pointer text-[var(--text-secondary)]"
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        {isOpen ? (
          <ChevronDown className="h-4 w-4 text-[var(--accent-primary)]" />
        ) : (
          <ChevronRight className="h-4 w-4 text-[var(--text-muted)]" />
        )}
        <Folder className={cn("h-4 w-4", isOpen ? "text-[var(--accent-primary)]" : "text-[var(--text-muted)]")} />
        <span className="flex-1">{node.name}</span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete(node.path, true)
          }}
          className="opacity-0 group-hover:opacity-100 p-1 hover:text-[var(--error)] transition-opacity"
        >
          <Trash2 className="h-3 w-3" />
        </button>
      </div>
      {isOpen && node.children?.map((child) => (
        <TreeNode
          key={child.path}
          node={child}
          selectedFile={selectedFile}
          onSelectFile={onSelectFile}
          onDelete={onDelete}
          level={level + 1}
        />
      ))}
    </div>
  )
}

export function FileTree({ selectedFile, onSelectFile, onRefresh }: FileTreeProps) {
  const [fileTree, setFileTree] = useState<FileInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showImportMenu, setShowImportMenu] = useState(false)
  const [importing, setImporting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadFileTree = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getFileTree()
      setFileTree(data.root)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadFileTree()
  }, [loadFileTree])

  const handleCreateFile = async () => {
    const name = prompt('Enter file name (e.g., script.py):')
    if (!name) return

    try {
      await writeFile(name, '')
      loadFileTree()
      onSelectFile(name)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create file')
    }
  }

  const handleCreateFolder = async () => {
    const name = prompt('Enter folder name:')
    if (!name) return

    try {
      await createDirectory(name)
      loadFileTree()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create folder')
    }
  }

  const handleDelete = async (path: string, isDir: boolean) => {
    const type = isDir ? 'folder' : 'file'
    if (!confirm(`Delete ${type} "${path}"?`)) return

    try {
      await deleteFile(path)
      loadFileTree()
      if (selectedFile === path) {
        onSelectFile('')
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : `Failed to delete ${type}`)
    }
  }

  const handleRefresh = () => {
    loadFileTree()
    onRefresh?.()
  }

  const handleImportDirectory = async () => {
    const sourcePath = prompt(
      'Enter the full path to the directory to import:\n\nExample: /home/user/my-project\n\nNote: node_modules, .git, __pycache__ will be skipped'
    )
    if (!sourcePath) return

    const targetName = prompt(
      'Enter name for imported directory (or leave empty to use source name):'
    )

    setImporting(true)
    setShowImportMenu(false)
    
    try {
      const result = await importDirectory(sourcePath, targetName || undefined)
      alert(`✅ Imported ${result.imported_count} files to "${result.target}"\n\nSkipped: ${result.skipped_count} files`)
      loadFileTree()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to import directory')
    } finally {
      setImporting(false)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    setImporting(true)
    setShowImportMenu(false)

    try {
      const results = []
      for (const file of Array.from(files)) {
        const result = await uploadFile(file)
        results.push(result)
      }
      alert(`✅ Uploaded ${results.length} file(s)`)
      loadFileTree()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to upload files')
    } finally {
      setImporting(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFileUpload}
      />

      {/* Actions Bar */}
      <div className="flex items-center justify-between px-2 py-2 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-[var(--text-secondary)] hover:text-[var(--accent-primary)] hover:bg-[var(--bg-tertiary)]"
            onClick={handleCreateFile}
            title="New File"
          >
            <Plus className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-[var(--text-secondary)] hover:text-[var(--accent-primary)] hover:bg-[var(--bg-tertiary)]"
            onClick={handleCreateFolder}
            title="New Folder"
          >
            <FolderPlus className="h-4 w-4" />
          </Button>
          
          {/* Import Dropdown */}
          <div className="relative">
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                "h-7 w-7 text-[var(--text-secondary)] hover:text-[var(--accent-primary)] hover:bg-[var(--bg-tertiary)]",
                (showImportMenu || importing) && "text-[var(--accent-primary)] bg-[var(--bg-tertiary)]"
              )}
              onClick={() => setShowImportMenu(!showImportMenu)}
              title="Import"
              disabled={importing}
            >
              {importing ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
            </Button>
            
            {showImportMenu && (
              <div className="absolute left-0 top-full mt-1 w-48 bg-[var(--bg-elevated)] border border-[var(--border-color)] rounded-lg shadow-xl z-50">
                <button
                  onClick={handleImportDirectory}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors"
                >
                  <FolderInput className="h-4 w-4 text-[var(--accent-primary)]" />
                  Import Directory
                </button>
                <button
                  onClick={() => {
                    setShowImportMenu(false)
                    fileInputRef.current?.click()
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors"
                >
                  <FileUp className="h-4 w-4 text-[var(--accent-secondary)]" />
                  Upload Files
                </button>
              </div>
            )}
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-[var(--text-secondary)] hover:text-[var(--accent-primary)] hover:bg-[var(--bg-tertiary)]"
          onClick={handleRefresh}
          title="Refresh"
        >
          <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
        </Button>
      </div>

      {/* Click outside to close menu */}
      {showImportMenu && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setShowImportMenu(false)}
        />
      )}

      {/* File Tree */}
      <div className="flex-1 overflow-y-auto py-2">
        {loading && !fileTree && (
          <div className="flex items-center justify-center py-8 text-[var(--text-muted)]">
            <RefreshCw className="h-5 w-5 animate-spin" />
          </div>
        )}

        {error && (
          <div className="px-4 py-8 text-center">
            <p className="text-[var(--error)] text-sm mb-2">{error}</p>
            <Button variant="ghost" size="sm" onClick={loadFileTree}>
              Retry
            </Button>
          </div>
        )}

        {fileTree && !fileTree.children?.length && (
          <div className="px-4 py-8 text-center text-[var(--text-muted)] text-sm">
            <p>No files yet</p>
            <p className="text-xs mt-1">Create a file or import a directory</p>
          </div>
        )}

        {fileTree?.children?.map((node) => (
          <TreeNode
            key={node.path}
            node={node}
            selectedFile={selectedFile}
            onSelectFile={onSelectFile}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </div>
  )
}
