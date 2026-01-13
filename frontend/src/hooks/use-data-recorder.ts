'use client'

import { useState, useEffect, useCallback } from 'react'
import { dataRecorder, RecordingStats, RecorderConfig } from '@/lib/trading/data-recorder'

/**
 * React hook for the market data recorder
 */
export function useDataRecorder() {
  const [stats, setStats] = useState<RecordingStats>({
    isRecording: false,
    startedAt: null,
    symbolsRecording: [],
    recordCounts: {},
  })

  // Subscribe to stats updates
  useEffect(() => {
    // Get initial stats
    setStats(dataRecorder.getStats())
    
    // Subscribe to updates
    const unsubscribe = dataRecorder.subscribe(setStats)
    
    return () => {
      unsubscribe()
    }
  }, [])

  // Start recording
  const startRecording = useCallback((config?: Partial<RecorderConfig>) => {
    dataRecorder.start(config)
  }, [])

  // Stop recording
  const stopRecording = useCallback(() => {
    dataRecorder.stop()
  }, [])

  // Toggle recording
  const toggleRecording = useCallback((config?: Partial<RecorderConfig>) => {
    if (dataRecorder.isRecording()) {
      dataRecorder.stop()
    } else {
      dataRecorder.start(config)
    }
  }, [])

  // Update config
  const updateConfig = useCallback((config: Partial<RecorderConfig>) => {
    dataRecorder.updateConfig(config)
  }, [])

  // Calculate total records
  const totalRecords = Object.values(stats.recordCounts).reduce((total, counts) => {
    return total + Object.values(counts).reduce((sum, count) => sum + count, 0)
  }, 0)

  return {
    ...stats,
    totalRecords,
    startRecording,
    stopRecording,
    toggleRecording,
    updateConfig,
  }
}

