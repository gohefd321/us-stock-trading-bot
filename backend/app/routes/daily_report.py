"""
Daily Report API Routes

LLM 기반 일일 시장 리포트 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.daily_report_service import DailyReportService

router = APIRouter(prefix="/api/daily-report", tags=["daily-report"])


@router.get("/latest")
async def get_latest_report(
    db: AsyncSession = Depends(get_db)
):
    """
    최신 일일 리포트 조회

    Returns:
        LLM 생성 시장 리포트 (추천 종목 포함)
    """
    service = DailyReportService(db)
    report = await service.get_latest_report()

    if not report or not report.get('success'):
        raise HTTPException(status_code=500, detail="Failed to generate report")

    return report


@router.post("/generate")
async def generate_report(
    db: AsyncSession = Depends(get_db)
):
    """
    새로운 일일 리포트 생성 (수동)

    Returns:
        생성된 리포트
    """
    service = DailyReportService(db)
    report = await service.generate_daily_report()

    if not report.get('success'):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {report.get('error')}"
        )

    return report
