"""
Portfolio Optimizer Service

포트폴리오 최적화 서비스
- Modern Portfolio Theory (MPT)
- Efficient Frontier 계산
- 리스크 조정 자산 배분
- 리밸런싱 추천
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from scipy.optimize import minimize
import yfinance as yf

from ..models.portfolio_position import PortfolioPosition

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """포트폴리오 최적화 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_optimal_portfolio(
        self,
        tickers: List[str],
        target_return: Optional[float] = None,
        risk_free_rate: float = 0.04,  # 4% (US Treasury)
        lookback_days: int = 252,  # 1년
        method: str = "sharpe"  # "sharpe", "min_variance", "max_return"
    ) -> Dict:
        """
        최적 포트폴리오 계산 (Modern Portfolio Theory)

        Args:
            tickers: 종목 리스트
            target_return: 목표 수익률 (None이면 자동)
            risk_free_rate: 무위험 수익률
            lookback_days: 과거 데이터 기간 (일)
            method: 최적화 방법
                - "sharpe": 샤프 비율 최대화 (기본)
                - "min_variance": 분산 최소화 (최소 리스크)
                - "max_return": 수익률 최대화 (고위험)

        Returns:
            최적 포트폴리오 정보
        """
        try:
            logger.info(f"Calculating optimal portfolio for {len(tickers)} stocks (method: {method})")

            # 과거 데이터 로드
            returns_data = await self._get_historical_returns(tickers, lookback_days)
            if returns_data.empty:
                return {
                    "success": False,
                    "error": "Insufficient historical data"
                }

            # 수익률 및 공분산 행렬 계산
            mean_returns = returns_data.mean()
            cov_matrix = returns_data.cov()

            # 연율화 (252 trading days)
            mean_returns_annual = mean_returns * 252
            cov_matrix_annual = cov_matrix * 252

            logger.info(f"Mean annual returns: {mean_returns_annual.to_dict()}")

            # 최적화 실행
            if method == "sharpe":
                weights, metrics = self._optimize_sharpe_ratio(
                    mean_returns_annual,
                    cov_matrix_annual,
                    risk_free_rate
                )
            elif method == "min_variance":
                weights, metrics = self._optimize_min_variance(
                    mean_returns_annual,
                    cov_matrix_annual
                )
            elif method == "max_return":
                weights, metrics = self._optimize_max_return(
                    mean_returns_annual,
                    cov_matrix_annual
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown method: {method}"
                }

            # 종목별 가중치
            portfolio_weights = dict(zip(tickers, weights))

            # Efficient Frontier 계산 (선택적)
            efficient_frontier = self._calculate_efficient_frontier(
                mean_returns_annual,
                cov_matrix_annual,
                num_points=50
            )

            result = {
                "success": True,
                "method": method,
                "portfolio_weights": portfolio_weights,
                "expected_return": metrics["return"],
                "expected_volatility": metrics["volatility"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "efficient_frontier": efficient_frontier,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"✓ Optimal portfolio calculated: Return={metrics['return']:.2%}, Vol={metrics['volatility']:.2%}, Sharpe={metrics['sharpe_ratio']:.2f}")

            return result

        except Exception as e:
            logger.error(f"Failed to calculate optimal portfolio: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_rebalancing_recommendations(
        self,
        target_weights: Dict[str, float],
        total_value: float,
        tolerance: float = 5.0  # 5% tolerance
    ) -> Dict:
        """
        리밸런싱 추천

        Args:
            target_weights: 목표 비중 (ticker -> weight)
            total_value: 총 포트폴리오 가치
            tolerance: 허용 이탈 비율 (%)

        Returns:
            리밸런싱 추천
        """
        try:
            # 현재 포지션 조회
            result = await self.db.execute(
                select(PortfolioPosition).where(PortfolioPosition.quantity > 0)
            )
            positions = result.scalars().all()

            # 현재 비중 계산
            current_weights = {}
            for pos in positions:
                if total_value > 0:
                    current_weights[pos.ticker] = (pos.current_value / total_value) * 100
                else:
                    current_weights[pos.ticker] = 0

            # 리밸런싱 액션 계산
            actions = []
            for ticker, target_weight_pct in target_weights.items():
                current_weight_pct = current_weights.get(ticker, 0)
                weight_diff = target_weight_pct - current_weight_pct

                # 허용 범위 초과 시에만 리밸런싱
                if abs(weight_diff) > tolerance:
                    target_value = total_value * (target_weight_pct / 100)
                    current_value = total_value * (current_weight_pct / 100)
                    value_diff = target_value - current_value

                    # 매수/매도 수량 계산
                    position = next((p for p in positions if p.ticker == ticker), None)
                    current_price = position.current_price if position else None

                    if current_price:
                        quantity_diff = int(value_diff / current_price)

                        actions.append({
                            "ticker": ticker,
                            "current_weight": current_weight_pct,
                            "target_weight": target_weight_pct,
                            "weight_diff": weight_diff,
                            "action": "BUY" if quantity_diff > 0 else "SELL",
                            "quantity": abs(quantity_diff),
                            "value": abs(value_diff)
                        })

            # 우선순위 정렬 (이탈 비율이 큰 순서)
            actions.sort(key=lambda x: abs(x["weight_diff"]), reverse=True)

            return {
                "success": True,
                "rebalancing_needed": len(actions) > 0,
                "actions": actions,
                "total_actions": len(actions),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get rebalancing recommendations: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def calculate_portfolio_metrics(self) -> Dict:
        """
        현재 포트폴리오 메트릭 계산

        Returns:
            포트폴리오 성과 지표
        """
        try:
            # 포지션 조회
            result = await self.db.execute(
                select(PortfolioPosition).where(PortfolioPosition.quantity > 0)
            )
            positions = result.scalars().all()

            if not positions:
                return {
                    "success": False,
                    "error": "No positions found"
                }

            # 총 가치 계산
            total_invested = sum(p.total_invested for p in positions)
            total_value = sum(p.current_value for p in positions if p.current_value)
            total_unrealized_pnl = sum(p.unrealized_pnl for p in positions if p.unrealized_pnl)
            total_realized_pnl = sum(p.realized_pnl for p in positions)

            # 수익률
            total_pnl = total_unrealized_pnl + total_realized_pnl
            total_return_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

            # 포지션별 비중
            position_weights = []
            for pos in positions:
                weight = (pos.current_value / total_value * 100) if total_value > 0 else 0
                position_weights.append({
                    "ticker": pos.ticker,
                    "weight": weight,
                    "value": pos.current_value,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "unrealized_pnl_pct": pos.unrealized_pnl_pct
                })

            # 섹터 다각화 (sector가 있는 경우)
            sector_allocation = {}
            for pos in positions:
                if pos.sector:
                    weight = (pos.current_value / total_value * 100) if total_value > 0 else 0
                    sector_allocation[pos.sector] = sector_allocation.get(pos.sector, 0) + weight

            # 포트폴리오 변동성 계산 (과거 데이터 기반)
            tickers = [p.ticker for p in positions]
            weights = [p.current_value / total_value for p in positions if total_value > 0]

            if len(tickers) > 0 and sum(weights) > 0:
                returns_data = await self._get_historical_returns(tickers, lookback_days=30)
                if not returns_data.empty:
                    cov_matrix = returns_data.cov() * 252  # 연율화
                    portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
                    portfolio_volatility = np.sqrt(portfolio_variance)
                else:
                    portfolio_volatility = None
            else:
                portfolio_volatility = None

            return {
                "success": True,
                "total_invested": total_invested,
                "total_value": total_value,
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_realized_pnl": total_realized_pnl,
                "total_return_pct": total_return_pct,
                "portfolio_volatility": portfolio_volatility,
                "position_count": len(positions),
                "position_weights": position_weights,
                "sector_allocation": sector_allocation,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to calculate portfolio metrics: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # ==================== Private Methods ====================

    async def _get_historical_returns(
        self,
        tickers: List[str],
        lookback_days: int
    ) -> pd.DataFrame:
        """과거 수익률 데이터 로드 (Yahoo Finance)"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 30)  # 여유분 추가

            # Yahoo Finance에서 데이터 다운로드
            data = yf.download(
                tickers,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                progress=False
            )

            if data.empty:
                logger.warning("No historical data downloaded")
                return pd.DataFrame()

            # 종가 추출
            if len(tickers) == 1:
                prices = data["Close"]
            else:
                prices = data["Close"][tickers]

            # 일간 수익률 계산
            returns = prices.pct_change().dropna()

            logger.info(f"Loaded {len(returns)} days of return data")

            return returns

        except Exception as e:
            logger.error(f"Failed to get historical returns: {e}")
            return pd.DataFrame()

    def _optimize_sharpe_ratio(
        self,
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        risk_free_rate: float
    ) -> Tuple[np.ndarray, Dict]:
        """샤프 비율 최대화"""

        num_assets = len(mean_returns)

        def neg_sharpe_ratio(weights):
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            sharpe = (portfolio_return - risk_free_rate) / portfolio_vol
            return -sharpe  # 최소화하므로 음수

        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}  # 가중치 합 = 1
        bounds = tuple((0, 1) for _ in range(num_assets))  # 각 가중치 0~100%
        initial_guess = num_assets * [1.0 / num_assets]

        result = minimize(
            neg_sharpe_ratio,
            initial_guess,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints
        )

        weights = result.x
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
        sharpe = (portfolio_return - risk_free_rate) / portfolio_vol

        metrics = {
            "return": portfolio_return,
            "volatility": portfolio_vol,
            "sharpe_ratio": sharpe
        }

        return weights, metrics

    def _optimize_min_variance(
        self,
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame
    ) -> Tuple[np.ndarray, Dict]:
        """분산 최소화 (최소 리스크 포트폴리오)"""

        num_assets = len(mean_returns)

        def portfolio_variance(weights):
            return np.dot(weights, np.dot(cov_matrix, weights))

        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0, 1) for _ in range(num_assets))
        initial_guess = num_assets * [1.0 / num_assets]

        result = minimize(
            portfolio_variance,
            initial_guess,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints
        )

        weights = result.x
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))

        metrics = {
            "return": portfolio_return,
            "volatility": portfolio_vol,
            "sharpe_ratio": (portfolio_return - 0.04) / portfolio_vol
        }

        return weights, metrics

    def _optimize_max_return(
        self,
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame
    ) -> Tuple[np.ndarray, Dict]:
        """수익률 최대화"""

        num_assets = len(mean_returns)

        def neg_return(weights):
            return -np.dot(weights, mean_returns)

        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0, 1) for _ in range(num_assets))
        initial_guess = num_assets * [1.0 / num_assets]

        result = minimize(
            neg_return,
            initial_guess,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints
        )

        weights = result.x
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))

        metrics = {
            "return": portfolio_return,
            "volatility": portfolio_vol,
            "sharpe_ratio": (portfolio_return - 0.04) / portfolio_vol
        }

        return weights, metrics

    def _calculate_efficient_frontier(
        self,
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        num_points: int = 50
    ) -> List[Dict]:
        """Efficient Frontier 계산"""

        try:
            target_returns = np.linspace(mean_returns.min(), mean_returns.max(), num_points)
            efficient_frontier = []

            for target_return in target_returns:
                # 목표 수익률에서 최소 분산 포트폴리오 계산
                num_assets = len(mean_returns)

                def portfolio_variance(weights):
                    return np.dot(weights, np.dot(cov_matrix, weights))

                constraints = [
                    {"type": "eq", "fun": lambda x: np.sum(x) - 1},  # 가중치 합 = 1
                    {"type": "eq", "fun": lambda x: np.dot(x, mean_returns) - target_return}  # 목표 수익률
                ]
                bounds = tuple((0, 1) for _ in range(num_assets))
                initial_guess = num_assets * [1.0 / num_assets]

                result = minimize(
                    portfolio_variance,
                    initial_guess,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=constraints
                )

                if result.success:
                    weights = result.x
                    portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))

                    efficient_frontier.append({
                        "return": target_return,
                        "volatility": portfolio_vol,
                        "sharpe_ratio": (target_return - 0.04) / portfolio_vol
                    })

            return efficient_frontier

        except Exception as e:
            logger.error(f"Failed to calculate efficient frontier: {e}")
            return []
