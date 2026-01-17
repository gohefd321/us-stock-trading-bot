"""
Portfolio Manager Service
Tracks portfolio state, positions, and calculates P/L
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
            raise

    async def get_position(self, ticker: str) -> Optional[Dict]:
        """
        Get specific position by ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Position dictionary or None if not found
        """
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
            return state['total_value']

        except Exception as e:
            logger.error(f"Failed to get total assets: {e}")
            return 0.0

    async def get_available_cash(self) -> float:
        """
        Get available cash balance

        Returns:
            Cash balance in KRW
        """
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
        return position['total_value'] if position else 0.0

    async def save_snapshot(self) -> bool:
        """
        Save current portfolio snapshot to database

        Returns:
            True if saved successfully
        """
        try:
            state = await self.get_current_state()
            today = date.today()

            # Check if snapshot for today already exists
            stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.snapshot_date == today)
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()

            holdings_json = json.dumps(state['positions'])

            if existing:
                # Update existing snapshot
                existing.cash_balance = state['cash_balance']
                existing.total_holdings_value = state['holdings_value']
                existing.total_value = state['total_value']
                existing.daily_pnl = state['daily_pnl']
                existing.daily_pnl_pct = state['daily_pnl_pct']
                existing.total_pnl = state['total_pnl']
                existing.total_pnl_pct = state['total_pnl_pct']
                existing.holdings_json = holdings_json
                logger.info(f"Updated portfolio snapshot for {today}")
            else:
                # Create new snapshot
                snapshot = PortfolioSnapshot(
                    snapshot_date=today,
                    cash_balance=state['cash_balance'],
                    total_holdings_value=state['holdings_value'],
                    total_value=state['total_value'],
                    daily_pnl=state['daily_pnl'],
                    daily_pnl_pct=state['daily_pnl_pct'],
                    total_pnl=state['total_pnl'],
                    total_pnl_pct=state['total_pnl_pct'],
                    holdings_json=holdings_json
                )
                self.db.add(snapshot)
                logger.info(f"Created portfolio snapshot for {today}")

            await self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
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
        try:
            stmt = select(PortfolioSnapshot).order_by(
                desc(PortfolioSnapshot.snapshot_date)
            ).limit(days)

            result = await self.db.execute(stmt)
            snapshots = result.scalars().all()

            return [
                {
                    'date': snap.snapshot_date.isoformat(),
                    'total_value': snap.total_value,
                    'cash_balance': snap.cash_balance,
                    'holdings_value': snap.total_holdings_value,
                    'daily_pnl': snap.daily_pnl,
                    'daily_pnl_pct': snap.daily_pnl_pct,
                    'total_pnl': snap.total_pnl,
                    'total_pnl_pct': snap.total_pnl_pct,
                    'holdings': json.loads(snap.holdings_json)
                }
                for snap in snapshots
            ]

        except Exception as e:
            logger.error(f"Failed to get historical snapshots: {e}")
            return []

    async def _get_start_of_day_value(self) -> Optional[float]:
        """
        Get portfolio value at start of day

        Returns:
            Start of day value or None if not available
        """
        try:
            today = date.today()
            stmt = select(PortfolioSnapshot).where(
                PortfolioSnapshot.snapshot_date == today
            )
            result = await self.db.execute(stmt)
            snapshot = result.scalar_one_or_none()

            if snapshot:
                return snapshot.total_value
            else:
                # Use yesterday's closing value
                yesterday = date.today().replace(day=date.today().day - 1)
                stmt = select(PortfolioSnapshot).where(
                    PortfolioSnapshot.snapshot_date == yesterday
                )
                result = await self.db.execute(stmt)
                snapshot = result.scalar_one_or_none()
                return snapshot.total_value if snapshot else self.initial_capital

        except Exception as e:
            logger.error(f"Failed to get start of day value: {e}")
            return None

    async def calculate_position_exposure(self) -> Dict[str, float]:
        """
        Calculate exposure percentage for each position

        Returns:
            Dictionary mapping ticker to exposure percentage
        """
        try:
            state = await self.get_current_state()
            total_value = state['total_value']

            if total_value == 0:
                return {}

            exposure = {}
            for pos in state['positions']:
                ticker = pos['ticker']
                pos_value = pos['total_value']
                exposure[ticker] = (pos_value / total_value) * 100

            return exposure

        except Exception as e:
            logger.error(f"Failed to calculate exposure: {e}")
            return {}
