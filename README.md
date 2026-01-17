# 미국 주식 자동매매 시스템 (Gemini 3.0 기반)

AI 기반 완전 자동화 미국 주식 트레이딩 봇

## 🎯 프로젝트 개요

WallStreetBets, Yahoo Finance, TipRanks의 신호를 모니터링하고, Google Gemini 3.0 AI가 자동으로 투자 판단을 내려 한국투자증권 API를 통해 미국 주식을 매매하는 완전 자동화 시스템입니다.

### 주요 기능

- ✅ **완전 자동화**: 사람 승인 없이 AI가 자동 거래
- ✅ **3개 거래 세션**: 장 전, 중간, 마감 전 자동 분석 및 거래
- ✅ **실시간 모니터링**: 웹UI에서 AI 판단 과정 실시간 확인
- ✅ **리스크 관리**: 40% 포지션 한도, 20% 손실 서킷브레이커, 30% stop-loss
- ✅ **대화형 챗봇**: AI에게 질문하고 전략 수정 가능

## 🚀 빠른 시작

### 필수 요구사항

- Python 3.14+
- Node.js 18+ (프론트엔드)
- 한국투자증권 계좌 및 API 키
- Google Gemini API 키

### 설치

```bash
# 1. 저장소 클론
git clone <repository-url>
cd us-stock-trading-bot

# 2. 초기 설정 스크립트 실행
bash scripts/setup.sh

# 3. .env 파일 편집 (API 키 입력)
nano .env
```

### 실행

**개발 모드:**
```bash
bash scripts/run_dev.sh
```

**프로덕션 모드 (24시간 구동):**
```bash
bash scripts/run_prod.sh
```

### 접속

- 백엔드 API: http://localhost:8000
- API 문서: http://localhost:8000/docs
- 프론트엔드: http://localhost:5173

## 📁 프로젝트 구조

```
us-stock-trading-bot/
├── backend/           # FastAPI 백엔드
│   ├── app/
│   │   ├── models/    # SQLAlchemy 모델
│   │   ├── services/  # 핵심 서비스
│   │   └── api/       # API 엔드포인트
├── frontend/          # React 프론트엔드
├── database/          # 데이터베이스 스키마
├── data/              # SQLite 데이터베이스 파일
├── logs/              # 로그 파일
└── scripts/           # 실행 스크립트
```

## 🔧 설정

### API 키 설정

`.env` 파일에 다음 키들을 설정하세요:

```env
KOREA_INVESTMENT_API_KEY=your_key
KOREA_INVESTMENT_API_SECRET=your_secret
KOREA_INVESTMENT_ACCOUNT_NUMBER=your_account
GEMINI_API_KEY=your_gemini_key
```

또는 웹UI에서 첫 접속 시 입력할 수 있습니다.

### 리스크 파라미터

- **최대 포지션 크기**: 총 자산의 40%
- **일일 손실 한도**: 총 자산의 20% (서킷브레이커)
- **Stop-loss**: 매수가 대비 -30%

## 📊 거래 스케줄

| 시간 | 동절기 (KST) | 서머타임 (KST) | 작업 |
|------|-------------|---------------|------|
| 장 시작 10분 전 | 23:20 | 22:20 | 초기 분석 및 매수 |
| 장 시작 2시간 후 | 01:30 | 00:30 | 중간 점검 및 조정 |
| 장 마감 10분 전 | 05:50 | 04:50 | 수익 분석 및 청산 |

## 🔍 모니터링

### 로그 파일

```
logs/
├── app.log        # 전체 로그
├── trading.log    # 거래 실행 로그
├── errors.log     # 에러만
├── scheduler.log  # 스케줄러 작업
└── gemini.log     # AI 판단 로그
```

### 데이터베이스 백업

```bash
# 수동 백업
bash scripts/backup_db.sh

# 자동 백업 (crontab)
0 6 * * * /path/to/scripts/backup_db.sh
```

## 📡 API 엔드포인트

### 스케줄러 제어
- `GET /api/scheduler/status` - 스케줄러 상태 확인
- `POST /api/scheduler/start` - 자동 거래 시작
- `POST /api/scheduler/stop` - 자동 거래 중지
- `POST /api/scheduler/execute/{decision_type}` - 수동 거래 세션 실행

### 거래 관리
- `POST /api/trading/analyze` - 특정 종목 분석 요청
- `GET /api/trading/history?days=7` - 거래 내역 조회
- `GET /api/trading/decisions` - AI 결정 로그 조회
- `GET /api/trading/decisions/{id}` - AI 결정 상세 조회

### 포트폴리오
- `GET /api/portfolio/status` - 현재 포트폴리오 상태
- `GET /api/portfolio/history?days=30` - 포트폴리오 히스토리
- `GET /api/portfolio/position/{ticker}` - 특정 포지션 조회
- `POST /api/portfolio/snapshot` - 스냅샷 수동 저장

### 시장 신호
- `GET /api/signals/trending?limit=20` - WallStreetBets 트렌딩 종목
- `GET /api/signals/ticker/{ticker}` - 특정 종목 신호 조회
- `GET /api/signals/recent?hours_back=24` - 최근 신호 조회

### 설정
- `GET /api/settings/api-keys` - API 키 목록 (마스킹)
- `POST /api/settings/api-keys` - API 키 저장/수정
- `DELETE /api/settings/api-keys/{name}` - API 키 삭제
- `GET /api/settings/preferences` - 사용자 설정 조회
- `POST /api/settings/preferences` - 사용자 설정 저장
- `GET /api/settings/risk-params` - 리스크 파라미터 조회

API 문서: http://localhost:8000/docs

## 🛠 개발

### 가상환경 활성화

```bash
cd backend
source venv/bin/activate
```

### 의존성 설치

```bash
pip install -r requirements.txt
```

### 데이터베이스 초기화

```bash
sqlite3 data/trading_bot.db < database/schema.sql
```

### 테스트 실행

```bash
# Gemini AI 통합 테스트
python backend/tests/test_gemini_integration.py

# 전체 테스트
pytest backend/tests/
```

## 🔒 보안

- API 키는 Fernet 암호화로 저장
- `.env` 파일은 git에서 제외
- 한국투자증권 API는 출금 권한 비활성화 권장

## ⚠️ 면책 조항

이 프로젝트는 **실험 및 교육 목적**입니다. 실제 거래에서 발생하는 손실에 대해 개발자는 책임지지 않습니다. 자신의 책임 하에 사용하세요.

## 📝 라이선스

MIT License

## 🤝 기여

이슈와 풀 리퀘스트를 환영합니다!
