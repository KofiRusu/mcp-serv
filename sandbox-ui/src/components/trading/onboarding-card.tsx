'use client'

import { useTradingStore } from '@/stores/trading-store'
import { Button } from '@/components/ui/button'
import { 
  Zap, 
  Link, 
  FileText, 
  TrendingUp,
  Shield,
  Bot
} from 'lucide-react'

interface OnboardingCardProps {
  onConnect: () => void
}

export function OnboardingCard({ onConnect }: OnboardingCardProps) {
  const { initializeMockData, setCurrentAccount } = useTradingStore()

  const handleSandboxMode = () => {
    initializeMockData()
    setCurrentAccount('paper-main')
  }

  return (
    <div className="max-w-2xl w-full">
      <div className="text-center mb-8">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center mx-auto mb-4">
          <Zap className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold mb-2">Welcome to Trading</h1>
        <p className="text-gray-400">Your AI-powered trading cockpit</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4 mb-8">
        {/* Connect Exchange */}
        <div 
          className="p-6 rounded-xl border border-gray-800 bg-gradient-to-br from-purple-900/20 to-transparent hover:border-purple-500/50 cursor-pointer transition-all group"
          onClick={onConnect}
        >
          <Link className="w-10 h-10 text-purple-400 mb-4" />
          <h3 className="text-lg font-semibold mb-2 group-hover:text-purple-400 transition-colors">
            Connect Exchange
          </h3>
          <p className="text-sm text-gray-400 mb-4">
            Link your Binance, Bybit, or other exchange for live trading
          </p>
          <Button className="w-full bg-purple-600 hover:bg-purple-700">
            Connect
          </Button>
        </div>

        {/* Sandbox Mode */}
        <div 
          className="p-6 rounded-xl border border-gray-800 bg-gradient-to-br from-amber-900/20 to-transparent hover:border-amber-500/50 cursor-pointer transition-all group"
          onClick={handleSandboxMode}
        >
          <FileText className="w-10 h-10 text-amber-400 mb-4" />
          <h3 className="text-lg font-semibold mb-2 group-hover:text-amber-400 transition-colors">
            Use Sandbox
          </h3>
          <p className="text-sm text-gray-400 mb-4">
            Practice with $100k paper money and learn without risk
          </p>
          <Button variant="outline" className="w-full border-amber-500/50 text-amber-400 hover:bg-amber-500/10">
            Start Paper Trading
          </Button>
        </div>
      </div>

      {/* Features */}
      <div className="grid grid-cols-3 gap-4 text-center">
        <div className="p-4">
          <TrendingUp className="w-6 h-6 text-green-400 mx-auto mb-2" />
          <div className="text-sm font-medium">Real-time Charts</div>
          <div className="text-xs text-gray-500">Live market data</div>
        </div>
        <div className="p-4">
          <Bot className="w-6 h-6 text-purple-400 mx-auto mb-2" />
          <div className="text-sm font-medium">AI Assistant</div>
          <div className="text-xs text-gray-500">Chat-to-trade</div>
        </div>
        <div className="p-4">
          <Shield className="w-6 h-6 text-blue-400 mx-auto mb-2" />
          <div className="text-sm font-medium">Risk Management</div>
          <div className="text-xs text-gray-500">Built-in safeguards</div>
        </div>
      </div>
    </div>
  )
}

