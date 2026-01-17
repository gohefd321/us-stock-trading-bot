"""
Signals Model
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.sql import func
from ..database import Base


class Signal(Base):
    """Model for storing market signals from various sources"""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False, index=True)  # WSB/YAHOO/TIPRANKS
    signal_type = Column(String, nullable=False)  # SENTIMENT/NEWS/ANALYST_RATING/PRICE_ALERT
    signal_data = Column(String, nullable=False)  # JSON data specific to signal type
    sentiment_score = Column(Float)  # -1 to 1
    strength = Column(Float)  # 0 to 1
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)

    def __repr__(self):
        return f"<Signal(ticker='{self.ticker}', source='{self.source}', type='{self.signal_type}')>"
