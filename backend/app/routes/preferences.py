"""
Investment Preferences API Routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from ..database import get_db
from ..models import InvestmentPreference

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


@router.get("/investment")
async def get_investment_preferences(db: AsyncSession = Depends(get_db)):
    """Get current investment preferences"""
    try:
        stmt = select(InvestmentPreference).limit(1)
        result = await db.execute(stmt)
        prefs = result.scalar_one_or_none()

        if not prefs:
            return {
                "exists": False,
                "message": "아직 투자 선호도가 설정되지 않았습니다. 챗봇과 대화해보세요!"
            }

        return {
            "exists": True,
            "preferences": {
                "risk_appetite": prefs.risk_appetite,
                "investment_style": prefs.investment_style,
                "preferred_sectors": prefs.preferred_sectors.split(',') if prefs.preferred_sectors else [],
                "avoided_sectors": prefs.avoided_sectors.split(',') if prefs.avoided_sectors else [],
                "preferred_tickers": prefs.preferred_tickers.split(',') if prefs.preferred_tickers else [],
                "avoided_tickers": prefs.avoided_tickers.split(',') if prefs.avoided_tickers else [],
                "prefer_diversification": prefs.prefer_diversification,
                "prefer_dip_buying": prefs.prefer_dip_buying,
                "prefer_momentum": prefs.prefer_momentum,
                "custom_instructions": prefs.custom_instructions,
                "last_updated": prefs.last_updated_by_chat.isoformat() if prefs.last_updated_by_chat else None
            }
        }

    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        return {
            "exists": False,
            "error": str(e)
        }
