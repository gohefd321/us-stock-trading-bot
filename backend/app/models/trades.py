"""
Trades Model
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Trade(Base):
    """Model for storing trade execution records"""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trade_id = Column(String, unique=True, index=True)  # Broker's trade ID
    ticker = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # 'BUY' or 'SELL'
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)  # In KRW
    order_type = Column(String, default='MARKET')  # 'MARKET' or 'LIMIT'
    status = Column(String, default='PENDING', index=True)  # PENDING/FILLED/CANCELLED/FAILED
    executed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    broker_response = Column(String)  # JSON response from broker
    llm_decision_id = Column(Integer, ForeignKey('llm_decisions.id'))

    # Relationship to LLM decision
    llm_decision = relationship("LLMDecision", back_populates="trades")

    def __repr__(self):
        return f"<Trade(ticker='{self.ticker}', action='{self.action}', quantity={self.quantity}, status='{self.status}')>"
