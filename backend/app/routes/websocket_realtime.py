"""
WebSocket Real-time Data Routes

실시간 데이터 WebSocket 엔드포인트
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlalchemy import select, desc
import json
import asyncio
import logging

from ..database import get_db
from ..services.kis_websocket_service import KISWebSocketService
from ..models.realtime_price import RealtimePrice, OrderBook, OHLCV

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/realtime", tags=["realtime"])


# Global WebSocket service instance
_ws_service: KISWebSocketService = None


async def get_ws_service(db: AsyncSession = Depends(get_db)) -> KISWebSocketService:
    """WebSocket 서비스 싱글톤"""
    global _ws_service
    if _ws_service is None:
        _ws_service = KISWebSocketService(db)
        await _ws_service.connect()
    return _ws_service


@router.post("/connect")
async def connect_websocket(
    db: AsyncSession = Depends(get_db)
):
    """
    KIS WebSocket 연결

    Returns:
        연결 상태
    """
    service = await get_ws_service(db)

    if service.is_connected:
        return {"success": True, "message": "Already connected"}

    success = await service.connect()

    if success:
        return {"success": True, "message": "WebSocket connected"}
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to WebSocket")


@router.post("/disconnect")
async def disconnect_websocket(
    db: AsyncSession = Depends(get_db)
):
    """
    KIS WebSocket 연결 종료

    Returns:
        연결 종료 결과
    """
    service = await get_ws_service(db)
    await service.disconnect()
    return {"success": True, "message": "WebSocket disconnected"}


@router.post("/subscribe/price/{ticker}")
async def subscribe_price(
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    실시간 체결가 구독

    Args:
        ticker: 종목 코드

    Returns:
        구독 성공 여부
    """
    service = await get_ws_service(db)
    success = await service.subscribe_realtime_price(ticker)

    if success:
        return {"success": True, "ticker": ticker, "message": f"Subscribed to {ticker} realtime price"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to subscribe to {ticker}")


@router.post("/subscribe/orderbook/{ticker}")
async def subscribe_orderbook(
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    호가창 구독

    Args:
        ticker: 종목 코드

    Returns:
        구독 성공 여부
    """
    service = await get_ws_service(db)
    success = await service.subscribe_orderbook(ticker)

    if success:
        return {"success": True, "ticker": ticker, "message": f"Subscribed to {ticker} orderbook"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to subscribe to {ticker}")


@router.post("/unsubscribe/{ticker}")
async def unsubscribe(
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    구독 해제

    Args:
        ticker: 종목 코드

    Returns:
        구독 해제 결과
    """
    service = await get_ws_service(db)
    await service.unsubscribe(ticker)
    return {"success": True, "ticker": ticker, "message": f"Unsubscribed from {ticker}"}


@router.get("/subscriptions")
async def get_subscriptions(
    db: AsyncSession = Depends(get_db)
):
    """
    현재 활성화된 구독 목록 조회

    Returns:
        구독 목록
    """
    service = await get_ws_service(db)
    subscriptions = await service.get_active_subscriptions()
    return {"subscriptions": subscriptions, "count": len(subscriptions)}


@router.get("/price/{ticker}/latest")
async def get_latest_price(
    ticker: str,
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    최근 체결가 조회 (DB에서)

    Args:
        ticker: 종목 코드
        limit: 조회할 데이터 수

    Returns:
        최근 체결가 리스트
    """
    try:
        stmt = (
            select(RealtimePrice)
            .where(RealtimePrice.ticker == ticker)
            .order_by(desc(RealtimePrice.trade_time))
            .limit(limit)
        )

        result = await db.execute(stmt)
        prices = result.scalars().all()

        return {
            "ticker": ticker,
            "prices": [
                {
                    "price": p.current_price,
                    "change": p.change_price,
                    "change_rate": p.change_rate,
                    "volume": p.volume,
                    "time": p.trade_time.isoformat() if p.trade_time else None,
                }
                for p in prices
            ],
            "count": len(prices)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orderbook/{ticker}/latest")
async def get_latest_orderbook(
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    최신 호가창 조회 (DB에서)

    Args:
        ticker: 종목 코드

    Returns:
        최신 호가창 데이터
    """
    try:
        stmt = (
            select(OrderBook)
            .where(OrderBook.ticker == ticker)
            .order_by(desc(OrderBook.updated_at))
            .limit(1)
        )

        result = await db.execute(stmt)
        orderbook = result.scalar_one_or_none()

        if not orderbook:
            raise HTTPException(status_code=404, detail=f"No orderbook data for {ticker}")

        # Ask 10호가
        asks = [
            {"price": getattr(orderbook, f"ask_price_{i}"), "volume": getattr(orderbook, f"ask_volume_{i}")}
            for i in range(1, 11)
        ]

        # Bid 10호가
        bids = [
            {"price": getattr(orderbook, f"bid_price_{i}"), "volume": getattr(orderbook, f"bid_volume_{i}")}
            for i in range(1, 11)
        ]

        return {
            "ticker": ticker,
            "asks": asks,
            "bids": bids,
            "total_ask_volume": orderbook.total_ask_volume,
            "total_bid_volume": orderbook.total_bid_volume,
            "updated_at": orderbook.updated_at.isoformat() if orderbook.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ohlcv/{ticker}")
async def get_ohlcv(
    ticker: str,
    timeframe: str = Query(default="1m", description="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)"),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """
    OHLCV 데이터 조회

    Args:
        ticker: 종목 코드
        timeframe: 시간 프레임
        limit: 조회할 캔들 수

    Returns:
        OHLCV 데이터
    """
    try:
        stmt = (
            select(OHLCV)
            .where(OHLCV.ticker == ticker)
            .where(OHLCV.timeframe == timeframe)
            .order_by(desc(OHLCV.timestamp))
            .limit(limit)
        )

        result = await db.execute(stmt)
        candles = result.scalars().all()

        return {
            "ticker": ticker,
            "timeframe": timeframe,
            "candles": [
                {
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                    "vwap": c.vwap,
                    "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                }
                for c in reversed(candles)  # 오래된 것부터 정렬
            ],
            "count": len(candles)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{ticker}")
async def websocket_endpoint(
    websocket: WebSocket,
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    클라이언트용 WebSocket 엔드포인트 (실시간 데이터 스트리밍)

    Args:
        websocket: WebSocket 연결
        ticker: 종목 코드
    """
    await websocket.accept()

    try:
        # KIS WebSocket 구독
        service = await get_ws_service(db)
        await service.subscribe_realtime_price(ticker)

        # 실시간 데이터 전송 루프
        while True:
            # DB에서 최신 데이터 조회
            stmt = (
                select(RealtimePrice)
                .where(RealtimePrice.ticker == ticker)
                .order_by(desc(RealtimePrice.trade_time))
                .limit(1)
            )
            result = await db.execute(stmt)
            latest_price = result.scalar_one_or_none()

            if latest_price:
                await websocket.send_json({
                    "type": "realtime_price",
                    "ticker": ticker,
                    "price": latest_price.current_price,
                    "change": latest_price.change_price,
                    "change_rate": latest_price.change_rate,
                    "volume": latest_price.volume,
                    "time": latest_price.trade_time.isoformat() if latest_price.trade_time else None,
                })

            await asyncio.sleep(1)  # 1초마다 업데이트

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {ticker}")
        await service.unsubscribe(ticker)
    except Exception as e:
        logger.error(f"WebSocket error for {ticker}: {e}")
        await websocket.close()
