"""
Phase 1.2 Database Migration

신규 테이블 추가:
- fundamental_data: 재무 데이터 (EPS, P/E, ROE, 부채비율 등)
"""

import asyncio
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Phase 1.2 마이그레이션 실행"""

    db_path = Path(__file__).parent / "data" / "trading_bot.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"🔧 Phase 1.2 마이그레이션 시작: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # fundamental_data 테이블 생성
        logger.info("📊 Creating fundamental_data table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fundamental_data (
                ticker VARCHAR PRIMARY KEY,
                eps FLOAT,
                pe_ratio FLOAT,
                pb_ratio FLOAT,
                market_cap FLOAT,
                roe FLOAT,
                roa FLOAT,
                profit_margin FLOAT,
                debt_to_equity FLOAT,
                current_ratio FLOAT,
                revenue_growth FLOAT,
                earnings_growth FLOAT,
                dividend_yield FLOAT,
                payout_ratio FLOAT,
                analyst_rating VARCHAR,
                analyst_target_price FLOAT,
                next_earnings_date DATE,
                last_earnings_date DATE,
                sector VARCHAR,
                industry VARCHAR,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ fundamental_data table created")

        # 인덱스 생성
        logger.info("📇 Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamental_pe ON fundamental_data(pe_ratio)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamental_roe ON fundamental_data(roe DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamental_sector ON fundamental_data(sector)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamental_earnings_date ON fundamental_data(next_earnings_date)")
        logger.info("✅ Indexes created")

        conn.commit()
        logger.info("✅ Phase 1.2 마이그레이션 완료!")

        # 테이블 정보 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fundamental_data'")
        result = cursor.fetchone()
        if result:
            logger.info(f"✓ Table 'fundamental_data' exists")
        else:
            logger.error("✗ Table 'fundamental_data' not found")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
