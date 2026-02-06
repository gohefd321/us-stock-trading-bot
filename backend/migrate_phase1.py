"""
Phase 1 Database Migration

신규 테이블 추가:
1. market_screener - 시장 스크리너 데이터
2. fundamental_data - 재무 데이터 (추후 추가)
3. news_events - 뉴스 & 이벤트 (추후 추가)
"""

import asyncio
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Phase 1 마이그레이션 실행"""

    db_path = Path(__file__).parent / "data" / "trading_bot.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"🔧 Phase 1 마이그레이션 시작: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. market_screener 테이블 생성
        logger.info("📊 Creating market_screener table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_screener (
                ticker VARCHAR PRIMARY KEY,
                market_cap FLOAT,
                volume_rank INTEGER,
                price_change_pct FLOAT,
                volume_change_pct FLOAT,
                is_52w_high BOOLEAN DEFAULT 0,
                is_52w_low BOOLEAN DEFAULT 0,
                avg_volume_10d FLOAT,
                current_price FLOAT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ market_screener table created")

        # 인덱스 생성
        logger.info("📇 Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_cap ON market_screener(market_cap DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_volume_rank ON market_screener(volume_rank ASC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_change ON market_screener(price_change_pct DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_52w_high ON market_screener(is_52w_high)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_52w_low ON market_screener(is_52w_low)")
        logger.info("✅ Indexes created")

        conn.commit()
        logger.info("✅ Phase 1 마이그레이션 완료!")

        # 테이블 정보 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='market_screener'")
        result = cursor.fetchone()
        if result:
            logger.info(f"✓ Table 'market_screener' exists")
        else:
            logger.error("✗ Table 'market_screener' not found")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
