"""
MACD (Moving Average Convergence Divergence) Strategy

MACD 전략
- MACD Line이 Signal Line을 상향 돌파 → BUY
- MACD Line이 Signal Line을 하향 돌파 → SELL
- Histogram 활용: 모멘텀 확인
"""

from typing import Dict, Optional
from datetime import datetime
import pandas as pd

from .base_strategy import BaseStrategy, TradingSignal


class MACDStrategy(BaseStrategy):
    """MACD 전략"""

    def __init__(self, params: Optional[Dict] = None):
        default_params = {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
        }

        if params:
            default_params.update(params)

        super().__init__("MACD", default_params)

    def generate_signal(
        self,
        indicators: Dict,
        price_data: Optional[pd.DataFrame] = None
    ) -> TradingSignal:
        """
        MACD 신호 생성

        Args:
            indicators: 기술적 지표 (macd 포함)
            price_data: OHLCV 데이터 (선택)

        Returns:
            TradingSignal
        """
        try:
            macd_data = indicators.get('macd', {})
            current_price = indicators.get('close_price', 0)
            timestamp = indicators.get('timestamp')

            macd = macd_data.get('macd')
            macd_signal = macd_data.get('signal')
            macd_histogram = macd_data.get('histogram')

            if macd is None or macd_signal is None:
                return TradingSignal(
                    signal_type="HOLD",
                    strength=0.0,
                    price=current_price,
                    timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now(),
                    reason="Insufficient MACD data"
                )

            # MACD 교차 판단
            macd_diff = macd - macd_signal

            # 신호 생성
            if macd > macd_signal and macd_diff > 0:
                # Bullish crossover → BUY
                signal_type = "BUY"
                # Histogram 절대값으로 강도 결정
                strength = self._calculate_signal_strength(abs(macd_histogram) if macd_histogram else 0, 0, 2)
                reason = f"Bullish MACD Crossover: MACD ({macd:.2f}) > Signal ({macd_signal:.2f})"

            elif macd < macd_signal and macd_diff < 0:
                # Bearish crossover → SELL
                signal_type = "SELL"
                strength = self._calculate_signal_strength(abs(macd_histogram) if macd_histogram else 0, 0, 2)
                reason = f"Bearish MACD Crossover: MACD ({macd:.2f}) < Signal ({macd_signal:.2f})"

            else:
                # 중립
                signal_type = "HOLD"
                strength = 0.0
                reason = f"MACD Neutral: Diff ({macd_diff:.2f})"

            return TradingSignal(
                signal_type=signal_type,
                strength=strength,
                price=current_price,
                timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now(),
                reason=reason,
                metadata={
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "macd_histogram": macd_histogram,
                    "macd_diff": macd_diff,
                }
            )

        except Exception as e:
            return TradingSignal(
                signal_type="HOLD",
                strength=0.0,
                price=current_price if 'current_price' in locals() else 0,
                timestamp=datetime.now(),
                reason=f"Error: {str(e)}"
            )

    def get_description(self) -> str:
        return f"MACD Strategy ({self.params['fast_period']}/{self.params['slow_period']}/{self.params['signal_period']})"
