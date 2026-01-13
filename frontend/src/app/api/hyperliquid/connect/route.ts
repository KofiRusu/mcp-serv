import { NextRequest, NextResponse } from 'next/server'

/**
 * Hyperliquid API - Connect
 * 
 * Establishes a connection to Hyperliquid and returns account details.
 * This stores the connection info in a server-side session for subsequent API calls.
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
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    const apiUrl = HYPERLIQUID_API[network as keyof typeof HYPERLIQUID_API]
    if (!apiUrl) {
      return NextResponse.json(
        { error: 'Invalid network' },
        { status: 400 }
      )
    }

    // Get account state from Hyperliquid
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
      return NextResponse.json(
        { error: 'Failed to connect to Hyperliquid' },
        { status: 400 }
      )
    }

    const data = await response.json()
    
    // Extract balance
    let balance = 0
    if (data.marginSummary) {
      balance = parseFloat(data.marginSummary.accountValue) || 0
    } else if (data.crossMarginSummary) {
      balance = parseFloat(data.crossMarginSummary.accountValue) || 0
    }

    // Get available markets
    const marketsResponse = await fetch(`${apiUrl}/info`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'meta' }),
    })

    let markets: any[] = []
    if (marketsResponse.ok) {
      const marketsData = await marketsResponse.json()
      markets = marketsData.universe?.map((m: any) => ({
        symbol: m.name,
        szDecimals: m.szDecimals,
      })) || []
    }

    return NextResponse.json({
      success: true,
      balance,
      walletAddress,
      network,
      positions: data.assetPositions || [],
      markets,
      marginSummary: data.marginSummary || data.crossMarginSummary,
    })

  } catch (error: any) {
    console.error('Hyperliquid connect error:', error)
    return NextResponse.json(
      { error: error.message || 'Connection failed' },
      { status: 500 }
    )
  }
}

