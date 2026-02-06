"""
Phase 1.3 Database Migration

신규 테이블 추가:
- news_events: 뉴스 & 이벤트 데이터
"""

import asyncio
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Phase 1.3 마이그레이션 실행"""

    db_path = Path(__file__).parent / "data" / "trading_bot.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"🔧 Phase 1.3 마이그레이션 시작: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # news_events 테이블 생성
        logger.info("📰 Creating news_events table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker VARCHAR NOT NULL,
                event_type VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                summary TEXT,
                url VARCHAR,
                source VARCHAR,
                sentiment FLOAT,
                sentiment_label VARCHAR,
                filing_type VARCHAR,
                filing_date TIMESTAMP,
                published_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ news_events table created")

        # 인덱스 생성
        logger.info("📇 Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_ticker ON news_events(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_type ON news_events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_published ON news_events(published_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_events(sentiment)")
        logger.info("✅ Indexes created")

        conn.commit()
        logger.info("✅ Phase 1.3 마이그레이션 완료!")

        # 테이블 정보 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news_events'")
        result = cursor.fetchone()
        if result:
            logger.info(f"✓ Table 'news_events' exists")
        else:
            logger.error("✗ Table 'news_events' not found")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
