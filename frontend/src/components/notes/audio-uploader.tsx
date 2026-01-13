"use client"

import { useState, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import {
  Mic,
  Upload,
  FileAudio,
  Loader2,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"
import {
  createTranscript,
  waitForTranscript,
  uploadAudioFile,
  type TranscriptDB,
  type TranscriptStatus,
  getTranscriptStatusLabel,
  getTranscriptStatusColor,
} from "@/lib/notes-db-api"

interface AudioUploaderProps {
  onTranscriptComplete?: (transcript: TranscriptDB) => void
  onNoteCreated?: () => void
  className?: string
}

interface UploadJob {
  id: string
  fileName: string
  transcriptId?: number
  status: TranscriptStatus | 'uploading'
  error?: string
}

export function AudioUploader({
  onTranscriptComplete,
  onNoteCreated,
  className,
}: AudioUploaderProps) {
  const [jobs, setJobs] = useState<UploadJob[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const updateJob = useCallback((id: string, updates: Partial<UploadJob>) => {
    setJobs(prev => prev.map(job => 
      job.id === id ? { ...job, ...updates } : job
    ))
  }, [])

  const removeJob = useCallback((id: string) => {
    setJobs(prev => prev.filter(job => job.id !== id))
  }, [])

  const processFile = useCallback(async (file: File) => {
    const jobId = `job_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`
    
    // Add job to list
    setJobs(prev => [...prev, {
      id: jobId,
      fileName: file.name,
      status: 'uploading',
    }])

    try {
      // Upload file to server storage first
      const uploadedFile = await uploadAudioFile(file)
      if (!uploadedFile) {
        throw new Error('Failed to upload audio file')
      }
      
      updateJob(jobId, { status: 'pending' })
      
      // Create transcript record with the actual stored path
      const transcript = await createTranscript(uploadedFile.audio_path)
      if (!transcript) {
        throw new Error('Failed to create transcript')
      }

      updateJob(jobId, {
        transcriptId: transcript.id,
        status: 'pending',
      })

      // Poll for completion
      const completedTranscript = await waitForTranscript(transcript.id, {
        pollIntervalMs: 1000,
        maxWaitMs: 60000,
      })

      if (!completedTranscript) {
        throw new Error('Transcript polling timed out')
      }

      updateJob(jobId, { status: completedTranscript.status })

      if (completedTranscript.status === 'completed') {
        onTranscriptComplete?.(completedTranscript)
        onNoteCreated?.()
        
        // Auto-remove successful jobs after a delay
        setTimeout(() => removeJob(jobId), 3000)
      } else if (completedTranscript.status === 'failed') {
        updateJob(jobId, { 
          status: 'failed',
          error: completedTranscript.error || 'Transcription failed',
        })
      }
    } catch (error) {
      updateJob(jobId, {
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
      })
    }
  }, [updateJob, removeJob, onTranscriptComplete, onNoteCreated])

  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files) return

    Array.from(files).forEach(file => {
      if (file.type.startsWith('audio/') || file.name.match(/\.(mp3|wav|m4a|ogg|flac|webm)$/i)) {
        processFile(file)
      }
    })
  }, [processFile])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFileSelect(e.dataTransfer.files)
  }, [handleFileSelect])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const getStatusIcon = (status: TranscriptStatus | 'uploading') => {
    switch (status) {
      case 'uploading':
      case 'pending':
      case 'processing':
        return <Loader2 className="h-4 w-4 animate-spin" />
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return null
    }
  }

  const getStatusText = (status: TranscriptStatus | 'uploading') => {
    if (status === 'uploading') return 'Uploading...'
    return getTranscriptStatusLabel(status as TranscriptStatus)
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200",
          isDragging
            ? "border-[var(--accent-primary)] bg-[var(--accent-primary)]/5"
            : "border-[var(--border-color)] hover:border-[var(--accent-primary)]/50 hover:bg-[var(--bg-tertiary)]"
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*,.mp3,.wav,.m4a,.ogg,.flac,.webm"
          multiple
          onChange={(e) => handleFileSelect(e.target.files)}
          className="hidden"
        />
        
        <div className="flex flex-col items-center gap-3">
          <div className={cn(
            "p-4 rounded-full transition-colors",
            isDragging
              ? "bg-[var(--accent-primary)]/20"
              : "bg-[var(--bg-elevated)]"
          )}>
            {isDragging ? (
              <Upload className="h-8 w-8 text-[var(--accent-primary)]" />
            ) : (
              <Mic className="h-8 w-8 text-[var(--text-muted)]" />
            )}
          </div>
          
          <div>
            <p className="font-medium text-[var(--text-primary)]">
              {isDragging ? "Drop audio files here" : "Upload Audio for Transcription"}
            </p>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              Drag & drop or click to select • MP3, WAV, M4A, OGG, FLAC
            </p>
          </div>
          
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={(e) => {
              e.stopPropagation()
              fileInputRef.current?.click()
            }}
          >
            <FileAudio className="h-4 w-4 mr-2" />
            Choose Files
          </Button>
        </div>
      </div>

      {/* Active Jobs */}
      {jobs.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-[var(--text-secondary)]">
            Processing
          </h4>
          {jobs.map((job) => (
            <div
              key={job.id}
              className={cn(
                "flex items-center gap-3 p-3 rounded-lg",
                "bg-[var(--bg-tertiary)] border border-[var(--border-color)]"
              )}
            >
              <FileAudio className="h-5 w-5 text-[var(--text-muted)] flex-shrink-0" />
              
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                  {job.fileName}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  {getStatusIcon(job.status)}
                  <span className={cn(
                    "text-xs",
                    job.status === 'failed'
                      ? "text-red-500"
                      : job.status === 'completed'
                      ? "text-green-500"
                      : "text-[var(--text-muted)]"
                  )}>
                    {job.error || getStatusText(job.status)}
                  </span>
                </div>
                
                {(job.status === 'uploading' || job.status === 'pending' || job.status === 'processing') && (
                  <Progress
                    value={job.status === 'processing' ? 60 : job.status === 'pending' ? 30 : 10}
                    className="h-1 mt-2"
                  />
                )}
              </div>
              
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 flex-shrink-0"
                onClick={() => removeJob(job.id)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

