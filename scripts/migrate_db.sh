#!/bin/bash

# Database migration script
# Adds is_active column to api_keys table

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${PROJECT_ROOT}/data/trading_bot.db"

echo "==========================================="
echo "  Database Migration"
echo "==========================================="
echo ""

if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database file not found at $DB_PATH"
    echo "Please run the application first to create the database."
    exit 1
fi

echo "Database: $DB_PATH"
echo ""

# Backup database
BACKUP_PATH="${DB_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$DB_PATH" "$BACKUP_PATH"
echo "✓ Database backed up to: $BACKUP_PATH"
echo ""

# Check if is_active column already exists
COLUMN_EXISTS=$(sqlite3 "$DB_PATH" "PRAGMA table_info(api_keys);" | grep -c "is_active" || true)

if [ "$COLUMN_EXISTS" -gt 0 ]; then
    echo "✓ Column 'is_active' already exists in api_keys table."
    echo "No migration needed."
else
    echo "Adding 'is_active' column to api_keys table..."

    sqlite3 "$DB_PATH" <<EOF
ALTER TABLE api_keys ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL;
EOF

    echo "✓ Migration complete!"
fi

echo ""
echo "==========================================="
echo "  Migration Summary"
echo "==========================================="
echo "✓ is_active column added to api_keys table"
echo "✓ Database schema updated"
echo ""
echo "You can now restart the application."
