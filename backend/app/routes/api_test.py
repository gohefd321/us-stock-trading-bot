"""
API Test Routes
Testing endpoints for Korea Investment Securities API
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import logging

from ..dependencies import get_broker_service, get_settings
from ..services.broker_service import BrokerService
from ..config import Settings

logger = logging.getLogger(__name__)

# Initialize templates
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/api/test", tags=["api-test"])


class BuyOrderRequest(BaseModel):
    ticker: str
    quantity: int
    price: float = 0
    order_type: str = "market"


class SellOrderRequest(BaseModel):
    ticker: str
    quantity: int
    price: float = 0
    order_type: str = "market"


@router.get("/balance")
async def test_balance(broker: BrokerService = Depends(get_broker_service)):
    """Test balance inquiry API"""
    try:
        if not broker or not broker.broker:
            raise HTTPException(status_code=500, detail="Broker not initialized")

        balance = await broker.get_balance()
        return {
            "success": True,
            "data": balance
        }

    except Exception as e:
        logger.error(f"Balance test failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/price/{ticker}")
async def test_price(ticker: str, broker: BrokerService = Depends(get_broker_service)):
    """Test current price inquiry API"""
    try:
        if not broker or not broker.broker:
            raise HTTPException(status_code=500, detail="Broker not initialized")

        price = await broker.get_current_price(ticker)

        return {
            "success": True,
            "ticker": ticker,
            "price": price
        }

    except Exception as e:
        logger.error(f"Price test failed for {ticker}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/buy")
async def test_buy_order(
    request: BuyOrderRequest,
    broker: BrokerService = Depends(get_broker_service)
):
    """Test buy order API (quantity 0)"""
    try:
        if not broker or not broker.broker:
            raise HTTPException(status_code=500, detail="Broker not initialized")

        # Force quantity to 0 for safety
        result = await broker.place_order(
            ticker=request.ticker,
            quantity=0,  # Always 0 for testing
            side='buy',
            order_type=request.order_type,
            price=request.price if request.order_type == 'limit' else None
        )

        return {
            "success": True,
            "test_note": "주문 수량이 0으로 강제 설정되었습니다 (테스트 모드)",
            "data": result
        }

    except Exception as e:
        logger.error(f"Buy order test failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/sell")
async def test_sell_order(
    request: SellOrderRequest,
    broker: BrokerService = Depends(get_broker_service)
):
    """Test sell order API (quantity 0)"""
    try:
        if not broker or not broker.broker:
            raise HTTPException(status_code=500, detail="Broker not initialized")

        # Force quantity to 0 for safety
        result = await broker.place_order(
            ticker=request.ticker,
            quantity=0,  # Always 0 for testing
            side='sell',
            order_type=request.order_type,
            price=request.price if request.order_type == 'limit' else None
        )

        return {
            "success": True,
            "test_note": "주문 수량이 0으로 강제 설정되었습니다 (테스트 모드)",
            "data": result
        }

    except Exception as e:
        logger.error(f"Sell order test failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
