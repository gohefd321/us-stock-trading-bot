"""
Integrated Scheduler API Routes

통합 스케줄러 제어 API
"""

from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

from ..services.integrated_scheduler import get_integrated_scheduler

router = APIRouter(prefix="/api/scheduler", tags=["integrated-scheduler"])


class WatchlistRequest(BaseModel):
    ticker: str


@router.post("/start")
async def start_scheduler():
    """
    통합 스케줄러 시작

    Returns:
        시작 결과
    """
    try:
        scheduler = get_integrated_scheduler()
        scheduler.start()

        return {
            "success": True,
            "message": "Integrated scheduler started",
            "status": scheduler.get_status()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler():
    """
    통합 스케줄러 중지

    Returns:
        중지 결과
    """
    try:
        scheduler = get_integrated_scheduler()
        scheduler.stop()

        return {
            "success": True,
            "message": "Integrated scheduler stopped"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_scheduler_status():
    """
    스케줄러 상태 조회

    Returns:
        스케줄러 상태 및 예약된 작업
    """
    scheduler = get_integrated_scheduler()
    status = scheduler.get_status()

    return status


@router.get("/watchlist")
async def get_watchlist():
    """
    워치리스트 조회

    Returns:
        모니터링 중인 종목 리스트
    """
    scheduler = get_integrated_scheduler()
    watchlist = scheduler.get_watchlist()

    return {
        "watchlist": watchlist,
        "count": len(watchlist)
    }


@router.post("/watchlist/add")
async def add_to_watchlist(request: WatchlistRequest):
    """
    워치리스트에 종목 추가

    Args:
        request: 종목 코드

    Returns:
        추가 결과
    """
    scheduler = get_integrated_scheduler()
    scheduler.add_to_watchlist(request.ticker)

    return {
        "success": True,
        "ticker": request.ticker,
        "message": f"Added {request.ticker} to watchlist",
        "watchlist": scheduler.get_watchlist()
    }


@router.delete("/watchlist/{ticker}")
async def remove_from_watchlist(ticker: str):
    """
    워치리스트에서 종목 제거

    Args:
        ticker: 종목 코드

    Returns:
        제거 결과
    """
    scheduler = get_integrated_scheduler()
    scheduler.remove_from_watchlist(ticker)

    return {
        "success": True,
        "ticker": ticker,
        "message": f"Removed {ticker} from watchlist",
        "watchlist": scheduler.get_watchlist()
    }
