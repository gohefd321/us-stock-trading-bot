"""
Order Management Service

한국투자증권 주문 관리 서비스
- 주문 생성, 수정, 취소
- 주문 상태 추적
- 체결 확인
"""

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.order import Order
from ..models.portfolio_position import PortfolioPosition
from .kis_rest_api import KISRestAPI

logger = logging.getLogger(__name__)


class OrderManagementService:
    """주문 관리 서비스"""

    def __init__(self, db: AsyncSession, kis_api: KISRestAPI):
        self.db = db
        self.kis_api = kis_api

    async def create_buy_order(
        self,
        ticker: str,
        quantity: int,
        order_method: str = "MARKET",
        price: float = 0,
        strategy_name: str = None,
        signal_id: int = None,
        reason: str = None,
        stop_loss_pct: float = None,
        take_profit_pct: float = None
    ) -> Dict:
        """
        매수 주문 생성

        Args:
            ticker: 종목코드
            quantity: 수량
            order_method: 주문방식 (MARKET, LIMIT)
            price: 지정가 (LIMIT 주문 시)
            strategy_name: 전략명
            signal_id: 신호 ID
            reason: 주문 사유
            stop_loss_pct: 손절 비율 (%)
            take_profit_pct: 익절 비율 (%)

        Returns:
            주문 결과
        """
        try:
            logger.info(f"Creating BUY order: {ticker} x {quantity} ({order_method})")

            # 현재가 조회 (시장가 주문이거나 손절/익절 설정 시)
            current_price = None
            if order_method == "MARKET" or stop_loss_pct or take_profit_pct:
                current_price = await self.kis_api.get_us_stock_price(ticker)
                if not current_price:
                    return {
                        "success": False,
                        "error": f"Failed to get current price for {ticker}"
                    }
                logger.info(f"Current price for {ticker}: ${current_price}")

            # KIS API로 주문 전송
            kis_order_type = "market" if order_method == "MARKET" else "limit"
            order_price = price if order_method == "LIMIT" else current_price

            result = await self.kis_api.buy_us_stock(
                ticker=ticker,
                quantity=quantity,
                price=order_price if order_method == "LIMIT" else 0,
                order_type=kis_order_type
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Order failed")
                }

            # 주문 정보 DB 저장
            order = Order(
                order_number=result.get("order_number"),
                ticker=ticker,
                market_type="US",
                order_type="BUY",
                order_method=order_method,
                order_quantity=quantity,
                order_price=order_price,
                status="SUBMITTED",
                strategy_name=strategy_name,
                signal_id=signal_id,
                reason=reason,
                broker_response=json.dumps(result),
                risk_checked=True
            )

            # 손절/익절가 설정
            if stop_loss_pct and current_price:
                order.stop_loss_price = current_price * (1 - stop_loss_pct / 100)

            if take_profit_pct and current_price:
                order.take_profit_price = current_price * (1 + take_profit_pct / 100)

            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)

            logger.info(f"✓ Order created: {order.order_number}")

            return {
                "success": True,
                "order_id": order.id,
                "order_number": order.order_number,
                "message": "Buy order created successfully"
            }

        except Exception as e:
            logger.error(f"Failed to create buy order: {e}")
            await self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def create_sell_order(
        self,
        ticker: str,
        quantity: int,
        order_method: str = "MARKET",
        price: float = 0,
        strategy_name: str = None,
        reason: str = None
    ) -> Dict:
        """
        매도 주문 생성

        Args:
            ticker: 종목코드
            quantity: 수량
            order_method: 주문방식
            price: 지정가
            strategy_name: 전략명
            reason: 주문 사유

        Returns:
            주문 결과
        """
        try:
            logger.info(f"Creating SELL order: {ticker} x {quantity} ({order_method})")

            # 보유 수량 확인
            position = await self._get_position(ticker)
            if not position or position.quantity < quantity:
                return {
                    "success": False,
                    "error": f"Insufficient quantity. Have: {position.quantity if position else 0}, Want to sell: {quantity}"
                }

            # 현재가 조회
            current_price = None
            if order_method == "MARKET":
                current_price = await self.kis_api.get_us_stock_price(ticker)
                if not current_price:
                    return {
                        "success": False,
                        "error": f"Failed to get current price for {ticker}"
                    }

            # KIS API로 주문 전송
            kis_order_type = "market" if order_method == "MARKET" else "limit"
            order_price = price if order_method == "LIMIT" else current_price

            result = await self.kis_api.sell_us_stock(
                ticker=ticker,
                quantity=quantity,
                price=order_price if order_method == "LIMIT" else 0,
                order_type=kis_order_type
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Order failed")
                }

            # 주문 정보 DB 저장
            order = Order(
                order_number=result.get("order_number"),
                ticker=ticker,
                market_type="US",
                order_type="SELL",
                order_method=order_method,
                order_quantity=quantity,
                order_price=order_price,
                status="SUBMITTED",
                strategy_name=strategy_name,
                reason=reason,
                broker_response=json.dumps(result),
                risk_checked=True
            )

            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)

            logger.info(f"✓ Order created: {order.order_number}")

            return {
                "success": True,
                "order_id": order.id,
                "order_number": order.order_number,
                "message": "Sell order created successfully"
            }

        except Exception as e:
            logger.error(f"Failed to create sell order: {e}")
            await self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def get_order_status(self, order_number: str) -> Optional[Dict]:
        """
        주문 상태 조회

        Args:
            order_number: 주문번호

        Returns:
            주문 상태 정보
        """
        try:
            result = await self.db.execute(
                select(Order).where(Order.order_number == order_number)
            )
            order = result.scalar_one_or_none()

            if not order:
                return None

            return {
                "order_id": order.id,
                "order_number": order.order_number,
                "ticker": order.ticker,
                "order_type": order.order_type,
                "order_method": order.order_method,
                "order_quantity": order.order_quantity,
                "filled_quantity": order.filled_quantity,
                "status": order.status,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "is_active": order.is_active(),
                "fill_rate": order.fill_rate()
            }

        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
            return None

    async def get_active_orders(self, ticker: Optional[str] = None) -> List[Dict]:
        """
        활성 주문 조회

        Args:
            ticker: 종목코드 (선택)

        Returns:
            활성 주문 리스트
        """
        try:
            query = select(Order).where(
                Order.status.in_(["SUBMITTED", "PENDING", "PARTIAL_FILLED"])
            )

            if ticker:
                query = query.where(Order.ticker == ticker)

            query = query.order_by(Order.submitted_at.desc())

            result = await self.db.execute(query)
            orders = result.scalars().all()

            return [
                {
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "ticker": order.ticker,
                    "order_type": order.order_type,
                    "order_quantity": order.order_quantity,
                    "filled_quantity": order.filled_quantity,
                    "status": order.status,
                    "submitted_at": order.submitted_at.isoformat()
                }
                for order in orders
            ]

        except Exception as e:
            logger.error(f"Failed to get active orders: {e}")
            return []

    async def get_order_history(
        self,
        ticker: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        주문 히스토리 조회

        Args:
            ticker: 종목코드 (선택)
            limit: 조회 개수

        Returns:
            주문 히스토리
        """
        try:
            query = select(Order)

            if ticker:
                query = query.where(Order.ticker == ticker)

            query = query.order_by(Order.submitted_at.desc()).limit(limit)

            result = await self.db.execute(query)
            orders = result.scalars().all()

            return [
                {
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "ticker": order.ticker,
                    "order_type": order.order_type,
                    "order_quantity": order.order_quantity,
                    "filled_quantity": order.filled_quantity,
                    "avg_filled_price": order.avg_filled_price,
                    "status": order.status,
                    "strategy_name": order.strategy_name,
                    "reason": order.reason,
                    "submitted_at": order.submitted_at.isoformat(),
                    "filled_at": order.filled_at.isoformat() if order.filled_at else None
                }
                for order in orders
            ]

        except Exception as e:
            logger.error(f"Failed to get order history: {e}")
            return []

    async def update_order_status(
        self,
        order_number: str,
        status: str,
        filled_quantity: int = 0,
        avg_filled_price: float = 0,
        filled_at: datetime = None
    ) -> bool:
        """
        주문 상태 업데이트 (체결 확인 시)

        Args:
            order_number: 주문번호
            status: 상태
            filled_quantity: 체결수량
            avg_filled_price: 평균체결가
            filled_at: 체결시각

        Returns:
            성공 여부
        """
        try:
            result = await self.db.execute(
                select(Order).where(Order.order_number == order_number)
            )
            order = result.scalar_one_or_none()

            if not order:
                logger.warning(f"Order not found: {order_number}")
                return False

            order.status = status
            order.filled_quantity = filled_quantity
            order.avg_filled_price = avg_filled_price
            order.filled_at = filled_at or datetime.now()

            if filled_quantity > 0 and avg_filled_price > 0:
                order.filled_amount = filled_quantity * avg_filled_price

            await self.db.commit()

            # 체결 완료 시 포지션 업데이트
            if status == "FILLED":
                await self._update_position_from_order(order)

            logger.info(f"✓ Order status updated: {order_number} -> {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update order status: {e}")
            await self.db.rollback()
            return False

    async def _update_position_from_order(self, order: Order):
        """주문 체결 후 포지션 업데이트"""
        try:
            position = await self._get_position(order.ticker)

            if order.order_type == "BUY":
                if position:
                    # 기존 포지션 업데이트
                    total_quantity = position.quantity + order.filled_quantity
                    total_invested = position.total_invested + order.filled_amount

                    position.quantity = total_quantity
                    position.avg_buy_price = total_invested / total_quantity
                    position.total_invested = total_invested
                else:
                    # 신규 포지션 생성
                    position = PortfolioPosition(
                        ticker=order.ticker,
                        market_type=order.market_type,
                        quantity=order.filled_quantity,
                        avg_buy_price=order.avg_filled_price,
                        total_invested=order.filled_amount,
                        entry_strategy=order.strategy_name,
                        entry_signal_id=order.signal_id,
                        entry_date=order.filled_at,
                        stop_loss_price=order.stop_loss_price,
                        take_profit_price=order.take_profit_price
                    )
                    self.db.add(position)

            elif order.order_type == "SELL":
                if position:
                    # 실현 손익 계산
                    sell_amount = order.filled_amount
                    cost_basis = position.avg_buy_price * order.filled_quantity
                    realized_pnl = sell_amount - cost_basis

                    position.quantity -= order.filled_quantity
                    position.total_invested -= cost_basis
                    position.realized_pnl += realized_pnl

                    if position.total_invested > 0:
                        position.realized_pnl_pct = (position.realized_pnl / position.total_invested) * 100

                    # 포지션 전량 청산 시 삭제
                    if position.quantity <= 0:
                        await self.db.delete(position)
                        logger.info(f"Position closed: {order.ticker}")

            await self.db.commit()
            logger.info(f"✓ Position updated for {order.ticker}")

        except Exception as e:
            logger.error(f"Failed to update position: {e}")
            await self.db.rollback()

    async def _get_position(self, ticker: str) -> Optional[PortfolioPosition]:
        """포지션 조회"""
        result = await self.db.execute(
            select(PortfolioPosition).where(PortfolioPosition.ticker == ticker)
        )
        return result.scalar_one_or_none()

    async def check_stop_loss_take_profit(self) -> List[Dict]:
        """
        손절/익절 체크 및 자동 주문

        Returns:
            생성된 주문 리스트
        """
        try:
            # 모든 포지션 조회
            result = await self.db.execute(
                select(PortfolioPosition).where(PortfolioPosition.quantity > 0)
            )
            positions = result.scalars().all()

            triggered_orders = []

            for position in positions:
                # 현재가 업데이트
                current_price = await self.kis_api.get_us_stock_price(position.ticker)
                if not current_price:
                    continue

                position.calculate_metrics(current_price)

                # 손절 체크
                if position.should_stop_loss():
                    logger.warning(f"🚨 Stop loss triggered for {position.ticker}: ${current_price} <= ${position.stop_loss_price}")

                    order_result = await self.create_sell_order(
                        ticker=position.ticker,
                        quantity=position.quantity,
                        order_method="MARKET",
                        reason=f"Stop loss triggered at ${current_price}"
                    )

                    if order_result.get("success"):
                        triggered_orders.append({
                            "ticker": position.ticker,
                            "type": "STOP_LOSS",
                            "order_number": order_result.get("order_number")
                        })

                # 익절 체크
                elif position.should_take_profit():
                    logger.info(f"🎯 Take profit triggered for {position.ticker}: ${current_price} >= ${position.take_profit_price}")

                    order_result = await self.create_sell_order(
                        ticker=position.ticker,
                        quantity=position.quantity,
                        order_method="MARKET",
                        reason=f"Take profit triggered at ${current_price}"
                    )

                    if order_result.get("success"):
                        triggered_orders.append({
                            "ticker": position.ticker,
                            "type": "TAKE_PROFIT",
                            "order_number": order_result.get("order_number")
                        })

            await self.db.commit()
            return triggered_orders

        except Exception as e:
            logger.error(f"Failed to check stop loss/take profit: {e}")
            return []
