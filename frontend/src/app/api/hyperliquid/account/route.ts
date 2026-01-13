import { NextRequest, NextResponse } from 'next/server'

/**
 * Hyperliquid API - Account Data
 * 
 * Fetches real-time account data including:
 * - Balance and margin info
 * - Open positions
 * - Open orders
 * - Recent trades
 */

const HYPERLIQUID_API = {
  mainnet: 'https://api.hyperliquid.xyz',
  testnet: 'https://api.hyperliquid-testnet.xyz',
}

export async function POST(request: NextRequest) {
  try {
    const { walletAddress, network } = await request.json()

    if (!walletAddress || !network) {
      return NextResponse.json(
        { error: 'Missing required fields: walletAddress, network' },
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

    // Fetch all account data in parallel with error handling
    const fetchWithErrorHandling = async (body: any) => {
      try {
        const response = await fetch(`${apiUrl}/info`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        if (!response.ok) {
          console.error(`Hyperliquid API error for ${body.type}:`, await response.text())
          return null
        }
        return await response.json()
      } catch (err) {
        console.error(`Failed to fetch ${body.type}:`, err)
        return null
      }
    }

    const [clearinghouseState, openOrders, userFills, meta] = await Promise.all([
      fetchWithErrorHandling({ type: 'clearinghouseState', user: walletAddress }),
      fetchWithErrorHandling({ type: 'openOrders', user: walletAddress }),
      fetchWithErrorHandling({ type: 'userFills', user: walletAddress }),
      fetchWithErrorHandling({ type: 'meta' }),
    ])

    // Check if we got the essential data
    if (!clearinghouseState) {
      return NextResponse.json(
        { error: 'Failed to fetch account state from Hyperliquid' },
        { status: 502 }
      )
    }

    // Extract balance safely
    const marginSummary = clearinghouseState?.marginSummary || clearinghouseState?.crossMarginSummary || {}
    const balance = parseFloat(marginSummary?.accountValue) || 0
    const availableBalance = parseFloat(marginSummary?.withdrawable) || 0

    // Transform positions to our format
    const positions = (clearinghouseState?.assetPositions || []).map((pos: any) => {
      const position = pos.position
      const coin = position.coin
      const size = parseFloat(position.szi)
      const entryPrice = parseFloat(position.entryPx)
      const markPrice = parseFloat(position.positionValue) / Math.abs(size) || entryPrice
      const unrealizedPnl = parseFloat(position.unrealizedPnl) || 0
      const leverage = parseFloat(position.leverage?.value) || 1

      return {
        id: `hl-${coin}-${Date.now()}`,
        symbol: `${coin}USDT`,
        side: size >= 0 ? 'long' : 'short',
        size: Math.abs(size),
        entryPrice,
        currentPrice: markPrice,
        pnl: unrealizedPnl,
        pnlPercent: entryPrice > 0 ? (unrealizedPnl / (entryPrice * Math.abs(size))) * 100 : 0,
        leverage,
        liquidationPrice: parseFloat(position.liquidationPx) || undefined,
        marginUsed: parseFloat(position.marginUsed) || 0,
        openedAt: new Date().toISOString(), // Hyperliquid doesn't provide this
        exchange: 'hyperliquid',
      }
    }).filter((p: any) => p.size > 0) // Filter out zero positions

    // Transform orders to our format
    const orders = (openOrders || []).map((order: any) => ({
      id: order.oid?.toString() || `hl-order-${Date.now()}`,
      symbol: `${order.coin}USDT`,
      side: order.side === 'B' ? 'buy' : 'sell',
      type: order.orderType === 'limit' ? 'limit' : 'market',
      size: parseFloat(order.sz) || 0,
      price: parseFloat(order.limitPx) || 0,
      status: 'pending',
      createdAt: new Date(order.timestamp || Date.now()).toISOString(),
      exchange: 'hyperliquid',
    }))

    // Transform recent trades
    const recentTrades = (userFills || []).slice(0, 50).map((fill: any) => ({
      id: fill.tid?.toString() || `hl-trade-${Date.now()}`,
      symbol: `${fill.coin}USDT`,
      side: fill.side === 'B' ? 'buy' : 'sell',
      size: parseFloat(fill.sz) || 0,
      price: parseFloat(fill.px) || 0,
      fee: parseFloat(fill.fee) || 0,
      timestamp: new Date(fill.time || Date.now()).toISOString(),
      exchange: 'hyperliquid',
    }))

    // Get available markets
    const markets = (meta?.universe || []).map((m: any) => ({
      symbol: `${m.name}USDT`,
      baseAsset: m.name,
      quoteAsset: 'USDT',
      exchange: 'hyperliquid',
      szDecimals: m.szDecimals,
    }))

    return NextResponse.json({
      success: true,
      balance,
      availableBalance,
      marginSummary: {
        accountValue: balance,
        totalMarginUsed: parseFloat(marginSummary?.totalMarginUsed) || 0,
        totalNtlPos: parseFloat(marginSummary?.totalNtlPos) || 0,
        withdrawable: availableBalance,
      },
      positions,
      orders,
      recentTrades,
      markets,
      network,
      walletAddress,
      updatedAt: new Date().toISOString(),
    })

  } catch (error: any) {
    console.error('Hyperliquid account fetch error:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to fetch account data' },
      { status: 500 }
    )
  }
}

