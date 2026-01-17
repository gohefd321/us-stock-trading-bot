#!/bin/bash

# US Stock Trading Bot - Initial Setup Script
# This script sets up the development environment

set -e  # Exit on error

echo "========================================="
echo "  US Stock Trading Bot - Setup"
echo "========================================="
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Found Python $PYTHON_VERSION"

# Create backend virtual environment
echo ""
echo "Creating Python virtual environment..."
cd backend
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "Python dependencies installed successfully"

# Go back to project root
cd "$PROJECT_ROOT"

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data logs database

# Initialize database
echo ""
echo "Initializing database..."
sqlite3 data/trading_bot.db < database/schema.sql

echo "Database initialized successfully"

# Setup frontend (Node.js)
echo ""
echo "Setting up frontend..."
if command -v node &> /dev/null; then
    cd frontend
    echo "Installing Node.js dependencies..."
    npm install
    echo "Frontend dependencies installed successfully"
    cd "$PROJECT_ROOT"
else
    echo "Warning: Node.js not found. Skipping frontend setup."
    echo "Please install Node.js to set up the frontend later."
fi

# Create .env file if it doesn't exist
echo ""
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ".env file created. Please edit it and add your API keys."
else
    echo ".env file already exists"
fi

# Summary
echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Run 'bash scripts/run_dev.sh' to start development server"
echo "3. Open http://localhost:5173 in your browser"
echo "4. Complete the first-time setup wizard in the web UI"
echo ""
echo "For production:"
echo "  Run 'bash scripts/run_prod.sh'"
echo ""
