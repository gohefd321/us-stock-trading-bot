"""
Order Model - 주문 관리

한국투자증권 주문 상태 추적 및 관리
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, Boolean
from sqlalchemy.sql import func
from ..database import Base


class Order(Base):
    """주문 모델 (Order Tracking)"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 주문 식별
    order_number = Column(String, unique=True, index=True, nullable=False)  # KIS 주문번호 (ODNO)
    original_order_number = Column(String, index=True)  # 원주문번호 (정정/취소 시)

    # 종목 정보
    ticker = Column(String, nullable=False, index=True)  # 종목코드
    ticker_name = Column(String)  # 종목명
    market_type = Column(String, default="US", index=True)  # 시장구분 (US, KR)
    exchange = Column(String)  # 거래소 (NASD, NYSE, AMEX, etc.)

    # 주문 정보
    order_type = Column(String, nullable=False, index=True)  # BUY, SELL
    order_method = Column(String, default="MARKET")  # MARKET, LIMIT, STOP_LOSS
    order_quantity = Column(Integer, nullable=False)  # 주문수량
    order_price = Column(Float)  # 주문단가 (지정가)

    # 체결 정보
    filled_quantity = Column(Integer, default=0)  # 체결수량
    avg_filled_price = Column(Float)  # 평균체결가
    filled_amount = Column(Float)  # 체결금액
    commission = Column(Float, default=0.0)  # 수수료

    # 주문 상태
    status = Column(String, default="SUBMITTED", index=True)
    # SUBMITTED: 주문 제출
    # PENDING: 대기 중
    # PARTIAL_FILLED: 부분 체결
    # FILLED: 전량 체결
    # CANCELLED: 취소
    # REJECTED: 거부
    # FAILED: 실패

    # 메타데이터
    signal_id = Column(Integer, index=True)  # 신호 ID (연결된 시그널)
    strategy_name = Column(String)  # 전략명
    reason = Column(String)  # 주문 사유

    # 시간 정보
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    filled_at = Column(DateTime(timezone=True))  # 체결 시각
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # API 응답
    broker_response = Column(String)  # KIS API 응답 (JSON)
    error_message = Column(String)  # 오류 메시지

    # 리스크 관리
    risk_checked = Column(Boolean, default=False)  # 리스크 검증 완료 여부
    position_size_pct = Column(Float)  # 포트폴리오 대비 비중 (%)
    stop_loss_price = Column(Float)  # 손절가
    take_profit_price = Column(Float)  # 익절가

    def __repr__(self):
        return f"<Order(order_number='{self.order_number}', ticker='{self.ticker}', type='{self.order_type}', status='{self.status}')>"

    def is_active(self) -> bool:
        """활성 주문 여부 (체결 가능한 상태)"""
        return self.status in ["SUBMITTED", "PENDING", "PARTIAL_FILLED"]

    def is_completed(self) -> bool:
        """완료된 주문 여부"""
        return self.status in ["FILLED", "CANCELLED", "REJECTED"]

    def fill_rate(self) -> float:
        """체결률 (0.0 ~ 1.0)"""
        if self.order_quantity == 0:
            return 0.0
        return self.filled_quantity / self.order_quantity
