"""
Technical Indicators API Routes

기술적 지표 계산 및 조회 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..database import get_db
from ..services.technical_indicator_service import TechnicalIndicatorService

router = APIRouter(prefix="/api/indicators", tags=["technical-indicators"])


@router.post("/calculate/{ticker}")
async def calculate_indicators(
    ticker: str,
    timeframe: str = Query(default="1h", description="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)"),
    lookback: int = Query(default=200, ge=50, le=1000, description="Number of periods to calculate"),
    db: AsyncSession = Depends(get_db)
):
    """
    특정 종목의 기술적 지표 계산

    Args:
        ticker: 종목 코드 (예: AAPL, TSLA)
        timeframe: 시간 프레임
        lookback: 계산할 과거 기간 수

    Returns:
        계산 결과 및 최신 지표값
    """
    service = TechnicalIndicatorService(db)
    result = await service.calculate_indicators(ticker, timeframe, lookback)

    if not result.get('success'):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate indicators: {result.get('error')}"
        )

    return result


@router.get("/{ticker}/latest")
async def get_latest_indicators(
    ticker: str,
    timeframe: str = Query(default="1h", description="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)"),
    db: AsyncSession = Depends(get_db)
):
    """
    최신 기술적 지표 조회

    Args:
        ticker: 종목 코드
        timeframe: 시간 프레임

    Returns:
        최신 지표값 (SMA, EMA, RSI, MACD, Bollinger, ATR, VWAP, etc.)
    """
    service = TechnicalIndicatorService(db)
    indicators = await service.get_latest_indicators(ticker, timeframe)

    if not indicators:
        raise HTTPException(
            status_code=404,
            detail=f"No indicators found for {ticker} ({timeframe})"
        )

    return indicators


@router.get("/{ticker}/moving-averages")
async def get_moving_averages(
    ticker: str,
    timeframe: str = Query(default="1h"),
    db: AsyncSession = Depends(get_db)
):
    """
    이동평균 조회 (SMA, EMA)

    Args:
        ticker: 종목 코드
        timeframe: 시간 프레임

    Returns:
        이동평균 데이터
    """
    service = TechnicalIndicatorService(db)
    indicators = await service.get_latest_indicators(ticker, timeframe)

    if not indicators:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    return {
        "ticker": ticker,
        "timeframe": timeframe,
        "close_price": indicators['close_price'],
        "moving_averages": indicators['moving_averages'],
        "timestamp": indicators['timestamp'],
    }


@router.get("/{ticker}/oscillators")
async def get_oscillators(
    ticker: str,
    timeframe: str = Query(default="1h"),
    db: AsyncSession = Depends(get_db)
):
    """
    오실레이터 지표 조회 (RSI, Stochastic, MACD)

    Args:
        ticker: 종목 코드
        timeframe: 시간 프레임

    Returns:
        오실레이터 지표
    """
    service = TechnicalIndicatorService(db)
    indicators = await service.get_latest_indicators(ticker, timeframe)

    if not indicators:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    return {
        "ticker": ticker,
        "timeframe": timeframe,
        "close_price": indicators['close_price'],
        "rsi": indicators['rsi'],
        "stochastic": indicators['stochastic'],
        "macd": indicators['macd'],
        "timestamp": indicators['timestamp'],
    }


@router.get("/{ticker}/volatility")
async def get_volatility_indicators(
    ticker: str,
    timeframe: str = Query(default="1h"),
    db: AsyncSession = Depends(get_db)
):
    """
    변동성 지표 조회 (Bollinger Bands, ATR)

    Args:
        ticker: 종목 코드
        timeframe: 시간 프레임

    Returns:
        변동성 지표
    """
    service = TechnicalIndicatorService(db)
    indicators = await service.get_latest_indicators(ticker, timeframe)

    if not indicators:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    return {
        "ticker": ticker,
        "timeframe": timeframe,
        "close_price": indicators['close_price'],
        "bollinger": indicators['bollinger'],
        "atr": indicators['atr'],
        "timestamp": indicators['timestamp'],
    }


@router.get("/{ticker}/trend")
async def get_trend_indicators(
    ticker: str,
    timeframe: str = Query(default="1h"),
    db: AsyncSession = Depends(get_db)
):
    """
    추세 지표 조회 (ADX, VWAP)

    Args:
        ticker: 종목 코드
        timeframe: 시간 프레임

    Returns:
        추세 지표
    """
    service = TechnicalIndicatorService(db)
    indicators = await service.get_latest_indicators(ticker, timeframe)

    if not indicators:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    return {
        "ticker": ticker,
        "timeframe": timeframe,
        "close_price": indicators['close_price'],
        "vwap": indicators['vwap'],
        "adx": indicators['adx'],
        "timestamp": indicators['timestamp'],
    }


@router.get("/{ticker}/volume")
async def get_volume_indicators(
    ticker: str,
    timeframe: str = Query(default="1h"),
    db: AsyncSession = Depends(get_db)
):
    """
    거래량 지표 조회

    Args:
        ticker: 종목 코드
        timeframe: 시간 프레임

    Returns:
        거래량 지표
    """
    service = TechnicalIndicatorService(db)
    indicators = await service.get_latest_indicators(ticker, timeframe)

    if not indicators:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    return {
        "ticker": ticker,
        "timeframe": timeframe,
        "volume": indicators['volume'],
        "timestamp": indicators['timestamp'],
    }
