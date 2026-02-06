"""
Phase 3 Database Migration

신규 테이블 추가:
- technical_indicators: 기술적 지표 (SMA, EMA, RSI, MACD, Bollinger, ATR, VWAP, etc.)
"""

import asyncio
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Phase 3 마이그레이션 실행"""

    db_path = Path(__file__).parent / "data" / "trading_bot.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"🔧 Phase 3 마이그레이션 시작: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # technical_indicators 테이블 생성
        logger.info("📊 Creating technical_indicators table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker VARCHAR NOT NULL,
                timeframe VARCHAR NOT NULL,
                sma_10 FLOAT,
                sma_20 FLOAT,
                sma_50 FLOAT,
                sma_100 FLOAT,
                sma_200 FLOAT,
                ema_10 FLOAT,
                ema_20 FLOAT,
                ema_50 FLOAT,
                ema_100 FLOAT,
                ema_200 FLOAT,
                rsi_14 FLOAT,
                macd FLOAT,
                macd_signal FLOAT,
                macd_histogram FLOAT,
                bb_upper FLOAT,
                bb_middle FLOAT,
                bb_lower FLOAT,
                bb_bandwidth FLOAT,
                bb_percent FLOAT,
                atr_14 FLOAT,
                vwap FLOAT,
                stoch_k FLOAT,
                stoch_d FLOAT,
                adx_14 FLOAT,
                plus_di FLOAT,
                minus_di FLOAT,
                volume_sma_20 FLOAT,
                volume_ratio FLOAT,
                close_price FLOAT NOT NULL,
                volume INTEGER,
                timestamp TIMESTAMP NOT NULL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, timeframe, timestamp)
            )
        """)
        logger.info("✅ technical_indicators table created")

        # 인덱스 생성
        logger.info("📇 Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tech_ticker ON technical_indicators(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tech_timeframe ON technical_indicators(timeframe)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tech_timestamp ON technical_indicators(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tech_composite ON technical_indicators(ticker, timeframe, timestamp DESC)")
        logger.info("✅ Indexes created")

        conn.commit()
        logger.info("✅ Phase 3 마이그레이션 완료!")

        # 테이블 정보 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='technical_indicators'")
        result = cursor.fetchone()
        if result:
            logger.info(f"✓ Table 'technical_indicators' exists")
        else:
            logger.error("✗ Table 'technical_indicators' not found")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
