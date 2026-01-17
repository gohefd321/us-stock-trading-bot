"""
Risk Manager Service
Enforces risk limits: 40% max position, 20% daily loss, 30% stop-loss
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession

from .portfolio_manager import PortfolioManager
from .broker_service import BrokerService
from ..config import Settings

logger = logging.getLogger(__name__)


class RiskManager:
    """Service for managing trading risk and enforcing limits"""

    def __init__(
        self,
        portfolio_manager: PortfolioManager,
        broker: BrokerService,
        settings: Settings
    ):
        """
        Initialize risk manager

        Args:
            portfolio_manager: Portfolio manager instance
            broker: Broker service instance
            settings: Application settings
        """
        self.portfolio_manager = portfolio_manager
        self.broker = broker
        self.settings = settings

        # Risk parameters
        self.max_position_size_pct = settings.max_position_size_pct  # 40%
        self.daily_loss_limit_pct = settings.daily_loss_limit_pct    # 20%
        self.stop_loss_pct = settings.stop_loss_pct                  # 30%

        logger.info(f"Risk manager initialized: max_position={self.max_position_size_pct}%, "
                   f"daily_loss={self.daily_loss_limit_pct}%, stop_loss={self.stop_loss_pct}%")

    async def check_position_size_limit(self, ticker: str, trade_value_krw: float) -> Tuple[bool, str]:
        """
        Check if trade would violate 40% max position size limit

        Args:
            ticker: Stock ticker symbol
            trade_value_krw: Value of trade in KRW

        Returns:
            Tuple of (can_trade, reason)
        """
        try:
            total_assets = await self.portfolio_manager.get_total_assets()
            max_position_value = total_assets * (self.max_position_size_pct / 100)

            # Get current position value
            current_position_value = await self.portfolio_manager.get_position_value(ticker)

            # Calculate new position value
            new_position_value = current_position_value + trade_value_krw

            if new_position_value > max_position_value:
                reason = (
                    f"Position size limit exceeded for {ticker}. "
                    f"New position would be {new_position_value:,.0f} KRW "
                    f"({(new_position_value/total_assets)*100:.1f}%), "
                    f"max allowed is {max_position_value:,.0f} KRW ({self.max_position_size_pct}%)"
                )
                logger.warning(reason)
                return False, reason

            logger.debug(f"Position size check passed for {ticker}: "
                        f"{new_position_value:,.0f} KRW ({(new_position_value/total_assets)*100:.1f}%) "
                        f"< {max_position_value:,.0f} KRW ({self.max_position_size_pct}%)")
            return True, "Position size within limits"

        except Exception as e:
            logger.error(f"Failed to check position size limit: {e}")
            return False, f"Error checking position size: {str(e)}"

    async def check_daily_loss_limit(self) -> Tuple[bool, float]:
        """
        Check if 20% daily loss circuit breaker should trigger

        Returns:
            Tuple of (triggered, daily_pnl_pct)
        """
        try:
            state = await self.portfolio_manager.get_current_state()
            daily_pnl_pct = state['daily_pnl_pct']

            triggered = daily_pnl_pct <= -self.daily_loss_limit_pct

            if triggered:
                logger.critical(
                    f"CIRCUIT BREAKER TRIGGERED! Daily loss: {daily_pnl_pct:.2f}% "
                    f"exceeds limit of -{self.daily_loss_limit_pct}%"
                )
            else:
                logger.debug(f"Daily loss check passed: {daily_pnl_pct:.2f}%")

            return triggered, daily_pnl_pct

        except Exception as e:
            logger.error(f"Failed to check daily loss limit: {e}")
            return False, 0.0

    async def check_stop_loss(self, ticker: str, current_price: float) -> Tuple[bool, float]:
        """
        Check if position has hit -30% stop-loss

        Args:
            ticker: Stock ticker symbol
            current_price: Current market price

        Returns:
            Tuple of (triggered, pnl_pct)
        """
        try:
            position = await self.portfolio_manager.get_position(ticker)

            if not position:
                return False, 0.0

            avg_cost = position['avg_cost']
            pnl_pct = ((current_price - avg_cost) / avg_cost) * 100

            triggered = pnl_pct <= -self.stop_loss_pct

            if triggered:
                logger.warning(
                    f"Stop-loss triggered for {ticker}: {pnl_pct:.2f}% loss "
                    f"(current: ${current_price:.2f}, avg_cost: ${avg_cost:.2f})"
                )
            else:
                logger.debug(f"Stop-loss check passed for {ticker}: {pnl_pct:.2f}%")

            return triggered, pnl_pct

        except Exception as e:
            logger.error(f"Failed to check stop-loss for {ticker}: {e}")
            return False, 0.0

    async def check_all_stop_losses(self) -> List[Dict]:
        """
        Check stop-loss for all positions

        Returns:
            List of positions that triggered stop-loss
        """
        try:
            state = await self.portfolio_manager.get_current_state()
            triggered_positions = []

            for position in state['positions']:
                ticker = position['ticker']
                current_price = position['current_price']

                triggered, pnl_pct = await self.check_stop_loss(ticker, current_price)

                if triggered:
                    triggered_positions.append({
                        'ticker': ticker,
                        'current_price': current_price,
                        'avg_cost': position['avg_cost'],
                        'quantity': position['quantity'],
                        'pnl_pct': pnl_pct,
                        'loss_amount_krw': position['unrealized_pnl']
                    })

            if triggered_positions:
                logger.warning(f"Found {len(triggered_positions)} positions with stop-loss triggered")
            else:
                logger.debug("No stop-loss triggers found")

            return triggered_positions

        except Exception as e:
            logger.error(f"Failed to check all stop-losses: {e}")
            return []

    async def calculate_position_size(
        self,
        ticker: str,
        confidence: float,
        price_per_share: float
    ) -> Dict:
        """
        Calculate optimal position size based on confidence and risk limits

        Args:
            ticker: Stock ticker symbol
            confidence: Confidence level (0.0 to 1.0)
            price_per_share: Current price per share in USD

        Returns:
            Dictionary with recommended quantity and reasoning
        """
        try:
            # Get total assets
            total_assets = await self.portfolio_manager.get_total_assets()
            available_cash = await self.portfolio_manager.get_available_cash()

            # Calculate max position value based on risk limit
            max_position_value_krw = total_assets * (self.max_position_size_pct / 100)

            # Get current position value
            current_position_value = await self.portfolio_manager.get_position_value(ticker)

            # Available room for this ticker
            available_position_room = max_position_value_krw - current_position_value

            # Scale by confidence (0.0 to 1.0)
            # Confidence of 1.0 = use full 40% max position
            # Confidence of 0.5 = use 20% of max position
            target_position_value = max_position_value_krw * confidence

            # Adjust for existing position
            target_trade_value = target_position_value - current_position_value

            # Ensure we don't exceed available cash or position limits
            target_trade_value = min(target_trade_value, available_cash, available_position_room)

            # Calculate quantity (approximate conversion USD to KRW = 1300)
            usd_krw_rate = 1300
            price_per_share_krw = price_per_share * usd_krw_rate
            quantity = int(target_trade_value / price_per_share_krw)

            # Ensure at least 1 share if there's room
            if quantity == 0 and available_cash > price_per_share_krw:
                quantity = 1

            final_trade_value = quantity * price_per_share_krw
            position_pct = (final_trade_value / total_assets) * 100

            reasoning = (
                f"Confidence: {confidence:.2f}, "
                f"Max position: {self.max_position_size_pct}%, "
                f"Target position: {position_pct:.1f}%, "
                f"Available cash: {available_cash:,.0f} KRW"
            )

            return {
                'quantity': quantity,
                'trade_value_krw': final_trade_value,
                'position_pct': position_pct,
                'reasoning': reasoning
            }

        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return {
                'quantity': 0,
                'trade_value_krw': 0,
                'position_pct': 0,
                'reasoning': f"Error: {str(e)}"
            }

    async def can_trade_now(self) -> Tuple[bool, str]:
        """
        Check if trading is currently allowed (not in circuit breaker)

        Returns:
            Tuple of (can_trade, reason)
        """
        try:
            # Check daily loss circuit breaker
            circuit_breaker_triggered, daily_pnl_pct = await self.check_daily_loss_limit()

            if circuit_breaker_triggered:
                reason = (
                    f"Trading halted: Circuit breaker triggered. "
                    f"Daily loss: {daily_pnl_pct:.2f}% exceeds -{self.daily_loss_limit_pct}%"
                )
                return False, reason

            return True, "Trading allowed"

        except Exception as e:
            logger.error(f"Failed to check if trading allowed: {e}")
            return False, f"Error checking trading status: {str(e)}"

    async def execute_stop_loss_sell(self, ticker: str, quantity: int) -> Dict:
        """
        Execute stop-loss sell order

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares to sell

        Returns:
            Order result dictionary
        """
        try:
            logger.warning(f"Executing stop-loss sell for {ticker}: {quantity} shares")

            result = await self.broker.place_us_order(
                ticker=ticker,
                action="SELL",
                quantity=quantity,
                order_type="MARKET"
            )

            if result['success']:
                logger.info(f"Stop-loss sell executed for {ticker}: {result.get('order_id')}")
            else:
                logger.error(f"Stop-loss sell failed for {ticker}: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"Failed to execute stop-loss sell for {ticker}: {e}")
            return {"success": False, "error": str(e)}
