"""
Market Screener Model

시장 스크리너 데이터 모델
- 시가총액 순위
- 거래량 급증
- 급등락 종목
- 52주 신고가/신저가
"""

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from ..database import Base


class MarketScreener(Base):
    """시장 스크리너 데이터 모델"""

    __tablename__ = "market_screener"

    ticker = Column(String, primary_key=True, index=True)
    market_cap = Column(Float, nullable=True)  # 시가총액
    volume_rank = Column(Integer, nullable=True)  # 거래량 순위
    price_change_pct = Column(Float, nullable=True)  # 가격 변동률 (%)
    volume_change_pct = Column(Float, nullable=True)  # 거래량 변동률 (%)
    is_52w_high = Column(Boolean, default=False)  # 52주 신고가 여부
    is_52w_low = Column(Boolean, default=False)  # 52주 신저가 여부
    avg_volume_10d = Column(Float, nullable=True)  # 10일 평균 거래량
    current_price = Column(Float, nullable=True)  # 현재 가격
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<MarketScreener(ticker={self.ticker}, market_cap={self.market_cap}, price_change_pct={self.price_change_pct})>"
