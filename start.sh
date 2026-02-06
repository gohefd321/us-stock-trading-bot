#!/bin/bash

# US Stock Trading Bot - Startup Script
# 백엔드와 프론트엔드를 한 번에 실행합니다

echo "🚀 Starting US Stock Trading Bot..."
echo "===================================="

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리
PROJECT_ROOT="/Users/mackbook/Documents/us-stock-trading-bot"

# 로그 파일
BACKEND_LOG="$PROJECT_ROOT/backend.log"
FRONTEND_LOG="$PROJECT_ROOT/frontend.log"

# 기존 로그 파일 삭제
rm -f "$BACKEND_LOG" "$FRONTEND_LOG"

# 1. 백엔드 서버 시작
echo -e "${BLUE}[1/2]${NC} Starting Backend Server..."
cd "$PROJECT_ROOT/backend" || exit

# 가상환경 활성화 및 백엔드 실행
(
  source venv/bin/activate
  echo -e "${GREEN}✓${NC} Backend virtual environment activated"

  # 백엔드 서버 시작 (백그라운드)
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > "$BACKEND_LOG" 2>&1 &
  BACKEND_PID=$!

  echo -e "${GREEN}✓${NC} Backend server started (PID: $BACKEND_PID)"
  echo "$BACKEND_PID" > "$PROJECT_ROOT/backend.pid"
) &

# 백엔드 시작 대기 (5초)
sleep 5

# 백엔드 헬스 체크
echo -e "${YELLOW}⏳${NC} Checking backend health..."
for i in {1..10}; do
  if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend is ready at http://localhost:8000"
    break
  fi

  if [ $i -eq 10 ]; then
    echo -e "${RED}✗${NC} Backend failed to start. Check $BACKEND_LOG for errors."
    exit 1
  fi

  sleep 2
done

# 2. 프론트엔드 시작
echo ""
echo -e "${BLUE}[2/2]${NC} Starting Frontend Server..."
cd "$PROJECT_ROOT/frontend" || exit

# 프론트엔드 실행 (백그라운드)
(
  npm run dev > "$FRONTEND_LOG" 2>&1 &
  FRONTEND_PID=$!

  echo -e "${GREEN}✓${NC} Frontend server started (PID: $FRONTEND_PID)"
  echo "$FRONTEND_PID" > "$PROJECT_ROOT/frontend.pid"
) &

# 프론트엔드 시작 대기 (5초)
sleep 5

# 프론트엔드 헬스 체크
echo -e "${YELLOW}⏳${NC} Checking frontend health..."
for i in {1..10}; do
  if curl -s http://localhost:5173/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend is ready at http://localhost:5173"
    break
  fi

  if [ $i -eq 10 ]; then
    echo -e "${RED}✗${NC} Frontend failed to start. Check $FRONTEND_LOG for errors."
    exit 1
  fi

  sleep 2
done

# 완료 메시지
echo ""
echo "===================================="
echo -e "${GREEN}✅ All servers started successfully!${NC}"
echo "===================================="
echo ""
echo "📊 Access URLs:"
echo "  - Backend API:  http://localhost:8000"
echo "  - API Docs:     http://localhost:8000/docs"
echo "  - Frontend:     http://localhost:5173"
echo ""
echo "📁 Log Files:"
echo "  - Backend:      $BACKEND_LOG"
echo "  - Frontend:     $FRONTEND_LOG"
echo ""
echo "🎯 Quick Start Pages:"
echo "  - System Control:    http://localhost:5173/system"
echo "  - Order Management:  http://localhost:5173/orders"
echo "  - Portfolio Optimizer: http://localhost:5173/optimizer"
echo "  - Algorithm Dashboard: http://localhost:5173/algorithm"
echo ""
echo "🛑 To stop servers, run: ./stop.sh"
echo ""

# 로그 실시간 보기 (선택사항)
echo -e "${YELLOW}💡 Press Ctrl+C to stop watching logs${NC}"
echo ""
tail -f "$BACKEND_LOG" "$FRONTEND_LOG"
