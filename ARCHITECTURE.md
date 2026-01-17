# 시스템 아키텍처

## 🏗 전체 구조

```
┌─────────────────────────────────────────────────────────────┐
│                         사용자 (WebUI)                       │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/WebSocket
┌───────────────────────▼─────────────────────────────────────┐
│                  React 프론트엔드 (Vite)                     │
│  ┌──────────┬──────────┬──────────┬──────────┬───────────┐ │
│  │Dashboard │ Trading  │Portfolio │ Signals  │ Settings  │ │
│  └──────────┴──────────┴──────────┴──────────┴───────────┘ │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API
┌───────────────────────▼─────────────────────────────────────┐
│                  FastAPI 백엔드 (Python)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API Routes (5개)                        │  │
│  │  /scheduler │ /trading │ /portfolio │ /signals │     │  │
│  │             /settings                                 │  │
│  └────────┬─────────────────────────────────────────────┘  │
│           │                                                  │
│  ┌────────▼────────────────────────────────────────────┐   │
│  │           서비스 레이어 (10개 서비스)               │   │
│  │  • TradingEngine      • GeminiService               │   │
│  │  • SchedulerService   • RiskManager                 │   │
│  │  • PortfolioManager   • SignalAggregator            │   │
│  │  • BrokerService      • WSBScraper                  │   │
│  │  • YahooFinance       • TipRanks                    │   │
│  └────────┬─────────────────────────────────────────────┘  │
│           │                                                  │
│  ┌────────▼────────────────────────────────────────────┐   │
│  │         Gemini Function Calling (8개 함수)          │   │
│  │  check_balance │ get_price │ execute_trade │ ...    │   │
│  └──────────────────────────────────────────────────────┘  │
└───┬──────────────────────┬────────────────┬────────────────┘
    │                      │                │
    ▼                      ▼                ▼
┌───────┐          ┌───────────┐    ┌──────────────┐
│SQLite │          │외부 API들  │    │Google Gemini │
│  DB   │          │• 한투증권  │    │   2.0 Flash  │
│       │          │• Reddit   │    │              │
└───────┘          │• Yahoo    │    └──────────────┘
                   │• TipRanks │
                   └───────────┘
```

## 📦 백엔드 아키텍처

### 레이어 구조

```
┌─────────────────────────────────────────┐
│         API Routes (Endpoints)          │  ← HTTP 요청 처리
├─────────────────────────────────────────┤
│         Services (비즈니스 로직)         │  ← 핵심 로직
├─────────────────────────────────────────┤
│         Models (데이터베이스)            │  ← ORM 모델
├─────────────────────────────────────────┤
│         Database (SQLite)               │  ← 데이터 저장
└─────────────────────────────────────────┘
```

### 핵심 서비스

#### 1. TradingEngine (거래 엔진)
**책임**: 전체 거래 워크플로우 총괄
```python
execute_trading_session(decision_type):
    1. 리스크 체크 (can_trade_now)
    2. 포트폴리오 상태 조회
    3. 시장 신호 수집
    4. Gemini AI 결정 요청
    5. 거래 실행
    6. 결과 로깅
    7. 스냅샷 저장
```

#### 2. GeminiService (AI 엔진)
**책임**: Gemini AI와 통신 및 Function Calling
```python
make_trading_decision(decision_type, portfolio, signals):
    1. 프롬프트 생성 (decision_type별)
    2. Gemini API 호출
    3. Function Calling 반복 처리 (최대 10회)
    4. 함수 실행 결과를 Gemini에 전달
    5. 최종 결정 파싱
```

**프롬프트 전략**:
- PRE_MARKET: 매수 기회 분석 (트렌딩 종목 중심)
- MID_SESSION: 기존 포지션 점검 및 조정
- PRE_CLOSE: 수익 실현 및 청산 판단

#### 3. SchedulerService (스케줄러)
**책임**: 자동 거래 세션 스케줄링
```python
start():
    - PRE_MARKET 세션 (23:20/22:20 KST)
    - MID_SESSION 세션 (01:30/00:30 KST)
    - PRE_CLOSE 세션 (05:50/04:50 KST)
    - Stop-loss 체크 (30분마다)
    - 일일 스냅샷 (06:05 KST)
```

#### 4. RiskManager (리스크 관리)
**책임**: 모든 거래 전 리스크 검증
```python
check_position_size_limit(ticker, value):
    → 최대 40% 제한 검증

check_daily_loss_limit():
    → -20% 서킷브레이커 검증

check_stop_loss(ticker, price):
    → -30% stop-loss 검증

calculate_position_size(ticker, confidence, price):
    → 신뢰도 기반 최적 포지션 계산
```

#### 5. SignalAggregator (신호 집계)
**책임**: 3개 소스의 시장 신호 통합
```python
aggregate_signals_for_ticker(ticker):
    # 병렬로 신호 수집
    wsb_signal = wsb_scraper.get_ticker_sentiment(ticker)
    yahoo_signal = yahoo_service.get_ticker_data(ticker)
    tipranks_signal = tipranks_service.get_ticker_analysis(ticker)

    # 가중 평균 계산
    composite_sentiment = (
        wsb_signal * 0.3 +
        yahoo_signal * 0.4 +
        tipranks_signal * 0.3
    )

    # 추천 생성
    recommendation = generate_recommendation(composite_sentiment, strength)
```

#### 6. PortfolioManager (포트폴리오 관리)
**책임**: 포트폴리오 상태 추적
```python
get_current_state():
    - 현금 잔고
    - 보유 포지션
    - 일일 P/L
    - 총 P/L
    - 포지션별 노출도

save_snapshot():
    - 일일 포트폴리오 스냅샷 저장
```

#### 7. BrokerService (브로커 연동)
**책임**: 한국투자증권 API 래퍼
```python
get_balance() → 계좌 잔고
get_us_stock_price(ticker) → 실시간 가격
place_us_order(ticker, action, quantity) → 주문 실행
get_us_positions() → 보유 포지션
```

### Gemini Function Calling

AI가 직접 호출 가능한 8개 함수:

| 함수명 | 설명 | 리턴 |
|--------|------|------|
| `check_balance()` | 계좌 잔고 조회 | {cash, total_value} |
| `get_current_price(ticker)` | 실시간 주가 | {ticker, price} |
| `get_portfolio_status()` | 포트폴리오 전체 상태 | {positions, pnl, exposure} |
| `execute_trade(...)` | 실제 매매 실행 | {success, order_id} |
| `analyze_signals(ticker)` | 시장 신호 분석 | {wsb, yahoo, tipranks, recommendation} |
| `calculate_position_size(...)` | 포지션 크기 계산 | {quantity, trade_value, reasoning} |
| `check_stop_loss_triggers()` | Stop-loss 체크 | {triggered_positions[]} |
| `get_trading_history(days)` | 거래 내역 조회 | {trades[], win_rate} |

### 데이터베이스 스키마

```sql
-- 6개 테이블

api_keys (id, key_name, encrypted_value, is_active)
  ↓ 암호화된 API 키 저장

trades (id, ticker, action, quantity, price, status, llm_decision_id)
  ↓ 모든 거래 기록

llm_decisions (id, decision_type, prompt, response, reasoning,
              confidence_score, function_calls, signals_used,
              portfolio_state)
  ↓ AI 결정 로그 (감사 추적)

signals (id, ticker, source, signal_type, sentiment_score,
        confidence, metadata)
  ↓ 시장 신호 히스토리

portfolio_snapshots (id, snapshot_date, cash_balance,
                    total_holdings_value, total_value,
                    daily_pnl, total_pnl, holdings_json)
  ↓ 일일 포트폴리오 스냅샷

user_preferences (id, key, value)
  ↓ 사용자 설정
```

## 🎨 프론트엔드 아키텍처

### 기술 스택
- **React 18**: UI 라이브러리
- **TypeScript**: 타입 안정성
- **Vite**: 빌드 도구
- **Material-UI**: UI 컴포넌트
- **Recharts**: 차트 시각화
- **Axios**: HTTP 클라이언트
- **React Router**: 라우팅

### 페이지 구조

```
/                 → Dashboard (대시보드)
  - 포트폴리오 요약 (4개 카드)
  - 스케줄러 제어
  - 보유 포지션 리스트
  - 리스크 경고

/trading          → Trading (거래 관리)
  - AI 결정 로그 (테이블)
  - 거래 내역 (테이블)
  - 결정 상세 다이얼로그

/portfolio        → Portfolio (포트폴리오)
  - 자산 추이 차트 (30일)
  - 일별 통계 카드

/signals          → Signals (시장 신호)
  - 종목 분석 검색
  - WallStreetBets 트렌딩 (20개)
  - 신호 상세 (WSB/Yahoo/TipRanks)

/settings         → Settings (설정)
  - API 키 관리
  - 리스크 파라미터 조회
```

### API 클라이언트 구조

```typescript
// services/api.ts

schedulerApi:
  - getStatus()
  - start()
  - stop()
  - executeSession(type)

portfolioApi:
  - getStatus()
  - getHistory(days)
  - getPosition(ticker)
  - saveSnapshot()

tradingApi:
  - analyzeTicker(ticker)
  - getHistory(days)
  - getDecisions(limit)
  - getDecisionDetail(id)

signalsApi:
  - getTrending(limit)
  - getTickerSignals(ticker)
  - getRecent(hours, limit)

settingsApi:
  - getApiKeys()
  - saveApiKey(name, value)
  - deleteApiKey(name)
  - getRiskParams()
```

## 🔄 거래 워크플로우

### 자동 거래 세션 플로우

```
1. Scheduler Trigger (예: 23:20 KST)
   ↓
2. TradingEngine.execute_trading_session('PRE_MARKET')
   ↓
3. RiskManager.can_trade_now()
   → 서킷브레이커 체크
   ↓
4. PortfolioManager.get_current_state()
   → 현재 포트폴리오 조회
   ↓
5. SignalAggregator.aggregate_signals()
   → WSB 트렌딩 top 10 분석
   ↓
6. GeminiService.make_trading_decision()
   ├─ 프롬프트 생성 (PRE_MARKET용)
   ├─ Gemini API 호출
   ├─ Function Calling 루프:
   │  ├─ AI가 check_balance() 호출
   │  ├─ AI가 analyze_signals('AAPL') 호출
   │  ├─ AI가 calculate_position_size() 호출
   │  ├─ AI가 execute_trade('AAPL', 'BUY', 5) 호출
   │  └─ ... (최대 10회 반복)
   └─ 최종 결정 파싱
   ↓
7. LLMDecision 데이터베이스에 저장
   → 감사 추적용
   ↓
8. PortfolioManager.save_snapshot()
   → 세션 후 스냅샷
```

### Stop-Loss 자동 실행 플로우

```
1. Scheduler Trigger (30분마다)
   ↓
2. TradingEngine.check_and_execute_stop_losses()
   ↓
3. RiskManager.check_all_stop_losses()
   → 모든 포지션 -30% 체크
   ↓
4. 트리거된 포지션별:
   RiskManager.execute_stop_loss_sell(ticker, quantity)
   ↓
5. BrokerService.place_us_order(ticker, 'SELL', quantity, 'MARKET')
   ↓
6. 결과 로깅
```

## 🔐 보안 아키텍처

### API 키 암호화
```python
EncryptionService (Fernet 대칭 암호화)
  ↓
encryption_key (data/encryption.key, 0o600 권한)
  ↓
encrypted_value (데이터베이스 저장)
```

### 접근 제어
- `.env` 파일: git에서 제외
- `encryption.key`: 0o600 권한 (소유자만 읽기/쓰기)
- API 키: 데이터베이스에 암호화 저장
- WebUI: API 키는 마스킹 표시 (`***...`)

## 📊 모니터링 및 로깅

### 로그 파일 (logs/)
- `app.log`: 전체 애플리케이션 로그
- `trading.log`: 거래 실행 로그
- `gemini.log`: AI 결정 로그
- `scheduler.log`: 스케줄러 작업 로그
- `errors.log`: 에러만 수집

### 로그 레벨
- DEBUG: 개발용 상세 정보
- INFO: 일반 작업 정보
- WARNING: 경고 (stop-loss 트리거 등)
- ERROR: 오류 발생
- CRITICAL: 서킷브레이커 발동 등

### 로그 로테이션
- 최대 파일 크기: 10MB
- 백업 파일 수: 5-10개
- 자동 압축 및 순환

## 🚀 배포 아키텍처

### 개발 환경
```
Mac localhost:
  - Backend: uvicorn (1 worker)
  - Frontend: vite dev server
  - Database: SQLite (data/trading_bot.db)
```

### 프로덕션 환경
```
Mac localhost (caffeinate로 슬립 방지):
  - Backend: uvicorn (2 workers)
  - Frontend: static build (dist/)
  - Database: SQLite + 일일 백업
  - Scheduler: APScheduler (자동 거래)
```

### 향후 확장 가능성
```
Linux Server:
  - Backend: Gunicorn + Uvicorn workers
  - Frontend: Nginx 정적 서빙
  - Database: PostgreSQL
  - Cache: Redis
  - Queue: Celery
  - Container: Docker
```

## 📈 성능 최적화

### 백엔드
- **비동기 I/O**: asyncio, aiohttp, aiosqlite
- **병렬 신호 수집**: asyncio.gather()
- **데이터베이스 인덱스**: ticker, created_at, snapshot_date
- **커넥션 풀**: SQLAlchemy AsyncEngine

### 프론트엔드
- **코드 분할**: React.lazy() (향후)
- **Vite 번들링**: 최적화된 프로덕션 빌드
- **API 폴링 간격**: 대시보드 10초, 거래 30초, 신호 60초

### 네트워크
- **HTTP/2**: uvicorn 지원
- **압축**: gzip 응답
- **캐싱**: 정적 파일 브라우저 캐싱

## 🧪 테스트 전략

### 단위 테스트 (pytest)
- 각 서비스 개별 테스트
- Mock 브로커 사용
- 격리된 데이터베이스

### 통합 테스트
- Gemini function calling 테스트
- 전체 거래 워크플로우 테스트
- API 엔드포인트 테스트 (httpx)

### 수동 테스트
- WebUI 전체 플로우
- API 문서 (/docs)에서 직접 호출
- 로그 파일 검증

---

이 아키텍처는 확장 가능하고 유지보수가 용이하도록 설계되었습니다.
