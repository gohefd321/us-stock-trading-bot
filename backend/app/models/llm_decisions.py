"""
LLM Decisions Model
"""

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class LLMDecision(Base):
    """Model for storing AI decision logs"""

    __tablename__ = "llm_decisions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    decision_type = Column(String, nullable=False, index=True)  # PRE_MARKET/MID_SESSION/PRE_CLOSE/CHAT_QUERY
    prompt = Column(String, nullable=False)
    response = Column(String, nullable=False)
    reasoning = Column(String)  # Extracted reasoning from LLM
    confidence_score = Column(Float)  # 0-1 confidence score
    function_calls = Column(String)  # JSON array of function calls made
    signals_used = Column(String)  # JSON of signals that influenced decision
    portfolio_state = Column(String)  # JSON snapshot of portfolio at decision time
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    execution_time_ms = Column(Integer)

    # Relationship to trades
    trades = relationship("Trade", back_populates="llm_decision")

    def __repr__(self):
        return f"<LLMDecision(type='{self.decision_type}', created_at='{self.created_at}')>"
