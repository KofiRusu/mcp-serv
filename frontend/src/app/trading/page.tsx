'use client'

import { useEffect, useState } from 'react'
import { useTradingStore } from '@/stores/trading-store'
import { useHyperliquidData } from '@/hooks/use-hyperliquid-data'
import { TradingHeader } from '@/components/trading/trading-header'
import { LeftPanel } from '@/components/trading/left-panel'
import { CenterPanel } from '@/components/trading/center-panel'
import { RightPanel } from '@/components/trading/right-panel'
import { BottomBar } from '@/components/trading/bottom-bar'
import { ConnectExchangeModal } from '@/components/trading/connect-exchange-modal'
import { OnboardingCard } from '@/components/trading/onboarding-card'

export default function TradingPage() {
  const { accounts, initializeMockData, currentAccountId } = useTradingStore()
  const [showConnectModal, setShowConnectModal] = useState(false)
  const [initialized, setInitialized] = useState(false)

  // Fetch real Hyperliquid data when connected
  const { isHyperliquid, loading: hlLoading, error: hlError, lastUpdate } = useHyperliquidData()

  useEffect(() => {
    // Initialize data on first load
    if (!initialized) {
      initializeMockData()
      setInitialized(true)
    }
  }, [initialized, initializeMockData])

  const hasConnectedExchange = accounts.some(a => a.connected)

  return (
    <div className="flex flex-col h-screen bg-[#0a0a0f] text-gray-100 overflow-hidden">
      {/* Top App Bar */}
      <TradingHeader onConnectExchange={() => setShowConnectModal(true)} />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {!hasConnectedExchange && !currentAccountId ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <OnboardingCard onConnect={() => setShowConnectModal(true)} />
          </div>
        ) : (
          <>
            {/* Left Panel - Navigation & Context (20-25%) */}
            <LeftPanel />

            {/* Center Panel - Trading & Charts (50-60%) */}
            <CenterPanel />

            {/* Right Panel - AI & News (20-25%) */}
            <RightPanel />
          </>
        )}
      </div>

      {/* Bottom Global Bar */}
      <BottomBar />

      {/* Connect Exchange Modal */}
      <ConnectExchangeModal 
        open={showConnectModal} 
        onClose={() => setShowConnectModal(false)} 
      />
    </div>
  )
}

