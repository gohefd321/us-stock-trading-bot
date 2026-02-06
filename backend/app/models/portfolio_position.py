"""
Portfolio Position Model - 포트폴리오 포지션

실시간 포지션 추적 및 관리
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from ..database import Base


class PortfolioPosition(Base):
    """포트폴리오 포지션 모델"""

    __tablename__ = "portfolio_positions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 종목 정보
    ticker = Column(String, nullable=False, unique=True, index=True)  # 종목코드
    ticker_name = Column(String)  # 종목명
    market_type = Column(String, default="US")  # 시장구분
    sector = Column(String)  # 섹터

    # 보유 정보
    quantity = Column(Integer, default=0, nullable=False)  # 보유수량
    avg_buy_price = Column(Float, nullable=False)  # 평균 매수가
    total_invested = Column(Float, nullable=False)  # 총 투자금액

    # 현재 가치
    current_price = Column(Float)  # 현재가
    current_value = Column(Float)  # 현재 평가금액
    unrealized_pnl = Column(Float)  # 미실현 손익
    unrealized_pnl_pct = Column(Float)  # 미실현 수익률 (%)

    # 실현 손익
    realized_pnl = Column(Float, default=0.0)  # 실현 손익
    realized_pnl_pct = Column(Float, default=0.0)  # 실현 수익률 (%)

    # 포트폴리오 비중
    portfolio_weight = Column(Float)  # 포트폴리오 내 비중 (%)
    target_weight = Column(Float)  # 목표 비중 (%)
    weight_deviation = Column(Float)  # 비중 이탈 정도 (%)

    # 리스크 관리
    stop_loss_price = Column(Float)  # 손절가
    take_profit_price = Column(Float)  # 익절가
    trailing_stop_pct = Column(Float)  # 트레일링 스탑 (%)
    max_price_achieved = Column(Float)  # 최고가

    # 전략 정보
    entry_strategy = Column(String)  # 진입 전략
    entry_signal_id = Column(Integer)  # 진입 신호 ID
    entry_date = Column(DateTime(timezone=True))  # 진입 일자
    holding_days = Column(Integer, default=0)  # 보유 일수

    # 리밸런싱
    rebalance_needed = Column(Boolean, default=False)  # 리밸런싱 필요 여부
    target_quantity = Column(Integer)  # 목표 수량 (리밸런싱 시)

    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_price_update = Column(DateTime(timezone=True))  # 마지막 가격 업데이트

    def __repr__(self):
        return f"<PortfolioPosition(ticker='{self.ticker}', quantity={self.quantity}, unrealized_pnl={self.unrealized_pnl:.2f})>"

    def calculate_metrics(self, current_price: float):
        """메트릭 계산"""
        self.current_price = current_price
        self.current_value = self.quantity * current_price
        self.unrealized_pnl = self.current_value - self.total_invested

        if self.total_invested > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl / self.total_invested) * 100

        # 최고가 업데이트
        if not self.max_price_achieved or current_price > self.max_price_achieved:
            self.max_price_achieved = current_price

        # 트레일링 스탑 체크
        if self.trailing_stop_pct and self.max_price_achieved:
            self.stop_loss_price = self.max_price_achieved * (1 - self.trailing_stop_pct / 100)

    def needs_rebalancing(self, tolerance: float = 5.0) -> bool:
        """리밸런싱 필요 여부 (기본 tolerance: 5%)"""
        if not self.target_weight or not self.portfolio_weight:
            return False

        self.weight_deviation = abs(self.portfolio_weight - self.target_weight)
        return self.weight_deviation > tolerance

    def should_stop_loss(self) -> bool:
        """손절 여부"""
        if not self.stop_loss_price or not self.current_price:
            return False
        return self.current_price <= self.stop_loss_price

    def should_take_profit(self) -> bool:
        """익절 여부"""
        if not self.take_profit_price or not self.current_price:
            return False
        return self.current_price >= self.take_profit_price
