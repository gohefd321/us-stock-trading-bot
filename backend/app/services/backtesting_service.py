"""
Backtesting Service

백테스팅 시스템
- 과거 데이터로 전략 검증
- 성과 지표: Sharpe Ratio, MDD, Win Rate, Profit Factor
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..models.backtest_result import BacktestResult
from ..models.realtime_price import OHLCV
from ..models.technical_indicator import TechnicalIndicator
from .strategies import BaseStrategy

logger = logging.getLogger(__name__)


class BacktestingService:
    """백테스팅 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_backtest(
        self,
        ticker: str,
        strategy: BaseStrategy,
        timeframe: str = '1h',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_capital: float = 10000.0,
        commission: float = 0.001  # 0.1% 수수료
    ) -> Dict:
        """
        백테스트 실행

        Args:
            ticker: 종목 코드
            strategy: 트레이딩 전략
            timeframe: 시간 프레임
            start_date: 시작일 (None이면 1년 전)
            end_date: 종료일 (None이면 현재)
            initial_capital: 초기 자본
            commission: 거래 수수료

        Returns:
            백테스트 결과
        """
        try:
            logger.info(f"🔬 Running backtest: {ticker} with {strategy.get_name()}")

            # 기간 설정
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                start_date = end_date - timedelta(days=365)

            # OHLCV 데이터 가져오기
            price_data = await self._fetch_price_data(ticker, timeframe, start_date, end_date)
            if price_data.empty:
                return {"success": False, "error": "No price data available"}

            # 기술적 지표 가져오기
            indicators_data = await self._fetch_indicators_data(ticker, timeframe, start_date, end_date)
            if indicators_data.empty:
                return {"success": False, "error": "No indicator data available"}

            # 백테스트 실행
            results = self._execute_backtest(
                price_data,
                indicators_data,
                strategy,
                initial_capital,
                commission
            )

            # 성과 지표 계산
            metrics = self._calculate_metrics(results, initial_capital)

            # DB 저장
            backtest_id = await self._save_backtest_result(
                ticker,
                strategy,
                timeframe,
                start_date,
                end_date,
                initial_capital,
                metrics,
                results['trades']
            )

            return {
                "success": True,
                "backtest_id": backtest_id,
                "ticker": ticker,
                "strategy": strategy.get_name(),
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "metrics": metrics,
                "equity_curve": results['equity_curve'],
                "trades": results['trades'],
            }

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return {"success": False, "error": str(e)}

    def _execute_backtest(
        self,
        price_data: pd.DataFrame,
        indicators_data: pd.DataFrame,
        strategy: BaseStrategy,
        initial_capital: float,
        commission: float
    ) -> Dict:
        """
        백테스트 실행 로직

        Returns:
            {'equity_curve': List, 'trades': List}
        """
        capital = initial_capital
        position = 0  # 0: no position, 1: long, -1: short (미지원)
        entry_price = 0
        trades = []
        equity_curve = []

        # 데이터 병합 (timestamp 기준)
        merged = pd.merge(price_data, indicators_data, on='timestamp', how='inner')

        for idx, row in merged.iterrows():
            timestamp = row['timestamp']
            close_price = row['close']

            # 지표 딕셔너리 구성
            indicators = {
                'close_price': close_price,
                'timestamp': timestamp.isoformat(),
                'moving_averages': {
                    'sma_10': row.get('sma_10'),
                    'sma_20': row.get('sma_20'),
                    'sma_50': row.get('sma_50'),
                    'ema_10': row.get('ema_10'),
                    'ema_20': row.get('ema_20'),
                    'ema_50': row.get('ema_50'),
                },
                'rsi': row.get('rsi_14'),
                'macd': {
                    'macd': row.get('macd'),
                    'signal': row.get('macd_signal'),
                    'histogram': row.get('macd_histogram'),
                },
                'bollinger': {
                    'upper': row.get('bb_upper'),
                    'middle': row.get('bb_middle'),
                    'lower': row.get('bb_lower'),
                    'percent': row.get('bb_percent'),
                },
                'vwap': row.get('vwap'),
            }

            # 신호 생성
            signal = strategy.generate_signal(indicators)

            # 거래 실행
            if position == 0 and signal.signal_type == 'BUY':
                # 매수
                shares = capital / (close_price * (1 + commission))
                entry_price = close_price
                position = 1
                capital = 0

                trades.append({
                    'timestamp': timestamp.isoformat(),
                    'action': 'BUY',
                    'price': close_price,
                    'shares': shares,
                    'reason': signal.reason,
                })

            elif position == 1 and signal.signal_type == 'SELL':
                # 매도
                capital = shares * close_price * (1 - commission)
                profit = capital - initial_capital
                profit_pct = (profit / initial_capital) * 100

                trades.append({
                    'timestamp': timestamp.isoformat(),
                    'action': 'SELL',
                    'price': close_price,
                    'shares': shares,
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'reason': signal.reason,
                })

                position = 0
                shares = 0

            # Equity curve 기록
            if position == 1:
                current_value = shares * close_price
            else:
                current_value = capital

            equity_curve.append({
                'timestamp': timestamp.isoformat(),
                'value': current_value,
            })

        # 포지션 정리 (미청산 포지션)
        if position == 1:
            final_price = merged.iloc[-1]['close']
            capital = shares * final_price * (1 - commission)
            trades.append({
                'timestamp': merged.iloc[-1]['timestamp'].isoformat(),
                'action': 'SELL',
                'price': final_price,
                'shares': shares,
                'profit': capital - initial_capital,
                'profit_pct': ((capital - initial_capital) / initial_capital) * 100,
                'reason': 'Backtest end',
            })

        return {
            'equity_curve': equity_curve,
            'trades': trades,
        }

    def _calculate_metrics(self, results: Dict, initial_capital: float) -> Dict:
        """성과 지표 계산"""
        trades = results['trades']
        equity_curve = results['equity_curve']

        if not trades:
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'final_capital': initial_capital,
            }

        # 최종 자본
        final_capital = equity_curve[-1]['value'] if equity_curve else initial_capital

        # 총 수익률
        total_return = ((final_capital - initial_capital) / initial_capital) * 100

        # 거래 통계
        sell_trades = [t for t in trades if t['action'] == 'SELL']
        winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        losing_trades = [t for t in sell_trades if t.get('profit', 0) <= 0]

        win_rate = (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0
        avg_win = np.mean([t['profit_pct'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['profit_pct'] for t in losing_trades]) if losing_trades else 0

        # Profit Factor
        total_wins = sum([t['profit'] for t in winning_trades])
        total_losses = abs(sum([t['profit'] for t in losing_trades]))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

        # Sharpe Ratio (간단한 계산)
        returns = [t['profit_pct'] for t in sell_trades]
        sharpe_ratio = (np.mean(returns) / np.std(returns)) if len(returns) > 1 and np.std(returns) > 0 else 0

        # Maximum Drawdown
        equity_values = [e['value'] for e in equity_curve]
        peak = equity_values[0]
        max_dd = 0
        for value in equity_values:
            if value > peak:
                peak = value
            dd = ((peak - value) / peak) * 100
            if dd > max_dd:
                max_dd = dd

        return {
            'total_return': round(total_return, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_dd, 2),
            'win_rate': round(win_rate, 2),
            'profit_factor': round(profit_factor, 2),
            'total_trades': len(sell_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'final_capital': round(final_capital, 2),
        }

    async def _fetch_price_data(
        self,
        ticker: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """OHLCV 데이터 가져오기"""
        stmt = (
            select(OHLCV)
            .where(OHLCV.ticker == ticker)
            .where(OHLCV.timeframe == timeframe)
            .where(OHLCV.timestamp >= start_date)
            .where(OHLCV.timestamp <= end_date)
            .order_by(OHLCV.timestamp)
        )

        result = await self.db.execute(stmt)
        candles = result.scalars().all()

        if not candles:
            return pd.DataFrame()

        df = pd.DataFrame([
            {
                'timestamp': c.timestamp,
                'open': c.open,
                'high': c.high,
                'low': c.low,
                'close': c.close,
                'volume': c.volume,
            }
            for c in candles
        ])

        return df

    async def _fetch_indicators_data(
        self,
        ticker: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """기술적 지표 데이터 가져오기"""
        stmt = (
            select(TechnicalIndicator)
            .where(TechnicalIndicator.ticker == ticker)
            .where(TechnicalIndicator.timeframe == timeframe)
            .where(TechnicalIndicator.timestamp >= start_date)
            .where(TechnicalIndicator.timestamp <= end_date)
            .order_by(TechnicalIndicator.timestamp)
        )

        result = await self.db.execute(stmt)
        indicators = result.scalars().all()

        if not indicators:
            return pd.DataFrame()

        df = pd.DataFrame([
            {
                'timestamp': i.timestamp,
                'sma_10': i.sma_10,
                'sma_20': i.sma_20,
                'sma_50': i.sma_50,
                'ema_10': i.ema_10,
                'ema_20': i.ema_20,
                'ema_50': i.ema_50,
                'rsi_14': i.rsi_14,
                'macd': i.macd,
                'macd_signal': i.macd_signal,
                'macd_histogram': i.macd_histogram,
                'bb_upper': i.bb_upper,
                'bb_middle': i.bb_middle,
                'bb_lower': i.bb_lower,
                'bb_percent': i.bb_percent,
                'vwap': i.vwap,
            }
            for i in indicators
        ])

        return df

    async def _save_backtest_result(
        self,
        ticker: str,
        strategy: BaseStrategy,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float,
        metrics: Dict,
        trades: List[Dict]
    ) -> int:
        """백테스트 결과 저장"""
        try:
            backtest = BacktestResult(
                ticker=ticker,
                strategy_name=strategy.get_name(),
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                total_return=metrics['total_return'],
                sharpe_ratio=metrics['sharpe_ratio'],
                max_drawdown=metrics['max_drawdown'],
                win_rate=metrics['win_rate'],
                profit_factor=metrics['profit_factor'],
                total_trades=metrics['total_trades'],
                winning_trades=metrics['winning_trades'],
                losing_trades=metrics['losing_trades'],
                avg_win=metrics['avg_win'],
                avg_loss=metrics['avg_loss'],
                initial_capital=initial_capital,
                final_capital=metrics['final_capital'],
                strategy_params=strategy.get_params(),
                trade_log=trades,
            )

            self.db.add(backtest)
            await self.db.commit()
            await self.db.refresh(backtest)

            return backtest.id

        except Exception as e:
            logger.error(f"Failed to save backtest result: {e}")
            await self.db.rollback()
            return 0

    async def get_backtest_results(
        self,
        ticker: Optional[str] = None,
        strategy_name: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """백테스트 결과 조회"""
        try:
            stmt = select(BacktestResult).order_by(desc(BacktestResult.created_at)).limit(limit)

            if ticker:
                stmt = stmt.where(BacktestResult.ticker == ticker)
            if strategy_name:
                stmt = stmt.where(BacktestResult.strategy_name == strategy_name)

            result = await self.db.execute(stmt)
            backtests = result.scalars().all()

            return [
                {
                    "id": b.id,
                    "ticker": b.ticker,
                    "strategy": b.strategy_name,
                    "timeframe": b.timeframe,
                    "period": {
                        "start": b.start_date.isoformat() if b.start_date else None,
                        "end": b.end_date.isoformat() if b.end_date else None,
                    },
                    "metrics": {
                        "total_return": b.total_return,
                        "sharpe_ratio": b.sharpe_ratio,
                        "max_drawdown": b.max_drawdown,
                        "win_rate": b.win_rate,
                        "profit_factor": b.profit_factor,
                        "total_trades": b.total_trades,
                    },
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                }
                for b in backtests
            ]

        except Exception as e:
            logger.error(f"Failed to get backtest results: {e}")
            return []
