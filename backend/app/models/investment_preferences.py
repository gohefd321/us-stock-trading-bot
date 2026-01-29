"""
Investment Preferences Model
Stores user investment preferences extracted from chat conversations
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func

from ..database import Base


class InvestmentPreference(Base):
    """User investment preferences from chat interactions"""
    __tablename__ = "investment_preferences"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Preference categories
    risk_appetite = Column(String, default="moderate", nullable=False)  # conservative, moderate, aggressive
    investment_style = Column(String, default="balanced", nullable=False)  # growth, value, dividend, balanced

    # Sector preferences (JSON-like comma-separated list)
    preferred_sectors = Column(Text, default="", nullable=True)  # e.g., "technology,healthcare,finance"
    avoided_sectors = Column(Text, default="", nullable=True)  # e.g., "energy,utilities"

    # Stock preferences
    preferred_tickers = Column(Text, default="", nullable=True)  # e.g., "AAPL,GOOGL,MSFT"
    avoided_tickers = Column(Text, default="", nullable=True)  # e.g., "TSLA,GME"

    # Investment strategy
    max_single_position_pct = Column(Float, default=20.0, nullable=False)
    prefer_diversification = Column(Boolean, default=True, nullable=False)

    # Market timing preferences
    prefer_dip_buying = Column(Boolean, default=False, nullable=False)
    prefer_momentum = Column(Boolean, default=False, nullable=False)

    # Trading behavior preferences (NEW)
    prefer_day_trading = Column(Boolean, default=False, nullable=False)  # 단타 선호
    prefer_swing_trading = Column(Boolean, default=False, nullable=False)  # 스윙 트레이딩
    prefer_long_term = Column(Boolean, default=True, nullable=False)  # 장기 투자 선호

    # Price range preferences (NEW)
    min_stock_price = Column(Float, default=0.0, nullable=True)  # 최소 주가
    max_stock_price = Column(Float, default=0.0, nullable=True)  # 최대 주가 (0 = 무제한)

    # Investment goals (NEW)
    target_annual_return_pct = Column(Float, default=0.0, nullable=True)  # 목표 수익률 (%)
    investment_goal = Column(Text, default="", nullable=True)  # e.g., "은퇴 자금", "단기 수익", "자산 증식"

    # Loss tolerance (NEW)
    max_acceptable_loss_pct = Column(Float, default=20.0, nullable=False)  # 최대 허용 손실률

    # Additional instructions (free text from chat)
    custom_instructions = Column(Text, default="", nullable=True)

    # Metadata
    last_updated_by_chat = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
