"""
Technical Indicator Model

기술적 지표 데이터 모델
- SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP
- 여러 timeframe 지원 (1m, 5m, 15m, 30m, 1h, 4h, 1d)
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from ..database import Base


class TechnicalIndicator(Base):
    """기술적 지표 데이터"""

    __tablename__ = "technical_indicators"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, nullable=False, index=True)
    timeframe = Column(String, nullable=False, index=True)  # 1m, 5m, 15m, 30m, 1h, 4h, 1d

    # Moving Averages
    sma_10 = Column(Float, nullable=True)
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    sma_100 = Column(Float, nullable=True)
    sma_200 = Column(Float, nullable=True)

    ema_10 = Column(Float, nullable=True)
    ema_20 = Column(Float, nullable=True)
    ema_50 = Column(Float, nullable=True)
    ema_100 = Column(Float, nullable=True)
    ema_200 = Column(Float, nullable=True)

    # RSI (Relative Strength Index)
    rsi_14 = Column(Float, nullable=True)  # 14-period RSI

    # MACD (Moving Average Convergence Divergence)
    macd = Column(Float, nullable=True)  # MACD line
    macd_signal = Column(Float, nullable=True)  # Signal line
    macd_histogram = Column(Float, nullable=True)  # Histogram

    # Bollinger Bands
    bb_upper = Column(Float, nullable=True)  # Upper band
    bb_middle = Column(Float, nullable=True)  # Middle band (SMA 20)
    bb_lower = Column(Float, nullable=True)  # Lower band
    bb_bandwidth = Column(Float, nullable=True)  # Bandwidth
    bb_percent = Column(Float, nullable=True)  # %B (position within bands)

    # ATR (Average True Range)
    atr_14 = Column(Float, nullable=True)  # 14-period ATR

    # VWAP (Volume Weighted Average Price)
    vwap = Column(Float, nullable=True)

    # Stochastic Oscillator
    stoch_k = Column(Float, nullable=True)  # %K
    stoch_d = Column(Float, nullable=True)  # %D

    # ADX (Average Directional Index) - Trend strength
    adx_14 = Column(Float, nullable=True)
    plus_di = Column(Float, nullable=True)  # +DI
    minus_di = Column(Float, nullable=True)  # -DI

    # Volume indicators
    volume_sma_20 = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)  # Current volume / SMA volume

    # Price data (for reference)
    close_price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=True)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Unique constraint: one indicator set per ticker/timeframe/timestamp
    __table_args__ = (
        UniqueConstraint('ticker', 'timeframe', 'timestamp', name='uix_ticker_timeframe_timestamp'),
    )

    def __repr__(self):
        return f"<TechnicalIndicator(ticker={self.ticker}, tf={self.timeframe}, time={self.timestamp})>"
