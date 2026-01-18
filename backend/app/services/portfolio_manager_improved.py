"""
Portfolio Manager Service (Improved)
Tracks portfolio state, positions, and calculates P/L
Works even when broker is not initialized
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import json

from ..models import PortfolioSnapshot
from .broker_service import BrokerService
from ..config import Settings

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Service for managing and tracking portfolio state"""

    def __init__(self, broker: BrokerService, settings: Settings = None, db: AsyncSession = None):
        """
        Initialize portfolio manager

        Args:
            broker: Broker service instance
            settings: Application settings (optional, for testing)
            db: Database session (optional, for testing)
        """
        self.broker = broker
        self.db = db
        self.settings = settings or Settings()
        self.initial_capital = self.settings.initial_capital_krw

    async def get_current_state(self) -> Dict:
        """
        Get current portfolio state

        Returns:
            Dictionary with current portfolio information
        """
        # Check if broker is initialized
        if not self.broker or not self.broker.broker:
            logger.warning("Broker not initialized. Returning empty portfolio state.")
            return {
                'timestamp': datetime.now().isoformat(),
                'cash_balance': 0,
                'holdings_value': 0,
                'total_value': 0,
                'positions': [],
                'position_count': 0,
                'daily_pnl': 0,
                'daily_pnl_pct': 0,
                'total_pnl': 0,
                'total_pnl_pct': 0,
                'warning': 'Broker not initialized. Please configure API credentials.'
            }

        try:
            # Fetch balance from broker
            balance = await self.broker.get_balance()

            # Fetch positions
            positions = await self.broker.get_us_positions()

            # Calculate totals
            cash_balance = balance['cash_balance']
            holdings_value = sum(pos['total_value'] for pos in positions)
            total_value = cash_balance + holdings_value

            # Calculate P/L
            total_pnl = total_value - self.initial_capital
            total_pnl_pct = (total_pnl / self.initial_capital) * 100 if self.initial_capital > 0 else 0

            # Get start of day value for daily P/L
            start_of_day_value = await self._get_start_of_day_value()
            daily_pnl = total_value - start_of_day_value if start_of_day_value else 0
            daily_pnl_pct = (daily_pnl / start_of_day_value) * 100 if start_of_day_value > 0 else 0

            state = {
                'timestamp': datetime.now().isoformat(),
                'cash_balance': cash_balance,
                'holdings_value': holdings_value,
                'total_value': total_value,
                'positions': positions,
                'position_count': len(positions),
                'daily_pnl': daily_pnl,
                'daily_pnl_pct': daily_pnl_pct,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct
            }

            logger.debug(f"Portfolio state: {total_value} KRW ({len(positions)} positions)")
            return state

        except Exception as e:
            logger.error(f"Failed to get portfolio state: {e}")
            # Return safe defaults instead of raising
            return {
                'timestamp': datetime.now().isoformat(),
                'cash_balance': 0,
                'holdings_value': 0,
                'total_value': 0,
                'positions': [],
                'position_count': 0,
                'daily_pnl': 0,
                'daily_pnl_pct': 0,
                'total_pnl': 0,
                'total_pnl_pct': 0,
                'error': str(e)
            }

    async def get_position(self, ticker: str) -> Optional[Dict]:
        """
        Get specific position by ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Position dictionary or None if not found
        """
        if not self.broker or not self.broker.broker:
            logger.warning("Broker not initialized. Cannot get position.")
            return None

        try:
            positions = await self.broker.get_us_positions()

            for pos in positions:
                if pos['ticker'] == ticker:
                    return pos

            return None

        except Exception as e:
            logger.error(f"Failed to get position for {ticker}: {e}")
            return None

    async def get_total_assets(self) -> float:
        """
        Get total asset value (cash + holdings)

        Returns:
            Total value in KRW
        """
        try:
            state = await self.get_current_state()
            return state.get('total_value', 0.0)

        except Exception as e:
            logger.error(f"Failed to get total assets: {e}")
            return 0.0

    async def get_available_cash(self) -> float:
        """
        Get available cash balance

        Returns:
            Cash balance in KRW
        """
        if not self.broker or not self.broker.broker:
            logger.warning("Broker not initialized. Returning 0 cash.")
            return 0.0

        try:
            balance = await self.broker.get_balance()
            return balance['cash_balance']

        except Exception as e:
            logger.error(f"Failed to get available cash: {e}")
            return 0.0

    async def get_position_value(self, ticker: str) -> float:
        """
        Get current value of position

        Args:
            ticker: Stock ticker symbol

        Returns:
            Position value in KRW
        """
        position = await self.get_position(ticker)
        return position.get('total_value', 0.0) if position else 0.0

    async def calculate_position_exposure(self) -> Dict:
        """
        Calculate position exposure as percentage of total assets

        Returns:
            Dictionary of ticker: exposure percentage
        """
        try:
            state = await self.get_current_state()
            total_value = state.get('total_value', 0)

            if total_value == 0:
                return {}

            exposure = {}
            for pos in state.get('positions', []):
                ticker = pos['ticker']
                pos_value = pos['total_value']
                exposure[ticker] = (pos_value / total_value) * 100

            return exposure

        except Exception as e:
            logger.error(f"Failed to calculate position exposure: {e}")
            return {}

    async def _get_start_of_day_value(self) -> Optional[float]:
        """
        Get portfolio value at start of trading day

        Returns:
            Start of day value or None if not available
        """
        if not self.db:
            return None

        try:
            today = date.today()
            stmt = select(PortfolioSnapshot).where(
                PortfolioSnapshot.snapshot_date == today
            ).order_by(desc(PortfolioSnapshot.created_at)).limit(1)

            result = await self.db.execute(stmt)
            snapshot = result.scalar_one_or_none()

            if snapshot:
                return snapshot.total_value
            else:
                # If no snapshot for today, use initial capital
                return self.initial_capital

        except Exception as e:
            logger.error(f"Failed to get start of day value: {e}")
            return None

    async def save_snapshot(self) -> bool:
        """
        Save current portfolio snapshot to database

        Returns:
            True if successful
        """
        if not self.db:
            logger.warning("No database session available for saving snapshot")
            return False

        try:
            state = await self.get_current_state()

            snapshot = PortfolioSnapshot(
                snapshot_date=date.today(),
                cash_balance=state['cash_balance'],
                total_holdings_value=state['holdings_value'],
                total_value=state['total_value'],
                daily_pnl=state.get('daily_pnl'),
                daily_pnl_pct=state.get('daily_pnl_pct'),
                total_pnl=state.get('total_pnl'),
                total_pnl_pct=state.get('total_pnl_pct'),
                holdings_json=json.dumps(state['positions'])
            )

            self.db.add(snapshot)
            await self.db.commit()

            logger.info(f"Portfolio snapshot saved: {state['total_value']} KRW")
            return True

        except Exception as e:
            logger.error(f"Failed to save portfolio snapshot: {e}")
            await self.db.rollback()
            return False

    async def get_historical_snapshots(self, days: int = 30) -> List[Dict]:
        """
        Get historical portfolio snapshots

        Args:
            days: Number of days to retrieve

        Returns:
            List of snapshot dictionaries
        """
        if not self.db:
            logger.warning("No database session available for historical data")
            return []

        try:
            stmt = select(PortfolioSnapshot).order_by(
                desc(PortfolioSnapshot.snapshot_date)
            ).limit(days)

            result = await self.db.execute(stmt)
            snapshots = result.scalars().all()

            return [
                {
                    'date': s.snapshot_date.isoformat(),
                    'total_value': s.total_value,
                    'cash_balance': s.cash_balance,
                    'holdings_value': s.total_holdings_value,
                    'daily_pnl': s.daily_pnl,
                    'daily_pnl_pct': s.daily_pnl_pct,
                    'total_pnl': s.total_pnl,
                    'total_pnl_pct': s.total_pnl_pct
                }
                for s in snapshots
            ]

        except Exception as e:
            logger.error(f"Failed to get historical snapshots: {e}")
            return []
