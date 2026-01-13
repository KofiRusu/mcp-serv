'use client'

import { useState, useEffect, useCallback } from 'react'
import { 
  trainingDataLogger, 
  MarketContext, 
  TradeDecision, 
  TradeOutcome,
  TrainingExample 
} from '@/lib/trading/training-data-logger'

interface TrainingStats {
  total: number
  withOutcomes: number
  profitable: number
  highQuality: number
  winRate: string
  byType: Record<string, number>
  bySource: Record<string, number>
  pendingOutcomes: number
  sessionId: string
}

export function useTrainingData() {
  const [stats, setStats] = useState<TrainingStats | null>(null)
  const [loading, setLoading] = useState(false)

  // Initialize logger on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      trainingDataLogger.initialize()
      refreshStats()
    }
  }, [])

  const refreshStats = useCallback(() => {
    const newStats = trainingDataLogger.getStats()
    setStats(newStats)
  }, [])

  // Log a trade decision
  const logTradeDecision = useCallback((
    decision: TradeDecision,
    marketContext: MarketContext,
    userPrompt?: string,
    accountState?: { balance: number; openPositions: number; unrealizedPnl: number },
    positionId?: string
  ) => {
    const id = trainingDataLogger.logTradeDecision(
      decision,
      marketContext,
      userPrompt,
      accountState,
      positionId
    )
    refreshStats()
    return id
  }, [refreshStats])

  // Log a conversation
  const logConversation = useCallback((
    userPrompt: string,
    assistantResponse: string,
    marketContext: MarketContext,
    modelUsed?: string,
    decision?: TradeDecision
  ) => {
    const id = trainingDataLogger.logConversation(
      userPrompt,
      assistantResponse,
      marketContext,
      modelUsed,
      decision
    )
    refreshStats()
    return id
  }, [refreshStats])

  // Log market analysis
  const logMarketAnalysis = useCallback((
    analysis: string,
    marketContext: MarketContext,
    decision?: TradeDecision
  ) => {
    const id = trainingDataLogger.logMarketAnalysis(analysis, marketContext, decision)
    refreshStats()
    return id
  }, [refreshStats])

  // Log backtest result
  const logBacktestResult = useCallback((
    config: any,
    result: any,
    trades: any[]
  ) => {
    const message = trainingDataLogger.logBacktestResult(config, result, trades)
    refreshStats()
    return message
  }, [refreshStats])

  // Record trade outcome
  const recordOutcome = useCallback((positionId: string, outcome: TradeOutcome) => {
    trainingDataLogger.recordOutcome(positionId, outcome)
    refreshStats()
  }, [refreshStats])

  // Get all examples with optional filters
  const getExamples = useCallback((filter?: {
    type?: TrainingExample['type']
    source?: TrainingExample['source']
    profitableOnly?: boolean
    minQuality?: number
  }) => {
    return trainingDataLogger.getExamples(filter)
  }, [])

  // Export for training
  const exportForTraining = useCallback(() => {
    return trainingDataLogger.exportForTraining()
  }, [])

  // Download training data
  const downloadTrainingData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/training-data?action=export&format=jsonl&minQuality=60&profitableOnly=true')
      const blob = await response.blob()
      
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `persrm_training_${Date.now()}.jsonl`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download training data:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // Clear all data
  const clearAll = useCallback(() => {
    trainingDataLogger.clearAll()
    refreshStats()
  }, [refreshStats])

  return {
    stats,
    loading,
    refreshStats,
    logTradeDecision,
    logConversation,
    logMarketAnalysis,
    logBacktestResult,
    recordOutcome,
    getExamples,
    exportForTraining,
    downloadTrainingData,
    clearAll,
  }
}

