'use client'

import { useEffect, useCallback, useState, useRef } from 'react'
import { useTradingStore } from '@/stores/trading-store'

interface HyperliquidAccountData {
  success: boolean
  balance: number
  availableBalance: number
  marginSummary?: {
    accountValue: number
    totalMarginUsed: number
    totalNtlPos: number
    withdrawable: number
  }
  positions: any[]
  orders: any[]
  recentTrades: any[]
  markets: any[]
  network: string
  walletAddress: string
  updatedAt: string
}

export function useHyperliquidData() {
  const { 
    accounts, 
    currentAccountId,
  } = useTradingStore()

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const hasLoggedError = useRef(false)

  // Get current Hyperliquid account - must be connected AND have valid credentials
  const currentAccount = accounts.find(a => a.id === currentAccountId)
  const isHyperliquid = !!(
    currentAccount?.exchange === 'hyperliquid' && 
    currentAccount?.connected === true &&
    currentAccount?.walletAddress && 
    currentAccount?.network &&
    currentAccount.walletAddress.startsWith('0x') &&
    currentAccount.walletAddress.length === 42
  )

  const fetchAccountData = useCallback(async () => {
    // Early return if not a valid, connected Hyperliquid account
    if (!isHyperliquid || !currentAccount?.walletAddress || !currentAccount?.network) {
      return null
    }

    setLoading(true)
    setError(null)

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000) // 10s timeout

      const response = await fetch('/api/hyperliquid/account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          walletAddress: currentAccount.walletAddress,
          network: currentAccount.network,
        }),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      // Handle non-OK responses safely
      if (!response.ok) {
        let errorMessage = 'Failed to fetch account data'
        try {
          const errorData = await response.json()
          errorMessage = errorData?.error || errorMessage
        } catch {
          // Response body wasn't valid JSON
        }
        throw new Error(errorMessage)
      }

      const data: HyperliquidAccountData = await response.json()
      
      if (!data || !data.success) {
        throw new Error('Invalid response from Hyperliquid API')
      }
      
      // Update store with real data
      const store = useTradingStore.getState()
      
      // Update account balance safely
      if (typeof data.balance === 'number') {
        useTradingStore.setState({
          accounts: store.accounts.map(a => 
            a.id === currentAccountId 
              ? { ...a, balance: data.balance }
              : a
          )
        })
      }

      // Update positions with real data (replace mock positions)
      if (data.positions && Array.isArray(data.positions)) {
        const nonHlPositions = store.positions.filter((p: any) => p.exchange !== 'hyperliquid')
        useTradingStore.setState({ 
          positions: [...nonHlPositions, ...data.positions],
          orders: data.orders || [],
        })
      }

      setLastUpdate(new Date())
      hasLoggedError.current = false // Reset error flag on success
      return data

    } catch (err: any) {
      // Only log error once to avoid console spam
      if (!hasLoggedError.current) {
        const errorMsg = err?.message || 'Unknown error fetching Hyperliquid data'
        setError(errorMsg)
        // Only log if it's a real connection error, not just "not connected"
        if (err?.name !== 'AbortError') {
          console.warn('Hyperliquid data fetch:', errorMsg)
        }
        hasLoggedError.current = true
      }
      return null
    } finally {
      setLoading(false)
    }
  }, [isHyperliquid, currentAccount, currentAccountId])

  // Fetch data on mount and periodically - ONLY if truly connected
  useEffect(() => {
    // Don't do anything if not a valid Hyperliquid connection
    if (!isHyperliquid) {
      setError(null)
      setLoading(false)
      return
    }

    // Initial fetch
    fetchAccountData()

    // Poll every 15 seconds (reduced from 10 to lower API load)
    const interval = setInterval(fetchAccountData, 15000)

    return () => clearInterval(interval)
  }, [isHyperliquid, fetchAccountData])

  return {
    isHyperliquid,
    loading,
    error,
    lastUpdate,
    refetch: fetchAccountData,
    account: currentAccount,
  }
}

