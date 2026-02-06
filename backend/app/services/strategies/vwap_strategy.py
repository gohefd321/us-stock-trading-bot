"""
VWAP (Volume Weighted Average Price) Mean Reversion Strategy

VWAP 평균 회귀 전략
- Price < VWAP: 저평가 → BUY
- Price > VWAP: 고평가 → SELL
- 거래량 가중 평균가격 기준
"""

from typing import Dict, Optional
from datetime import datetime
import pandas as pd

from .base_strategy import BaseStrategy, TradingSignal


class VWAPStrategy(BaseStrategy):
    """VWAP 평균 회귀 전략"""

    def __init__(self, params: Optional[Dict] = None):
        default_params = {
            "deviation_threshold": 1.0,  # VWAP 대비 편차 기준 (%)
            "volume_threshold": 1.5,  # 평균 거래량 대비 배수
        }

        if params:
            default_params.update(params)

        super().__init__("VWAP_MeanReversion", default_params)

    def generate_signal(
        self,
        indicators: Dict,
        price_data: Optional[pd.DataFrame] = None
    ) -> TradingSignal:
        """
        VWAP 신호 생성

        Args:
            indicators: 기술적 지표 (vwap, volume 포함)
            price_data: OHLCV 데이터 (선택)

        Returns:
            TradingSignal
        """
        try:
            vwap = indicators.get('vwap')
            current_price = indicators.get('close_price', 0)
            timestamp = indicators.get('timestamp')

            volume_data = indicators.get('volume', {})
            current_volume = volume_data.get('current')
            volume_ratio = volume_data.get('ratio')

            if vwap is None:
                return TradingSignal(
                    signal_type="HOLD",
                    strength=0.0,
                    price=current_price,
                    timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now(),
                    reason="No VWAP data available"
                )

            # VWAP 대비 편차 계산
            deviation_pct = ((current_price - vwap) / vwap) * 100
            threshold = self.params['deviation_threshold']

            # 거래량 확인 (거래량이 충분해야 신호 유효)
            volume_sufficient = (
                volume_ratio is None or
                volume_ratio >= self.params['volume_threshold']
            )

            # 신호 생성
            if deviation_pct < -threshold:
                # Price < VWAP (저평가) → BUY
                signal_type = "BUY"
                # 편차가 클수록 강한 신호
                strength = self._calculate_signal_strength(abs(deviation_pct), threshold, threshold * 3)

                if not volume_sufficient:
                    strength *= 0.5  # 거래량 부족 시 강도 감소

                reason = f"Below VWAP: Price ({current_price:.2f}) < VWAP ({vwap:.2f}) by {abs(deviation_pct):.1f}%"

            elif deviation_pct > threshold:
                # Price > VWAP (고평가) → SELL
                signal_type = "SELL"
                strength = self._calculate_signal_strength(deviation_pct, threshold, threshold * 3)

                if not volume_sufficient:
                    strength *= 0.5

                reason = f"Above VWAP: Price ({current_price:.2f}) > VWAP ({vwap:.2f}) by {deviation_pct:.1f}%"

            else:
                # VWAP 근처 → HOLD
                signal_type = "HOLD"
                strength = 0.0
                reason = f"Near VWAP: Deviation ({deviation_pct:.1f}%) within threshold (±{threshold}%)"

            return TradingSignal(
                signal_type=signal_type,
                strength=strength,
                price=current_price,
                timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now(),
                reason=reason,
                metadata={
                    "vwap": vwap,
                    "deviation_pct": deviation_pct,
                    "volume_ratio": volume_ratio,
                    "volume_sufficient": volume_sufficient,
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
        return f"VWAP Mean Reversion Strategy (Deviation: ±{self.params['deviation_threshold']}%)"
