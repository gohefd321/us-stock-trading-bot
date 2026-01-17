#!/bin/bash

# US Stock Trading Bot - Production Mode Runner with Sleep Prevention

set -e

echo "========================================="
echo "  Starting US Stock Trading Bot (Prod)"
echo "========================================="
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# Prevent Mac from sleeping
echo "Preventing Mac from sleeping..."
caffeinate -s -w $$ &
CAFFEINATE_PID=$!

# Build frontend
if [ -d "frontend" ]; then
    echo "Building frontend..."
    cd frontend
    if command -v npm &> /dev/null; then
        npm run build
        echo "Frontend built successfully"
    else
        echo "Warning: npm not found. Skipping frontend build."
    fi
    cd "$PROJECT_ROOT"
fi

# Start backend with multiple workers for stability
echo ""
echo "Starting production server..."
cd backend
source venv/bin/activate

# Run with multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 &
SERVER_PID=$!

cd "$PROJECT_ROOT"

# Display info
echo ""
echo "========================================="
echo "  Production Server Running"
echo "========================================="
echo "Server:   http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Mac sleep prevention: ACTIVE"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping server..."
    kill $SERVER_PID 2>/dev/null || true
    kill $CAFFEINATE_PID 2>/dev/null || true
    echo "Server stopped"
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Wait for server
wait $SERVER_PID
