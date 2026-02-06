"""
Bollinger Bands Breakout Strategy

볼린저 밴드 돌파 전략
- Price < Lower Band: 과매도 → BUY
- Price > Upper Band: 과매수 → SELL
- %B 활용: 밴드 내 가격 위치
"""

from typing import Dict, Optional
from datetime import datetime
import pandas as pd

from .base_strategy import BaseStrategy, TradingSignal


class BollingerStrategy(BaseStrategy):
    """볼린저 밴드 전략"""

    def __init__(self, params: Optional[Dict] = None):
        default_params = {
            "period": 20,  # 볼린저 밴드 기간
            "std": 2,  # 표준편차 배수
            "breakout_threshold": 0.1,  # 돌파 기준 (%)
        }

        if params:
            default_params.update(params)

        super().__init__("Bollinger_Bands", default_params)

    def generate_signal(
        self,
        indicators: Dict,
        price_data: Optional[pd.DataFrame] = None
    ) -> TradingSignal:
        """
        볼린저 밴드 신호 생성

        Args:
            indicators: 기술적 지표 (bollinger 포함)
            price_data: OHLCV 데이터 (선택)

        Returns:
            TradingSignal
        """
        try:
            bollinger = indicators.get('bollinger', {})
            current_price = indicators.get('close_price', 0)
            timestamp = indicators.get('timestamp')

            bb_upper = bollinger.get('upper')
            bb_middle = bollinger.get('middle')
            bb_lower = bollinger.get('lower')
            bb_percent = bollinger.get('percent')  # %B

            if not all([bb_upper, bb_middle, bb_lower]):
                return TradingSignal(
                    signal_type="HOLD",
                    strength=0.0,
                    price=current_price,
                    timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now(),
                    reason="Insufficient Bollinger Bands data"
                )

            # 밴드폭 계산
            bb_range = bb_upper - bb_lower
            threshold_pct = self.params['breakout_threshold']

            # 신호 생성
            if current_price < bb_lower:
                # 하단 밴드 이탈 (과매도) → BUY
                signal_type = "BUY"
                # 이탈 정도에 따라 강도 결정
                deviation = ((bb_lower - current_price) / bb_range) * 100
                strength = self._calculate_signal_strength(deviation, 0, 10)
                reason = f"Below Lower Band: Price ({current_price:.2f}) < Lower ({bb_lower:.2f})"

            elif current_price > bb_upper:
                # 상단 밴드 이탈 (과매수) → SELL
                signal_type = "SELL"
                deviation = ((current_price - bb_upper) / bb_range) * 100
                strength = self._calculate_signal_strength(deviation, 0, 10)
                reason = f"Above Upper Band: Price ({current_price:.2f}) > Upper ({bb_upper:.2f})"

            elif bb_percent is not None:
                # %B 기반 판단 (밴드 내)
                if bb_percent < 0.2:
                    # 하단 근처 → 약한 BUY
                    signal_type = "BUY"
                    strength = self._calculate_signal_strength(0.2 - bb_percent, 0, 0.2)
                    reason = f"Near Lower Band: %B ({bb_percent:.2f})"

                elif bb_percent > 0.8:
                    # 상단 근처 → 약한 SELL
                    signal_type = "SELL"
                    strength = self._calculate_signal_strength(bb_percent - 0.8, 0, 0.2)
                    reason = f"Near Upper Band: %B ({bb_percent:.2f})"

                else:
                    # 중립
                    signal_type = "HOLD"
                    strength = 0.0
                    reason = f"Within Bands: %B ({bb_percent:.2f})"

            else:
                signal_type = "HOLD"
                strength = 0.0
                reason = "Neutral"

            return TradingSignal(
                signal_type=signal_type,
                strength=strength,
                price=current_price,
                timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now(),
                reason=reason,
                metadata={
                    "bb_upper": bb_upper,
                    "bb_middle": bb_middle,
                    "bb_lower": bb_lower,
                    "bb_percent": bb_percent,
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
        return f"Bollinger Bands Strategy (Period: {self.params['period']}, Std: {self.params['std']})"
