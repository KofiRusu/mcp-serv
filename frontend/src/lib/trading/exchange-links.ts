/**
 * Exchange Links & Configuration
 * 
 * Centralized configuration for all supported exchanges.
 * Contains URLs, API docs, and integration guides.
 */

export interface ExchangeConfig {
  id: string
  name: string
  logo: string
  description: string
  type: 'CEX' | 'DEX'
  
  // URLs
  tradingUrl: string
  apiDocsUrl: string
  apiSettingsUrl?: string
  testnetUrl?: string
  faucetUrl?: string
  
  // Features
  features: string[]
  supports: {
    spot: boolean
    perpetuals: boolean
    options: boolean
    paper: boolean
    testnet: boolean
  }
  
  // API setup instructions
  apiSetupSteps: string[]
  
  // Warnings
  warnings?: string[]
}

// =============================================================================
// Exchange Configurations
// =============================================================================

export const EXCHANGE_CONFIGS: Record<string, ExchangeConfig> = {
  hyperliquid: {
    id: 'hyperliquid',
    name: 'Hyperliquid',
    logo: '💧',
    description: 'Decentralized perpetuals DEX - fastest on-chain orderbook',
    type: 'DEX',
    
    // URLs
    tradingUrl: 'https://app.hyperliquid.xyz/trade',
    apiDocsUrl: 'https://hyperliquid.gitbook.io/hyperliquid-docs',
    apiSettingsUrl: 'https://app.hyperliquid.xyz/settings',
    testnetUrl: 'https://app.hyperliquid-testnet.xyz/trade',
    faucetUrl: 'https://app.hyperliquid-testnet.xyz/faucet',
    
    features: [
      'No KYC required',
      'Self-custody (your keys)',
      'On-chain settlement',
      '50x leverage',
      'Sub-second fills',
    ],
    
    supports: {
      spot: false,
      perpetuals: true,
      options: false,
      paper: false,
      testnet: true,
    },
    
    apiSetupSteps: [
      'Connect your wallet at app.hyperliquid.xyz',
      'Go to Settings → API',
      'Create a new API wallet',
      'Copy the wallet address and private key',
      'For testnet: use app.hyperliquid-testnet.xyz',
    ],
    
    warnings: [
      'Never share your private key',
      'API wallets can only trade - no withdrawals',
      'Start with testnet to practice',
    ],
  },
  
  binance: {
    id: 'binance',
    name: 'Binance',
    logo: '🔶',
    description: 'World\'s largest crypto exchange by volume',
    type: 'CEX',
    
    tradingUrl: 'https://www.binance.com/en/trade',
    apiDocsUrl: 'https://binance-docs.github.io/apidocs',
    apiSettingsUrl: 'https://www.binance.com/en/my/settings/api-management',
    testnetUrl: 'https://testnet.binance.vision/',
    
    features: [
      'Highest liquidity',
      'Lowest fees (0.1%)',
      'Advanced order types',
      '125x leverage (futures)',
      'Testnet available',
    ],
    
    supports: {
      spot: true,
      perpetuals: true,
      options: true,
      paper: false,
      testnet: true,
    },
    
    apiSetupSteps: [
      'Log in to Binance',
      'Go to API Management',
      'Create a new API key',
      'Enable "Read" and "Spot/Margin Trading"',
      'Set IP restrictions (recommended)',
      'Copy API Key and Secret Key',
    ],
    
    warnings: [
      'Do NOT enable withdrawals',
      'Use IP whitelist for security',
      'Store credentials securely',
    ],
  },
  
  bybit: {
    id: 'bybit',
    name: 'Bybit',
    logo: '🟡',
    description: 'Popular derivatives exchange with copy trading',
    type: 'CEX',
    
    tradingUrl: 'https://www.bybit.com/trade',
    apiDocsUrl: 'https://bybit-exchange.github.io/docs',
    apiSettingsUrl: 'https://www.bybit.com/user/api-management',
    testnetUrl: 'https://testnet.bybit.com/',
    
    features: [
      'Copy trading',
      'Low latency',
      '100x leverage',
      'Unified trading account',
      'Testnet available',
    ],
    
    supports: {
      spot: true,
      perpetuals: true,
      options: true,
      paper: false,
      testnet: true,
    },
    
    apiSetupSteps: [
      'Log in to Bybit',
      'Go to API Management',
      'Create System-generated Keys',
      'Select "Read-Write" for Trading',
      'Set IP restrictions',
      'Save API Key and Secret',
    ],
    
    warnings: [
      'Do NOT enable withdrawals',
      'Bind IP address for security',
    ],
  },
  
  coinbase: {
    id: 'coinbase',
    name: 'Coinbase Advanced',
    logo: '🔵',
    description: 'US-regulated exchange with institutional features',
    type: 'CEX',
    
    tradingUrl: 'https://www.coinbase.com/advanced-trade',
    apiDocsUrl: 'https://docs.cloud.coinbase.com/advanced-trade-api',
    apiSettingsUrl: 'https://www.coinbase.com/settings/api',
    
    features: [
      'US regulated',
      'Institutional grade',
      'Advanced charting',
      'Portfolio tools',
    ],
    
    supports: {
      spot: true,
      perpetuals: false,
      options: false,
      paper: false,
      testnet: false,
    },
    
    apiSetupSteps: [
      'Log in to Coinbase',
      'Go to Settings → API',
      'Create new API key',
      'Select "Trade" permission',
      'Copy API Key and Secret',
    ],
    
    warnings: [
      'No perpetuals trading',
      'Higher fees than competitors',
    ],
  },
}

// =============================================================================
// Helper Functions
// =============================================================================

export function getExchangeConfig(exchangeId: string): ExchangeConfig | undefined {
  return EXCHANGE_CONFIGS[exchangeId]
}

export function getExchangeUrl(exchangeId: string, type: 'trading' | 'api' | 'settings' | 'testnet' | 'faucet' = 'trading'): string {
  const config = EXCHANGE_CONFIGS[exchangeId]
  if (!config) return ''
  
  switch (type) {
    case 'trading':
      return config.tradingUrl
    case 'api':
      return config.apiDocsUrl
    case 'settings':
      return config.apiSettingsUrl || config.tradingUrl
    case 'testnet':
      return config.testnetUrl || ''
    case 'faucet':
      return config.faucetUrl || ''
    default:
      return config.tradingUrl
  }
}

export function getAllExchanges(): ExchangeConfig[] {
  return Object.values(EXCHANGE_CONFIGS)
}

export function getExchangesWithFeature(feature: keyof ExchangeConfig['supports']): ExchangeConfig[] {
  return Object.values(EXCHANGE_CONFIGS).filter(e => e.supports[feature])
}

