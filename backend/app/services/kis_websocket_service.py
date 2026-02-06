"""
KIS WebSocket Service

한국투자증권 WebSocket API 통합
- 실시간 체결가
- 호가창 (10호가)
- OHLCV 데이터 (분봉)
"""

import logging
import json
import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime
import websockets
from websockets.client import WebSocketClientProtocol
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert

from ..models.realtime_price import RealtimePrice, OrderBook, OHLCV
from ..config import settings

logger = logging.getLogger(__name__)


class KISWebSocketService:
    """한국투자증권 WebSocket 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ws: Optional[WebSocketClientProtocol] = None
        self.is_connected = False
        self.subscriptions: Dict[str, List[str]] = {}  # {ticker: [tr_type1, tr_type2, ...]}
        self.callbacks: Dict[str, Callable] = {}  # {tr_type: callback_function}

        # KIS WebSocket 설정
        self.ws_url = "ws://ops.koreainvestment.com:21000"  # 실제 URL은 KIS API 문서 참조
        self.app_key = getattr(settings, 'kis_websocket_app_key', None)
        self.app_secret = getattr(settings, 'kis_websocket_app_secret', None)

    async def connect(self) -> bool:
        """
        WebSocket 연결

        Returns:
            연결 성공 여부
        """
        try:
            if not self.app_key or not self.app_secret:
                logger.error("KIS WebSocket API keys not configured")
                return False

            logger.info(f"🔌 Connecting to KIS WebSocket: {self.ws_url}")

            self.ws = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
            )

            # 인증
            await self._authenticate()

            self.is_connected = True
            logger.info("✅ KIS WebSocket connected")

            # 메시지 수신 루프 시작
            asyncio.create_task(self._receive_loop())

            return True

        except Exception as e:
            logger.error(f"Failed to connect to KIS WebSocket: {e}")
            return False

    async def disconnect(self):
        """WebSocket 연결 종료"""
        if self.ws:
            await self.ws.close()
            self.is_connected = False
            logger.info("🔌 KIS WebSocket disconnected")

    async def subscribe_realtime_price(self, ticker: str) -> bool:
        """
        실시간 체결가 구독

        Args:
            ticker: 종목 코드 (US)

        Returns:
            구독 성공 여부
        """
        try:
            if not self.is_connected:
                logger.error("WebSocket not connected")
                return False

            tr_type = "realtime_price"

            # 구독 요청 메시지 (KIS API 형식)
            subscribe_msg = {
                "header": {
                    "approval_key": self.app_key,
                    "custtype": "P",
                    "tr_type": "1",  # 등록
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": "HDFSCNT0",  # 해외주식 실시간시세 (체결가)
                        "tr_key": ticker
                    }
                }
            }

            await self.ws.send(json.dumps(subscribe_msg))

            # 구독 목록에 추가
            if ticker not in self.subscriptions:
                self.subscriptions[ticker] = []
            if tr_type not in self.subscriptions[ticker]:
                self.subscriptions[ticker].append(tr_type)

            logger.info(f"📊 Subscribed to realtime price: {ticker}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe to realtime price for {ticker}: {e}")
            return False

    async def subscribe_orderbook(self, ticker: str) -> bool:
        """
        호가창 구독

        Args:
            ticker: 종목 코드 (US)

        Returns:
            구독 성공 여부
        """
        try:
            if not self.is_connected:
                logger.error("WebSocket not connected")
                return False

            tr_type = "orderbook"

            # 구독 요청 메시지
            subscribe_msg = {
                "header": {
                    "approval_key": self.app_key,
                    "custtype": "P",
                    "tr_type": "1",
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": "HDFSCNT1",  # 해외주식 실시간호가
                        "tr_key": ticker
                    }
                }
            }

            await self.ws.send(json.dumps(subscribe_msg))

            if ticker not in self.subscriptions:
                self.subscriptions[ticker] = []
            if tr_type not in self.subscriptions[ticker]:
                self.subscriptions[ticker].append(tr_type)

            logger.info(f"📊 Subscribed to orderbook: {ticker}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe to orderbook for {ticker}: {e}")
            return False

    async def unsubscribe(self, ticker: str, tr_type: Optional[str] = None):
        """
        구독 해제

        Args:
            ticker: 종목 코드
            tr_type: 구독 타입 (None이면 모든 타입 해제)
        """
        try:
            if ticker not in self.subscriptions:
                return

            types_to_remove = [tr_type] if tr_type else self.subscriptions[ticker]

            for t in types_to_remove:
                # 구독 해제 메시지
                unsubscribe_msg = {
                    "header": {
                        "approval_key": self.app_key,
                        "custtype": "P",
                        "tr_type": "2",  # 해제
                        "content-type": "utf-8"
                    },
                    "body": {
                        "input": {
                            "tr_id": "HDFSCNT0" if t == "realtime_price" else "HDFSCNT1",
                            "tr_key": ticker
                        }
                    }
                }

                await self.ws.send(json.dumps(unsubscribe_msg))

            # 구독 목록에서 제거
            if tr_type:
                self.subscriptions[ticker].remove(tr_type)
            else:
                del self.subscriptions[ticker]

            logger.info(f"🔕 Unsubscribed from {ticker}: {types_to_remove}")

        except Exception as e:
            logger.error(f"Failed to unsubscribe from {ticker}: {e}")

    async def _authenticate(self):
        """WebSocket 인증"""
        auth_msg = {
            "header": {
                "approval_key": self.app_key,
                "custtype": "P",
                "tr_type": "3",  # 인증
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "app_key": self.app_key,
                    "app_secret": self.app_secret
                }
            }
        }

        await self.ws.send(json.dumps(auth_msg))
        logger.info("🔐 Authentication request sent")

    async def _receive_loop(self):
        """메시지 수신 루프"""
        try:
            async for message in self.ws:
                await self._handle_message(message)

        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            self.is_connected = False

    async def _handle_message(self, message: str):
        """
        수신된 메시지 처리

        Args:
            message: WebSocket 메시지 (JSON)
        """
        try:
            data = json.loads(message)

            # 메시지 타입 확인
            tr_id = data.get('header', {}).get('tr_id')

            if tr_id == "HDFSCNT0":
                # 실시간 체결가
                await self._handle_realtime_price(data)
            elif tr_id == "HDFSCNT1":
                # 호가창
                await self._handle_orderbook(data)
            else:
                logger.debug(f"Unknown tr_id: {tr_id}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _handle_realtime_price(self, data: Dict):
        """
        실시간 체결가 데이터 처리 및 DB 저장

        Args:
            data: WebSocket 메시지 데이터
        """
        try:
            body = data.get('body', {})
            output = body.get('output', {})

            ticker = output.get('rsym')  # 종목 코드
            current_price = float(output.get('last', 0))  # 현재가
            change_price = float(output.get('diff', 0))  # 전일대비
            change_rate = float(output.get('rate', 0))  # 등락률
            volume = int(output.get('tvol', 0))  # 누적 거래량
            trade_volume = int(output.get('tamt_1', 0))  # 체결량

            # DB 저장
            price_data = RealtimePrice(
                ticker=ticker,
                current_price=current_price,
                change_price=change_price,
                change_rate=change_rate,
                volume=volume,
                trade_volume=trade_volume,
                trade_time=datetime.now(),
            )

            self.db.add(price_data)
            await self.db.commit()

            logger.debug(f"✓ Saved realtime price: {ticker} ${current_price}")

        except Exception as e:
            logger.error(f"Failed to handle realtime price: {e}")
            await self.db.rollback()

    async def _handle_orderbook(self, data: Dict):
        """
        호가창 데이터 처리 및 DB 저장

        Args:
            data: WebSocket 메시지 데이터
        """
        try:
            body = data.get('body', {})
            output = body.get('output', {})

            ticker = output.get('rsym')

            # 10호가 데이터 파싱
            orderbook_data = {
                "ticker": ticker,
                "total_ask_volume": int(output.get('total_askp_rsqn', 0)),
                "total_bid_volume": int(output.get('total_bidp_rsqn', 0)),
            }

            # Ask (매도) 10호가
            for i in range(1, 11):
                orderbook_data[f"ask_price_{i}"] = float(output.get(f'askp{i}', 0))
                orderbook_data[f"ask_volume_{i}"] = int(output.get(f'askp_rsqn{i}', 0))

            # Bid (매수) 10호가
            for i in range(1, 11):
                orderbook_data[f"bid_price_{i}"] = float(output.get(f'bidp{i}', 0))
                orderbook_data[f"bid_volume_{i}"] = int(output.get(f'bidp_rsqn{i}', 0))

            # Upsert (최신 데이터로 업데이트)
            stmt = insert(OrderBook).values(**orderbook_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker'],
                set_=orderbook_data
            )

            await self.db.execute(stmt)
            await self.db.commit()

            logger.debug(f"✓ Saved orderbook: {ticker}")

        except Exception as e:
            logger.error(f"Failed to handle orderbook: {e}")
            await self.db.rollback()

    async def get_active_subscriptions(self) -> Dict[str, List[str]]:
        """
        현재 활성화된 구독 목록 조회

        Returns:
            {ticker: [tr_type1, tr_type2, ...]}
        """
        return self.subscriptions.copy()
