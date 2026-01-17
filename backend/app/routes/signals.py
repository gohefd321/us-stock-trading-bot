"""
Signals API Routes
Market signals and trending tickers
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict
import logging

from ..services.signal_aggregator import SignalAggregator
from ..dependencies import get_signal_aggregator

router = APIRouter(prefix="/api/signals", tags=["signals"])
logger = logging.getLogger(__name__)


@router.get("/trending")
async def get_trending_tickers(
    limit: int = Query(default=20, ge=1, le=100),
    signals: SignalAggregator = Depends(get_signal_aggregator)
) -> Dict:
    """
    Get trending tickers from WallStreetBets

    Args:
        limit: Maximum number of tickers to return

    Returns:
        List of trending tickers with sentiment
    """
    try:
        trending = await signals.wsb_scraper.get_trending_tickers(limit=limit)

        return {
            'success': True,
            'tickers': trending,
            'count': len(trending)
        }

    except Exception as e:
        logger.error(f"Failed to get trending tickers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticker/{ticker}")
async def get_ticker_signals(
    ticker: str,
    signals: SignalAggregator = Depends(get_signal_aggregator)
) -> Dict:
    """
    Get aggregated signals for a specific ticker

    Args:
        ticker: Stock ticker symbol

    Returns:
        Aggregated signals from all sources
    """
    try:
        result = await signals.aggregate_signals_for_ticker(ticker)

        return {
            'success': True,
            'ticker': ticker,
            'signals': result
        }

    except Exception as e:
        logger.error(f"Failed to get signals for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def get_recent_signals(
    hours_back: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=50, ge=1, le=200),
    signals: SignalAggregator = Depends(get_signal_aggregator)
) -> Dict:
    """
    Get recent signals from database

    Args:
        hours_back: Number of hours to look back
        limit: Maximum number of signals to return

    Returns:
        Recent signals
    """
    try:
        from sqlalchemy import select, desc
        from ..models import Signal
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(hours=hours_back)

        stmt = select(Signal).where(
            Signal.created_at >= cutoff
        ).order_by(desc(Signal.created_at)).limit(limit)

        # We need db session - get it from signal aggregator
        result = await signals.db.execute(stmt)
        signal_records = result.scalars().all()

        signal_list = [
            {
                'id': s.id,
                'ticker': s.ticker,
                'source': s.source,
                'signal_type': s.signal_type,
                'sentiment_score': s.sentiment_score,
                'confidence': s.confidence,
                'metadata': s.metadata,
                'created_at': s.created_at.isoformat() if s.created_at else None
            }
            for s in signal_records
        ]

        return {
            'success': True,
            'signals': signal_list,
            'count': len(signal_list)
        }

    except Exception as e:
        logger.error(f"Failed to get recent signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))
