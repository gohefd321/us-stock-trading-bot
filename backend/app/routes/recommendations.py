"""
Trading Recommendations Routes
API routes for AI-generated trading recommendations with user approval
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Optional
from datetime import datetime
import logging

from ..database import get_db
from ..dependencies import get_market_data_scheduler, get_portfolio_manager, get_broker_service
from ..services.market_data_scheduler import MarketDataScheduler
from ..services.portfolio_manager import PortfolioManager
from ..services.broker_service import BrokerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/latest")
async def get_latest_recommendation(
    scheduler: MarketDataScheduler = Depends(get_market_data_scheduler)
) -> Dict:
    """
    Get the latest AI-generated trading recommendation

    Returns:
        {
            'recommendations': [
                {
                    'action': 'BUY' | 'SELL' | 'HOLD',
                    'ticker': str,
                    'percentage': float,
                    'rationale': str,
                    'confidence': float
                }
            ],
            'summary': str,
            'timestamp': str,
            'market_phase': str
        }
    """
    try:
        recommendation = scheduler.get_latest_recommendation()

        if not recommendation:
            return {
                'recommendations': [],
                'summary': '아직 추천이 생성되지 않았습니다.',
                'timestamp': datetime.now().isoformat(),
                'market_phase': 'none'
            }

        return recommendation

    except Exception as e:
        logger.error(f"[RECOMMEND] Failed to fetch latest recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_recommendation(
    ticker: str,
    action: str,
    percentage: float,
    portfolio_manager: PortfolioManager = Depends(get_portfolio_manager),
    broker: BrokerService = Depends(get_broker_service),
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Execute a trading recommendation

    Args:
        ticker: Stock ticker symbol
        action: BUY, SELL, or HOLD
        percentage: Percentage of portfolio (BUY) or position (SELL)

    Returns:
        {
            'success': bool,
            'message': str,
            'order_id': str (optional),
            'executed_quantity': int (optional),
            'executed_price': float (optional)
        }
    """
    try:
        # Validate action
        action = action.upper()
        if action not in ['BUY', 'SELL', 'HOLD']:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

        # HOLD doesn't require execution
        if action == 'HOLD':
            return {
                'success': True,
                'message': f'{ticker} 포지션을 유지합니다.'
            }

        # Get current portfolio state
        portfolio_state = await portfolio_manager.get_current_state()

        if action == 'BUY':
            # Calculate buy amount based on percentage of cash
            cash_balance = portfolio_state.get('cash_balance', 0)

            if cash_balance <= 0:
                raise HTTPException(status_code=400, detail="현금 잔고가 부족합니다.")

            # Calculate amount to invest
            invest_amount = cash_balance * (percentage / 100)

            if invest_amount < 1:
                raise HTTPException(status_code=400, detail="투자 금액이 너무 적습니다.")

            # Get current price
            current_price = await broker.get_current_price(ticker)

            if not current_price or current_price <= 0:
                raise HTTPException(status_code=400, detail=f"{ticker} 가격 정보를 가져올 수 없습니다.")

            # Calculate quantity (fractional shares not supported, round down)
            quantity = int(invest_amount / current_price)

            if quantity < 1:
                raise HTTPException(status_code=400, detail=f"매수 가능 수량이 부족합니다. (현재가: ${current_price:.2f})")

            logger.info(f"[RECOMMEND] Executing BUY: {ticker} x {quantity} @ ${current_price:.2f}")

            # Execute buy order
            order_result = await broker.place_order(
                ticker=ticker,
                quantity=quantity,
                side='buy',
                order_type='market'
            )

            if not order_result or not order_result.get('success'):
                error_msg = order_result.get('message', '알 수 없는 오류') if order_result else '주문 실패'
                raise HTTPException(status_code=500, detail=f"매수 주문 실패: {error_msg}")

            return {
                'success': True,
                'message': f'{ticker} {quantity}주 매수 완료',
                'order_id': order_result.get('order_id'),
                'executed_quantity': quantity,
                'executed_price': current_price
            }

        elif action == 'SELL':
            # Find position
            positions = portfolio_state.get('positions', [])
            position = next((p for p in positions if p.get('ticker') == ticker), None)

            if not position:
                raise HTTPException(status_code=400, detail=f"{ticker} 포지션을 찾을 수 없습니다.")

            # Calculate sell quantity based on percentage
            total_quantity = position.get('quantity', 0)

            if total_quantity <= 0:
                raise HTTPException(status_code=400, detail=f"{ticker} 보유 수량이 없습니다.")

            # Calculate quantity to sell
            sell_quantity = int(total_quantity * (percentage / 100))

            if sell_quantity < 1:
                raise HTTPException(status_code=400, detail="매도 수량이 너무 적습니다.")

            # Don't sell more than we have
            sell_quantity = min(sell_quantity, total_quantity)

            logger.info(f"[RECOMMEND] Executing SELL: {ticker} x {sell_quantity} (보유: {total_quantity}주)")

            # Execute sell order
            order_result = await broker.place_order(
                ticker=ticker,
                quantity=sell_quantity,
                side='sell',
                order_type='market'
            )

            if not order_result or not order_result.get('success'):
                error_msg = order_result.get('message', '알 수 없는 오류') if order_result else '주문 실패'
                raise HTTPException(status_code=500, detail=f"매도 주문 실패: {error_msg}")

            current_price = position.get('current_price', 0)

            return {
                'success': True,
                'message': f'{ticker} {sell_quantity}주 매도 완료',
                'order_id': order_result.get('order_id'),
                'executed_quantity': sell_quantity,
                'executed_price': current_price
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RECOMMEND] Failed to execute recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"추천 실행 실패: {str(e)}")


@router.get("/status")
async def get_recommendation_status(
    scheduler: MarketDataScheduler = Depends(get_market_data_scheduler)
) -> Dict:
    """
    Get recommendation system status

    Returns scheduler status and latest recommendation metadata
    """
    try:
        scheduler_status = scheduler.get_status()
        latest_rec = scheduler.get_latest_recommendation()

        return {
            'scheduler': scheduler_status,
            'latest_recommendation': {
                'timestamp': latest_rec.get('timestamp') if latest_rec else None,
                'market_phase': latest_rec.get('market_phase') if latest_rec else None,
                'count': len(latest_rec.get('recommendations', [])) if latest_rec else 0
            }
        }

    except Exception as e:
        logger.error(f"[RECOMMEND] Failed to get status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
