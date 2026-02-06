"""
Real-time Price Data Model

실시간 가격 데이터 (WebSocket)
- 실시간 체결가
- 호가창 (Bid/Ask)
- OHLCV (분봉, 일봉)
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.sql import func
from ..database import Base


class RealtimePrice(Base):
    """실시간 체결가 데이터"""

    __tablename__ = "realtime_prices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, nullable=False, index=True)

    # Price Data
    current_price = Column(Float, nullable=False)  # 현재가
    change_price = Column(Float, nullable=True)  # 전일대비
    change_rate = Column(Float, nullable=True)  # 등락률 (%)

    # Volume
    volume = Column(BigInteger, nullable=True)  # 누적 거래량
    trade_volume = Column(Integer, nullable=True)  # 체결 거래량 (현재 틱)

    # High/Low
    high_price = Column(Float, nullable=True)  # 고가
    low_price = Column(Float, nullable=True)  # 저가
    open_price = Column(Float, nullable=True)  # 시가

    # Market Data
    market_cap = Column(BigInteger, nullable=True)  # 시가총액

    # Timestamp
    trade_time = Column(DateTime(timezone=True), nullable=False, index=True)  # 체결 시간
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<RealtimePrice(ticker={self.ticker}, price={self.current_price}, time={self.trade_time})>"


class OrderBook(Base):
    """호가창 데이터 (Bid/Ask)"""

    __tablename__ = "order_books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, nullable=False, index=True)

    # Ask (매도) - 10호가
    ask_price_1 = Column(Float, nullable=True)
    ask_volume_1 = Column(BigInteger, nullable=True)
    ask_price_2 = Column(Float, nullable=True)
    ask_volume_2 = Column(BigInteger, nullable=True)
    ask_price_3 = Column(Float, nullable=True)
    ask_volume_3 = Column(BigInteger, nullable=True)
    ask_price_4 = Column(Float, nullable=True)
    ask_volume_4 = Column(BigInteger, nullable=True)
    ask_price_5 = Column(Float, nullable=True)
    ask_volume_5 = Column(BigInteger, nullable=True)
    ask_price_6 = Column(Float, nullable=True)
    ask_volume_6 = Column(BigInteger, nullable=True)
    ask_price_7 = Column(Float, nullable=True)
    ask_volume_7 = Column(BigInteger, nullable=True)
    ask_price_8 = Column(Float, nullable=True)
    ask_volume_8 = Column(BigInteger, nullable=True)
    ask_price_9 = Column(Float, nullable=True)
    ask_volume_9 = Column(BigInteger, nullable=True)
    ask_price_10 = Column(Float, nullable=True)
    ask_volume_10 = Column(BigInteger, nullable=True)

    # Bid (매수) - 10호가
    bid_price_1 = Column(Float, nullable=True)
    bid_volume_1 = Column(BigInteger, nullable=True)
    bid_price_2 = Column(Float, nullable=True)
    bid_volume_2 = Column(BigInteger, nullable=True)
    bid_price_3 = Column(Float, nullable=True)
    bid_volume_3 = Column(BigInteger, nullable=True)
    bid_price_4 = Column(Float, nullable=True)
    bid_volume_4 = Column(BigInteger, nullable=True)
    bid_price_5 = Column(Float, nullable=True)
    bid_volume_5 = Column(BigInteger, nullable=True)
    bid_price_6 = Column(Float, nullable=True)
    bid_volume_6 = Column(BigInteger, nullable=True)
    bid_price_7 = Column(Float, nullable=True)
    bid_volume_7 = Column(BigInteger, nullable=True)
    bid_price_8 = Column(Float, nullable=True)
    bid_volume_8 = Column(BigInteger, nullable=True)
    bid_price_9 = Column(Float, nullable=True)
    bid_volume_9 = Column(BigInteger, nullable=True)
    bid_price_10 = Column(Float, nullable=True)
    bid_volume_10 = Column(BigInteger, nullable=True)

    # Total Ask/Bid
    total_ask_volume = Column(BigInteger, nullable=True)  # 총 매도 잔량
    total_bid_volume = Column(BigInteger, nullable=True)  # 총 매수 잔량

    # Timestamp
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)

    def __repr__(self):
        return f"<OrderBook(ticker={self.ticker}, best_ask={self.ask_price_1}, best_bid={self.bid_price_1})>"


class OHLCV(Base):
    """OHLCV 캔들 데이터 (분봉, 일봉)"""

    __tablename__ = "ohlcv"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, nullable=False, index=True)

    # Timeframe: '1m', '5m', '15m', '30m', '1h', '4h', '1d'
    timeframe = Column(String, nullable=False, index=True)

    # OHLCV
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)

    # Additional
    trade_count = Column(Integer, nullable=True)  # 거래 횟수
    vwap = Column(Float, nullable=True)  # Volume Weighted Average Price

    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)  # 캔들 시작 시간
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<OHLCV(ticker={self.ticker}, tf={self.timeframe}, close={self.close}, time={self.timestamp})>"
