import axios from 'axios'
import type {
  PortfolioState,
  Trade,
  Signal,
  AggregatedSignals,
  LLMDecision,
  SchedulerStatus,
  TrendingTicker,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Scheduler API
export const schedulerApi = {
  getStatus: () => api.get<SchedulerStatus>('/api/scheduler/status'),
  start: () => api.post('/api/scheduler/start'),
  stop: () => api.post('/api/scheduler/stop'),
  executeSession: (decisionType: string) =>
    api.post(`/api/scheduler/execute/${decisionType}`),
}

// Portfolio API
export const portfolioApi = {
  getStatus: () => api.get<PortfolioState>('/api/portfolio/status'),
  getHistory: (days: number = 30) =>
    api.get('/api/portfolio/history', { params: { days } }),
  getPosition: (ticker: string) =>
    api.get(`/api/portfolio/position/${ticker}`),
  saveSnapshot: () => api.post('/api/portfolio/snapshot'),
}

// Trading API
export const tradingApi = {
  analyzeTicker: (ticker: string) =>
    api.post('/api/trading/analyze', { ticker }),
  getHistory: (days: number = 7) =>
    api.get<{ trades: Trade[] }>('/api/trading/history', { params: { days } }),
  getDecisions: (limit: number = 20) =>
    api.get<{ decisions: LLMDecision[] }>('/api/trading/decisions', {
      params: { limit },
    }),
  getDecisionDetail: (id: number) =>
    api.get<{ decision: LLMDecision }>(`/api/trading/decisions/${id}`),
}

// Signals API
export const signalsApi = {
  getTrending: (limit: number = 20) =>
    api.get<{ tickers: TrendingTicker[] }>('/api/signals/trending', {
      params: { limit },
    }),
  getTickerSignals: (ticker: string) =>
    api.get<{ signals: AggregatedSignals }>(`/api/signals/ticker/${ticker}`),
  getRecent: (hoursBack: number = 24, limit: number = 50) =>
    api.get<{ signals: Signal[] }>('/api/signals/recent', {
      params: { hours_back: hoursBack, limit },
    }),
}

// Settings API
export const settingsApi = {
  getApiKeys: () => api.get('/api/settings/api-keys'),
  saveApiKey: (keyName: string, keyValue: string) =>
    api.post('/api/settings/api-keys', { key_name: keyName, key_value: keyValue }),
  deleteApiKey: (keyName: string) =>
    api.delete(`/api/settings/api-keys/${keyName}`),
  getPreferences: () => api.get('/api/settings/preferences'),
  savePreference: (key: string, value: string) =>
    api.post('/api/settings/preferences', { key, value }),
  getRiskParams: () => api.get('/api/settings/risk-params'),
}

// System API
export const systemApi = {
  getInfo: () => api.get('/api/info'),
  getHealth: () => api.get('/health'),
}

export default api
