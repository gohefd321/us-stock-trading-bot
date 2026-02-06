"""
Base Strategy Class

모든 트레이딩 전략의 기본 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd


class TradingSignal:
    """트레이딩 신호"""

    def __init__(
        self,
        signal_type: str,  # 'BUY', 'SELL', 'HOLD'
        strength: float,  # 신호 강도 (0.0 - 1.0)
        price: float,  # 신호 발생 가격
        timestamp: datetime,
        reason: str,  # 신호 발생 이유
        metadata: Optional[Dict] = None  # 추가 정보
    ):
        self.signal_type = signal_type
        self.strength = strength
        self.price = price
        self.timestamp = timestamp
        self.reason = reason
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        return {
            "signal_type": self.signal_type,
            "strength": self.strength,
            "price": self.price,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "reason": self.reason,
            "metadata": self.metadata,
        }


class BaseStrategy(ABC):
    """트레이딩 전략 베이스 클래스"""

    def __init__(self, name: str, params: Optional[Dict] = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def generate_signal(
        self,
        indicators: Dict,
        price_data: Optional[pd.DataFrame] = None
    ) -> TradingSignal:
        """
        트레이딩 신호 생성

        Args:
            indicators: 기술적 지표 딕셔너리
            price_data: OHLCV 데이터 (선택)

        Returns:
            TradingSignal 객체
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """전략 설명"""
        pass

    def get_name(self) -> str:
        """전략 이름"""
        return self.name

    def get_params(self) -> Dict:
        """전략 파라미터"""
        return self.params

    def _calculate_signal_strength(
        self,
        score: float,
        min_score: float = 0.0,
        max_score: float = 1.0
    ) -> float:
        """
        신호 강도 계산 (0.0 - 1.0)

        Args:
            score: 원본 점수
            min_score: 최소값
            max_score: 최대값

        Returns:
            정규화된 강도 (0.0 - 1.0)
        """
        if max_score == min_score:
            return 0.5

        normalized = (score - min_score) / (max_score - min_score)
        return max(0.0, min(1.0, normalized))
