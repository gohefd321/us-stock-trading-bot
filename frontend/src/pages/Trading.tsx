import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import { tradingApi } from '../services/api'
import type { Trade, LLMDecision } from '../types'
import { format } from 'date-fns'

export default function Trading() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [decisions, setDecisions] = useState<LLMDecision[]>([])
  const [selectedDecision, setSelectedDecision] = useState<LLMDecision | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [tradesRes, decisionsRes] = await Promise.all([
        tradingApi.getHistory(7),
        tradingApi.getDecisions(20),
      ])
      setTrades(tradesRes.data.trades || [])
      setDecisions(decisionsRes.data.decisions || [])
    } catch (error) {
      console.error('Failed to load trading data:', error)
    }
  }

  const handleDecisionClick = async (id: number) => {
    try {
      const res = await tradingApi.getDecisionDetail(id)
      setSelectedDecision(res.data.decision)
      setDialogOpen(true)
    } catch (error) {
      console.error('Failed to load decision detail:', error)
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        거래 관리
      </Typography>

      {/* AI Decisions */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          AI 거래 결정 (최근 20개)
        </Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>시간</TableCell>
                <TableCell>결정 타입</TableCell>
                <TableCell>신뢰도</TableCell>
                <TableCell>요약</TableCell>
                <TableCell>액션</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {decisions.map((decision) => (
                <TableRow key={decision.id} hover>
                  <TableCell>
                    {decision.created_at
                      ? format(new Date(decision.created_at), 'MM/dd HH:mm')
                      : '-'}
                  </TableCell>
                  <TableCell>
                    <Chip label={decision.decision_type} size="small" />
                  </TableCell>
                  <TableCell>
                    {(decision.confidence_score * 100).toFixed(0)}%
                  </TableCell>
                  <TableCell>
                    {decision.reasoning.substring(0, 100)}...
                  </TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      onClick={() => handleDecisionClick(decision.id)}
                    >
                      상세
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Trade History */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          거래 내역 (최근 7일)
        </Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>시간</TableCell>
                <TableCell>티커</TableCell>
                <TableCell>액션</TableCell>
                <TableCell>수량</TableCell>
                <TableCell>가격</TableCell>
                <TableCell>총액</TableCell>
                <TableCell>상태</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {trades.map((trade) => (
                <TableRow key={trade.trade_id}>
                  <TableCell>
                    {trade.executed_at
                      ? format(new Date(trade.executed_at), 'MM/dd HH:mm')
                      : '-'}
                  </TableCell>
                  <TableCell>
                    <strong>{trade.ticker}</strong>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={trade.action}
                      color={trade.action === 'BUY' ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{trade.quantity}</TableCell>
                  <TableCell>${trade.price.toFixed(2)}</TableCell>
                  <TableCell>
                    ₩{new Intl.NumberFormat('ko-KR').format(trade.total_value)}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={trade.status}
                      color={trade.status === 'FILLED' ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Decision Detail Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>AI 결정 상세</DialogTitle>
        <DialogContent>
          {selectedDecision && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                결정 타입: {selectedDecision.decision_type}
              </Typography>
              <Typography variant="subtitle2" gutterBottom>
                신뢰도: {(selectedDecision.confidence_score * 100).toFixed(0)}%
              </Typography>
              <Typography variant="subtitle2" gutterBottom>
                시간: {selectedDecision.created_at}
              </Typography>
              <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                AI 추론:
              </Typography>
              <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {selectedDecision.reasoning}
                </Typography>
              </Paper>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>닫기</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
