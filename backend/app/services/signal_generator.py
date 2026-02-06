"""
Signal Generator Service

실시간 신호 생성 및 관리
- 여러 전략 신호 통합
- DB 저장
- 실시간 신호 스트리밍
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..models.signals import Signal
from .strategy_engine import StrategyEngine
from .technical_indicator_service import TechnicalIndicatorService

logger = logging.getLogger(__name__)


class SignalGenerator:
    """신호 생성기"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.strategy_engine = StrategyEngine(db)
        self.indicator_service = TechnicalIndicatorService(db)

    async def generate_and_save_signal(
        self,
        ticker: str,
        timeframe: str = '1h',
        strategy_names: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        신호 생성 및 DB 저장

        Args:
            ticker: 종목 코드
            timeframe: 시간 프레임
            strategy_names: 사용할 전략 리스트
            weights: 전략별 가중치

        Returns:
            생성된 신호 정보
        """
        try:
            # 전략 추가
            if strategy_names:
                for strategy_name in strategy_names:
                    self.strategy_engine.add_strategy(strategy_name)

            # 통합 신호 생성
            signal_result = await self.strategy_engine.generate_combined_signal(
                ticker, timeframe, weights
            )

            if not signal_result.get('success'):
                return {
                    "success": False,
                    "error": signal_result.get('error')
                }

            combined = signal_result['combined_signal']

            # DB에 저장
            signal = Signal(
                ticker=ticker,
                signal_type=combined['signal_type'],
                strength=combined['strength'],
                confidence=combined['confidence'],
                strategy_name=','.join(self.strategy_engine.get_available_strategies()),
                timeframe=timeframe,
                reason=f"Combined signal from {len(signal_result['individual_signals'])} strategies",
                metadata={
                    'individual_signals': signal_result['individual_signals'],
                    'scores': {
                        'buy_score': combined['buy_score'],
                        'sell_score': combined['sell_score'],
                        'hold_score': combined['hold_score'],
                    },
                    'weights': weights,
                },
                created_at=datetime.now(),
            )

            self.db.add(signal)
            await self.db.commit()
            await self.db.refresh(signal)

            logger.info(f"✅ Signal saved: {ticker} - {combined['signal_type']} (strength: {combined['strength']:.2f})")

            return {
                "success": True,
                "signal_id": signal.id,
                "ticker": ticker,
                "signal": combined,
                "individual_signals": signal_result['individual_signals'],
            }

        except Exception as e:
            logger.error(f"Failed to generate signal: {e}")
            await self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def get_latest_signal(
        self,
        ticker: str,
        timeframe: Optional[str] = None
    ) -> Optional[Dict]:
        """
        최신 신호 조회

        Args:
            ticker: 종목 코드
            timeframe: 시간 프레임 (선택)

        Returns:
            최신 신호
        """
        try:
            stmt = (
                select(Signal)
                .where(Signal.ticker == ticker)
                .order_by(desc(Signal.created_at))
                .limit(1)
            )

            if timeframe:
                stmt = stmt.where(Signal.timeframe == timeframe)

            result = await self.db.execute(stmt)
            signal = result.scalar_one_or_none()

            if not signal:
                return None

            return {
                "id": signal.id,
                "ticker": signal.ticker,
                "signal_type": signal.signal_type,
                "strength": signal.strength,
                "confidence": signal.confidence,
                "strategy_name": signal.strategy_name,
                "timeframe": signal.timeframe,
                "reason": signal.reason,
                "metadata": signal.metadata,
                "created_at": signal.created_at.isoformat() if signal.created_at else None,
            }

        except Exception as e:
            logger.error(f"Failed to get latest signal: {e}")
            return None

    async def get_signal_history(
        self,
        ticker: str,
        limit: int = 20,
        signal_type: Optional[str] = None
    ) -> List[Dict]:
        """
        신호 히스토리 조회

        Args:
            ticker: 종목 코드
            limit: 조회 개수
            signal_type: 신호 타입 필터 (BUY/SELL/HOLD)

        Returns:
            신호 리스트
        """
        try:
            stmt = (
                select(Signal)
                .where(Signal.ticker == ticker)
                .order_by(desc(Signal.created_at))
                .limit(limit)
            )

            if signal_type:
                stmt = stmt.where(Signal.signal_type == signal_type)

            result = await self.db.execute(stmt)
            signals = result.scalars().all()

            return [
                {
                    "id": s.id,
                    "ticker": s.ticker,
                    "signal_type": s.signal_type,
                    "strength": s.strength,
                    "confidence": s.confidence,
                    "strategy_name": s.strategy_name,
                    "timeframe": s.timeframe,
                    "reason": s.reason,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in signals
            ]

        except Exception as e:
            logger.error(f"Failed to get signal history: {e}")
            return []

    async def scan_multiple_tickers(
        self,
        tickers: List[str],
        timeframe: str = '1h',
        strategy_names: Optional[List[str]] = None
    ) -> Dict:
        """
        여러 종목 동시 스캔

        Args:
            tickers: 종목 코드 리스트
            timeframe: 시간 프레임
            strategy_names: 사용할 전략

        Returns:
            종목별 신호
        """
        results = []

        for ticker in tickers:
            signal_result = await self.generate_and_save_signal(
                ticker, timeframe, strategy_names
            )

            if signal_result.get('success'):
                results.append({
                    "ticker": ticker,
                    "signal": signal_result['signal'],
                })

        # 매수/매도 신호만 필터링
        buy_signals = [r for r in results if r['signal']['signal_type'] == 'BUY']
        sell_signals = [r for r in results if r['signal']['signal_type'] == 'SELL']

        # 강도순 정렬
        buy_signals.sort(key=lambda x: x['signal']['strength'], reverse=True)
        sell_signals.sort(key=lambda x: x['signal']['strength'], reverse=True)

        return {
            "success": True,
            "scanned_count": len(tickers),
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "timestamp": datetime.now().isoformat(),
        }
