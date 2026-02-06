"""
Strategy Engine API Routes

전략 엔진 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional
from pydantic import BaseModel

from ..database import get_db
from ..services.strategy_engine import StrategyEngine

router = APIRouter(prefix="/api/strategies", tags=["strategy-engine"])


# Request Models
class AddStrategyRequest(BaseModel):
    strategy_name: str
    params: Optional[Dict] = None


class GenerateSignalRequest(BaseModel):
    ticker: str
    timeframe: str = "1h"
    strategy_names: Optional[List[str]] = None  # None이면 모든 전략 사용
    weights: Optional[Dict[str, float]] = None


# Global strategy engine instance
_strategy_engine: StrategyEngine = None


async def get_strategy_engine(db: AsyncSession = Depends(get_db)) -> StrategyEngine:
    """전략 엔진 싱글톤"""
    global _strategy_engine
    if _strategy_engine is None:
        _strategy_engine = StrategyEngine(db)
    return _strategy_engine


@router.get("/available")
async def get_available_strategies(
    db: AsyncSession = Depends(get_db)
):
    """
    사용 가능한 전략 목록 조회

    Returns:
        전략 이름 리스트
    """
    engine = await get_strategy_engine(db)
    strategies = engine.get_available_strategies()

    return {
        "strategies": strategies,
        "count": len(strategies),
        "descriptions": {
            "MA_CROSS": "Moving Average Crossover (Golden/Death Cross)",
            "RSI": "Relative Strength Index (Overbought/Oversold)",
            "BOLLINGER": "Bollinger Bands Breakout",
            "MACD": "MACD Crossover",
            "VWAP": "VWAP Mean Reversion",
        }
    }


@router.get("/active")
async def get_active_strategies(
    db: AsyncSession = Depends(get_db)
):
    """
    활성화된 전략 목록 조회

    Returns:
        활성화된 전략 정보
    """
    engine = await get_strategy_engine(db)
    strategies = engine.get_active_strategies()

    return {
        "strategies": strategies,
        "count": len(strategies)
    }


@router.post("/add")
async def add_strategy(
    request: AddStrategyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    전략 추가

    Args:
        request: 전략 이름 및 파라미터

    Returns:
        추가 결과
    """
    engine = await get_strategy_engine(db)
    success = engine.add_strategy(request.strategy_name, request.params)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to add strategy: {request.strategy_name}"
        )

    return {
        "success": True,
        "strategy": request.strategy_name,
        "params": request.params,
        "message": f"Strategy {request.strategy_name} added successfully"
    }


@router.delete("/{strategy_name}")
async def remove_strategy(
    strategy_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    전략 제거

    Args:
        strategy_name: 전략 이름

    Returns:
        제거 결과
    """
    engine = await get_strategy_engine(db)
    success = engine.remove_strategy(strategy_name)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to remove strategy: {strategy_name}"
        )

    return {
        "success": True,
        "strategy": strategy_name,
        "message": f"Strategy {strategy_name} removed successfully"
    }


@router.post("/clear")
async def clear_all_strategies(
    db: AsyncSession = Depends(get_db)
):
    """
    모든 전략 제거

    Returns:
        제거 결과
    """
    engine = await get_strategy_engine(db)
    engine.clear_strategies()

    return {
        "success": True,
        "message": "All strategies cleared"
    }


@router.post("/signal")
async def generate_signal(
    request: GenerateSignalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    트레이딩 신호 생성

    Args:
        request: 종목, 시간프레임, 전략 목록, 가중치

    Returns:
        통합 신호 및 개별 전략 신호
    """
    engine = await get_strategy_engine(db)

    # 임시로 전략 추가 (strategy_names 제공 시)
    temp_strategies = []
    if request.strategy_names:
        for strategy_name in request.strategy_names:
            if strategy_name not in [s.get_name() for s in engine.active_strategies]:
                engine.add_strategy(strategy_name)
                temp_strategies.append(strategy_name)

    # 신호 생성
    result = await engine.generate_combined_signal(
        request.ticker,
        request.timeframe,
        request.weights
    )

    # 임시 전략 제거
    for strategy_name in temp_strategies:
        engine.remove_strategy(strategy_name)

    if not result.get('success'):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate signal: {result.get('error')}"
        )

    return result


@router.get("/{ticker}/quick-signal")
async def generate_quick_signal(
    ticker: str,
    timeframe: str = Query(default="1h"),
    strategies: str = Query(default="MA_CROSS,RSI,MACD", description="Comma-separated strategy names"),
    db: AsyncSession = Depends(get_db)
):
    """
    빠른 신호 생성 (미리 정의된 전략 조합)

    Args:
        ticker: 종목 코드
        timeframe: 시간 프레임
        strategies: 전략 이름들 (쉼표로 구분)

    Returns:
        통합 신호
    """
    strategy_list = [s.strip() for s in strategies.split(',')]

    request = GenerateSignalRequest(
        ticker=ticker,
        timeframe=timeframe,
        strategy_names=strategy_list
    )

    return await generate_signal(request, db)
