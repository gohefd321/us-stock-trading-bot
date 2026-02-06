"""
Portfolio Optimizer API Routes

포트폴리오 최적화 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional
from pydantic import BaseModel

from ..database import get_db
from ..services.portfolio_optimizer import PortfolioOptimizer

router = APIRouter(prefix="/api/portfolio", tags=["portfolio-optimizer"])


class OptimalPortfolioRequest(BaseModel):
    tickers: List[str]
    target_return: Optional[float] = None
    risk_free_rate: float = 0.04  # 4%
    lookback_days: int = 252  # 1년
    method: str = "sharpe"  # "sharpe", "min_variance", "max_return"


class RebalancingRequest(BaseModel):
    target_weights: Dict[str, float]  # ticker -> weight (%)
    total_value: float
    tolerance: float = 5.0  # 5%


@router.post("/optimize")
async def get_optimal_portfolio(
    request: OptimalPortfolioRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    최적 포트폴리오 계산 (Modern Portfolio Theory)

    Args:
        request: 최적화 요청

    Returns:
        최적 포트폴리오 정보
    """
    optimizer = PortfolioOptimizer(db)

    result = await optimizer.get_optimal_portfolio(
        tickers=request.tickers,
        target_return=request.target_return,
        risk_free_rate=request.risk_free_rate,
        lookback_days=request.lookback_days,
        method=request.method
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.post("/rebalancing")
async def get_rebalancing_recommendations(
    request: RebalancingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    리밸런싱 추천

    Args:
        request: 리밸런싱 요청

    Returns:
        리밸런싱 액션
    """
    optimizer = PortfolioOptimizer(db)

    result = await optimizer.get_rebalancing_recommendations(
        target_weights=request.target_weights,
        total_value=request.total_value,
        tolerance=request.tolerance
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.get("/metrics")
async def get_portfolio_metrics(
    db: AsyncSession = Depends(get_db)
):
    """
    현재 포트폴리오 메트릭 계산

    Returns:
        포트폴리오 성과 지표
    """
    optimizer = PortfolioOptimizer(db)

    result = await optimizer.calculate_portfolio_metrics()

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.get("/positions")
async def get_all_positions(
    db: AsyncSession = Depends(get_db)
):
    """
    모든 포지션 조회

    Returns:
        포지션 리스트
    """
    from ..models.portfolio_position import PortfolioPosition
    from sqlalchemy import select

    result = await db.execute(
        select(PortfolioPosition).where(PortfolioPosition.quantity > 0)
    )
    positions = result.scalars().all()

    return {
        "positions": [
            {
                "ticker": pos.ticker,
                "quantity": pos.quantity,
                "avg_buy_price": pos.avg_buy_price,
                "current_price": pos.current_price,
                "current_value": pos.current_value,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                "portfolio_weight": pos.portfolio_weight,
                "entry_date": pos.entry_date.isoformat() if pos.entry_date else None,
                "holding_days": pos.holding_days
            }
            for pos in positions
        ],
        "count": len(positions)
    }


@router.get("/positions/{ticker}")
async def get_position_detail(
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 포지션 상세 조회

    Args:
        ticker: 종목코드

    Returns:
        포지션 상세 정보
    """
    from ..models.portfolio_position import PortfolioPosition
    from sqlalchemy import select

    result = await db.execute(
        select(PortfolioPosition).where(PortfolioPosition.ticker == ticker)
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(status_code=404, detail=f"Position not found: {ticker}")

    return {
        "ticker": position.ticker,
        "ticker_name": position.ticker_name,
        "market_type": position.market_type,
        "sector": position.sector,
        "quantity": position.quantity,
        "avg_buy_price": position.avg_buy_price,
        "total_invested": position.total_invested,
        "current_price": position.current_price,
        "current_value": position.current_value,
        "unrealized_pnl": position.unrealized_pnl,
        "unrealized_pnl_pct": position.unrealized_pnl_pct,
        "realized_pnl": position.realized_pnl,
        "portfolio_weight": position.portfolio_weight,
        "target_weight": position.target_weight,
        "stop_loss_price": position.stop_loss_price,
        "take_profit_price": position.take_profit_price,
        "entry_strategy": position.entry_strategy,
        "entry_date": position.entry_date.isoformat() if position.entry_date else None,
        "holding_days": position.holding_days
    }
