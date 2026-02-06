"""
Fundamental Data Model

재무 데이터 모델
- EPS (주당순이익)
- P/E Ratio (주가수익비율)
- ROE (자기자본이익률)
- Debt Ratio (부채비율)
- Next Earnings Date (다음 실적 발표일)
"""

from sqlalchemy import Column, String, Float, Date, DateTime, Text
from sqlalchemy.sql import func
from ..database import Base


class FundamentalData(Base):
    """재무 데이터 모델"""

    __tablename__ = "fundamental_data"

    ticker = Column(String, primary_key=True, index=True)

    # Valuation Metrics
    eps = Column(Float, nullable=True)  # Earnings Per Share (주당순이익)
    pe_ratio = Column(Float, nullable=True)  # Price-to-Earnings Ratio
    pb_ratio = Column(Float, nullable=True)  # Price-to-Book Ratio
    market_cap = Column(Float, nullable=True)  # Market Capitalization

    # Profitability Metrics
    roe = Column(Float, nullable=True)  # Return on Equity (%)
    roa = Column(Float, nullable=True)  # Return on Assets (%)
    profit_margin = Column(Float, nullable=True)  # Net Profit Margin (%)

    # Financial Health
    debt_to_equity = Column(Float, nullable=True)  # Debt-to-Equity Ratio
    current_ratio = Column(Float, nullable=True)  # Current Ratio (유동비율)

    # Growth Metrics
    revenue_growth = Column(Float, nullable=True)  # Revenue Growth (%) YoY
    earnings_growth = Column(Float, nullable=True)  # Earnings Growth (%) YoY

    # Dividend Info
    dividend_yield = Column(Float, nullable=True)  # Dividend Yield (%)
    payout_ratio = Column(Float, nullable=True)  # Dividend Payout Ratio (%)

    # Analyst Ratings (from TipRanks or similar)
    analyst_rating = Column(String, nullable=True)  # BUY/HOLD/SELL
    analyst_target_price = Column(Float, nullable=True)  # Consensus target price

    # Earnings Calendar
    next_earnings_date = Column(Date, nullable=True)  # 다음 실적 발표일
    last_earnings_date = Column(Date, nullable=True)  # 최근 실적 발표일

    # Additional Info
    sector = Column(String, nullable=True)  # 섹터
    industry = Column(String, nullable=True)  # 산업
    description = Column(Text, nullable=True)  # 회사 설명

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FundamentalData(ticker={self.ticker}, eps={self.eps}, pe_ratio={self.pe_ratio}, roe={self.roe})>"
