import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
} from '@mui/material'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { portfolioApi } from '../services/api'
import { format } from 'date-fns'

export default function Portfolio() {
  const [history, setHistory] = useState<any[]>([])

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    try {
      const res = await portfolioApi.getHistory(30)
      setHistory(res.data.snapshots || [])
    } catch (error) {
      console.error('Failed to load portfolio history:', error)
    }
  }

  const chartData = history.map((snapshot) => ({
    date: format(new Date(snapshot.date), 'MM/dd'),
    총자산: snapshot.total_value,
    현금: snapshot.cash_balance,
    보유주식: snapshot.holdings_value,
  }))

  const formatCurrency = (value: number) => {
    return `₩${new Intl.NumberFormat('ko-KR').format(Math.round(value))}`
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        포트폴리오
      </Typography>

      {/* Performance Chart */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          자산 추이 (최근 30일)
        </Typography>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Legend />
            <Line type="monotone" dataKey="총자산" stroke="#2196f3" strokeWidth={2} />
            <Line type="monotone" dataKey="현금" stroke="#4caf50" />
            <Line type="monotone" dataKey="보유주식" stroke="#ff9800" />
          </LineChart>
        </ResponsiveContainer>
      </Paper>

      {/* Historical Statistics */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          통계
        </Typography>
        <Grid container spacing={2}>
          {history.slice(0, 10).map((snapshot, idx) => (
            <Grid item xs={12} md={6} key={idx}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">
                    {format(new Date(snapshot.date), 'yyyy-MM-dd')}
                  </Typography>
                  <Typography variant="h6">
                    {formatCurrency(snapshot.total_value)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    일일 손익: {snapshot.daily_pnl_pct.toFixed(2)}% ({formatCurrency(snapshot.daily_pnl)})
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    누적 손익: {snapshot.total_pnl_pct.toFixed(2)}% ({formatCurrency(snapshot.total_pnl)})
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
