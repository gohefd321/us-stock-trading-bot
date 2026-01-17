import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Chip,
  TextField,
  Button,
  Alert,
} from '@mui/material'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import { signalsApi, tradingApi } from '../services/api'
import type { TrendingTicker, AggregatedSignals } from '../types'

export default function Signals() {
  const [trending, setTrending] = useState<TrendingTicker[]>([])
  const [searchTicker, setSearchTicker] = useState('')
  const [selectedSignals, setSelectedSignals] = useState<AggregatedSignals | null>(null)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    loadTrending()
    const interval = setInterval(loadTrending, 60000)
    return () => clearInterval(interval)
  }, [])

  const loadTrending = async () => {
    try {
      const res = await signalsApi.getTrending(20)
      setTrending(res.data.tickers || [])
    } catch (error) {
      console.error('Failed to load trending tickers:', error)
    }
  }

  const handleAnalyzeTicker = async () => {
    if (!searchTicker) return

    setAnalyzing(true)
    try {
      const res = await signalsApi.getTickerSignals(searchTicker.toUpperCase())
      setSelectedSignals(res.data.signals)
    } catch (error) {
      console.error('Failed to analyze ticker:', error)
    } finally {
      setAnalyzing(false)
    }
  }

  const getRecommendationColor = (rec: string) => {
    if (rec === 'STRONG_BUY' || rec === 'BUY') return 'success'
    if (rec === 'STRONG_SELL' || rec === 'SELL') return 'error'
    return 'default'
  }

  const getSentimentIcon = (sentiment: number) => {
    return sentiment >= 0 ? (
      <TrendingUpIcon color="success" />
    ) : (
      <TrendingDownIcon color="error" />
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        시장 신호
      </Typography>

      {/* Ticker Analysis */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          종목 분석
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField
            label="티커 심볼"
            value={searchTicker}
            onChange={(e) => setSearchTicker(e.target.value.toUpperCase())}
            placeholder="AAPL"
            size="small"
          />
          <Button
            variant="contained"
            onClick={handleAnalyzeTicker}
            disabled={analyzing || !searchTicker}
          >
            분석
          </Button>
        </Box>

        {selectedSignals && (
          <Alert
            severity={
              selectedSignals.recommendation.includes('BUY')
                ? 'success'
                : selectedSignals.recommendation.includes('SELL')
                ? 'error'
                : 'info'
            }
            sx={{ mb: 2 }}
          >
            <Typography variant="h6">
              {selectedSignals.ticker} - {selectedSignals.recommendation}
            </Typography>
            <Typography>
              종합 심리: {(selectedSignals.composite_sentiment * 100).toFixed(0)}% |
              신호 강도: {(selectedSignals.signal_strength * 100).toFixed(0)}%
            </Typography>
          </Alert>
        )}

        {selectedSignals && (
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">
                    WallStreetBets
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                    {getSentimentIcon(selectedSignals.wsb?.sentiment || 0)}
                    <Typography variant="h6" sx={{ ml: 1 }}>
                      {((selectedSignals.wsb?.sentiment || 0) * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    언급: {selectedSignals.wsb?.mentions || 0}회
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">
                    Yahoo Finance
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                    {getSentimentIcon(selectedSignals.yahoo?.technical_sentiment || 0)}
                    <Typography variant="h6" sx={{ ml: 1 }}>
                      {((selectedSignals.yahoo?.technical_sentiment || 0) * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    RSI: {selectedSignals.yahoo?.rsi?.toFixed(1) || 'N/A'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">
                    TipRanks
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                    {getSentimentIcon(selectedSignals.tipranks?.consensus || 0)}
                    <Typography variant="h6" sx={{ ml: 1 }}>
                      {((selectedSignals.tipranks?.consensus || 0) * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    애널리스트 평가
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
      </Paper>

      {/* Trending Tickers */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          WallStreetBets 트렌딩 (실시간)
        </Typography>
        <Grid container spacing={2}>
          {trending.map((ticker) => (
            <Grid item xs={12} sm={6} md={4} key={ticker.ticker}>
              <Card
                variant="outlined"
                sx={{ cursor: 'pointer' }}
                onClick={() => {
                  setSearchTicker(ticker.ticker)
                  handleAnalyzeTicker()
                }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="h6">{ticker.ticker}</Typography>
                    <Chip
                      label={`${ticker.mentions}회`}
                      size="small"
                      color="primary"
                    />
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    {getSentimentIcon(ticker.sentiment_score)}
                    <Typography variant="body2" sx={{ ml: 1 }}>
                      심리: {(ticker.sentiment_score * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}
                  >
                    {ticker.top_post?.substring(0, 60)}...
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Paper>
    </Box>
  )
}
