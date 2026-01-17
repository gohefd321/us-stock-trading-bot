import { useState, useEffect } from 'react'
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  Chip,
  Alert,
} from '@mui/material'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import StopIcon from '@mui/icons-material/Stop'
import { portfolioApi, schedulerApi } from '../services/api'
import type { PortfolioState, SchedulerStatus } from '../types'

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<PortfolioState | null>(null)
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    try {
      const [portfolioRes, schedulerRes] = await Promise.all([
        portfolioApi.getStatus(),
        schedulerApi.getStatus(),
      ])
      setPortfolio(portfolioRes.data)
      setScheduler(schedulerRes.data)
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 10000) // Refresh every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const handleStartScheduler = async () => {
    try {
      await schedulerApi.start()
      await loadData()
    } catch (error) {
      console.error('Failed to start scheduler:', error)
    }
  }

  const handleStopScheduler = async () => {
    try {
      await schedulerApi.stop()
      await loadData()
    } catch (error) {
      console.error('Failed to stop scheduler:', error)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ko-KR').format(Math.round(value))
  }

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  if (loading) {
    return <Typography>로딩 중...</Typography>
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          대시보드
        </Typography>
        <Typography variant="body2" color="text.secondary">
          실시간 포트폴리오 현황 및 AI 트레이딩 상태
        </Typography>
      </Box>

      {/* Scheduler Control */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h6" gutterBottom>
              자동 거래 스케줄러
            </Typography>
            <Chip
              label={scheduler?.is_running ? '실행 중' : '중지됨'}
              color={scheduler?.is_running ? 'success' : 'default'}
              size="small"
            />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              예정된 작업: {scheduler?.job_count || 0}개
            </Typography>
          </Box>
          <Box>
            {scheduler?.is_running ? (
              <Button
                variant="contained"
                color="error"
                startIcon={<StopIcon />}
                onClick={handleStopScheduler}
              >
                중지
              </Button>
            ) : (
              <Button
                variant="contained"
                color="success"
                startIcon={<PlayArrowIcon />}
                onClick={handleStartScheduler}
              >
                시작
              </Button>
            )}
          </Box>
        </Box>
      </Paper>

      {/* Portfolio Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                총 자산
              </Typography>
              <Typography variant="h5">
                ₩{formatCurrency(portfolio?.total_value || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                현금 잔고
              </Typography>
              <Typography variant="h5">
                ₩{formatCurrency(portfolio?.cash_balance || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                일일 손익
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography
                  variant="h5"
                  color={
                    (portfolio?.daily_pnl_pct || 0) >= 0 ? 'success.main' : 'error.main'
                  }
                >
                  {formatPercent(portfolio?.daily_pnl_pct || 0)}
                </Typography>
                {(portfolio?.daily_pnl_pct || 0) >= 0 ? (
                  <TrendingUpIcon color="success" sx={{ ml: 1 }} />
                ) : (
                  <TrendingDownIcon color="error" sx={{ ml: 1 }} />
                )}
              </Box>
              <Typography variant="body2" color="text.secondary">
                ₩{formatCurrency(portfolio?.daily_pnl || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                총 손익
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography
                  variant="h5"
                  color={
                    (portfolio?.total_pnl_pct || 0) >= 0 ? 'success.main' : 'error.main'
                  }
                >
                  {formatPercent(portfolio?.total_pnl_pct || 0)}
                </Typography>
                {(portfolio?.total_pnl_pct || 0) >= 0 ? (
                  <TrendingUpIcon color="success" sx={{ ml: 1 }} />
                ) : (
                  <TrendingDownIcon color="error" sx={{ ml: 1 }} />
                )}
              </Box>
              <Typography variant="body2" color="text.secondary">
                ₩{formatCurrency(portfolio?.total_pnl || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Risk Warnings */}
      {portfolio && portfolio.daily_pnl_pct <= -15 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          일일 손실률이 -15%를 초과했습니다. -20%에 도달하면 서킷브레이커가 발동됩니다.
        </Alert>
      )}

      {/* Current Positions */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          보유 포지션 ({portfolio?.position_count || 0}개)
        </Typography>
        {portfolio?.positions && portfolio.positions.length > 0 ? (
          <Grid container spacing={2}>
            {portfolio.positions.map((position) => (
              <Grid item xs={12} md={6} key={position.ticker}>
                <Card variant="outlined">
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="h6">{position.ticker}</Typography>
                      <Chip
                        label={formatPercent(position.unrealized_pnl_pct)}
                        color={position.unrealized_pnl_pct >= 0 ? 'success' : 'error'}
                        size="small"
                      />
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      수량: {position.quantity}주 | 평단가: ${position.avg_cost.toFixed(2)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      현재가: ${position.current_price.toFixed(2)} | 평가액: ₩
                      {formatCurrency(position.total_value)}
                    </Typography>
                    <Typography
                      variant="body2"
                      color={position.unrealized_pnl >= 0 ? 'success.main' : 'error.main'}
                    >
                      미실현 손익: ₩{formatCurrency(position.unrealized_pnl)}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        ) : (
          <Typography color="text.secondary">보유 중인 포지션이 없습니다.</Typography>
        )}
      </Paper>
    </Box>
  )
}
