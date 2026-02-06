"""
RSI (Relative Strength Index) Strategy

RSI 과매수/과매도 전략
- RSI < 30: 과매도 → BUY
- RSI > 70: 과매수 → SELL
- 30 < RSI < 70: HOLD
"""

from typing import Dict, Optional
from datetime import datetime
import pandas as pd

from .base_strategy import BaseStrategy, TradingSignal


class RSIStrategy(BaseStrategy):
    """RSI 전략"""

    def __init__(self, params: Optional[Dict] = None):
        default_params = {
            "oversold_threshold": 30,  # 과매도 기준
            "overbought_threshold": 70,  # 과매수 기준
            "period": 14,  # RSI 기간
        }

        if params:
            default_params.update(params)

        super().__init__("RSI", default_params)

    def generate_signal(
        self,
        indicators: Dict,
        price_data: Optional[pd.DataFrame] = None
    ) -> TradingSignal:
        """
        RSI 신호 생성

        Args:
            indicators: 기술적 지표 (rsi 포함)
            price_data: OHLCV 데이터 (선택)

        Returns:
            TradingSignal
        """
        try:
            rsi = indicators.get('rsi')
            current_price = indicators.get('close_price', 0)
            timestamp = indicators.get('timestamp')

            if rsi is None:
                return TradingSignal(
                    signal_type="HOLD",
                    strength=0.0,
                    price=current_price,
                    timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now(),
                    reason="No RSI data available"
                )

            oversold = self.params['oversold_threshold']
            overbought = self.params['overbought_threshold']

            # 신호 생성
            if rsi < oversold:
                # 과매도 → BUY
                signal_type = "BUY"
                # RSI가 낮을수록 강한 매수 신호
                strength = self._calculate_signal_strength(oversold - rsi, 0, oversold)
                reason = f"Oversold: RSI ({rsi:.1f}) < {oversold}"

            elif rsi > overbought:
                # 과매수 → SELL
                signal_type = "SELL"
                # RSI가 높을수록 강한 매도 신호
                strength = self._calculate_signal_strength(rsi - overbought, 0, 100 - overbought)
                reason = f"Overbought: RSI ({rsi:.1f}) > {overbought}"

            else:
                # 중립
                signal_type = "HOLD"
                strength = 0.0
                reason = f"Neutral: RSI ({rsi:.1f}) in range [{oversold}, {overbought}]"

            return TradingSignal(
                signal_type=signal_type,
                strength=strength,
                price=current_price,
                timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now(),
                reason=reason,
                metadata={
                    "rsi": rsi,
                    "oversold_threshold": oversold,
                    "overbought_threshold": overbought,
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
        return f"RSI Strategy (Oversold: {self.params['oversold_threshold']}, Overbought: {self.params['overbought_threshold']})"
