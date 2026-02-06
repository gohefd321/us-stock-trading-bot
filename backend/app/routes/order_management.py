"""
Order Management API Routes

주문 관리 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db
from ..services.order_management_service import OrderManagementService
from ..services.kis_rest_api import KISRestAPI
from ..config import get_settings

router = APIRouter(prefix="/api/orders", tags=["order-management"])

settings = get_settings()


class CreateBuyOrderRequest(BaseModel):
    ticker: str
    quantity: int
    order_method: str = "MARKET"  # MARKET or LIMIT
    price: Optional[float] = 0
    strategy_name: Optional[str] = None
    signal_id: Optional[int] = None
    reason: Optional[str] = None
    stop_loss_pct: Optional[float] = None  # 손절 비율 (%)
    take_profit_pct: Optional[float] = None  # 익절 비율 (%)


class CreateSellOrderRequest(BaseModel):
    ticker: str
    quantity: int
    order_method: str = "MARKET"
    price: Optional[float] = 0
    strategy_name: Optional[str] = None
    reason: Optional[str] = None


def get_kis_api() -> KISRestAPI:
    """KIS API 클라이언트 가져오기"""
    return KISRestAPI(
        app_key=settings.KOREA_INVESTMENT_API_KEY,
        app_secret=settings.KOREA_INVESTMENT_API_SECRET,
        account_number=settings.KOREA_INVESTMENT_ACCOUNT_NUMBER,
        account_password=settings.KOREA_INVESTMENT_ACCOUNT_PASSWORD or "",
        password_padding=settings.KOREA_INVESTMENT_PASSWORD_PADDING,
        is_paper=settings.KOREA_INVESTMENT_PAPER_MODE
    )


@router.post("/buy")
async def create_buy_order(
    request: CreateBuyOrderRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    매수 주문 생성

    Args:
        request: 매수 주문 요청

    Returns:
        주문 결과
    """
    kis_api = get_kis_api()
    service = OrderManagementService(db, kis_api)

    result = await service.create_buy_order(
        ticker=request.ticker,
        quantity=request.quantity,
        order_method=request.order_method,
        price=request.price,
        strategy_name=request.strategy_name,
        signal_id=request.signal_id,
        reason=request.reason,
        stop_loss_pct=request.stop_loss_pct,
        take_profit_pct=request.take_profit_pct
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.post("/sell")
async def create_sell_order(
    request: CreateSellOrderRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    매도 주문 생성

    Args:
        request: 매도 주문 요청

    Returns:
        주문 결과
    """
    kis_api = get_kis_api()
    service = OrderManagementService(db, kis_api)

    result = await service.create_sell_order(
        ticker=request.ticker,
        quantity=request.quantity,
        order_method=request.order_method,
        price=request.price,
        strategy_name=request.strategy_name,
        reason=request.reason
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.get("/status/{order_number}")
async def get_order_status(
    order_number: str,
    db: AsyncSession = Depends(get_db)
):
    """
    주문 상태 조회

    Args:
        order_number: 주문번호

    Returns:
        주문 상태
    """
    kis_api = get_kis_api()
    service = OrderManagementService(db, kis_api)

    order_status = await service.get_order_status(order_number)

    if not order_status:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_number}")

    return order_status


@router.get("/active")
async def get_active_orders(
    ticker: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    활성 주문 조회

    Args:
        ticker: 종목코드 (선택)

    Returns:
        활성 주문 리스트
    """
    kis_api = get_kis_api()
    service = OrderManagementService(db, kis_api)

    orders = await service.get_active_orders(ticker)

    return {
        "orders": orders,
        "count": len(orders)
    }


@router.get("/history")
async def get_order_history(
    ticker: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    주문 히스토리 조회

    Args:
        ticker: 종목코드 (선택)
        limit: 조회 개수

    Returns:
        주문 히스토리
    """
    kis_api = get_kis_api()
    service = OrderManagementService(db, kis_api)

    orders = await service.get_order_history(ticker, limit)

    return {
        "orders": orders,
        "count": len(orders)
    }


@router.post("/check-stop-loss-take-profit")
async def check_stop_loss_take_profit(
    db: AsyncSession = Depends(get_db)
):
    """
    손절/익절 체크 및 자동 주문

    Returns:
        생성된 주문 리스트
    """
    kis_api = get_kis_api()
    service = OrderManagementService(db, kis_api)

    triggered_orders = await service.check_stop_loss_take_profit()

    return {
        "success": True,
        "triggered_orders": triggered_orders,
        "count": len(triggered_orders)
    }
