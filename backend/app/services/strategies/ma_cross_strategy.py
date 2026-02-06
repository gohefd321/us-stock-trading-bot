"""
Moving Average Crossover Strategy

이동평균 교차 전략
- Golden Cross: 단기 MA가 장기 MA를 상향 돌파 → BUY
- Death Cross: 단기 MA가 장기 MA를 하향 돌파 → SELL
"""

from typing import Dict, Optional
from datetime import datetime
import pandas as pd

from .base_strategy import BaseStrategy, TradingSignal


class MACrossStrategy(BaseStrategy):
    """이동평균 교차 전략"""

    def __init__(self, params: Optional[Dict] = None):
        default_params = {
            "fast_period": 20,  # 단기 MA
            "slow_period": 50,  # 장기 MA
            "ma_type": "EMA",  # SMA 또는 EMA
        }

        if params:
            default_params.update(params)

        super().__init__("MA_Cross", default_params)

    def generate_signal(
        self,
        indicators: Dict,
        price_data: Optional[pd.DataFrame] = None
    ) -> TradingSignal:
        """
        이동평균 교차 신호 생성

        Args:
            indicators: 기술적 지표 (moving_averages 포함)
            price_data: OHLCV 데이터 (선택)

        Returns:
            TradingSignal
        """
        try:
            ma_data = indicators.get('moving_averages', {})
            current_price = indicators.get('close_price', 0)
            timestamp = indicators.get('timestamp')

            # MA 타입에 따라 선택
            ma_prefix = self.params['ma_type'].lower()
            fast_ma = ma_data.get(f"{ma_prefix}_{self.params['fast_period']}")
            slow_ma = ma_data.get(f"{ma_prefix}_{self.params['slow_period']}")

            if fast_ma is None or slow_ma is None:
                return TradingSignal(
                    signal_type="HOLD",
                    strength=0.0,
                    price=current_price,
                    timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now(),
                    reason="Insufficient MA data"
                )

            # 교차 비율 계산
            ma_diff = fast_ma - slow_ma
            ma_diff_pct = (ma_diff / slow_ma) * 100

            # 신호 생성
            if ma_diff > 0:
                # Golden Cross (상승 추세)
                signal_type = "BUY"
                strength = self._calculate_signal_strength(ma_diff_pct, 0, 5)
                reason = f"Golden Cross: {ma_prefix.upper()}{self.params['fast_period']} ({fast_ma:.2f}) > {ma_prefix.upper()}{self.params['slow_period']} ({slow_ma:.2f})"

            elif ma_diff < 0:
                # Death Cross (하락 추세)
                signal_type = "SELL"
                strength = self._calculate_signal_strength(abs(ma_diff_pct), 0, 5)
                reason = f"Death Cross: {ma_prefix.upper()}{self.params['fast_period']} ({fast_ma:.2f}) < {ma_prefix.upper()}{self.params['slow_period']} ({slow_ma:.2f})"

            else:
                signal_type = "HOLD"
                strength = 0.0
                reason = "MA Neutral"

            return TradingSignal(
                signal_type=signal_type,
                strength=strength,
                price=current_price,
                timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now(),
                reason=reason,
                metadata={
                    "fast_ma": fast_ma,
                    "slow_ma": slow_ma,
                    "ma_diff_pct": ma_diff_pct,
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
        return f"MA Crossover Strategy ({self.params['ma_type']}{self.params['fast_period']}/{self.params['slow_period']})"
