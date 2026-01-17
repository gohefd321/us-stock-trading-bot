import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Grid,
  Alert,
  Divider,
  List,
  ListItem,
  ListItemText,
  IconButton,
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import SaveIcon from '@mui/icons-material/Save'
import { settingsApi } from '../services/api'

export default function Settings() {
  const [apiKeys, setApiKeys] = useState<any[]>([])
  const [riskParams, setRiskParams] = useState<any>(null)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  // Form state
  const [geminiKey, setGeminiKey] = useState('')
  const [koreaInvestKey, setKoreaInvestKey] = useState('')
  const [koreaInvestSecret, setKoreaInvestSecret] = useState('')
  const [koreaInvestAccount, setKoreaInvestAccount] = useState('')
  const [redditClientId, setRedditClientId] = useState('')
  const [redditClientSecret, setRedditClientSecret] = useState('')

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const [keysRes, riskRes] = await Promise.all([
        settingsApi.getApiKeys(),
        settingsApi.getRiskParams(),
      ])
      setApiKeys(keysRes.data.api_keys || [])
      setRiskParams(riskRes.data.risk_params || {})
    } catch (err) {
      setError('설정을 불러오는데 실패했습니다.')
    }
  }

  const handleSaveApiKey = async (keyName: string, keyValue: string) => {
    if (!keyValue) return

    try {
      await settingsApi.saveApiKey(keyName, keyValue)
      setSuccess(`${keyName} 저장됨`)
      loadSettings()

      // Clear the input
      switch (keyName) {
        case 'GEMINI_API_KEY':
          setGeminiKey('')
          break
        case 'KOREA_INVESTMENT_API_KEY':
          setKoreaInvestKey('')
          break
        case 'KOREA_INVESTMENT_API_SECRET':
          setKoreaInvestSecret('')
          break
        case 'KOREA_INVESTMENT_ACCOUNT_NUMBER':
          setKoreaInvestAccount('')
          break
        case 'REDDIT_CLIENT_ID':
          setRedditClientId('')
          break
        case 'REDDIT_CLIENT_SECRET':
          setRedditClientSecret('')
          break
      }

      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError('API 키 저장 실패')
    }
  }

  const handleDeleteApiKey = async (keyName: string) => {
    try {
      await settingsApi.deleteApiKey(keyName)
      setSuccess(`${keyName} 삭제됨`)
      loadSettings()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError('API 키 삭제 실패')
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        설정
      </Typography>

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* Risk Parameters */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          리스크 관리 파라미터
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              초기 자본금
            </Typography>
            <Typography variant="h6">
              ₩{new Intl.NumberFormat('ko-KR').format(riskParams?.initial_capital_krw || 0)}
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              최대 포지션 크기
            </Typography>
            <Typography variant="h6">{riskParams?.max_position_size_pct || 0}%</Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              일일 손실 한도 (서킷브레이커)
            </Typography>
            <Typography variant="h6">{riskParams?.daily_loss_limit_pct || 0}%</Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              Stop-Loss
            </Typography>
            <Typography variant="h6">{riskParams?.stop_loss_pct || 0}%</Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* API Keys Configuration */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          API 키 설정
        </Typography>

        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Google Gemini API
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              fullWidth
              label="Gemini API Key"
              type="password"
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              placeholder="AIza..."
              size="small"
            />
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={() => handleSaveApiKey('GEMINI_API_KEY', geminiKey)}
              disabled={!geminiKey}
            >
              저장
            </Button>
          </Box>
          <Typography variant="caption" color="text.secondary">
            https://aistudio.google.com/app/apikey 에서 발급
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            한국투자증권 API
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  label="API Key"
                  type="password"
                  value={koreaInvestKey}
                  onChange={(e) => setKoreaInvestKey(e.target.value)}
                  size="small"
                />
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={() => handleSaveApiKey('KOREA_INVESTMENT_API_KEY', koreaInvestKey)}
                  disabled={!koreaInvestKey}
                >
                  저장
                </Button>
              </Box>
            </Grid>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  label="API Secret"
                  type="password"
                  value={koreaInvestSecret}
                  onChange={(e) => setKoreaInvestSecret(e.target.value)}
                  size="small"
                />
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={() =>
                    handleSaveApiKey('KOREA_INVESTMENT_API_SECRET', koreaInvestSecret)
                  }
                  disabled={!koreaInvestSecret}
                >
                  저장
                </Button>
              </Box>
            </Grid>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  label="계좌번호"
                  value={koreaInvestAccount}
                  onChange={(e) => setKoreaInvestAccount(e.target.value)}
                  size="small"
                />
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={() =>
                    handleSaveApiKey('KOREA_INVESTMENT_ACCOUNT_NUMBER', koreaInvestAccount)
                  }
                  disabled={!koreaInvestAccount}
                >
                  저장
                </Button>
              </Box>
            </Grid>
          </Grid>
        </Box>

        <Divider sx={{ my: 2 }} />

        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Reddit API (선택사항)
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  label="Client ID"
                  type="password"
                  value={redditClientId}
                  onChange={(e) => setRedditClientId(e.target.value)}
                  size="small"
                />
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={() => handleSaveApiKey('REDDIT_CLIENT_ID', redditClientId)}
                  disabled={!redditClientId}
                >
                  저장
                </Button>
              </Box>
            </Grid>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  label="Client Secret"
                  type="password"
                  value={redditClientSecret}
                  onChange={(e) => setRedditClientSecret(e.target.value)}
                  size="small"
                />
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={() => handleSaveApiKey('REDDIT_CLIENT_SECRET', redditClientSecret)}
                  disabled={!redditClientSecret}
                >
                  저장
                </Button>
              </Box>
            </Grid>
          </Grid>
          <Typography variant="caption" color="text.secondary">
            Reddit API 없이도 WallStreetBets 스크래핑은 작동합니다
          </Typography>
        </Box>
      </Paper>

      {/* Saved API Keys */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          저장된 API 키
        </Typography>
        <List>
          {apiKeys.map((key) => (
            <ListItem
              key={key.id}
              secondaryAction={
                <IconButton
                  edge="end"
                  aria-label="delete"
                  onClick={() => handleDeleteApiKey(key.key_name)}
                >
                  <DeleteIcon />
                </IconButton>
              }
            >
              <ListItemText
                primary={key.key_name}
                secondary={`${key.value} (${key.is_active ? '활성' : '비활성'})`}
              />
            </ListItem>
          ))}
        </List>
      </Paper>
    </Box>
  )
}
