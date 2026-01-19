"""
Korea Investment Securities Broker Service
Wrapper for Mojito2 library for US stock trading
"""

import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import mojito

logger = logging.getLogger(__name__)


class BrokerService:
    """Service for interacting with Korea Investment Securities API"""

    def __init__(self, settings):
        """
        Initialize broker service

        Args:
            settings: Application settings with API credentials
        """
        # Import here to avoid circular dependency
        from ..config import Settings

        self.api_key = settings.korea_investment_api_key
        self.api_secret = settings.korea_investment_api_secret
        self.account_number = settings.korea_investment_account_number
        self.is_paper = settings.korea_investment_paper_mode
        self.broker = None
        self.token_created_at = None

        # Only initialize broker if credentials are provided
        if not self.api_key or not self.api_secret or not self.account_number:
            logger.warning("Korea Investment API credentials not configured. Broker service will be unavailable.")
            logger.warning("Please configure API keys in .env file or via WebUI settings.")
            return

        # Initialize Mojito broker
        self._initialize_broker()

    def _initialize_broker(self):
        """Initialize or reinitialize broker with access token"""
        try:
            self.broker = mojito.KoreaInvestment(
                api_key=self.api_key,
                api_secret=self.api_secret,
                acc_no=self.account_number,
                mock=self.is_paper
            )
            self.token_created_at = datetime.now()
            logger.info(f"Broker initialized (paper_mode={self.is_paper})")
            logger.info(f"Access token created at: {self.token_created_at.isoformat()}")
        except Exception as e:
            logger.error(f"Failed to initialize broker: {e}")
            logger.warning("Broker service will be unavailable. Please check your API credentials.")
            self.broker = None
            self.token_created_at = None

    def refresh_token(self):
        """Refresh access token (call every 22 hours)"""
        if not self.api_key or not self.api_secret or not self.account_number:
            logger.warning("Cannot refresh token: API credentials not configured")
            return False

        logger.info("Refreshing access token...")
        self._initialize_broker()
        return self.broker is not None

    def needs_token_refresh(self) -> bool:
        """Check if token needs refresh (older than 22 hours)"""
        if not self.token_created_at:
            return True

        age = datetime.now() - self.token_created_at
        needs_refresh = age > timedelta(hours=22)

        if needs_refresh:
            logger.warning(f"Token is {age.total_seconds() / 3600:.1f} hours old, needs refresh")

        return needs_refresh

    def reload_credentials(self, api_key: str, api_secret: str, account_number: str, is_paper: bool):
        """Reload broker with new credentials"""
        logger.info("Reloading broker with new credentials...")
        self.api_key = api_key
        self.api_secret = api_secret
        self.account_number = account_number
        self.is_paper = is_paper
        self._initialize_broker()

    async def get_balance(self) -> Dict:
        """
        Get account balance (cash + stocks)

        Returns:
            Dictionary with balance information
        """
        if not self.broker:
            logger.error("Broker not initialized. Cannot fetch balance.")
            raise RuntimeError("Broker service not initialized. Please configure API credentials.")

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            balance_data = await loop.run_in_executor(
                None,
                self.broker.fetch_balance
            )

            # Log raw response for debugging
            logger.debug(f"Balance API response: {balance_data}")

            # Try to extract balance information
            # API response format varies, try different keys
            cash_balance = 0
            total_value = 0

            # Try output2 format (Korean stocks)
            if 'output2' in balance_data and balance_data['output2']:
                output2 = balance_data['output2'][0] if isinstance(balance_data['output2'], list) else balance_data['output2']
                cash_balance = float(output2.get('dnca_tot_amt', 0))
                total_value = float(output2.get('tot_evlu_amt', 0))

            # Try output1 format (alternative)
            elif 'output1' in balance_data and balance_data['output1']:
                output1 = balance_data['output1'][0] if isinstance(balance_data['output1'], list) else balance_data['output1']
                cash_balance = float(output1.get('prvs_rcdl_excc_amt', 0))  # 예수금
                total_value = float(output1.get('tot_evlu_amt', 0))

            # If still no data, return zeros
            if cash_balance == 0 and total_value == 0:
                logger.warning("Could not extract balance from API response")

            result = {
                'cash_balance': cash_balance,
                'total_value': total_value,
                'holdings_value': total_value - cash_balance,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Balance fetched: Cash={cash_balance}, Total={total_value}")
            return result

        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            # Return zeros instead of raising
            return {
                'cash_balance': 0,
                'total_value': 0,
                'holdings_value': 0,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }

    async def get_us_stock_price(self, ticker: str) -> Optional[float]:
        """
        Get current price for US stock

        Args:
            ticker: Stock ticker symbol (e.g., AAPL)

        Returns:
            Current price or None if failed
        """
        if not self.broker:
            logger.error("Broker not initialized. Cannot fetch price.")
            return None

        try:
            loop = asyncio.get_event_loop()
            price_data = await loop.run_in_executor(
                None,
                self.broker.fetch_price,
                ticker
            )

            # Extract current price
            current_price = float(price_data.get('output', {}).get('last', 0))

            if current_price > 0:
                logger.debug(f"Price for {ticker}: ${current_price}")
                return current_price
            else:
                logger.warning(f"Invalid price for {ticker}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch price for {ticker}: {e}")
            return None

    async def place_us_order(
        self,
        ticker: str,
        action: str,
        quantity: int,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None
    ) -> Dict:
        """
        Place order for US stock

        Args:
            ticker: Stock ticker symbol
            action: 'BUY' or 'SELL'
            quantity: Number of shares
            order_type: 'MARKET' or 'LIMIT'
            limit_price: Limit price (required for LIMIT orders)

        Returns:
            Order result dictionary
        """
        if not self.broker:
            logger.error("Broker not initialized. Cannot place order.")
            return {
                'success': False,
                'error': 'Broker service not initialized. Please configure API credentials.',
                'timestamp': datetime.now().isoformat()
            }

        try:
            logger.info(f"Placing order: {action} {quantity} {ticker} ({order_type})")

            loop = asyncio.get_event_loop()

            if action == "BUY":
                if order_type == "MARKET":
                    result = await loop.run_in_executor(
                        None,
                        self.broker.create_market_buy_order,
                        ticker,
                        quantity
                    )
                else:  # LIMIT
                    result = await loop.run_in_executor(
                        None,
                        self.broker.create_limit_buy_order,
                        ticker,
                        limit_price,
                        quantity
                    )
            else:  # SELL
                if order_type == "MARKET":
                    result = await loop.run_in_executor(
                        None,
                        self.broker.create_market_sell_order,
                        ticker,
                        quantity
                    )
                else:  # LIMIT
                    result = await loop.run_in_executor(
                        None,
                        self.broker.create_limit_sell_order,
                        ticker,
                        limit_price,
                        quantity
                    )

            # Parse result
            order_info = {
                'success': result.get('rt_cd') == '0',
                'order_id': result.get('output', {}).get('ODNO', ''),
                'message': result.get('msg1', ''),
                'timestamp': datetime.now().isoformat(),
                'raw_response': result
            }

            if order_info['success']:
                logger.info(f"Order placed successfully: {order_info['order_id']}")
            else:
                logger.error(f"Order failed: {order_info['message']}")

            return order_info

        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def get_us_positions(self) -> List[Dict]:
        """
        Get all US stock positions

        Returns:
            List of position dictionaries
        """
        if not self.broker:
            logger.error("Broker not initialized. Cannot fetch positions.")
            return []

        try:
            loop = asyncio.get_event_loop()
            positions_data = await loop.run_in_executor(
                None,
                self.broker.fetch_present_balance
            )

            positions = []
            output = positions_data.get('output1', [])

            for pos in output:
                # Only include US stocks
                if pos.get('ovrs_excg_cd') == 'NASD' or pos.get('ovrs_excg_cd') == 'NYSE':
                    ticker = pos.get('ovrs_pdno', '')
                    quantity = int(pos.get('ord_psbl_qty', 0))
                    avg_cost = float(pos.get('pchs_avg_pric', 0))
                    current_price = float(pos.get('now_pric2', 0))
                    total_value = float(pos.get('ovrs_stck_evlu_amt', 0))
                    profit_loss = float(pos.get('frcr_evlu_pfls_amt', 0))
                    profit_loss_pct = float(pos.get('evlu_pfls_rt', 0))

                    if quantity > 0:
                        positions.append({
                            'ticker': ticker,
                            'quantity': quantity,
                            'avg_cost': avg_cost,
                            'current_price': current_price,
                            'total_value': total_value,
                            'profit_loss': profit_loss,
                            'profit_loss_pct': profit_loss_pct
                        })

            logger.info(f"Fetched {len(positions)} US positions")
            return positions

        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            return []

    async def get_order_status(self, order_id: str) -> Optional[Dict]:
        """
        Get status of specific order

        Args:
            order_id: Order ID to check

        Returns:
            Order status dictionary or None if not found
        """
        if not self.broker:
            logger.error("Broker not initialized. Cannot fetch order status.")
            return None

        try:
            loop = asyncio.get_event_loop()
            orders_data = await loop.run_in_executor(
                None,
                self.broker.fetch_orders
            )

            # Find matching order
            for order in orders_data.get('output', []):
                if order.get('ODNO') == order_id:
                    return {
                        'order_id': order_id,
                        'status': order.get('ord_st'),
                        'filled_quantity': int(order.get('tot_ccld_qty', 0)),
                        'avg_price': float(order.get('avg_pric', 0)),
                        'timestamp': datetime.now().isoformat()
                    }

            logger.warning(f"Order {order_id} not found")
            return None

        except Exception as e:
            logger.error(f"Failed to fetch order status: {e}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel pending order

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        if not self.broker:
            logger.error("Broker not initialized. Cannot cancel order.")
            return False

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.broker.cancel_order,
                order_id
            )

            success = result.get('rt_cd') == '0'
            if success:
                logger.info(f"Order {order_id} cancelled successfully")
            else:
                logger.error(f"Failed to cancel order {order_id}: {result.get('msg1')}")

            return success

        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False


# Note: Global broker instance initialization is now handled by dependencies.py
# These functions are kept for backward compatibility but are deprecated
