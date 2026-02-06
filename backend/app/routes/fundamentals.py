"""
Fundamentals API Routes

재무 데이터 조회 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..database import get_db
from ..services.fundamental_service import FundamentalService

router = APIRouter(prefix="/api/fundamentals", tags=["fundamentals"])


@router.get("/{ticker}")
async def get_fundamentals(
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 종목의 재무 데이터 조회

    Args:
        ticker: 종목 코드 (예: AAPL, MSFT)

    Returns:
        재무 데이터 (EPS, P/E, ROE, 부채비율 등)
    """
    service = FundamentalService(db)
    data = await service.get_fundamentals(ticker)

    if not data:
        raise HTTPException(status_code=404, detail=f"No fundamental data found for {ticker}")

    return data


@router.get("/{ticker}/earnings")
async def get_earnings_calendar(
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 종목의 실적 발표 일정 조회

    Args:
        ticker: 종목 코드

    Returns:
        다음/최근 실적 발표일
    """
    service = FundamentalService(db)
    calendar = await service.get_earnings_calendar(ticker)
    return calendar


@router.get("/screener/top-roe")
async def get_top_roe_stocks(
    limit: int = Query(default=20, ge=1, le=100, description="조회할 종목 수"),
    db: AsyncSession = Depends(get_db)
):
    """
    ROE 상위 종목 조회

    Args:
        limit: 조회할 종목 수 (기본 20)

    Returns:
        ROE 상위 종목 리스트
    """
    service = FundamentalService(db)
    stocks = await service.get_top_by_roe(limit)
    return {"stocks": stocks, "count": len(stocks)}


@router.get("/screener/upcoming-earnings")
async def get_upcoming_earnings(
    days: int = Query(default=7, ge=1, le=30, description="조회 기간 (일)"),
    db: AsyncSession = Depends(get_db)
):
    """
    향후 N일 이내 실적 발표 예정 종목

    Args:
        days: 조회 기간 (기본 7일)

    Returns:
        실적 발표 예정 종목 리스트
    """
    service = FundamentalService(db)
    stocks = await service.get_upcoming_earnings(days)
    return {"stocks": stocks, "count": len(stocks), "period_days": days}


@router.post("/update/{ticker}")
async def update_fundamental(
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 종목의 재무 데이터 업데이트

    Args:
        ticker: 종목 코드

    Returns:
        업데이트 성공 여부
    """
    service = FundamentalService(db)
    success = await service.update_fundamental(ticker)

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to update fundamentals for {ticker}")

    return {"success": True, "ticker": ticker, "message": "Fundamentals updated successfully"}


@router.post("/update-batch")
async def update_batch(
    tickers: List[str],
    db: AsyncSession = Depends(get_db)
):
    """
    여러 종목의 재무 데이터 일괄 업데이트

    Args:
        tickers: 종목 코드 리스트

    Returns:
        업데이트 결과
    """
    service = FundamentalService(db)
    result = await service.update_all(tickers)
    return result
