"""
Gemini Function Handlers
Implements the actual logic for each Gemini function call
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from ..services.broker_service import BrokerService
from ..services.portfolio_manager import PortfolioManager
from ..services.signal_aggregator import SignalAggregator
from ..services.risk_manager import RiskManager
from ..models import Trade

logger = logging.getLogger(__name__)


class FunctionHandler:
    """Handler for Gemini function calls"""

    def __init__(
        self,
        broker: BrokerService,
        portfolio_manager: PortfolioManager,
        signal_aggregator: SignalAggregator,
        risk_manager: RiskManager,
        db: AsyncSession
    ):
        """
        Initialize function handler

        Args:
            broker: Broker service instance
            portfolio_manager: Portfolio manager instance
            signal_aggregator: Signal aggregator instance
            risk_manager: Risk manager instance
            db: Database session
        """
        self.broker = broker
        self.portfolio_manager = portfolio_manager
        self.signal_aggregator = signal_aggregator
        self.risk_manager = risk_manager
        self.db = db

    async def handle_function_call(self, function_name: str, arguments: Dict) -> Dict:
        """
        Route function call to appropriate handler

        Args:
            function_name: Name of function to call
            arguments: Function arguments

        Returns:
            Function result dictionary
        """
        try:
            logger.info(f"Handling function call: {function_name} with args: {arguments}")

            handlers = {
                "check_balance": self.check_balance,
                "get_current_price": self.get_current_price,
                "get_portfolio_status": self.get_portfolio_status,
                "execute_trade": self.execute_trade,
                "analyze_signals": self.analyze_signals,
                "calculate_position_size": self.calculate_position_size,
                "check_stop_loss_triggers": self.check_stop_loss_triggers,
                "get_trading_history": self.get_trading_history
            }

            if function_name not in handlers:
                return {"error": f"Unknown function: {function_name}"}

            handler = handlers[function_name]
            result = await handler(**arguments)

            logger.info(f"Function {function_name} completed successfully")
            return result

        except Exception as e:
            logger.error(f"Error handling function {function_name}: {e}")
            return {"error": str(e)}

    async def check_balance(self) -> Dict:
        """Get current account balance"""
        try:
            balance = await self.broker.get_balance()
            return {
                "success": True,
                "cash_balance_krw": balance['cash_balance'],
                "total_value_krw": balance['total_value'],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to check balance: {e}")
            return {"success": False, "error": str(e)}

    async def get_current_price(self, ticker: str) -> Dict:
        """Get current price for ticker"""
        try:
            price = await self.broker.get_us_stock_price(ticker)
            if price:
                return {
                    "success": True,
                    "ticker": ticker,
                    "price_usd": price,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"Could not fetch price for {ticker}"
                }
        except Exception as e:
            logger.error(f"Failed to get price for {ticker}: {e}")
            return {"success": False, "error": str(e)}

    async def get_portfolio_status(self) -> Dict:
        """Get comprehensive portfolio status"""
        try:
            state = await self.portfolio_manager.get_current_state()
            exposure = await self.portfolio_manager.calculate_position_exposure()

            return {
                "success": True,
                "cash_balance_krw": state['cash_balance'],
                "holdings_value_krw": state['holdings_value'],
                "total_value_krw": state['total_value'],
                "positions": state['positions'],
                "position_count": state['position_count'],
                "daily_pnl_krw": state['daily_pnl'],
                "daily_pnl_pct": state['daily_pnl_pct'],
                "total_pnl_krw": state['total_pnl'],
                "total_pnl_pct": state['total_pnl_pct'],
                "exposure_by_ticker": exposure,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get portfolio status: {e}")
            return {"success": False, "error": str(e)}

    async def execute_trade(
        self,
        ticker: str,
        action: str,
        quantity: int,
        order_type: str,
        limit_price: Optional[float] = None
    ) -> Dict:
        """Execute a trade"""
        try:
            # Get current price for validation
            current_price = await self.broker.get_us_stock_price(ticker)
            if not current_price:
                return {
                    "success": False,
                    "error": f"Could not fetch current price for {ticker}"
                }

            # Calculate trade value
            price_to_use = limit_price if order_type == "LIMIT" and limit_price else current_price
            trade_value_krw = quantity * price_to_use * 1300  # Approximate USD to KRW

            # Risk checks before executing
            if action == "BUY":
                # Check position size limit
                can_trade, reason = await self.risk_manager.check_position_size_limit(
                    ticker, trade_value_krw
                )
                if not can_trade:
                    return {
                        "success": False,
                        "error": f"Risk check failed: {reason}",
                        "risk_violation": True
                    }

                # Check daily loss limit
                circuit_breaker_triggered, daily_pnl_pct = await self.risk_manager.check_daily_loss_limit()
                if circuit_breaker_triggered:
                    return {
                        "success": False,
                        "error": f"Circuit breaker triggered: Daily loss at {daily_pnl_pct:.2f}%",
                        "circuit_breaker": True
                    }

            # Execute trade through broker
            order_result = await self.broker.place_us_order(
                ticker=ticker,
                action=action,
                quantity=quantity,
                order_type=order_type,
                limit_price=limit_price
            )

            if order_result['success']:
                return {
                    "success": True,
                    "ticker": ticker,
                    "action": action,
                    "quantity": quantity,
                    "order_type": order_type,
                    "order_id": order_result.get('order_id'),
                    "estimated_price": current_price,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": order_result.get('error', 'Unknown error')
                }

        except Exception as e:
            logger.error(f"Failed to execute trade for {ticker}: {e}")
            return {"success": False, "error": str(e)}

    async def analyze_signals(self, ticker: str, hours_back: int = 24) -> Dict:
        """Analyze market signals for ticker"""
        try:
            # Get fresh aggregated signals
            signals = await self.signal_aggregator.aggregate_signals_for_ticker(ticker)

            # Get recent historical signals from DB
            recent_signals = await self.signal_aggregator.get_recent_signals(
                ticker, hours_back=hours_back
            )

            return {
                "success": True,
                "ticker": ticker,
                "current_signals": signals,
                "recent_signals": recent_signals,
                "composite_sentiment": signals.get('composite_sentiment'),
                "signal_strength": signals.get('signal_strength'),
                "recommendation": signals.get('recommendation'),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to analyze signals for {ticker}: {e}")
            return {"success": False, "error": str(e)}

    async def calculate_position_size(
        self,
        ticker: str,
        confidence: float,
        price: float
    ) -> Dict:
        """Calculate optimal position size"""
        try:
            result = await self.risk_manager.calculate_position_size(
                ticker=ticker,
                confidence=confidence,
                price_per_share=price
            )

            return {
                "success": True,
                "ticker": ticker,
                "confidence": confidence,
                "price_per_share": price,
                "recommended_quantity": result['quantity'],
                "trade_value_krw": result['trade_value_krw'],
                "position_pct": result['position_pct'],
                "reasoning": result['reasoning'],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return {"success": False, "error": str(e)}

    async def check_stop_loss_triggers(self) -> Dict:
        """Check if any positions have triggered stop-loss"""
        try:
            triggered_positions = await self.risk_manager.check_all_stop_losses()

            return {
                "success": True,
                "triggered_positions": triggered_positions,
                "count": len(triggered_positions),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to check stop-loss triggers: {e}")
            return {"success": False, "error": str(e)}

    async def get_trading_history(self, days_back: int = 7) -> Dict:
        """Get recent trading history"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)

            stmt = select(Trade).where(
                Trade.executed_at >= cutoff_date
            ).order_by(desc(Trade.executed_at))

            result = await self.db.execute(stmt)
            trades = result.scalars().all()

            trade_list = [
                {
                    "trade_id": trade.trade_id,
                    "ticker": trade.ticker,
                    "action": trade.action,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "total_value": trade.total_value,
                    "status": trade.status,
                    "executed_at": trade.executed_at.isoformat() if trade.executed_at else None
                }
                for trade in trades
            ]

            # Calculate win rate
            completed_trades = [t for t in trades if t.status == 'FILLED']
            buy_trades = {t.ticker: t for t in completed_trades if t.action == 'BUY'}
            sell_trades = [t for t in completed_trades if t.action == 'SELL']

            wins = 0
            losses = 0
            for sell_trade in sell_trades:
                if sell_trade.ticker in buy_trades:
                    buy_trade = buy_trades[sell_trade.ticker]
                    if sell_trade.price > buy_trade.price:
                        wins += 1
                    else:
                        losses += 1

            win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

            return {
                "success": True,
                "trades": trade_list,
                "total_trades": len(trade_list),
                "days_back": days_back,
                "win_rate_pct": win_rate,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get trading history: {e}")
            return {"success": False, "error": str(e)}
