"""
Strategy Engine Service

전략 엔진 서비스
- 여러 전략 동시 실행
- 신호 통합 및 가중 평균
- 최종 매매 신호 생성
"""

import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .strategies import (
    BaseStrategy,
    TradingSignal,
    MACrossStrategy,
    RSIStrategy,
    BollingerStrategy,
    MACDStrategy,
    VWAPStrategy,
)
from .technical_indicator_service import TechnicalIndicatorService

logger = logging.getLogger(__name__)


class StrategyEngine:
    """전략 엔진"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.indicator_service = TechnicalIndicatorService(db)

        # 사용 가능한 전략들
        self.available_strategies = {
            "MA_CROSS": MACrossStrategy,
            "RSI": RSIStrategy,
            "BOLLINGER": BollingerStrategy,
            "MACD": MACDStrategy,
            "VWAP": VWAPStrategy,
        }

        # 활성화된 전략들
        self.active_strategies: List[BaseStrategy] = []

    def add_strategy(
        self,
        strategy_name: str,
        params: Optional[Dict] = None
    ) -> bool:
        """
        전략 추가

        Args:
            strategy_name: 전략 이름 (MA_CROSS, RSI, etc.)
            params: 전략 파라미터

        Returns:
            성공 여부
        """
        try:
            if strategy_name not in self.available_strategies:
                logger.error(f"Unknown strategy: {strategy_name}")
                return False

            strategy_class = self.available_strategies[strategy_name]
            strategy = strategy_class(params)

            self.active_strategies.append(strategy)
            logger.info(f"Added strategy: {strategy.get_description()}")

            return True

        except Exception as e:
            logger.error(f"Failed to add strategy {strategy_name}: {e}")
            return False

    def remove_strategy(self, strategy_name: str) -> bool:
        """
        전략 제거

        Args:
            strategy_name: 전략 이름

        Returns:
            성공 여부
        """
        try:
            self.active_strategies = [
                s for s in self.active_strategies
                if s.get_name() != strategy_name
            ]
            logger.info(f"Removed strategy: {strategy_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove strategy {strategy_name}: {e}")
            return False

    def clear_strategies(self):
        """모든 전략 제거"""
        self.active_strategies = []
        logger.info("Cleared all strategies")

    async def generate_combined_signal(
        self,
        ticker: str,
        timeframe: str = '1h',
        weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        여러 전략의 신호를 통합하여 최종 신호 생성

        Args:
            ticker: 종목 코드
            timeframe: 시간 프레임
            weights: 전략별 가중치 (기본값: 동일 가중)

        Returns:
            통합 신호 결과
        """
        try:
            if not self.active_strategies:
                return {
                    "success": False,
                    "error": "No active strategies"
                }

            # 기술적 지표 조회
            indicators = await self.indicator_service.get_latest_indicators(ticker, timeframe)

            if not indicators:
                return {
                    "success": False,
                    "error": "No indicator data available"
                }

            # 각 전략에서 신호 생성
            signals = []
            for strategy in self.active_strategies:
                signal = strategy.generate_signal(indicators)
                signals.append({
                    "strategy": strategy.get_name(),
                    "signal": signal.to_dict(),
                })

            # 신호 통합 (가중 평균)
            combined_signal = self._combine_signals(signals, weights)

            return {
                "success": True,
                "ticker": ticker,
                "timeframe": timeframe,
                "individual_signals": signals,
                "combined_signal": combined_signal,
                "active_strategies": [s.get_name() for s in self.active_strategies],
            }

        except Exception as e:
            logger.error(f"Failed to generate combined signal: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _combine_signals(
        self,
        signals: List[Dict],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        여러 신호를 통합

        Args:
            signals: 전략별 신호 리스트
            weights: 전략별 가중치

        Returns:
            통합 신호
        """
        if not signals:
            return {
                "signal_type": "HOLD",
                "strength": 0.0,
                "confidence": 0.0,
            }

        # 기본 가중치: 동일
        if weights is None:
            weights = {s['strategy']: 1.0 for s in signals}

        # 정규화된 가중치
        total_weight = sum(weights.values())
        normalized_weights = {k: v / total_weight for k, v in weights.items()}

        # 신호 타입별 가중 점수 계산
        buy_score = 0.0
        sell_score = 0.0
        hold_score = 0.0

        for signal_data in signals:
            strategy_name = signal_data['strategy']
            signal = signal_data['signal']
            weight = normalized_weights.get(strategy_name, 0.0)

            signal_type = signal['signal_type']
            strength = signal['strength']

            if signal_type == 'BUY':
                buy_score += strength * weight
            elif signal_type == 'SELL':
                sell_score += strength * weight
            else:  # HOLD
                hold_score += weight

        # 최종 신호 결정
        max_score = max(buy_score, sell_score, hold_score)

        if max_score == buy_score and buy_score > 0.3:
            final_signal = "BUY"
            final_strength = buy_score
        elif max_score == sell_score and sell_score > 0.3:
            final_signal = "SELL"
            final_strength = sell_score
        else:
            final_signal = "HOLD"
            final_strength = 0.0

        # 신뢰도: 동의하는 전략의 비율
        agreement_count = sum(
            1 for s in signals
            if s['signal']['signal_type'] == final_signal
        )
        confidence = agreement_count / len(signals) if signals else 0.0

        return {
            "signal_type": final_signal,
            "strength": final_strength,
            "confidence": confidence,
            "buy_score": buy_score,
            "sell_score": sell_score,
            "hold_score": hold_score,
        }

    def get_active_strategies(self) -> List[Dict]:
        """활성화된 전략 목록 조회"""
        return [
            {
                "name": s.get_name(),
                "description": s.get_description(),
                "params": s.get_params(),
            }
            for s in self.active_strategies
        ]

    def get_available_strategies(self) -> List[str]:
        """사용 가능한 전략 목록"""
        return list(self.available_strategies.keys())
