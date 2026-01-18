# Cloudflare Tunnel 설정 가이드

이 가이드는 Cloudflare Tunnel을 사용하여 하나의 도메인으로 프론트엔드와 백엔드를 모두 서비스하는 방법을 설명합니다.

## 옵션 1: 같은 도메인 사용 (권장)

프론트엔드와 백엔드를 같은 도메인에서 서비스하면 CORS 문제를 피할 수 있습니다.

### Cloudflare Tunnel 설정

`config.yml` 파일 예시:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /path/to/credentials.json

ingress:
  # API 요청은 백엔드로 라우팅
  - hostname: stocking.daechanserver.com
    path: /api/*
    service: http://localhost:8000

  # Health check도 백엔드로
  - hostname: stocking.daechanserver.com
    path: /health
    service: http://localhost:8000

  # API 문서도 백엔드로
  - hostname: stocking.daechanserver.com
    path: /docs
    service: http://localhost:8000

  - hostname: stocking.daechanserver.com
    path: /openapi.json
    service: http://localhost:8000

  # 나머지 모든 요청은 프론트엔드로
  - hostname: stocking.daechanserver.com
    service: http://localhost:5173

  # Catch-all rule
  - service: http_status:404
```

### 환경 변수 설정

**백엔드 (`.env`):**
```bash
# CORS에 도메인 추가
CORS_ORIGINS=https://stocking.daechanserver.com,http://localhost:5173

# 기타 설정...
```

**프론트엔드 (`frontend/.env`):**
```bash
# 빈 값으로 설정하면 상대 URL 사용 (같은 도메인)
VITE_API_URL=

# 개발 모드 프록시 타겟
VITE_BACKEND_TARGET=http://localhost:8000
```

### 서버 시작

```bash
# 프로젝트 루트에서
./scripts/run_dev.sh
```

별도 터미널에서 Cloudflare Tunnel 시작:
```bash
cloudflared tunnel run <tunnel-name>
```

### 접속

브라우저에서 `https://stocking.daechanserver.com` 접속

---

## 옵션 2: 서브도메인 사용

프론트엔드와 백엔드를 다른 서브도메인으로 분리할 수도 있습니다.

### Cloudflare Tunnel 설정

`config.yml` 파일 예시:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /path/to/credentials.json

ingress:
  # 백엔드: api.stocking.daechanserver.com
  - hostname: api.stocking.daechanserver.com
    service: http://localhost:8000

  # 프론트엔드: stocking.daechanserver.com
  - hostname: stocking.daechanserver.com
    service: http://localhost:5173

  # Catch-all rule
  - service: http_status:404
```

### 환경 변수 설정

**백엔드 (`.env`):**
```bash
# CORS에 프론트엔드 도메인 추가
CORS_ORIGINS=https://stocking.daechanserver.com,http://localhost:5173

# 기타 설정...
```

**프론트엔드 (`frontend/.env`):**
```bash
# 백엔드 API URL 지정
VITE_API_URL=https://api.stocking.daechanserver.com

# 개발 모드 프록시 타겟
VITE_BACKEND_TARGET=http://localhost:8000
```

---

## 로컬 개발 모드

로컬에서만 개발할 때는 환경 변수를 다음과 같이 설정:

**프론트엔드 (`frontend/.env`):**
```bash
# 로컬 백엔드 사용
VITE_API_URL=http://localhost:8000
VITE_BACKEND_TARGET=http://localhost:8000
```

**백엔드 (`.env`):**
```bash
# 로컬 CORS만 허용
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 프로덕션 배포

프로덕션 환경에서는:

1. **옵션 1 (같은 도메인)** 사용 권장
2. HTTPS 사용 (Cloudflare가 자동으로 처리)
3. 환경 변수에서 localhost 제거
4. 서비스를 systemd나 PM2로 관리

### systemd 서비스 예시

**백엔드 서비스 (`/etc/systemd/system/trading-bot-backend.service`):**
```ini
[Unit]
Description=US Stock Trading Bot Backend
After=network.target

[Service]
Type=simple
User=sixseven
WorkingDirectory=/home/sixseven/us-stock-trading-bot/backend
ExecStart=/home/sixseven/us-stock-trading-bot/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**프론트엔드 빌드 및 서비스:**
```bash
# 프론트엔드 빌드
cd /home/sixseven/us-stock-trading-bot/frontend
npm run build

# Nginx나 다른 웹서버로 dist/ 폴더 서비스
# 또는 Vite preview 서버 사용
```

---

## 문제 해결

### CORS 오류가 계속 발생하는 경우

1. 백엔드 로그에서 CORS Origins 확인:
   ```bash
   cd /home/sixseven/us-stock-trading-bot
   tail -f logs/app.log
   ```

2. `.env` 파일이 올바르게 로드되는지 확인

3. 서버 재시작:
   ```bash
   # 개발 서버 중지 (Ctrl+C)
   ./scripts/run_dev.sh
   ```

### API 요청이 404 오류를 반환하는 경우

1. Cloudflare Tunnel의 ingress 순서 확인 (더 구체적인 규칙이 위에 있어야 함)
2. 백엔드가 실제로 실행 중인지 확인: `curl http://localhost:8000/health`

### 프론트엔드가 백엔드를 찾지 못하는 경우

1. 브라우저 개발자 도구에서 네트워크 탭 확인
2. API 요청의 URL이 올바른지 확인
3. `frontend/.env` 파일의 `VITE_API_URL` 설정 확인

---

## 보안 주의사항

1. `.env` 파일을 절대 Git에 커밋하지 마세요
2. API 키는 안전하게 보관하세요
3. 프로덕션에서는 `allow_credentials=True`와 함께 구체적인 CORS origins만 허용하세요
4. Cloudflare의 추가 보안 기능 (WAF, Rate Limiting) 활용을 고려하세요
