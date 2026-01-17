// Portfolio Types
export interface Position {
  ticker: string
  quantity: number
  avg_cost: number
  current_price: number
  total_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
}

export interface PortfolioState {
  timestamp: string
  cash_balance: number
  holdings_value: number
  total_value: number
  positions: Position[]
  position_count: number
  daily_pnl: number
  daily_pnl_pct: number
  total_pnl: number
  total_pnl_pct: number
  exposure?: Record<string, number>
}

// Trade Types
export interface Trade {
  trade_id: string
  ticker: string
  action: 'BUY' | 'SELL'
  quantity: number
  price: number
  total_value: number
  status: string
  executed_at: string | null
}

// Signal Types
export interface Signal {
  ticker: string
  source: 'WSB' | 'YAHOO' | 'TIPRANKS'
  signal_type: string
  sentiment_score: number
  confidence: number
  created_at: string
}

export interface AggregatedSignals {
  ticker: string
  composite_sentiment: number
  signal_strength: number
  recommendation: 'STRONG_BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG_SELL'
  wsb: any
  yahoo: any
  tipranks: any
}

// LLM Decision Types
export interface LLMDecision {
  id: number
  decision_type: 'PRE_MARKET' | 'MID_SESSION' | 'PRE_CLOSE' | 'ON_DEMAND'
  reasoning: string
  confidence_score: number
  created_at: string
  function_calls?: any[]
  signals_used?: any[]
  portfolio_state?: any
}

// Scheduler Types
export interface SchedulerStatus {
  is_running: boolean
  job_count: number
  jobs: SchedulerJob[]
  timezone: string
}

export interface SchedulerJob {
  id: string
  name: string
  next_run: string | null
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

// Trending Ticker
export interface TrendingTicker {
  ticker: string
  mentions: number
  sentiment_score: number
  top_post: string
}
