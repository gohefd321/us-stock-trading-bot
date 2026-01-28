"""
Risk Parameters Model
Stores risk management parameters for the trading bot
"""

from sqlalchemy import Column, Integer, Float, DateTime
from sqlalchemy.sql import func

from ..database import Base


class RiskParameter(Base):
    """Risk parameters for trading"""
    __tablename__ = "risk_parameters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    initial_capital_usd = Column(Float, default=1000.0, nullable=False)  # Initial capital in USD
    max_positions = Column(Integer, default=5, nullable=False)
    max_position_size_pct = Column(Float, default=20.0, nullable=False)
    stop_loss_pct = Column(Float, default=10.0, nullable=False)
    take_profit_pct = Column(Float, default=20.0, nullable=False)
    daily_loss_limit_pct = Column(Float, default=20.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
