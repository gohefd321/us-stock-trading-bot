"""
Phase 3.3 Database Migration - Backtest Results
"""

import asyncio
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Phase 3.3 백테스팅 마이그레이션"""

    db_path = Path(__file__).parent / "data" / "trading_bot.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        logger.info("📊 Creating backtest_results table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker VARCHAR NOT NULL,
                strategy_name VARCHAR NOT NULL,
                timeframe VARCHAR NOT NULL,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                total_return FLOAT,
                sharpe_ratio FLOAT,
                max_drawdown FLOAT,
                win_rate FLOAT,
                profit_factor FLOAT,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                avg_win FLOAT,
                avg_loss FLOAT,
                initial_capital FLOAT,
                final_capital FLOAT,
                strategy_params JSON,
                trade_log JSON,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_backtest_ticker ON backtest_results(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_backtest_strategy ON backtest_results(strategy_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_backtest_created ON backtest_results(created_at DESC)")
        
        conn.commit()
        logger.info("✅ Phase 3.3 마이그레이션 완료!")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
