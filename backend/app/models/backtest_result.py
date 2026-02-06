"""
Backtest Result Model

백테스팅 결과 저장 모델
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.sql import func
from ..database import Base


class BacktestResult(Base):
    """백테스팅 결과"""

    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, nullable=False, index=True)
    strategy_name = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False)

    # Test Period
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)

    # Performance Metrics
    total_return = Column(Float, nullable=True)  # 총 수익률 (%)
    sharpe_ratio = Column(Float, nullable=True)  # 샤프 비율
    max_drawdown = Column(Float, nullable=True)  # 최대 낙폭 (%)
    win_rate = Column(Float, nullable=True)  # 승률 (%)
    profit_factor = Column(Float, nullable=True)  # 손익비

    # Trade Statistics
    total_trades = Column(Integer, nullable=True)  # 총 거래 수
    winning_trades = Column(Integer, nullable=True)  # 승리 거래 수
    losing_trades = Column(Integer, nullable=True)  # 손실 거래 수
    avg_win = Column(Float, nullable=True)  # 평균 승리 금액 (%)
    avg_loss = Column(Float, nullable=True)  # 평균 손실 금액 (%)

    # Initial/Final
    initial_capital = Column(Float, nullable=True)  # 초기 자본
    final_capital = Column(Float, nullable=True)  # 최종 자본

    # Strategy Parameters
    strategy_params = Column(JSON, nullable=True)  # 전략 파라미터

    # Trade Log (JSON)
    trade_log = Column(JSON, nullable=True)  # 거래 로그

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<BacktestResult(ticker={self.ticker}, strategy={self.strategy_name}, return={self.total_return}%)>"
