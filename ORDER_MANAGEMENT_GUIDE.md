# 📋 주문 관리 & 포트폴리오 최적화 가이드

## 🎯 개요

한국투자증권 API를 통한 **실제 주문 관리** 및 **Modern Portfolio Theory 기반 포트폴리오 최적화** 시스템이 구축되었습니다.

---

## 🏗️ 새로 추가된 기능

### 1. 주문 관리 시스템
- ✅ 매수/매도 주문 생성 (시장가, 지정가)
- ✅ 주문 상태 추적 및 체결 확인
- ✅ 손절/익절 자동 주문
- ✅ 포지션 자동 업데이트

### 2. 포트폴리오 최적화
- ✅ Modern Portfolio Theory (MPT) 구현
- ✅ Efficient Frontier 계산
- ✅ 샤프 비율 최대화
- ✅ 리밸런싱 추천

---

## 📁 새로 생성된 파일

### 모델 (Models)
```
backend/app/models/
├── order.py                    # 주문 모델 (상태, 체결 정보)
└── portfolio_position.py       # 포지션 모델 (실시간 손익, 비중)
```

### 서비스 (Services)
```
backend/app/services/
├── order_management_service.py    # 주문 생성, 상태 추적, 손절/익절
└── portfolio_optimizer.py         # MPT 최적화, Efficient Frontier
```

### API 라우트 (Routes)
```
backend/app/routes/
├── order_management.py           # 주문 API
└── portfolio_optimizer.py        # 포트폴리오 최적화 API
```

### 마이그레이션
```
backend/
└── migrate_orders.py             # DB 테이블 생성 스크립트
```

---

## 📊 데이터베이스 테이블

### 1. `orders` 테이블
주문 정보 및 체결 상태 추적

```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    order_number VARCHAR UNIQUE NOT NULL,     -- KIS 주문번호
    ticker VARCHAR NOT NULL,                   -- 종목코드
    market_type VARCHAR DEFAULT 'US',         -- 시장구분
    order_type VARCHAR NOT NULL,              -- BUY, SELL
    order_method VARCHAR DEFAULT 'MARKET',    -- MARKET, LIMIT
    order_quantity INTEGER NOT NULL,          -- 주문수량
    order_price FLOAT,                        -- 주문단가
    filled_quantity INTEGER DEFAULT 0,        -- 체결수량
    avg_filled_price FLOAT,                   -- 평균체결가
    status VARCHAR DEFAULT 'SUBMITTED',       -- 주문 상태
    signal_id INTEGER,                        -- 연결된 신호 ID
    strategy_name VARCHAR,                    -- 전략명
    stop_loss_price FLOAT,                    -- 손절가
    take_profit_price FLOAT,                  -- 익절가
    submitted_at TIMESTAMP,
    filled_at TIMESTAMP,
    broker_response VARCHAR                   -- KIS API 응답
);
```

**주문 상태 (status):**
- `SUBMITTED`: 주문 제출
- `PENDING`: 대기 중
- `PARTIAL_FILLED`: 부분 체결
- `FILLED`: 전량 체결
- `CANCELLED`: 취소
- `REJECTED`: 거부

### 2. `portfolio_positions` 테이블
실시간 포지션 추적 및 손익 관리

```sql
CREATE TABLE portfolio_positions (
    id INTEGER PRIMARY KEY,
    ticker VARCHAR UNIQUE NOT NULL,           -- 종목코드
    quantity INTEGER NOT NULL,                -- 보유수량
    avg_buy_price FLOAT NOT NULL,            -- 평균 매수가
    total_invested FLOAT NOT NULL,           -- 총 투자금액
    current_price FLOAT,                     -- 현재가
    current_value FLOAT,                     -- 현재 평가금액
    unrealized_pnl FLOAT,                    -- 미실현 손익
    unrealized_pnl_pct FLOAT,                -- 미실현 수익률 (%)
    realized_pnl FLOAT DEFAULT 0,            -- 실현 손익
    portfolio_weight FLOAT,                  -- 포트폴리오 비중 (%)
    target_weight FLOAT,                     -- 목표 비중 (%)
    stop_loss_price FLOAT,                   -- 손절가
    take_profit_price FLOAT,                 -- 익절가
    trailing_stop_pct FLOAT,                 -- 트레일링 스탑 (%)
    max_price_achieved FLOAT,                -- 최고가
    entry_strategy VARCHAR,                  -- 진입 전략
    entry_date TIMESTAMP,                    -- 진입 일자
    holding_days INTEGER DEFAULT 0           -- 보유 일수
);
```

---

## 🔌 API 엔드포인트

### 주문 관리 API (`/api/orders`)

#### 1. 매수 주문 생성
```http
POST /api/orders/buy
Content-Type: application/json

{
  "ticker": "AAPL",
  "quantity": 10,
  "order_method": "MARKET",           // "MARKET" or "LIMIT"
  "price": 0,                         // 지정가 (LIMIT 주문 시)
  "strategy_name": "MA_CROSS",
  "signal_id": 123,
  "reason": "Golden cross signal",
  "stop_loss_pct": 5.0,               // 손절 비율 (선택)
  "take_profit_pct": 10.0             // 익절 비율 (선택)
}
```

**응답:**
```json
{
  "success": true,
  "order_id": 1,
  "order_number": "0000123456",
  "message": "Buy order created successfully"
}
```

#### 2. 매도 주문 생성
```http
POST /api/orders/sell
Content-Type: application/json

{
  "ticker": "AAPL",
  "quantity": 5,
  "order_method": "MARKET",
  "reason": "Take profit triggered"
}
```

#### 3. 주문 상태 조회
```http
GET /api/orders/status/0000123456
```

**응답:**
```json
{
  "order_id": 1,
  "order_number": "0000123456",
  "ticker": "AAPL",
  "order_type": "BUY",
  "order_quantity": 10,
  "filled_quantity": 10,
  "status": "FILLED",
  "submitted_at": "2026-02-06T10:00:00Z",
  "filled_at": "2026-02-06T10:00:05Z",
  "is_active": false,
  "fill_rate": 1.0
}
```

#### 4. 활성 주문 조회
```http
GET /api/orders/active?ticker=AAPL
```

#### 5. 주문 히스토리
```http
GET /api/orders/history?limit=50
```

#### 6. 손절/익절 자동 체크
```http
POST /api/orders/check-stop-loss-take-profit
```

**응답:**
```json
{
  "success": true,
  "triggered_orders": [
    {
      "ticker": "TSLA",
      "type": "STOP_LOSS",
      "order_number": "0000123457"
    }
  ],
  "count": 1
}
```

---

### 포트폴리오 최적화 API (`/api/portfolio`)

#### 1. 최적 포트폴리오 계산 (MPT)
```http
POST /api/portfolio/optimize
Content-Type: application/json

{
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
  "method": "sharpe",                    // "sharpe", "min_variance", "max_return"
  "risk_free_rate": 0.04,               // 무위험 수익률 (4%)
  "lookback_days": 252                  // 과거 데이터 기간 (1년)
}
```

**응답:**
```json
{
  "success": true,
  "method": "sharpe",
  "portfolio_weights": {
    "AAPL": 0.25,
    "MSFT": 0.20,
    "GOOGL": 0.18,
    "AMZN": 0.22,
    "NVDA": 0.15
  },
  "expected_return": 0.185,              // 18.5% 연간 수익률
  "expected_volatility": 0.22,           // 22% 연간 변동성
  "sharpe_ratio": 0.66,
  "efficient_frontier": [
    {"return": 0.10, "volatility": 0.15, "sharpe_ratio": 0.40},
    {"return": 0.15, "volatility": 0.18, "sharpe_ratio": 0.61},
    ...
  ]
}
```

**최적화 방법:**
- `sharpe`: **샤프 비율 최대화** (리스크 대비 수익률 최적)
- `min_variance`: **분산 최소화** (최소 리스크 포트폴리오)
- `max_return`: **수익률 최대화** (고위험 포트폴리오)

#### 2. 리밸런싱 추천
```http
POST /api/portfolio/rebalancing
Content-Type: application/json

{
  "target_weights": {
    "AAPL": 25.0,
    "MSFT": 20.0,
    "GOOGL": 15.0,
    "AMZN": 20.0,
    "NVDA": 20.0
  },
  "total_value": 100000,                 // 총 포트폴리오 가치 ($)
  "tolerance": 5.0                       // 허용 이탈 비율 (5%)
}
```

**응답:**
```json
{
  "success": true,
  "rebalancing_needed": true,
  "actions": [
    {
      "ticker": "NVDA",
      "current_weight": 28.5,
      "target_weight": 20.0,
      "weight_diff": -8.5,
      "action": "SELL",
      "quantity": 5,
      "value": 8500
    },
    {
      "ticker": "GOOGL",
      "current_weight": 10.2,
      "target_weight": 15.0,
      "weight_diff": 4.8,
      "action": "BUY",
      "quantity": 3,
      "value": 4800
    }
  ],
  "total_actions": 2
}
```

#### 3. 포트폴리오 메트릭
```http
GET /api/portfolio/metrics
```

**응답:**
```json
{
  "success": true,
  "total_invested": 95000.0,
  "total_value": 105000.0,
  "total_unrealized_pnl": 10000.0,
  "total_realized_pnl": 2500.0,
  "total_return_pct": 13.16,
  "portfolio_volatility": 0.18,
  "position_count": 5,
  "position_weights": [
    {
      "ticker": "AAPL",
      "weight": 25.0,
      "value": 26250.0,
      "unrealized_pnl": 2500.0,
      "unrealized_pnl_pct": 10.5
    }
  ],
  "sector_allocation": {
    "Technology": 75.0,
    "Consumer": 25.0
  }
}
```

#### 4. 포지션 조회
```http
GET /api/portfolio/positions          # 전체 포지션
GET /api/portfolio/positions/AAPL    # 특정 포지션 상세
```

---

## 🚀 사용 시나리오

### 시나리오 1: 신호 기반 자동 매매

```python
# 1. 신호 생성 (기존 Phase 3.4)
POST /api/signals/generate
{
  "ticker": "AAPL",
  "timeframe": "1h",
  "strategy_names": ["MA_CROSS", "RSI", "MACD"]
}

# 2. 신호 조회
GET /api/signals/AAPL/latest
# Response: { "signal_type": "BUY", "strength": 0.85 }

# 3. 주문 생성 (신호 ID 연결)
POST /api/orders/buy
{
  "ticker": "AAPL",
  "quantity": 10,
  "order_method": "MARKET",
  "strategy_name": "MA_CROSS",
  "signal_id": 123,
  "stop_loss_pct": 5.0,         # 5% 손절
  "take_profit_pct": 15.0       # 15% 익절
}
```

### 시나리오 2: 포트폴리오 최적화 & 리밸런싱

```python
# 1. 추천 종목 (LLM Daily Report)
GET /api/daily-report/latest
# Response: ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

# 2. 최적 포트폴리오 계산
POST /api/portfolio/optimize
{
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
  "method": "sharpe"
}
# Response: { "portfolio_weights": {...} }

# 3. 리밸런싱 추천
POST /api/portfolio/rebalancing
{
  "target_weights": { "AAPL": 25, ... },
  "total_value": 100000
}
# Response: { "actions": [{"ticker": "AAPL", "action": "BUY", "quantity": 5}] }

# 4. 리밸런싱 주문 실행
POST /api/orders/buy
{
  "ticker": "AAPL",
  "quantity": 5,
  "reason": "Rebalancing to target weight"
}
```

### 시나리오 3: 손절/익절 자동화

```python
# 스케줄러에 추가 (5분마다 체크)
# integrated_scheduler.py

self.scheduler.add_job(
    self._check_stop_loss_take_profit,
    CronTrigger(minute="*/5"),  # 5분마다
    id="stop_loss_check",
    name="Stop Loss & Take Profit Check"
)

async def _check_stop_loss_take_profit(self):
    """손절/익절 자동 체크"""
    response = await requests.post(
        "http://localhost:8000/api/orders/check-stop-loss-take-profit"
    )
    # 자동으로 손절/익절 주문 생성
```

---

## 📈 포트폴리오 최적화 이론

### Modern Portfolio Theory (MPT)

**핵심 개념:**
- 리스크(변동성)와 수익률의 트레이드오프
- 분산 투자를 통한 리스크 감소
- Efficient Frontier: 동일 리스크에서 최대 수익률을 달성하는 포트폴리오 조합

**샤프 비율 (Sharpe Ratio):**
```
Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Volatility

예시:
- 포트폴리오 수익률: 18.5%
- 무위험 수익률: 4%
- 포트폴리오 변동성: 22%
- Sharpe Ratio = (0.185 - 0.04) / 0.22 = 0.66
```

**해석:**
- > 1.0: 좋음
- > 2.0: 매우 좋음
- > 3.0: 탁월함

---

## 🔧 통합 스케줄러 추가

`integrated_scheduler.py`에 다음 작업 추가 권장:

```python
# 주문 상태 업데이트 (1분마다)
self.scheduler.add_job(
    self._sync_order_status,
    CronTrigger(minute="*"),
    id="sync_orders",
    name="Sync Order Status"
)

# 손절/익절 체크 (5분마다)
self.scheduler.add_job(
    self._check_stop_loss_take_profit,
    CronTrigger(minute="*/5"),
    id="stop_loss_check",
    name="Stop Loss Check"
)

# 포트폴리오 메트릭 업데이트 (30분마다)
self.scheduler.add_job(
    self._update_portfolio_metrics,
    CronTrigger(minute="0,30"),
    id="portfolio_metrics",
    name="Portfolio Metrics Update"
)

# 리밸런싱 체크 (매주 월요일 10시)
self.scheduler.add_job(
    self._check_rebalancing,
    CronTrigger(day_of_week='mon', hour=10, minute=0),
    id="rebalancing_check",
    name="Weekly Rebalancing Check"
)
```

---

## ⚙️ 환경 변수 설정

`.env` 파일에 다음 추가 (기존 KIS API 키 사용):

```env
# 한국투자증권 API (기존 키 사용)
KOREA_INVESTMENT_API_KEY=your_app_key
KOREA_INVESTMENT_API_SECRET=your_app_secret
KOREA_INVESTMENT_ACCOUNT_NUMBER=12345678-01
KOREA_INVESTMENT_ACCOUNT_PASSWORD=1234          # 해외주식 거래 시 필수
KOREA_INVESTMENT_PASSWORD_PADDING=true          # 4자리 → 8자리 패딩
KOREA_INVESTMENT_PAPER_MODE=true                # 모의투자: true, 실전투자: false
```

---

## 🧪 테스트 시나리오

### 1. 매수 주문 테스트
```bash
curl -X POST http://localhost:8000/api/orders/buy \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "quantity": 1,
    "order_method": "MARKET",
    "stop_loss_pct": 5.0,
    "take_profit_pct": 10.0
  }'
```

### 2. 주문 상태 확인
```bash
curl http://localhost:8000/api/orders/status/0000123456
```

### 3. 포트폴리오 최적화
```bash
curl -X POST http://localhost:8000/api/portfolio/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
    "method": "sharpe",
    "lookback_days": 252
  }'
```

### 4. 리밸런싱 추천
```bash
curl -X POST http://localhost:8000/api/portfolio/rebalancing \
  -H "Content-Type: application/json" \
  -d '{
    "target_weights": {
      "AAPL": 20.0,
      "MSFT": 20.0,
      "GOOGL": 20.0,
      "AMZN": 20.0,
      "NVDA": 20.0
    },
    "total_value": 100000,
    "tolerance": 5.0
  }'
```

### 5. 포트폴리오 메트릭
```bash
curl http://localhost:8000/api/portfolio/metrics
```

---

## 📊 프론트엔드 통합 (다음 단계)

### 추천 UI 컴포넌트:

1. **주문 대시보드** (`OrderDashboard.tsx`)
   - 활성 주문 리스트
   - 주문 히스토리
   - 빠른 매수/매도 버튼

2. **포지션 뷰어** (`PositionViewer.tsx`)
   - 보유 종목 리스트
   - 실시간 손익
   - 비중 차트

3. **포트폴리오 최적화 UI** (`PortfolioOptimizer.tsx`)
   - Efficient Frontier 차트
   - 최적 비중 계산
   - 리밸런싱 추천 표시

4. **리스크 관리 패널** (`RiskPanel.tsx`)
   - 손절/익절 설정
   - 포지션 사이징
   - 일일 손익 제한

---

## 🎉 완성된 시스템 통합

### 전체 트레이딩 플로우:

```
1. 데이터 수집 (Phase 1)
   └─> 시장 스크리너, 재무 데이터, 뉴스

2. LLM 분석 (Phase 1.4)
   └─> 추천 종목 3-5개 선정

3. 포트폴리오 최적화 (NEW!)
   └─> 최적 비중 계산 (MPT)

4. 기술적 지표 계산 (Phase 3.1)
   └─> SMA, RSI, MACD 등

5. 전략 신호 생성 (Phase 3.2, 3.4)
   └─> 5가지 전략 통합 신호

6. 주문 생성 (NEW!)
   └─> KIS API 주문 전송
   └─> 손절/익절 설정

7. 체결 확인 & 포지션 업데이트 (NEW!)
   └─> 자동 포지션 추적
   └─> 실시간 손익 계산

8. 리밸런싱 (NEW!)
   └─> 목표 비중 대비 이탈 체크
   └─> 자동 리밸런싱 주문
```

---

## 🚨 주의사항

### 1. 실전 투자 전 확인 사항
- ⚠️ 반드시 **모의투자 모드**에서 충분히 테스트
- ⚠️ 손절/익절 비율 적절히 설정 (권장: 손절 5%, 익절 10-15%)
- ⚠️ 포지션 크기 제한 (단일 종목 최대 20-30%)
- ⚠️ 일일 최대 손실 제한 설정

### 2. API 제한
- 한국투자증권 API: **초당 20건** 제한
- 주문 API는 **시장 시간에만** 동작 (미국 시장 기준)
- 토큰 만료: 24시간 (자동 갱신 구현됨)

### 3. 리스크 관리
- 분산 투자 (최소 5개 이상 종목)
- 섹터 다각화
- 레버리지 사용 금지
- 충분한 현금 보유 (포트폴리오의 10-20%)

---

## 📚 참고 자료

- **Modern Portfolio Theory**: [Wikipedia](https://en.wikipedia.org/wiki/Modern_portfolio_theory)
- **Sharpe Ratio**: [Investopedia](https://www.investopedia.com/terms/s/sharperatio.asp)
- **Efficient Frontier**: [Corporate Finance Institute](https://corporatefinanceinstitute.com/resources/knowledge/finance/efficient-frontier/)
- **한국투자증권 API 문서**: [KIS Developers](https://apiportal.koreainvestment.com/)

---

**🎉 모든 Phase 완료! (Phase 1-4 + 주문 관리 + 포트폴리오 최적화)**

**Happy Trading! 📈🚀**
