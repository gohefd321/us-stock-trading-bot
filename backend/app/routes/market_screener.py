"""
Market Screener API Routes

시장 스크리너 API 엔드포인트
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict
import logging

from ..database import get_db
from ..services.market_screener_service import MarketScreenerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screener", tags=["market_screener"])


@router.get("/top-gainers")
async def get_top_gainers(
    limit: int = Query(20, ge=1, le=100, description="조회할 종목 수"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    """
    급등 종목 조회

    - **limit**: 조회할 종목 수 (1-100)
    - 가격 상승률 기준 내림차순
    """
    screener = MarketScreenerService(db)
    return await screener.get_top_gainers(limit=limit)


@router.get("/top-losers")
async def get_top_losers(
    limit: int = Query(20, ge=1, le=100, description="조회할 종목 수"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    """
    급락 종목 조회

    - **limit**: 조회할 종목 수 (1-100)
    - 가격 하락률 기준 오름차순
    """
    screener = MarketScreenerService(db)
    return await screener.get_top_losers(limit=limit)


@router.get("/volume-surge")
async def get_volume_surge(
    limit: int = Query(20, ge=1, le=100, description="조회할 종목 수"),
    threshold: float = Query(200.0, ge=50.0, description="거래량 증가 기준 (%)"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    """
    거래량 급증 종목 조회

    - **limit**: 조회할 종목 수 (1-100)
    - **threshold**: 거래량 증가 기준 (%, 기본 200%)
    - 10일 평균 대비 거래량 증가율 기준
    """
    screener = MarketScreenerService(db)
    return await screener.get_volume_surge(limit=limit, threshold=threshold)


@router.get("/market-cap")
async def get_market_cap_leaders(
    limit: int = Query(50, ge=1, le=200, description="조회할 종목 수"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    """
    시가총액 상위 종목 조회

    - **limit**: 조회할 종목 수 (1-200)
    - 시가총액 기준 내림차순
    """
    screener = MarketScreenerService(db)
    return await screener.get_market_cap_leaders(limit=limit)


@router.get("/52w-extremes")
async def get_52w_extremes(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, List[Dict]]:
    """
    52주 신고가/신저가 종목 조회

    Returns:
        {"highs": [...], "lows": [...]}
    """
    screener = MarketScreenerService(db)
    return await screener.get_52w_extremes()


@router.post("/scan")
async def run_market_scan(
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    전체 시장 스캔 실행

    - 모든 추적 종목의 데이터를 수집하여 DB 업데이트
    - 시간이 오래 걸릴 수 있음 (약 1-2분)

    Returns:
        {"success": bool, "updated_count": int, "timestamp": str}
    """
    logger.info("🔍 Market scan requested via API")
    screener = MarketScreenerService(db)
    result = await screener.scan_all()

    if result["success"]:
        logger.info(f"✅ Market scan completed: {result['updated_count']} stocks updated")
    else:
        logger.error(f"❌ Market scan failed: {result.get('error')}")

    return result


@router.get("/summary")
async def get_market_summary(
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    시장 전체 요약 정보

    Returns:
        {
            "top_gainers": [...],
            "top_losers": [...],
            "volume_leaders": [...],
            "52w_highs": [...],
            "timestamp": str
        }
    """
    screener = MarketScreenerService(db)

    # 병렬로 데이터 조회
    gainers = await screener.get_top_gainers(limit=10)
    losers = await screener.get_top_losers(limit=10)
    volume_surge = await screener.get_volume_surge(limit=10, threshold=150.0)
    extremes = await screener.get_52w_extremes()

    from datetime import datetime

    return {
        "top_gainers": gainers,
        "top_losers": losers,
        "volume_leaders": volume_surge,
        "52w_highs": extremes["highs"][:10],
        "timestamp": datetime.now().isoformat(),
    }
