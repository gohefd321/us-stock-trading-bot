"""
Portfolio API Routes
Portfolio status and historical performance
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict
import logging

from ..services.portfolio_manager import PortfolioManager
from ..dependencies import get_portfolio_manager

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_portfolio_status(
    portfolio: PortfolioManager = Depends(get_portfolio_manager)
) -> Dict:
    """
    Get current portfolio status

    Returns:
        Portfolio state with positions and P/L
    """
    try:
        state = await portfolio.get_current_state()
        exposure = await portfolio.calculate_position_exposure()

        return {
            'success': True,
            **state,
            'exposure': exposure
        }

    except Exception as e:
        logger.error(f"Failed to get portfolio status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_portfolio_history(
    days: int = Query(default=30, ge=1, le=365),
    portfolio: PortfolioManager = Depends(get_portfolio_manager)
) -> Dict:
    """
    Get historical portfolio snapshots

    Args:
        days: Number of days to retrieve (1-365)

    Returns:
        Historical snapshots
    """
    try:
        snapshots = await portfolio.get_historical_snapshots(days=days)

        return {
            'success': True,
            'snapshots': snapshots,
            'count': len(snapshots)
        }

    except Exception as e:
        logger.error(f"Failed to get portfolio history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position/{ticker}")
async def get_position(
    ticker: str,
    portfolio: PortfolioManager = Depends(get_portfolio_manager)
) -> Dict:
    """
    Get specific position details

    Args:
        ticker: Stock ticker symbol

    Returns:
        Position details or 404 if not found
    """
    try:
        position = await portfolio.get_position(ticker)

        if position:
            return {
                'success': True,
                'position': position
            }
        else:
            raise HTTPException(status_code=404, detail=f"No position found for {ticker}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get position for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot")
async def save_snapshot(
    portfolio: PortfolioManager = Depends(get_portfolio_manager)
) -> Dict:
    """
    Manually save a portfolio snapshot

    Returns:
        Success status
    """
    try:
        success = await portfolio.save_snapshot()

        if success:
            return {
                'success': True,
                'message': 'Portfolio snapshot saved'
            }
        else:
            raise HTTPException(status_code=500, detail='Failed to save snapshot')

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save portfolio snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))
