#!/bin/bash

# FastAPI Only - Run Backend Server with Templates
# This script runs only the FastAPI server with Jinja2 templates
# React/Vite is no longer needed

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "========================================"
echo "  US Stock Trading Bot - FastAPI Server"
echo "========================================"
echo ""
echo "프로젝트 경로: $PROJECT_ROOT"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3이 설치되지 않았습니다."
    exit 1
fi

echo "✓ Python: $(python3 --version)"

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo ""
    echo "가상환경이 없습니다. 생성 중..."
    python3 -m venv "$PROJECT_ROOT/venv"
    echo "✓ 가상환경 생성 완료"
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

# Install dependencies
echo ""
echo "패키지 설치 중..."
pip install -q -r "$PROJECT_ROOT/backend/requirements.txt"
echo "✓ 패키지 설치 완료"

# Run FastAPI server
echo ""
echo "========================================"
echo "  FastAPI 서버 시작"
echo "========================================"
echo ""
echo "📍 접속 주소: http://localhost:8000"
echo "📍 API 문서: http://localhost:8000/docs"
echo ""
echo "Ctrl+C로 서버를 중지할 수 있습니다."
echo ""

cd "$PROJECT_ROOT/backend"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
