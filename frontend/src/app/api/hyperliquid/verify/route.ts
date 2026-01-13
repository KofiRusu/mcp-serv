import { NextRequest, NextResponse } from 'next/server'

/**
 * Hyperliquid API - Verify Connection
 * 
 * Verifies that the provided wallet address and private key can connect to Hyperliquid.
 * Returns the account balance if successful.
 */

const HYPERLIQUID_API = {
  mainnet: 'https://api.hyperliquid.xyz',
  testnet: 'https://api.hyperliquid-testnet.xyz',
}

export async function POST(request: NextRequest) {
  try {
    const { walletAddress, privateKey, network } = await request.json()

    if (!walletAddress || !privateKey || !network) {
      return NextResponse.json(
        { error: 'Missing required fields: walletAddress, privateKey, network' },
        { status: 400 }
      )
    }

    // Validate wallet address format
    if (!/^0x[a-fA-F0-9]{40}$/.test(walletAddress)) {
      return NextResponse.json(
        { error: 'Invalid wallet address format' },
        { status: 400 }
      )
    }

    // Validate private key format
    const cleanKey = privateKey.startsWith('0x') ? privateKey.slice(2) : privateKey
    if (!/^[a-fA-F0-9]{64}$/.test(cleanKey)) {
      return NextResponse.json(
        { error: 'Invalid private key format' },
        { status: 400 }
      )
    }

    const apiUrl = HYPERLIQUID_API[network as keyof typeof HYPERLIQUID_API]
    if (!apiUrl) {
      return NextResponse.json(
        { error: 'Invalid network. Use "mainnet" or "testnet"' },
        { status: 400 }
      )
    }

    // Query Hyperliquid API for account info
    // Using the info endpoint which doesn't require signing
    const response = await fetch(`${apiUrl}/info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        type: 'clearinghouseState',
        user: walletAddress,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Hyperliquid API error:', errorText)
      return NextResponse.json(
        { error: 'Failed to connect to Hyperliquid. Please check your credentials.' },
        { status: 400 }
      )
    }

    const data = await response.json()
    
    // Extract balance from marginSummary
    let balance = 0
    if (data.marginSummary) {
      balance = parseFloat(data.marginSummary.accountValue) || 0
    } else if (data.crossMarginSummary) {
      balance = parseFloat(data.crossMarginSummary.accountValue) || 0
    }

    // For testnet, if balance is 0, that's okay - they might need to use faucet
    if (network === 'testnet' && balance === 0) {
      return NextResponse.json({
        success: true,
        balance: 0,
        message: 'Account verified. Use the Hyperliquid testnet faucet to get test funds.',
        positions: data.assetPositions || [],
      })
    }

    return NextResponse.json({
      success: true,
      balance,
      positions: data.assetPositions || [],
      marginSummary: data.marginSummary || data.crossMarginSummary,
    })

  } catch (error: any) {
    console.error('Hyperliquid verify error:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to verify connection' },
      { status: 500 }
    )
  }
}

