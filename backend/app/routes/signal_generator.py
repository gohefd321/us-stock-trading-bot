"""
Signal Generator API Routes

실시간 신호 생성 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict
from pydantic import BaseModel

from ..database import get_db
from ..services.signal_generator import SignalGenerator

router = APIRouter(prefix="/api/signals", tags=["signal-generator"])


class GenerateSignalRequest(BaseModel):
    ticker: str
    timeframe: str = "1h"
    strategy_names: Optional[List[str]] = None
    weights: Optional[Dict[str, float]] = None


class ScanRequest(BaseModel):
    tickers: List[str]
    timeframe: str = "1h"
    strategy_names: Optional[List[str]] = ["MA_CROSS", "RSI", "MACD"]


@router.post("/generate")
async def generate_signal(
    request: GenerateSignalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    신호 생성 및 저장

    Args:
        request: 신호 생성 요청

    Returns:
        생성된 신호
    """
    generator = SignalGenerator(db)
    result = await generator.generate_and_save_signal(
        ticker=request.ticker,
        timeframe=request.timeframe,
        strategy_names=request.strategy_names,
        weights=request.weights
    )

    if not result.get('success'):
        raise HTTPException(status_code=500, detail=result.get('error'))

    return result


@router.get("/{ticker}/latest")
async def get_latest_signal(
    ticker: str,
    timeframe: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    최신 신호 조회

    Args:
        ticker: 종목 코드
        timeframe: 시간 프레임 (선택)

    Returns:
        최신 신호
    """
    generator = SignalGenerator(db)
    signal = await generator.get_latest_signal(ticker, timeframe)

    if not signal:
        raise HTTPException(status_code=404, detail=f"No signal found for {ticker}")

    return signal


@router.get("/{ticker}/history")
async def get_signal_history(
    ticker: str,
    limit: int = Query(default=20, ge=1, le=100),
    signal_type: Optional[str] = Query(None, description="BUY, SELL, or HOLD"),
    db: AsyncSession = Depends(get_db)
):
    """
    신호 히스토리 조회

    Args:
        ticker: 종목 코드
        limit: 조회 개수
        signal_type: 신호 타입 필터

    Returns:
        신호 리스트
    """
    generator = SignalGenerator(db)
    signals = await generator.get_signal_history(ticker, limit, signal_type)

    return {
        "ticker": ticker,
        "signals": signals,
        "count": len(signals)
    }


@router.post("/scan")
async def scan_multiple_tickers(
    request: ScanRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    여러 종목 스캔

    Args:
        request: 스캔 요청 (종목 리스트)

    Returns:
        매수/매도 신호 목록
    """
    generator = SignalGenerator(db)
    result = await generator.scan_multiple_tickers(
        tickers=request.tickers,
        timeframe=request.timeframe,
        strategy_names=request.strategy_names
    )

    return result
