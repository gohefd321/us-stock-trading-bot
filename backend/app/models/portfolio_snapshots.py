"""
Portfolio Snapshots Model
"""

from sqlalchemy import Column, Integer, Float, Date, String, DateTime
from sqlalchemy.sql import func
from ..database import Base


class PortfolioSnapshot(Base):
    """Model for storing daily portfolio snapshots"""

    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False, unique=True, index=True)
    cash_balance = Column(Float, nullable=False)
    total_holdings_value = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    daily_pnl = Column(Float)
    daily_pnl_pct = Column(Float)
    total_pnl = Column(Float)
    total_pnl_pct = Column(Float)
    holdings_json = Column(String, nullable=False)  # JSON of all positions
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PortfolioSnapshot(date='{self.snapshot_date}', total_value={self.total_value})>"
