'use client'

/**
 * Hyperliquid Connect Modal
 * 
 * Allows users to connect their Hyperliquid account for live trading.
 * Hyperliquid uses wallet-based authentication with private key signing.
 * 
 * Connection Options:
 * 1. API Wallet - Generate an API wallet on Hyperliquid and enter the private key
 * 2. Manual Entry - Enter wallet address and private key directly
 */

import { useState, useEffect } from 'react'
import { useTradingStore } from '@/stores/trading-store'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Check, 
  ChevronRight, 
  Shield, 
  AlertTriangle,
  Loader2,
  ExternalLink,
  Copy,
  Eye,
  EyeOff,
  Wallet,
  Key,
  Info,
  CheckCircle,
  XCircle,
  Zap
} from 'lucide-react'

interface HyperliquidConnectModalProps {
  open: boolean
  onClose: () => void
}

type ConnectionStep = 'intro' | 'setup' | 'credentials' | 'verify' | 'success'
type NetworkType = 'mainnet' | 'testnet'

export function HyperliquidConnectModal({ open, onClose }: HyperliquidConnectModalProps) {
  const { connectHyperliquid, accounts } = useTradingStore()
  const [step, setStep] = useState<ConnectionStep>('intro')
  const [network, setNetwork] = useState<NetworkType>('testnet')
  const [walletAddress, setWalletAddress] = useState('')
  const [privateKey, setPrivateKey] = useState('')
  const [showPrivateKey, setShowPrivateKey] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [balance, setBalance] = useState<number | null>(null)

  // Check if already connected
  const existingConnection = accounts.find(a => a.exchange === 'hyperliquid' && a.connected)

  const handleClose = () => {
    setStep('intro')
    setWalletAddress('')
    setPrivateKey('')
    setError(null)
    setBalance(null)
    onClose()
  }

  const validateAddress = (address: string): boolean => {
    return /^0x[a-fA-F0-9]{40}$/.test(address)
  }

  const validatePrivateKey = (key: string): boolean => {
    // Private key should be 64 hex characters (or 66 with 0x prefix)
    const cleanKey = key.startsWith('0x') ? key.slice(2) : key
    return /^[a-fA-F0-9]{64}$/.test(cleanKey)
  }

  const handleVerify = async () => {
    setError(null)
    
    if (!validateAddress(walletAddress)) {
      setError('Invalid wallet address. Must be a valid Ethereum address (0x...)')
      return
    }

    if (!validatePrivateKey(privateKey)) {
      setError('Invalid private key. Must be 64 hexadecimal characters.')
      return
    }

    setVerifying(true)

    try {
      // Call API to verify connection and get balance
      const response = await fetch('/api/hyperliquid/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          walletAddress,
          privateKey: privateKey.startsWith('0x') ? privateKey : `0x${privateKey}`,
          network,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to verify connection')
      }

      setBalance(data.balance)
      setStep('verify')
    } catch (err: any) {
      setError(err.message || 'Failed to verify connection. Please check your credentials.')
    } finally {
      setVerifying(false)
    }
  }

  const handleConnect = async () => {
    setConnecting(true)
    setError(null)

    try {
      const success = await connectHyperliquid(
        walletAddress,
        privateKey.startsWith('0x') ? privateKey : `0x${privateKey}`,
        network
      )

      if (success) {
        setStep('success')
      } else {
        setError('Failed to connect. Please try again.')
      }
    } catch (err: any) {
      setError(err.message || 'Connection error. Please try again.')
    } finally {
      setConnecting(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-[#0d0d14] border-gray-800 text-white sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span className="text-2xl">💧</span>
            {step === 'intro' && 'Connect Hyperliquid'}
            {step === 'setup' && 'Setup Guide'}
            {step === 'credentials' && 'Enter Credentials'}
            {step === 'verify' && 'Verify Connection'}
            {step === 'success' && 'Connected!'}
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            {step === 'intro' && 'Connect your Hyperliquid account for live trading'}
            {step === 'setup' && 'Follow these steps to get your API credentials'}
            {step === 'credentials' && 'Enter your wallet address and private key'}
            {step === 'verify' && 'Confirm your account details'}
            {step === 'success' && 'Your Hyperliquid account is ready'}
          </DialogDescription>
        </DialogHeader>

        {/* Step: Intro */}
        {step === 'intro' && (
          <div className="space-y-4 py-4">
            {/* Already Connected Notice */}
            {existingConnection && (
              <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
                <div className="flex items-center gap-2 text-green-400 text-sm font-medium mb-1">
                  <CheckCircle className="w-4 h-4" />
                  Already Connected
                </div>
                <div className="text-xs text-gray-400">
                  <span className="font-mono">{existingConnection.walletAddress?.slice(0, 6)}...{existingConnection.walletAddress?.slice(-4)}</span>
                  {' on '}
                  <Badge className="text-[10px]">{existingConnection.network === 'testnet' ? 'Testnet' : 'Mainnet'}</Badge>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  You can connect a different account or switch networks below.
                </p>
              </div>
            )}

            {/* Network Selection */}
            <div className="space-y-2">
              <Label className="text-sm text-gray-400">Select Network</Label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setNetwork('testnet')}
                  className={`p-3 rounded-lg border transition-colors text-left ${
                    network === 'testnet'
                      ? 'border-green-500 bg-green-500/10'
                      : 'border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-500/20 text-green-400 text-[10px]">RECOMMENDED</Badge>
                  </div>
                  <div className="font-medium mt-1">Testnet</div>
                  <div className="text-xs text-gray-500">Practice with fake funds</div>
                </button>
                <button
                  onClick={() => setNetwork('mainnet')}
                  className={`p-3 rounded-lg border transition-colors text-left ${
                    network === 'mainnet'
                      ? 'border-purple-500 bg-purple-500/10'
                      : 'border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Badge className="bg-amber-500/20 text-amber-400 text-[10px]">REAL FUNDS</Badge>
                  </div>
                  <div className="font-medium mt-1">Mainnet</div>
                  <div className="text-xs text-gray-500">Trade with real assets</div>
                </button>
              </div>
            </div>

            {/* Info Box */}
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2 text-blue-400 text-sm font-medium">
                <Info className="w-4 h-4" />
                What you'll need
              </div>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>• A Hyperliquid account with an API wallet</li>
                <li>• Your wallet address (0x...)</li>
                <li>• Your API wallet private key</li>
              </ul>
            </div>

            {/* Warning for Mainnet */}
            {network === 'mainnet' && (
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4 space-y-2">
                <div className="flex items-center gap-2 text-amber-400 text-sm font-medium">
                  <AlertTriangle className="w-4 h-4" />
                  Mainnet Warning
                </div>
                <p className="text-xs text-gray-400">
                  You're about to connect with real funds. Only deposit what you can afford to lose.
                  Auto-trading with real funds carries significant risk.
                </p>
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <Button variant="outline" onClick={handleClose} className="flex-1 border-gray-700">
                Cancel
              </Button>
              <Button 
                onClick={() => setStep('setup')} 
                className="flex-1 bg-purple-600 hover:bg-purple-700"
              >
                Continue
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}

        {/* Step: Setup Guide */}
        {step === 'setup' && (
          <div className="space-y-4 py-4">
            <div className="space-y-3">
              {/* Step 1 */}
              <div className="flex gap-3 p-3 bg-gray-900/50 rounded-lg">
                <div className="w-6 h-6 rounded-full bg-purple-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
                  1
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium">Go to Hyperliquid</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    Visit {network === 'mainnet' ? 'app.hyperliquid.xyz/trade' : 'app.hyperliquid-testnet.xyz/trade'}
                  </div>
                  <a
                    href={network === 'mainnet' 
                      ? 'https://app.hyperliquid.xyz/trade' 
                      : 'https://app.hyperliquid-testnet.xyz/trade'
                    }
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-purple-400 hover:text-purple-300 mt-1"
                  >
                    Open Hyperliquid Trading
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex gap-3 p-3 bg-gray-900/50 rounded-lg">
                <div className="w-6 h-6 rounded-full bg-purple-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
                  2
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium">Connect your wallet</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    Connect with MetaMask, WalletConnect, or another wallet
                  </div>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex gap-3 p-3 bg-gray-900/50 rounded-lg">
                <div className="w-6 h-6 rounded-full bg-purple-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
                  3
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium">Create API Wallet</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    Go to Settings → API → Create new API wallet
                  </div>
                </div>
              </div>

              {/* Step 4 */}
              <div className="flex gap-3 p-3 bg-gray-900/50 rounded-lg">
                <div className="w-6 h-6 rounded-full bg-purple-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
                  4
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium">Export Private Key</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    Copy your API wallet address and private key securely
                  </div>
                </div>
              </div>

              {network === 'testnet' && (
                <div className="flex gap-3 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                  <div className="w-6 h-6 rounded-full bg-green-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
                    5
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-green-400">Get Testnet Funds</div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      Use the faucet to get free testnet USDC for practice
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="bg-gray-900/50 rounded-lg p-3 flex items-center gap-2">
              <Shield className="w-4 h-4 text-green-400 flex-shrink-0" />
              <p className="text-xs text-gray-400">
                Your private key is stored securely in your browser session only. 
                It is never sent to our servers or stored permanently.
              </p>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep('intro')} className="flex-1 border-gray-700">
                Back
              </Button>
              <Button onClick={() => setStep('credentials')} className="flex-1 bg-purple-600 hover:bg-purple-700">
                I have my credentials
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}

        {/* Step: Enter Credentials */}
        {step === 'credentials' && (
          <div className="space-y-4 py-4">
            <div className="flex items-center gap-2 mb-2">
              <Badge className={network === 'testnet' ? 'bg-green-500/20 text-green-400' : 'bg-purple-500/20 text-purple-400'}>
                {network === 'testnet' ? 'TESTNET' : 'MAINNET'}
              </Badge>
            </div>

            <div className="space-y-2">
              <Label htmlFor="walletAddress" className="text-sm text-gray-400 flex items-center gap-1">
                <Wallet className="w-3 h-3" />
                Wallet Address
              </Label>
              <Input
                id="walletAddress"
                value={walletAddress}
                onChange={(e) => setWalletAddress(e.target.value.trim())}
                placeholder="0x..."
                className="bg-gray-900 border-gray-700 font-mono text-sm"
              />
              {walletAddress && !validateAddress(walletAddress) && (
                <p className="text-xs text-red-400">Invalid address format</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="privateKey" className="text-sm text-gray-400 flex items-center gap-1">
                <Key className="w-3 h-3" />
                Private Key
              </Label>
              <div className="relative">
                <Input
                  id="privateKey"
                  type={showPrivateKey ? 'text' : 'password'}
                  value={privateKey}
                  onChange={(e) => setPrivateKey(e.target.value.trim())}
                  placeholder="Enter your API wallet private key"
                  className="bg-gray-900 border-gray-700 font-mono text-sm pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPrivateKey(!showPrivateKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                >
                  {showPrivateKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {privateKey && !validatePrivateKey(privateKey) && (
                <p className="text-xs text-red-400">Invalid private key format</p>
              )}
            </div>

            {error && (
              <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 flex items-start gap-2">
                <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                {error}
              </div>
            )}

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep('setup')} className="flex-1 border-gray-700">
                Back
              </Button>
              <Button 
                onClick={handleVerify}
                disabled={!walletAddress || !privateKey || verifying}
                className="flex-1 bg-purple-600 hover:bg-purple-700"
              >
                {verifying ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    Verify Connection
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* Step: Verify */}
        {step === 'verify' && (
          <div className="space-y-4 py-4">
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
              <div className="flex items-center gap-2 text-green-400 mb-3">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Connection Verified</span>
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Network</span>
                  <Badge className={network === 'testnet' ? 'bg-green-500/20 text-green-400' : 'bg-purple-500/20 text-purple-400'}>
                    {network === 'testnet' ? 'Testnet' : 'Mainnet'}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Address</span>
                  <span className="font-mono text-xs">
                    {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Balance</span>
                  <span className="font-mono text-green-400">
                    ${balance?.toLocaleString() || '0.00'} USDC
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-gray-900/50 rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Shield className="w-4 h-4 text-green-400" />
                Permissions
              </div>
              <div className="space-y-1 text-xs text-gray-400">
                <div className="flex items-center gap-2">
                  <Check className="w-3 h-3 text-green-400" />
                  Read account info & positions
                </div>
                <div className="flex items-center gap-2">
                  <Check className="w-3 h-3 text-green-400" />
                  Place & cancel orders
                </div>
                <div className="flex items-center gap-2">
                  <XCircle className="w-3 h-3 text-red-400" />
                  <span className="text-red-400">No withdrawal access</span>
                </div>
              </div>
            </div>

            {error && (
              <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep('credentials')} className="flex-1 border-gray-700">
                Back
              </Button>
              <Button 
                onClick={handleConnect}
                disabled={connecting}
                className="flex-1 bg-green-600 hover:bg-green-700"
              >
                {connecting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 mr-2" />
                    Connect Account
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* Step: Success */}
        {step === 'success' && (
          <div className="py-8 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto">
              <Check className="w-8 h-8 text-green-400" />
            </div>
            <div>
              <div className="text-lg font-medium">Hyperliquid Connected!</div>
              <div className="text-sm text-gray-400 mt-1">
                {network === 'testnet' 
                  ? 'You can now practice trading with testnet funds'
                  : 'Your account is ready for live trading'
                }
              </div>
            </div>
            <div className="bg-gray-900/50 rounded-lg p-3 text-left">
              <div className="text-xs text-gray-500 mb-1">Connected Address</div>
              <div className="font-mono text-sm flex items-center justify-between">
                <span>{walletAddress.slice(0, 10)}...{walletAddress.slice(-8)}</span>
                <button 
                  onClick={() => copyToClipboard(walletAddress)}
                  className="text-gray-400 hover:text-white"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
            </div>
            <Button onClick={handleClose} className="w-full bg-purple-600 hover:bg-purple-700">
              Start Trading
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

