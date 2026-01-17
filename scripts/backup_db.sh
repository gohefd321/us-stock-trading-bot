#!/bin/bash

# US Stock Trading Bot - Database Backup Script

set -e

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

BACKUP_DIR="data/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_FILE="data/trading_bot.db"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    echo "Error: Database file not found at $DB_FILE"
    exit 1
fi

# Create backup
echo "Creating database backup..."
sqlite3 "$DB_FILE" ".backup '$BACKUP_DIR/trading_bot_$TIMESTAMP.db'"

echo "Backup created: $BACKUP_DIR/trading_bot_$TIMESTAMP.db"

# Keep only last 30 days of backups
echo "Cleaning up old backups (keeping last 30 days)..."
find "$BACKUP_DIR" -name "trading_bot_*.db" -type f -mtime +30 -delete

echo "Backup complete"
