"""
News & Events Model

뉴스 및 이벤트 데이터 모델
- 뉴스 (Google News, Yahoo Finance)
- SEC Filings (8-K, 10-Q, 10-K)
- 이벤트 (어닝콜, M&A, 배당 등)
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from ..database import Base


class NewsEvent(Base):
    """뉴스 & 이벤트 데이터 모델"""

    __tablename__ = "news_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, nullable=False, index=True)  # 관련 종목

    # Event Type: 'news', 'sec_filing', 'earnings', 'dividend', 'merger', 'split'
    event_type = Column(String, nullable=False, index=True)

    # News/Event Details
    title = Column(String, nullable=False)  # 제목
    summary = Column(Text, nullable=True)  # 요약
    url = Column(String, nullable=True)  # 뉴스 링크
    source = Column(String, nullable=True)  # 출처 (Bloomberg, Reuters, SEC, etc.)

    # Sentiment Analysis
    sentiment = Column(Float, nullable=True)  # 감정 점수 (-1.0 to 1.0)
    sentiment_label = Column(String, nullable=True)  # POSITIVE/NEUTRAL/NEGATIVE

    # SEC Filings Specific
    filing_type = Column(String, nullable=True)  # 8-K, 10-Q, 10-K, etc.
    filing_date = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)  # 발행일
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<NewsEvent(ticker={self.ticker}, type={self.event_type}, title={self.title[:30]})>"
