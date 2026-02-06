"""
News & Events API Routes

뉴스 및 이벤트 조회 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..database import get_db
from ..services.news_event_service import NewsEventService

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/latest")
async def get_latest_news(
    ticker: str = Query(..., description="종목 코드"),
    limit: int = Query(default=10, ge=1, le=50, description="조회할 뉴스 수"),
    db: AsyncSession = Depends(get_db)
):
    """
    특정 종목의 최신 뉴스 조회 (DB에서)

    Args:
        ticker: 종목 코드
        limit: 조회할 뉴스 수

    Returns:
        뉴스 리스트
    """
    service = NewsEventService(db)
    news_list = await service.get_latest_news(ticker, limit)
    return {"ticker": ticker, "news": news_list, "count": len(news_list)}


@router.get("/realtime")
async def get_realtime_news(
    ticker: str = Query(..., description="종목 코드"),
    hours: int = Query(default=24, ge=1, le=72, description="조회 기간 (시간)"),
    db: AsyncSession = Depends(get_db)
):
    """
    여러 소스에서 실시간 뉴스 수집 (Google News, Yahoo Finance)

    Args:
        ticker: 종목 코드
        hours: 조회 기간

    Returns:
        뉴스 리스트
    """
    service = NewsEventService(db)
    news_list = await service.get_recent_news_all_sources(ticker, hours)
    return {"ticker": ticker, "news": news_list, "count": len(news_list)}


@router.get("/sec-filings")
async def get_sec_filings(
    ticker: str = Query(..., description="종목 코드"),
    limit: int = Query(default=10, ge=1, le=50, description="조회할 서류 수"),
    db: AsyncSession = Depends(get_db)
):
    """
    SEC 제출 서류 조회 (8-K, 10-Q, 10-K)

    Args:
        ticker: 종목 코드
        limit: 조회할 서류 수

    Returns:
        SEC 서류 리스트
    """
    service = NewsEventService(db)
    filings = await service.get_sec_filings(ticker, limit)
    return {"ticker": ticker, "filings": filings, "count": len(filings)}


@router.post("/fetch-news/{ticker}")
async def fetch_news(
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    뉴스 수집 후 DB 저장

    Args:
        ticker: 종목 코드

    Returns:
        저장된 뉴스 수
    """
    service = NewsEventService(db)
    count = await service.fetch_and_store_news(ticker)
    return {"success": True, "ticker": ticker, "stored_count": count}


@router.post("/fetch-sec/{ticker}")
async def fetch_sec_filings(
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    SEC 서류 수집 후 DB 저장

    Args:
        ticker: 종목 코드

    Returns:
        저장된 서류 수
    """
    service = NewsEventService(db)
    count = await service.fetch_and_store_sec_filings(ticker)
    return {"success": True, "ticker": ticker, "stored_count": count}
