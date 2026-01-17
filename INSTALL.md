# 설치 및 시작 가이드

## 📋 필수 요구사항

### 소프트웨어
- **Python 3.14+** (3.10 이상 권장)
- **Node.js 18+** (npm 포함)
- **SQLite 3** (macOS에 기본 포함)

### API 키 및 계정
1. **한국투자증권 계좌**
   - 해외주식 거래가 가능한 계좌
   - API 사용 신청 및 승인 필요
   - https://securities.koreainvestment.com/

2. **Google Gemini API 키**
   - https://aistudio.google.com/app/apikey
   - 무료 티어 사용 가능

3. **Reddit API (선택사항)**
   - https://www.reddit.com/prefs/apps
   - WallStreetBets 스크래핑 시 안정성 향상

## 🚀 설치 단계

### 1. 저장소 클론

```bash
cd /Users/mackbook/Documents
git clone <repository-url> us-stock-trading-bot
cd us-stock-trading-bot
```

### 2. 자동 설치 스크립트 실행

```bash
bash scripts/setup.sh
```

이 스크립트는 자동으로:
- Python 가상환경 생성 및 의존성 설치
- 데이터베이스 초기화
- 프론트엔드 의존성 설치
- .env 파일 생성

### 3. API 키 설정

`.env` 파일을 편집하여 API 키를 입력:

```bash
nano .env
```

또는 나중에 WebUI에서 설정 가능합니다.

필수 항목:
```env
GEMINI_API_KEY=your_gemini_api_key_here
KOREA_INVESTMENT_API_KEY=your_api_key_here
KOREA_INVESTMENT_API_SECRET=your_api_secret_here
KOREA_INVESTMENT_ACCOUNT_NUMBER=your_account_number_here
```

선택 항목:
```env
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
```

### 4. 시스템 시작

**개발 모드 (수동 중지 필요):**
```bash
bash scripts/run_dev.sh
```

**프로덕션 모드 (24시간 자동 구동):**
```bash
bash scripts/run_prod.sh
```

### 5. 웹 UI 접속

브라우저에서 다음 주소로 접속:
- **프론트엔드**: http://localhost:5173
- **API 문서**: http://localhost:8000/docs
- **백엔드 Health**: http://localhost:8000/health

## ⚙️ 초기 설정

### 1. WebUI에서 API 키 확인
1. 설정 페이지 접속 (http://localhost:5173/settings)
2. 모든 API 키가 올바르게 저장되었는지 확인
3. 필요시 WebUI에서 직접 수정/추가 가능

### 2. 자동 거래 스케줄러 시작
1. 대시보드 접속 (http://localhost:5173)
2. "자동 거래 스케줄러" 섹션에서 **시작** 버튼 클릭
3. 상태가 "실행 중"으로 변경되면 성공

### 3. 수동 거래 테스트 (권장)
실제 자동 거래 전에 수동으로 AI 분석을 테스트:

```bash
# API를 통한 수동 세션 실행
curl -X POST http://localhost:8000/api/scheduler/execute/PRE_MARKET
```

또는 WebUI에서:
- 시장 신호 페이지에서 종목 분석
- 거래 페이지에서 AI 결정 로그 확인

## 🔍 동작 확인

### 로그 확인
```bash
# 전체 로그
tail -f logs/app.log

# 거래 로그만
tail -f logs/trading.log

# AI 결정 로그
tail -f logs/gemini.log

# 에러만
tail -f logs/errors.log
```

### 데이터베이스 확인
```bash
sqlite3 data/trading_bot.db

# 포트폴리오 스냅샷 확인
SELECT * FROM portfolio_snapshots ORDER BY snapshot_date DESC LIMIT 5;

# 거래 내역 확인
SELECT * FROM trades ORDER BY executed_at DESC LIMIT 10;

# AI 결정 확인
SELECT id, decision_type, confidence_score, created_at FROM llm_decisions ORDER BY created_at DESC LIMIT 10;

.quit
```

## 📅 거래 스케줄

자동 거래는 다음 시간에 실행됩니다 (한국 시간):

### 동절기 (11월~3월)
- **23:20** - PRE_MARKET: 장 시작 10분 전 분석 및 매수
- **01:30** - MID_SESSION: 장 시작 2시간 후 점검
- **05:50** - PRE_CLOSE: 장 마감 10분 전 청산 판단

### 서머타임 (3월~11월)
- **22:20** - PRE_MARKET
- **00:30** - MID_SESSION
- **04:50** - PRE_CLOSE

### Stop-Loss 체크
- 시장 시간 중 **30분마다** 자동 체크
- -30% 손실 시 자동 청산

### 일일 스냅샷
- **06:05** - 매일 포트폴리오 스냅샷 저장

## ⚠️ 주의사항

### 첫 실행 전 체크리스트
- [ ] 한국투자증권 API 키 발급 완료
- [ ] Gemini API 키 발급 완료
- [ ] .env 파일에 모든 필수 키 입력
- [ ] 계좌에 최소 100만원 이상 입금 (권장)
- [ ] API 출금 권한 비활성화 (보안)
- [ ] WebUI에서 API 키 저장 확인
- [ ] 로그 파일 경로 확인 (logs/ 디렉토리)

### 리스크 관리
시스템은 다음 리스크 제한을 자동으로 적용합니다:
- **최대 포지션**: 총 자산의 40%
- **일일 손실 한도**: -20% (서킷브레이커)
- **Stop-Loss**: 매수가 대비 -30%

이 값들은 `.env`에서 수정 가능하지만 **권장하지 않습니다**.

### 백업
```bash
# 수동 백업
bash scripts/backup_db.sh

# 자동 백업 설정 (crontab)
crontab -e
# 추가: 0 6 * * * /Users/mackbook/Documents/us-stock-trading-bot/scripts/backup_db.sh
```

## 🛠 문제 해결

### 백엔드가 시작되지 않음
```bash
# 의존성 재설치
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 프론트엔드가 시작되지 않음
```bash
# 의존성 재설치
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### API 연결 오류
1. `.env` 파일의 API 키 확인
2. 한국투자증권 API 사용 승인 상태 확인
3. Gemini API 할당량 확인

### 거래가 실행되지 않음
1. 스케줄러가 실행 중인지 확인
2. 로그 파일에서 에러 확인
3. 서킷브레이커 발동 여부 확인 (일일 -20% 손실)
4. API 키 유효성 확인

### macOS가 자꾸 슬립 모드로 진입
`run_prod.sh`를 사용하면 `caffeinate` 명령어로 자동 방지됩니다.

## 📞 지원

- **GitHub Issues**: 버그 리포트 및 기능 요청
- **로그 분석**: logs/ 디렉토리의 로그 파일 확인
- **API 문서**: http://localhost:8000/docs

## 🔐 보안 권장사항

1. **출금 권한 비활성화**: 한국투자증권 API 설정에서 출금 권한 제거
2. **최소 권한**: API 키에 거래 권한만 부여
3. **백업**: 정기적으로 데이터베이스 백업
4. **모니터링**: 일일 1회 이상 WebUI에서 상태 확인
5. **테스트**: 소액으로 먼저 테스트 후 본격 운영

---

설치 완료! 🎉

이제 http://localhost:5173 에 접속하여 시스템을 사용하세요.
