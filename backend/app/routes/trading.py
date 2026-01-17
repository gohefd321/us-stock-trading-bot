"""
Trading API Routes
Manual trading operations and analysis
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
from pydantic import BaseModel
import logging

from ..services.trading_engine import TradingEngine
from ..dependencies import get_trading_engine

router = APIRouter(prefix="/api/trading", tags=["trading"])
logger = logging.getLogger(__name__)


class AnalyzeTickerRequest(BaseModel):
    """Request model for ticker analysis"""
    ticker: str


@router.post("/analyze")
async def analyze_ticker(
    request: AnalyzeTickerRequest,
    engine: TradingEngine = Depends(get_trading_engine)
) -> Dict:
    """
    Analyze a specific ticker for trading opportunities

    Args:
        request: Ticker to analyze

    Returns:
        Analysis result with signals and AI recommendation
    """
    try:
        result = await engine.analyze_ticker_on_demand(request.ticker)

        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Analysis failed'))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze ticker {request.ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_trading_history(
    days: int = Query(default=7, ge=1, le=90),
    engine: TradingEngine = Depends(get_trading_engine)
) -> Dict:
    """
    Get recent trading history

    Args:
        days: Number of days to look back (1-90)

    Returns:
        Trading history
    """
    try:
        # Use the function handler to get trading history
        from ..dependencies import get_function_handler
        handler = get_function_handler()

        result = await handler.get_trading_history(days_back=days)

        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Failed to get history'))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trading history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decisions")
async def get_llm_decisions(
    limit: int = Query(default=20, ge=1, le=100),
    engine: TradingEngine = Depends(get_trading_engine)
) -> Dict:
    """
    Get recent LLM trading decisions

    Args:
        limit: Number of decisions to retrieve

    Returns:
        List of LLM decisions
    """
    try:
        from sqlalchemy import select, desc
        from ..models import LLMDecision

        stmt = select(LLMDecision).order_by(desc(LLMDecision.created_at)).limit(limit)
        result = await engine.db.execute(stmt)
        decisions = result.scalars().all()

        decision_list = [
            {
                'id': d.id,
                'decision_type': d.decision_type,
                'reasoning': d.reasoning[:500] if d.reasoning else '',  # Truncate for API
                'confidence_score': d.confidence_score,
                'created_at': d.created_at.isoformat() if d.created_at else None
            }
            for d in decisions
        ]

        return {
            'success': True,
            'decisions': decision_list,
            'count': len(decision_list)
        }

    except Exception as e:
        logger.error(f"Failed to get LLM decisions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decisions/{decision_id}")
async def get_decision_detail(
    decision_id: int,
    engine: TradingEngine = Depends(get_trading_engine)
) -> Dict:
    """
    Get detailed information about a specific LLM decision

    Args:
        decision_id: Decision ID

    Returns:
        Detailed decision information
    """
    try:
        from sqlalchemy import select
        from ..models import LLMDecision
        import json

        stmt = select(LLMDecision).where(LLMDecision.id == decision_id)
        result = await engine.db.execute(stmt)
        decision = result.scalar_one_or_none()

        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        return {
            'success': True,
            'decision': {
                'id': decision.id,
                'decision_type': decision.decision_type,
                'prompt': decision.prompt,
                'response': decision.response,
                'reasoning': decision.reasoning,
                'confidence_score': decision.confidence_score,
                'function_calls': json.loads(decision.function_calls) if decision.function_calls else [],
                'signals_used': json.loads(decision.signals_used) if decision.signals_used else [],
                'portfolio_state': json.loads(decision.portfolio_state) if decision.portfolio_state else {},
                'created_at': decision.created_at.isoformat() if decision.created_at else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get decision detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
