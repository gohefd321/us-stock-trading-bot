"""
Database migration script to add new columns to investment_preferences table
Run this script once to update the database schema
"""

import asyncio
import sqlite3
from pathlib import Path


async def migrate_investment_preferences():
    """Add new columns to investment_preferences table"""

    # Path to database
    db_path = Path(__file__).parent / "data" / "trading_bot.db"

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return

    print(f"📂 Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='investment_preferences'
    """)

    if not cursor.fetchone():
        print("❌ investment_preferences table does not exist")
        conn.close()
        return

    print("✅ Found investment_preferences table")

    # Get existing columns
    cursor.execute("PRAGMA table_info(investment_preferences)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"📋 Existing columns: {existing_columns}")

    # Define new columns to add
    new_columns = {
        'prefer_day_trading': 'INTEGER DEFAULT 0 NOT NULL',
        'prefer_swing_trading': 'INTEGER DEFAULT 0 NOT NULL',
        'prefer_long_term': 'INTEGER DEFAULT 1 NOT NULL',
        'min_stock_price': 'REAL DEFAULT 0.0',
        'max_stock_price': 'REAL DEFAULT 0.0',
        'target_annual_return_pct': 'REAL DEFAULT 0.0',
        'investment_goal': 'TEXT DEFAULT ""',
        'max_acceptable_loss_pct': 'REAL DEFAULT 20.0 NOT NULL'
    }

    # Add missing columns
    added_count = 0
    for column_name, column_type in new_columns.items():
        if column_name not in existing_columns:
            try:
                sql = f"ALTER TABLE investment_preferences ADD COLUMN {column_name} {column_type}"
                print(f"➕ Adding column: {column_name}")
                cursor.execute(sql)
                added_count += 1
            except sqlite3.OperationalError as e:
                print(f"⚠️  Warning adding {column_name}: {e}")
        else:
            print(f"✓ Column {column_name} already exists")

    conn.commit()
    conn.close()

    if added_count > 0:
        print(f"\n✅ Successfully added {added_count} new columns to investment_preferences table")
    else:
        print("\n✅ All columns already exist, no changes needed")


if __name__ == "__main__":
    asyncio.run(migrate_investment_preferences())
