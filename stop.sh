#!/bin/bash

# US Stock Trading Bot - Stop Script
# 실행 중인 서버를 종료합니다

echo "🛑 Stopping US Stock Trading Bot..."
echo "===================================="

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ROOT="/Users/mackbook/Documents/us-stock-trading-bot"

# 백엔드 종료
if [ -f "$PROJECT_ROOT/backend.pid" ]; then
  BACKEND_PID=$(cat "$PROJECT_ROOT/backend.pid")
  if ps -p "$BACKEND_PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}⏳${NC} Stopping backend server (PID: $BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null
    sleep 2

    # 강제 종료 (필요 시)
    if ps -p "$BACKEND_PID" > /dev/null 2>&1; then
      kill -9 "$BACKEND_PID" 2>/dev/null
    fi

    echo -e "${GREEN}✓${NC} Backend server stopped"
  else
    echo -e "${YELLOW}⚠${NC} Backend server is not running"
  fi
  rm -f "$PROJECT_ROOT/backend.pid"
else
  echo -e "${YELLOW}⚠${NC} Backend PID file not found"
fi

# 프론트엔드 종료
if [ -f "$PROJECT_ROOT/frontend.pid" ]; then
  FRONTEND_PID=$(cat "$PROJECT_ROOT/frontend.pid")
  if ps -p "$FRONTEND_PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}⏳${NC} Stopping frontend server (PID: $FRONTEND_PID)..."
    kill "$FRONTEND_PID" 2>/dev/null
    sleep 2

    # 강제 종료 (필요 시)
    if ps -p "$FRONTEND_PID" > /dev/null 2>&1; then
      kill -9 "$FRONTEND_PID" 2>/dev/null
    fi

    echo -e "${GREEN}✓${NC} Frontend server stopped"
  else
    echo -e "${YELLOW}⚠${NC} Frontend server is not running"
  fi
  rm -f "$PROJECT_ROOT/frontend.pid"
else
  echo -e "${YELLOW}⚠${NC} Frontend PID file not found"
fi

# 포트에서 실행 중인 프로세스 추가 확인 및 종료
echo ""
echo -e "${YELLOW}⏳${NC} Checking for processes on ports 8000 and 5173..."

# 8000 포트 (백엔드)
BACKEND_PORT_PID=$(lsof -ti:8000 2>/dev/null)
if [ -n "$BACKEND_PORT_PID" ]; then
  echo -e "${YELLOW}⚠${NC} Found process on port 8000 (PID: $BACKEND_PORT_PID), terminating..."
  kill -9 "$BACKEND_PORT_PID" 2>/dev/null
  echo -e "${GREEN}✓${NC} Port 8000 cleared"
fi

# 5173 포트 (프론트엔드)
FRONTEND_PORT_PID=$(lsof -ti:5173 2>/dev/null)
if [ -n "$FRONTEND_PORT_PID" ]; then
  echo -e "${YELLOW}⚠${NC} Found process on port 5173 (PID: $FRONTEND_PORT_PID), terminating..."
  kill -9 "$FRONTEND_PORT_PID" 2>/dev/null
  echo -e "${GREEN}✓${NC} Port 5173 cleared"
fi

echo ""
echo "===================================="
echo -e "${GREEN}✅ All servers stopped successfully!${NC}"
echo "===================================="
