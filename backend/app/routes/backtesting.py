"""
Backtesting API Routes

백테스팅 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from ..database import get_db
from ..services.backtesting_service import BacktestingService
from ..services.strategies import MACrossStrategy, RSIStrategy, BollingerStrategy, MACDStrategy, VWAPStrategy

router = APIRouter(prefix="/api/backtest", tags=["backtesting"])


class BacktestRequest(BaseModel):
    ticker: str
    strategy_name: str
    timeframe: str = "1h"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 10000.0
    commission: float = 0.001


@router.post("/run")
async def run_backtest(
    request: BacktestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    백테스트 실행

    Args:
        request: 백테스트 설정

    Returns:
        백테스트 결과
    """
    service = BacktestingService(db)

    # 전략 인스턴스 생성
    strategy_map = {
        "MA_CROSS": MACrossStrategy(),
        "RSI": RSIStrategy(),
        "BOLLINGER": BollingerStrategy(),
        "MACD": MACDStrategy(),
        "VWAP": VWAPStrategy(),
    }

    strategy = strategy_map.get(request.strategy_name)
    if not strategy:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {request.strategy_name}")

    # 날짜 파싱
    start_date = datetime.fromisoformat(request.start_date) if request.start_date else None
    end_date = datetime.fromisoformat(request.end_date) if request.end_date else None

    # 백테스트 실행
    result = await service.run_backtest(
        ticker=request.ticker,
        strategy=strategy,
        timeframe=request.timeframe,
        start_date=start_date,
        end_date=end_date,
        initial_capital=request.initial_capital,
        commission=request.commission
    )

    if not result.get('success'):
        raise HTTPException(status_code=500, detail=result.get('error'))

    return result


@router.get("/results")
async def get_backtest_results(
    ticker: Optional[str] = Query(None),
    strategy_name: Optional[str] = Query(None),
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    백테스트 결과 조회

    Args:
        ticker: 종목 코드 (선택)
        strategy_name: 전략 이름 (선택)
        limit: 조회 개수

    Returns:
        백테스트 결과 리스트
    """
    service = BacktestingService(db)
    results = await service.get_backtest_results(ticker, strategy_name, limit)

    return {
        "results": results,
        "count": len(results)
    }
