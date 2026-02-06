"""
Phase 2 Database Migration

신규 테이블 추가:
- realtime_prices: 실시간 체결가
- order_books: 호가창 (10호가)
- ohlcv: OHLCV 캔들 데이터
"""

import asyncio
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Phase 2 마이그레이션 실행"""

    db_path = Path(__file__).parent / "data" / "trading_bot.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"🔧 Phase 2 마이그레이션 시작: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # realtime_prices 테이블 생성
        logger.info("💹 Creating realtime_prices table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS realtime_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker VARCHAR NOT NULL,
                current_price FLOAT NOT NULL,
                change_price FLOAT,
                change_rate FLOAT,
                volume BIGINT,
                trade_volume INTEGER,
                high_price FLOAT,
                low_price FLOAT,
                open_price FLOAT,
                market_cap BIGINT,
                trade_time TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ realtime_prices table created")

        # order_books 테이블 생성
        logger.info("📊 Creating order_books table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker VARCHAR NOT NULL,
                ask_price_1 FLOAT, ask_volume_1 BIGINT,
                ask_price_2 FLOAT, ask_volume_2 BIGINT,
                ask_price_3 FLOAT, ask_volume_3 BIGINT,
                ask_price_4 FLOAT, ask_volume_4 BIGINT,
                ask_price_5 FLOAT, ask_volume_5 BIGINT,
                ask_price_6 FLOAT, ask_volume_6 BIGINT,
                ask_price_7 FLOAT, ask_volume_7 BIGINT,
                ask_price_8 FLOAT, ask_volume_8 BIGINT,
                ask_price_9 FLOAT, ask_volume_9 BIGINT,
                ask_price_10 FLOAT, ask_volume_10 BIGINT,
                bid_price_1 FLOAT, bid_volume_1 BIGINT,
                bid_price_2 FLOAT, bid_volume_2 BIGINT,
                bid_price_3 FLOAT, bid_volume_3 BIGINT,
                bid_price_4 FLOAT, bid_volume_4 BIGINT,
                bid_price_5 FLOAT, bid_volume_5 BIGINT,
                bid_price_6 FLOAT, bid_volume_6 BIGINT,
                bid_price_7 FLOAT, bid_volume_7 BIGINT,
                bid_price_8 FLOAT, bid_volume_8 BIGINT,
                bid_price_9 FLOAT, bid_volume_9 BIGINT,
                bid_price_10 FLOAT, bid_volume_10 BIGINT,
                total_ask_volume BIGINT,
                total_bid_volume BIGINT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ order_books table created")

        # ohlcv 테이블 생성
        logger.info("📈 Creating ohlcv table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker VARCHAR NOT NULL,
                timeframe VARCHAR NOT NULL,
                open FLOAT NOT NULL,
                high FLOAT NOT NULL,
                low FLOAT NOT NULL,
                close FLOAT NOT NULL,
                volume BIGINT NOT NULL,
                trade_count INTEGER,
                vwap FLOAT,
                timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ ohlcv table created")

        # 인덱스 생성
        logger.info("📇 Creating indexes...")

        # realtime_prices indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_realtime_ticker ON realtime_prices(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_realtime_time ON realtime_prices(trade_time DESC)")

        # order_books indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orderbook_ticker ON order_books(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orderbook_updated ON order_books(updated_at DESC)")

        # ohlcv indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker ON ohlcv(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_timeframe ON ohlcv(timeframe)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_timestamp ON ohlcv(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_composite ON ohlcv(ticker, timeframe, timestamp DESC)")

        logger.info("✅ Indexes created")

        conn.commit()
        logger.info("✅ Phase 2 마이그레이션 완료!")

        # 테이블 정보 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('realtime_prices', 'order_books', 'ohlcv')")
        tables = cursor.fetchall()
        logger.info(f"✓ Created tables: {[t[0] for t in tables]}")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
