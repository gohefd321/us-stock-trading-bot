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
  CircularProgress,
  Snackbar,
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import SaveIcon from '@mui/icons-material/Save'
import { settingsApi } from '../services/api'

export default function Settings() {
  const [apiKeys, setApiKeys] = useState<any[]>([])
  const [riskParams, setRiskParams] = useState<any>(null)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

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
      setLoading(true)
      setError('')

      const [keysRes, riskRes] = await Promise.all([
        settingsApi.getApiKeys().catch(() => ({ data: { api_keys: [] } })),
        settingsApi.getRiskParams().catch(() => ({ data: { risk_params: {} } })),
      ])

      setApiKeys(keysRes.data.api_keys || [])
      setRiskParams(riskRes.data.risk_params || {})
    } catch (err: any) {
      console.error('Failed to load settings:', err)
      setError(err?.response?.data?.detail || '설정을 불러오는데 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveApiKey = async (keyName: string, keyValue: string) => {
    if (!keyValue || !keyValue.trim()) {
      setError('API 키 값을 입력해주세요')
      return
    }

    try {
      setSaving(true)
      setError('')

      await settingsApi.saveApiKey(keyName, keyValue)
      setSuccess(`${keyName} 저장 완료`)

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

      // Reload settings to show the new key
      await loadSettings()

    } catch (err: any) {
      console.error('Failed to save API key:', err)
      setError(err?.response?.data?.detail || 'API 키 저장 실패')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteApiKey = async (keyName: string) => {
    if (!confirm(`${keyName}를 삭제하시겠습니까?`)) {
      return
    }

    try {
      setError('')
      await settingsApi.deleteApiKey(keyName)
      setSuccess(`${keyName} 삭제 완료`)
      await loadSettings()
    } catch (err: any) {
      console.error('Failed to delete API key:', err)
      setError(err?.response?.data?.detail || 'API 키 삭제 실패')
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      {/* Success Snackbar */}
      <Snackbar
        open={!!success}
        autoHideDuration={3000}
        onClose={() => setSuccess('')}
        message={success}
      />

      <Typography variant="h4" gutterBottom>
        설정
      </Typography>

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
        <Alert severity="info" sx={{ mt: 2 }}>
          리스크 파라미터는 .env 파일 또는 환경 변수에서 설정할 수 있습니다.
        </Alert>
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
              disabled={saving}
            />
            <Button
              variant="contained"
              startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
              onClick={() => handleSaveApiKey('GEMINI_API_KEY', geminiKey)}
              disabled={!geminiKey || saving}
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
                  disabled={saving}
                />
                <Button
                  variant="contained"
                  startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
                  onClick={() => handleSaveApiKey('KOREA_INVESTMENT_API_KEY', koreaInvestKey)}
                  disabled={!koreaInvestKey || saving}
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
                  disabled={saving}
                />
                <Button
                  variant="contained"
                  startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
                  onClick={() =>
                    handleSaveApiKey('KOREA_INVESTMENT_API_SECRET', koreaInvestSecret)
                  }
                  disabled={!koreaInvestSecret || saving}
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
                  disabled={saving}
                  placeholder="12345678-01"
                />
                <Button
                  variant="contained"
                  startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
                  onClick={() =>
                    handleSaveApiKey('KOREA_INVESTMENT_ACCOUNT_NUMBER', koreaInvestAccount)
                  }
                  disabled={!koreaInvestAccount || saving}
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
                  disabled={saving}
                />
                <Button
                  variant="contained"
                  startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
                  onClick={() => handleSaveApiKey('REDDIT_CLIENT_ID', redditClientId)}
                  disabled={!redditClientId || saving}
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
                  disabled={saving}
                />
                <Button
                  variant="contained"
                  startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
                  onClick={() => handleSaveApiKey('REDDIT_CLIENT_SECRET', redditClientSecret)}
                  disabled={!redditClientSecret || saving}
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
        {apiKeys.length === 0 ? (
          <Typography color="text.secondary">저장된 API 키가 없습니다.</Typography>
        ) : (
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
        )}
      </Paper>
    </Box>
  )
}
