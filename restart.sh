#!/bin/bash

# US Stock Trading Bot - Restart Script
# 서버를 재시작합니다

echo "🔄 Restarting US Stock Trading Bot..."
echo "===================================="

PROJECT_ROOT="/Users/mackbook/Documents/us-stock-trading-bot"

# 서버 종료
"$PROJECT_ROOT/stop.sh"

# 2초 대기
sleep 2

# 서버 시작
"$PROJECT_ROOT/start.sh"
