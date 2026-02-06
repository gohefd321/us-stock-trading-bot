# 🚀 빠른 시작 가이드

## 한 번에 서버 실행하기

### 1. 서버 시작
```bash
./start.sh
```

이 명령어는:
- ✅ 백엔드 서버 시작 (http://localhost:8000)
- ✅ 프론트엔드 서버 시작 (http://localhost:5173)
- ✅ 자동 헬스 체크
- ✅ 실시간 로그 표시

### 2. 서버 종료
```bash
./stop.sh
```

### 3. 서버 재시작
```bash
./restart.sh
```

---

## 📊 접속 URL

서버가 시작되면 브라우저에서 다음 주소로 접속하세요:

### 프론트엔드
- **메인 대시보드**: http://localhost:5173
- **시스템 제어** (시작하기 좋음!): http://localhost:5173/system
- **주문 관리**: http://localhost:5173/orders
- **포트폴리오 최적화**: http://localhost:5173/optimizer
- **알고리즘 대시보드**: http://localhost:5173/algorithm
- **실시간 가격**: http://localhost:5173/realtime

### 백엔드
- **API 서버**: http://localhost:8000
- **API 문서 (Swagger)**: http://localhost:8000/docs
- **대체 API 문서 (ReDoc)**: http://localhost:8000/redoc

---

## 🎯 첫 실행 가이드

### 1단계: 서버 시작
```bash
./start.sh
```

### 2단계: 시스템 제어 페이지 접속
브라우저에서: http://localhost:5173/system

### 3단계: 워치리스트에 종목 추가
- 입력창에 `AAPL` 입력 → "Add" 버튼 클릭
- 추가 종목: `MSFT`, `GOOGL`, `AMZN`, `NVDA`

### 4단계: 초기 지표 계산
- "Calculate Indicators" 버튼 클릭

### 5단계: 스케줄러 시작
- "Start" 버튼 클릭 (자동 데이터 수집 시작)

### 6단계: 결과 확인
- 알고리즘 대시보드: http://localhost:5173/algorithm
- 생성된 신호 확인 및 백테스트 결과 보기

---

## 📁 로그 파일

서버 실행 중 문제가 발생하면 로그 파일을 확인하세요:

- **백엔드 로그**: `backend.log`
- **프론트엔드 로그**: `frontend.log`

```bash
# 백엔드 로그 확인
tail -f backend.log

# 프론트엔드 로그 확인
tail -f frontend.log
```

---

## 🔧 수동 실행 (개발 모드)

스크립트 대신 수동으로 실행하려면:

### 백엔드
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### 프론트엔드 (새 터미널)
```bash
cd frontend
npm run dev
```

---

## ⚙️ 환경 변수 설정

첫 실행 전에 `.env` 파일을 설정하세요:

```bash
cd backend
cp .env.example .env
nano .env  # 또는 원하는 에디터 사용
```

필수 설정:
- `KOREA_INVESTMENT_API_KEY` - 한국투자증권 API 키
- `KOREA_INVESTMENT_API_SECRET` - 한국투자증권 API 시크릿
- `KOREA_INVESTMENT_ACCOUNT_NUMBER` - 계좌번호
- `GOOGLE_API_KEY` - Google Gemini API 키
- `ALPHA_VANTAGE_API_KEY` - Alpha Vantage API 키

---

## 🚨 문제 해결

### 포트가 이미 사용 중인 경우
```bash
# 8000 포트 확인
lsof -ti:8000

# 프로세스 종료
kill -9 $(lsof -ti:8000)

# 또는 stop.sh 실행
./stop.sh
```

### 데이터베이스 초기화
```bash
cd backend
source venv/bin/activate
python migrate_orders.py
```

### 의존성 재설치
```bash
# 백엔드
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 프론트엔드
cd frontend
npm install
```

---

## 📚 추가 문서

- **주문 관리 가이드**: `ORDER_MANAGEMENT_GUIDE.md`
- **전체 시스템 총정리**: `COMPLETE_SYSTEM_SUMMARY.md`
- **Phase 완성 가이드**: `PHASE_COMPLETE_GUIDE.md`

---

## 🎉 모든 준비 완료!

```bash
./start.sh
```

명령어 하나로 시작하세요! 🚀
