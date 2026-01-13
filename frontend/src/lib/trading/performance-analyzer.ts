/**
 * Performance Analyzer
 * 
 * Analyzes and compares performance across backtest, paper trading, and live trading modes.
 */

export interface BacktestResult {
  metrics: {
    totalReturn: number
    winRate: number
    sharpeRatio: number
    totalTrades: number
    maxDrawdown: number
    profitFactor: number
  }
  trades: Array<{
    entryPrice: number
    exitPrice: number
    pnl: number
    pnlPercent: number
    entryTime: number
    exitTime: number
  }>
}

export interface PaperTradingResult {
  portfolio: {
    totalPnlPercent: number
    maxDrawdown: number
  }
  trades: Array<{
    entryPrice: number
    exitPrice: number
    pnl: number
    pnlPercent: number
    entryTime: number
    exitTime: number
    slippage?: number
  }>
}

export interface LiveTradingResult {
  portfolio: {
    totalPnlPercent: number
    maxDrawdown: number
  }
  trades: Array<{
    entryPrice: number
    exitPrice: number
    pnl: number
    pnlPercent: number
    entryTime: number
    exitTime: number
    slippage?: number
  }>
}

export interface ComparisonReport {
  backtest: BacktestResult['metrics']
  paper?: PaperTradingResult['portfolio']
  live?: LiveTradingResult['portfolio']
  differences: {
    returnDiff?: number
    winRateDiff?: number
    sharpeDiff?: number
    slippageDiff?: number
  }
  validation: {
    passed: boolean
    warnings: string[]
    errors: string[]
  }
}

export interface SlippageAnalysis {
  expectedSlippage: number
  actualSlippage: number
  slippageDiff: number
  slippagePercent: number
  distribution: {
    min: number
    max: number
    mean: number
    median: number
    stdDev: number
  }
}

export interface ValidationReport {
  overall: 'pass' | 'warning' | 'fail'
  criteria: Array<{
    name: string
    status: 'pass' | 'warning' | 'fail'
    expected: number
    actual: number
    threshold: number
    message: string
  }>
  recommendations: string[]
}

/**
 * Compare backtest to paper trading results
 */
export function compareBacktestToPaper(
  backtest: BacktestResult,
  paper: PaperTradingResult
): ComparisonReport {
  const backtestWinRate = backtest.metrics.winRate
  const paperWinRate = paper.trades.length > 0
    ? paper.trades.filter(t => t.pnl > 0).length / paper.trades.length
    : 0
  
  const returnDiff = paper.portfolio.totalPnlPercent - backtest.metrics.totalReturn
  const winRateDiff = paperWinRate - backtestWinRate
  
  // Calculate average slippage from paper trades
  const avgSlippage = paper.trades.length > 0
    ? paper.trades.reduce((sum, t) => sum + (t.slippage || 0), 0) / paper.trades.length
    : 0
  
  const warnings: string[] = []
  const errors: string[] = []
  
  // Validation criteria
  if (Math.abs(returnDiff) > 0.2) {
    warnings.push(`Return difference is ${(returnDiff * 100).toFixed(2)}% (threshold: 20%)`)
  }
  
  if (Math.abs(winRateDiff) > 0.1) {
    warnings.push(`Win rate difference is ${(winRateDiff * 100).toFixed(2)}% (threshold: 10%)`)
  }
  
  if (paper.portfolio.maxDrawdown > backtest.metrics.maxDrawdown * 1.5) {
    errors.push(`Paper drawdown (${(paper.portfolio.maxDrawdown * 100).toFixed(2)}%) exceeds backtest by more than 50%`)
  }
  
  const passed = errors.length === 0 && warnings.length <= 2
  
  return {
    backtest: backtest.metrics,
    paper: paper.portfolio,
    differences: {
      returnDiff,
      winRateDiff,
      slippageDiff: avgSlippage,
    },
    validation: {
      passed,
      warnings,
      errors,
    },
  }
}

/**
 * Analyze slippage between expected and actual prices
 */
export function analyzeSlippage(
  expectedPrices: number[],
  actualPrices: number[],
  expectedSlippage: number = 0.0005
): SlippageAnalysis {
  if (expectedPrices.length !== actualPrices.length) {
    throw new Error('Price arrays must have the same length')
  }
  
  const slippages: number[] = []
  
  for (let i = 0; i < expectedPrices.length; i++) {
    const expected = expectedPrices[i]
    const actual = actualPrices[i]
    const slippage = Math.abs(actual - expected) / expected
    slippages.push(slippage)
  }
  
  const actualSlippage = slippages.reduce((a, b) => a + b, 0) / slippages.length
  const slippageDiff = actualSlippage - expectedSlippage
  
  // Calculate distribution
  slippages.sort((a, b) => a - b)
  const min = slippages[0]
  const max = slippages[slippages.length - 1]
  const mean = actualSlippage
  const median = slippages[Math.floor(slippages.length / 2)]
  
  const variance = slippages.reduce((sum, s) => sum + Math.pow(s - mean, 2), 0) / slippages.length
  const stdDev = Math.sqrt(variance)
  
  return {
    expectedSlippage,
    actualSlippage,
    slippageDiff,
    slippagePercent: (slippageDiff / expectedSlippage) * 100,
    distribution: {
      min,
      max,
      mean,
      median,
      stdDev,
    },
  }
}

/**
 * Validate strategy performance across modes
 */
export function validateStrategy(
  backtest?: BacktestResult,
  paper?: PaperTradingResult,
  live?: LiveTradingResult
): ValidationReport {
  const criteria: ValidationReport['criteria'] = []
  const recommendations: string[] = []
  
  if (!backtest) {
    return {
      overall: 'fail',
      criteria: [{
        name: 'Backtest Required',
        status: 'fail',
        expected: 0,
        actual: 0,
        threshold: 0,
        message: 'Backtest results are required for validation',
      }],
      recommendations: ['Run a backtest before validating strategy'],
    }
  }
  
  // Validate paper trading if available
  if (paper) {
    const returnDiff = Math.abs(paper.portfolio.totalPnlPercent - backtest.metrics.totalReturn)
    const returnStatus = returnDiff <= 0.2 ? 'pass' : returnDiff <= 0.3 ? 'warning' : 'fail'
    
    criteria.push({
      name: 'Return Consistency (Paper vs Backtest)',
      status: returnStatus,
      expected: backtest.metrics.totalReturn,
      actual: paper.portfolio.totalPnlPercent,
      threshold: 0.2,
      message: returnDiff <= 0.2
        ? `Return difference is within acceptable range (${(returnDiff * 100).toFixed(2)}%)`
        : `Return difference is ${(returnDiff * 100).toFixed(2)}% (threshold: 20%)`,
    })
    
    const paperWinRate = paper.trades.length > 0
      ? paper.trades.filter(t => t.pnl > 0).length / paper.trades.length
      : 0
    const winRateDiff = Math.abs(paperWinRate - backtest.metrics.winRate)
    const winRateStatus = winRateDiff <= 0.1 ? 'pass' : winRateDiff <= 0.15 ? 'warning' : 'fail'
    
    criteria.push({
      name: 'Win Rate Consistency (Paper vs Backtest)',
      status: winRateStatus,
      expected: backtest.metrics.winRate,
      actual: paperWinRate,
      threshold: 0.1,
      message: winRateDiff <= 0.1
        ? `Win rate difference is within acceptable range (${(winRateDiff * 100).toFixed(2)}%)`
        : `Win rate difference is ${(winRateDiff * 100).toFixed(2)}% (threshold: 10%)`,
    })
    
    const drawdownRatio = paper.portfolio.maxDrawdown / backtest.metrics.maxDrawdown
    const drawdownStatus = drawdownRatio <= 1.5 ? 'pass' : drawdownRatio <= 2.0 ? 'warning' : 'fail'
    
    criteria.push({
      name: 'Drawdown Consistency (Paper vs Backtest)',
      status: drawdownStatus,
      expected: backtest.metrics.maxDrawdown,
      actual: paper.portfolio.maxDrawdown,
      threshold: 1.5,
      message: drawdownRatio <= 1.5
        ? `Drawdown is within acceptable range (${(drawdownRatio * 100).toFixed(0)}% of backtest)`
        : `Drawdown exceeds backtest by ${((drawdownRatio - 1) * 100).toFixed(0)}% (threshold: 50%)`,
    })
    
    // Analyze slippage
    const avgSlippage = paper.trades.length > 0
      ? paper.trades.reduce((sum, t) => sum + Math.abs(t.slippage || 0), 0) / paper.trades.length
      : 0
    
    if (avgSlippage > 0.002) {
      recommendations.push(`High average slippage detected: ${(avgSlippage * 100).toFixed(3)}%. Consider using limit orders or reducing position sizes.`)
    }
  }
  
  // Validate live trading if available
  if (live) {
    const returnDiff = Math.abs(live.portfolio.totalPnlPercent - backtest.metrics.totalReturn)
    const returnStatus = returnDiff <= 0.25 ? 'pass' : returnDiff <= 0.35 ? 'warning' : 'fail'
    
    criteria.push({
      name: 'Return Consistency (Live vs Backtest)',
      status: returnStatus,
      expected: backtest.metrics.totalReturn,
      actual: live.portfolio.totalPnlPercent,
      threshold: 0.25,
      message: returnDiff <= 0.25
        ? `Return difference is within acceptable range (${(returnDiff * 100).toFixed(2)}%)`
        : `Return difference is ${(returnDiff * 100).toFixed(2)}% (threshold: 25%)`,
    })
    
    if (paper) {
      const liveVsPaperDiff = Math.abs(live.portfolio.totalPnlPercent - paper.portfolio.totalPnlPercent)
      if (liveVsPaperDiff > 0.15) {
        recommendations.push(`Significant difference between paper and live trading (${(liveVsPaperDiff * 100).toFixed(2)}%). Review execution model and market conditions.`)
      }
    }
  }
  
  // Determine overall status
  const failCount = criteria.filter(c => c.status === 'fail').length
  const warnCount = criteria.filter(c => c.status === 'warning').length
  
  let overall: 'pass' | 'warning' | 'fail'
  if (failCount > 0) {
    overall = 'fail'
  } else if (warnCount > 0) {
    overall = 'warning'
  } else {
    overall = 'pass'
  }
  
  // Add general recommendations
  if (overall === 'pass' && paper && paper.trades.length >= 20) {
    recommendations.push('Strategy validation passed. Consider starting with micro positions in live trading.')
  } else if (overall === 'warning') {
    recommendations.push('Some validation criteria showed warnings. Monitor closely and consider adjustments before increasing position sizes.')
  } else if (overall === 'fail') {
    recommendations.push('Validation failed. Do not proceed to live trading until issues are resolved.')
  }
  
  return {
    overall,
    criteria,
    recommendations,
  }
}

/**
 * Calculate performance metrics from trades
 */
export function calculatePerformanceMetrics(trades: Array<{ pnl: number; pnlPercent: number }>): {
  totalReturn: number
  winRate: number
  avgWin: number
  avgLoss: number
  profitFactor: number
  expectancy: number
} {
  if (trades.length === 0) {
    return {
      totalReturn: 0,
      winRate: 0,
      avgWin: 0,
      avgLoss: 0,
      profitFactor: 0,
      expectancy: 0,
    }
  }
  
  const winningTrades = trades.filter(t => t.pnl > 0)
  const losingTrades = trades.filter(t => t.pnl <= 0)
  
  const totalReturn = trades.reduce((sum, t) => sum + t.pnlPercent, 0)
  const winRate = winningTrades.length / trades.length
  
  const grossProfit = winningTrades.reduce((sum, t) => sum + t.pnl, 0)
  const grossLoss = Math.abs(losingTrades.reduce((sum, t) => sum + t.pnl, 0))
  
  const avgWin = winningTrades.length > 0 ? grossProfit / winningTrades.length : 0
  const avgLoss = losingTrades.length > 0 ? grossLoss / losingTrades.length : 0
  
  const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0
  const expectancy = (winRate * avgWin) - ((1 - winRate) * avgLoss)
  
  return {
    totalReturn,
    winRate,
    avgWin,
    avgLoss,
    profitFactor,
    expectancy,
  }
}

