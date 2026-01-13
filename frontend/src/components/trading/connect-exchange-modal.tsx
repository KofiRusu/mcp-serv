'use client'

import { useState } from 'react'
import { useTradingStore, Exchange } from '@/stores/trading-store'
import { EXCHANGE_CONFIGS, getExchangeConfig } from '@/lib/trading/exchange-links'
import { HyperliquidConnectModal } from './hyperliquid-connect-modal'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { 
  Check, 
  ChevronRight, 
  Shield, 
  AlertTriangle,
  Loader2,
  ExternalLink,
  Star,
  Zap,
  Globe
} from 'lucide-react'

interface ConnectExchangeModalProps {
  open: boolean
  onClose: () => void
}

const exchanges: { id: Exchange; name: string; logo: string; description: string; recommended?: boolean; type: string }[] = [
  { id: 'hyperliquid', name: 'Hyperliquid', logo: '💧', description: 'Decentralized perps - No KYC', recommended: true, type: 'DEX' },
  { id: 'binance', name: 'Binance', logo: '🔶', description: 'Largest crypto exchange', type: 'CEX' },
  { id: 'bybit', name: 'Bybit', logo: '🟡', description: 'Popular derivatives exchange', type: 'CEX' },
  { id: 'coinbase', name: 'Coinbase', logo: '🔵', description: 'US-regulated exchange', type: 'CEX' },
]

export function ConnectExchangeModal({ open, onClose }: ConnectExchangeModalProps) {
  const { connectExchange } = useTradingStore()
  const [step, setStep] = useState(1)
  const [selectedExchange, setSelectedExchange] = useState<Exchange | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showHyperliquidModal, setShowHyperliquidModal] = useState(false)

  const handleSelectExchange = (exchange: Exchange) => {
    // Hyperliquid has its own modal with wallet-based auth
    if (exchange === 'hyperliquid') {
      setShowHyperliquidModal(true)
      return
    }
    
    setSelectedExchange(exchange)
    setStep(2)
  }

  const handleConnect = async () => {
    if (!selectedExchange || !apiKey || !apiSecret) return

    setConnecting(true)
    setError(null)

    try {
      const success = await connectExchange(selectedExchange, apiKey, apiSecret)
      if (success) {
        setStep(4)
      } else {
        setError('Failed to connect. Please check your API credentials.')
      }
    } catch (err) {
      setError('Connection error. Please try again.')
    } finally {
      setConnecting(false)
    }
  }

  const handleClose = () => {
    setStep(1)
    setSelectedExchange(null)
    setApiKey('')
    setApiSecret('')
    setError(null)
    onClose()
  }

  const exchangeData = exchanges.find(e => e.id === selectedExchange)
  const exchangeConfig = selectedExchange ? getExchangeConfig(selectedExchange) : null

  return (
    <>
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-[#0d0d14] border-gray-800 text-white sm:max-w-md">
        <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {step === 1 && (
                <>
                  <Globe className="w-5 h-5 text-purple-400" />
                  Connect Exchange
                </>
              )}
            {step === 2 && 'API Permissions'}
            {step === 3 && 'Enter API Credentials'}
            {step === 4 && 'Connected!'}
          </DialogTitle>
          <DialogDescription className="text-gray-400">
              {step === 1 && 'Select an exchange to enable live trading'}
            {step === 2 && `Setting up ${exchangeData?.name}`}
            {step === 3 && 'Paste your API key and secret'}
            {step === 4 && 'Your exchange is now connected'}
          </DialogDescription>
        </DialogHeader>

        {/* Step 1: Select Exchange */}
        {step === 1 && (
          <div className="space-y-2 py-4">
            {exchanges.map((exchange) => (
              <button
                key={exchange.id}
                onClick={() => handleSelectExchange(exchange.id)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-colors text-left ${
                    exchange.recommended 
                      ? 'border-purple-500/50 bg-purple-500/5 hover:bg-purple-500/10' 
                      : 'border-gray-800 hover:border-purple-500 hover:bg-purple-500/10'
                  }`}
              >
                <div className="text-2xl">{exchange.logo}</div>
                <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{exchange.name}</span>
                      {exchange.recommended && (
                        <Badge className="bg-purple-500/20 text-purple-400 text-[10px] px-1.5">
                          <Star className="w-2.5 h-2.5 mr-0.5 fill-current" />
                          RECOMMENDED
                        </Badge>
                      )}
                      <Badge className={`text-[9px] px-1 ${exchange.type === 'DEX' ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'}`}>
                        {exchange.type}
                      </Badge>
                    </div>
                  <div className="text-xs text-gray-500">{exchange.description}</div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-500" />
              </button>
            ))}
              
              <div className="pt-3 border-t border-gray-800 mt-3">
                <p className="text-[10px] text-gray-500 text-center">
                  We recommend starting with <span className="text-purple-400">Hyperliquid Testnet</span> to practice with virtual funds
                </p>
              </div>
          </div>
        )}

        {/* Step 2: Permissions Info */}
          {step === 2 && exchangeConfig && (
          <div className="space-y-4 py-4">
            <div className="bg-gray-900 rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Shield className="w-4 h-4 text-green-400" />
                Required Permissions
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2 text-gray-300">
                  <Check className="w-4 h-4 text-green-400" />
                  Read account info & balances
                </div>
                <div className="flex items-center gap-2 text-gray-300">
                  <Check className="w-4 h-4 text-green-400" />
                  Read & place spot/futures orders
                </div>
              </div>
            </div>

              {/* Setup Steps */}
              <div className="bg-gray-900/50 rounded-lg p-3 space-y-2">
                <div className="text-xs font-medium text-gray-400">Setup Steps:</div>
                <ol className="text-xs text-gray-400 space-y-1">
                  {exchangeConfig.apiSetupSteps.slice(0, 4).map((step, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-purple-400">{i + 1}.</span>
                      {step}
                    </li>
                  ))}
                </ol>
              </div>

            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2 text-amber-400 text-sm font-medium">
                <AlertTriangle className="w-4 h-4" />
                Important
              </div>
              <ul className="text-xs text-gray-400 space-y-1">
                  {exchangeConfig.warnings?.map((warning, i) => (
                    <li key={i}>• {warning}</li>
                  ))}
              </ul>
            </div>

              <div className="flex flex-col gap-2">
                <a 
                  href={exchangeConfig.apiSettingsUrl || exchangeConfig.tradingUrl}
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 p-2 bg-purple-600/20 rounded-lg text-purple-400 hover:bg-purple-600/30 transition-colors text-sm"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open {exchangeData?.name} API Settings
                </a>
                
                {exchangeConfig.testnetUrl && (
                  <a 
                    href={exchangeConfig.testnetUrl}
                target="_blank" 
                rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 p-2 bg-green-600/20 rounded-lg text-green-400 hover:bg-green-600/30 transition-colors text-xs"
              >
                    <Zap className="w-3 h-3" />
                    Try on Testnet First (Recommended)
              </a>
                )}
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep(1)} className="flex-1 border-gray-700">
                Back
              </Button>
              <Button onClick={() => setStep(3)} className="flex-1 bg-purple-600 hover:bg-purple-700">
                  I have my API keys
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Enter Credentials */}
        {step === 3 && (
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="apiKey" className="text-sm text-gray-400">API Key</Label>
              <Input
                id="apiKey"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your API key"
                className="bg-gray-900 border-gray-700 font-mono text-sm"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="apiSecret" className="text-sm text-gray-400">API Secret</Label>
              <Input
                id="apiSecret"
                type="password"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                placeholder="Enter your API secret"
                className="bg-gray-900 border-gray-700 font-mono text-sm"
              />
            </div>

              <div className="bg-gray-900/50 rounded-lg p-3 flex items-center gap-2">
                <Shield className="w-4 h-4 text-green-400 flex-shrink-0" />
                <p className="text-[10px] text-gray-400">
                  Your credentials are encrypted and stored securely in your browser session only.
                </p>
              </div>

            {error && (
              <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep(2)} className="flex-1 border-gray-700">
                Back
              </Button>
              <Button 
                onClick={handleConnect} 
                disabled={!apiKey || !apiSecret || connecting}
                className="flex-1 bg-purple-600 hover:bg-purple-700"
              >
                {connecting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  'Connect'
                )}
              </Button>
            </div>
          </div>
        )}

        {/* Step 4: Success */}
        {step === 4 && (
          <div className="py-8 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto">
              <Check className="w-8 h-8 text-green-400" />
            </div>
            <div>
              <div className="text-lg font-medium">{exchangeData?.name} Connected!</div>
                <div className="text-sm text-gray-400">Your account is ready for live trading</div>
              </div>
              
              <div className="bg-gray-900/50 rounded-lg p-3 text-xs text-gray-400">
                <p>You can now:</p>
                <ul className="mt-2 space-y-1 text-left">
                  <li className="flex items-center gap-2">
                    <Check className="w-3 h-3 text-green-400" />
                    View live balances & positions
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="w-3 h-3 text-green-400" />
                    Place orders directly
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="w-3 h-3 text-green-400" />
                    Enable PersRM auto-trading
                  </li>
                </ul>
            </div>
              
            <Button onClick={handleClose} className="bg-purple-600 hover:bg-purple-700">
              Start Trading
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>

      {/* Hyperliquid has its own specialized modal */}
      <HyperliquidConnectModal
        open={showHyperliquidModal}
        onClose={() => {
          setShowHyperliquidModal(false)
          handleClose()
        }}
      />
    </>
  )
}
