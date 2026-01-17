"""
Scheduler Service
Automated trading sessions at scheduled times
"""

import logging
from datetime import datetime, time
from typing import Optional, Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from .trading_engine import TradingEngine

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for scheduling automated trading sessions"""

    def __init__(self, trading_engine: TradingEngine):
        """
        Initialize scheduler service

        Args:
            trading_engine: Trading engine instance
        """
        self.trading_engine = trading_engine
        self.scheduler = AsyncIOScheduler(timezone='Asia/Seoul')
        self.is_running = False

        # US Market Trading Times (in Korean Time KST/KDT)
        # Winter (DST off): Market 23:30-06:00 KST
        # Summer (DST on): Market 22:30-05:00 KST

        # We'll use both schedules and let APScheduler handle DST
        self.trading_schedules = {
            'PRE_MARKET_WINTER': {
                'hour': 23,
                'minute': 20,
                'description': '10 min before market open (winter)'
            },
            'PRE_MARKET_SUMMER': {
                'hour': 22,
                'minute': 20,
                'description': '10 min before market open (summer)'
            },
            'MID_SESSION_WINTER': {
                'hour': 1,
                'minute': 30,
                'description': '2 hours after market open (winter)'
            },
            'MID_SESSION_SUMMER': {
                'hour': 0,
                'minute': 30,
                'description': '2 hours after market open (summer)'
            },
            'PRE_CLOSE_WINTER': {
                'hour': 5,
                'minute': 50,
                'description': '10 min before market close (winter)'
            },
            'PRE_CLOSE_SUMMER': {
                'hour': 4,
                'minute': 50,
                'description': '10 min before market close (summer)'
            }
        }

        # Stop-loss check every 30 minutes during market hours
        self.stop_loss_check_interval = 30  # minutes

        logger.info("Scheduler service initialized")

    def start(self) -> bool:
        """
        Start the scheduler

        Returns:
            True if started successfully
        """
        try:
            if self.is_running:
                logger.warning("Scheduler is already running")
                return False

            # Schedule PRE_MARKET sessions
            self.scheduler.add_job(
                self._execute_pre_market,
                CronTrigger(
                    hour=23,
                    minute=20,
                    timezone='Asia/Seoul'
                ),
                id='pre_market_winter',
                name='PRE_MARKET Trading Session (Winter)',
                replace_existing=True
            )

            self.scheduler.add_job(
                self._execute_pre_market,
                CronTrigger(
                    hour=22,
                    minute=20,
                    timezone='Asia/Seoul'
                ),
                id='pre_market_summer',
                name='PRE_MARKET Trading Session (Summer)',
                replace_existing=True
            )

            # Schedule MID_SESSION
            self.scheduler.add_job(
                self._execute_mid_session,
                CronTrigger(
                    hour=1,
                    minute=30,
                    timezone='Asia/Seoul'
                ),
                id='mid_session_winter',
                name='MID_SESSION Trading Session (Winter)',
                replace_existing=True
            )

            self.scheduler.add_job(
                self._execute_mid_session,
                CronTrigger(
                    hour=0,
                    minute=30,
                    timezone='Asia/Seoul'
                ),
                id='mid_session_summer',
                name='MID_SESSION Trading Session (Summer)',
                replace_existing=True
            )

            # Schedule PRE_CLOSE
            self.scheduler.add_job(
                self._execute_pre_close,
                CronTrigger(
                    hour=5,
                    minute=50,
                    timezone='Asia/Seoul'
                ),
                id='pre_close_winter',
                name='PRE_CLOSE Trading Session (Winter)',
                replace_existing=True
            )

            self.scheduler.add_job(
                self._execute_pre_close,
                CronTrigger(
                    hour=4,
                    minute=50,
                    timezone='Asia/Seoul'
                ),
                id='pre_close_summer',
                name='PRE_CLOSE Trading Session (Summer)',
                replace_existing=True
            )

            # Schedule stop-loss checks every 30 minutes during market hours
            # Winter market hours: 23:30 - 06:00
            for hour in range(24):
                for minute in [0, 30]:
                    # Skip times outside market hours
                    if (hour >= 23 or hour <= 6):
                        self.scheduler.add_job(
                            self._check_stop_losses,
                            CronTrigger(
                                hour=hour,
                                minute=minute,
                                timezone='Asia/Seoul'
                            ),
                            id=f'stop_loss_check_{hour:02d}_{minute:02d}',
                            name=f'Stop-Loss Check {hour:02d}:{minute:02d}',
                            replace_existing=True
                        )

            # Schedule daily snapshot at market close
            self.scheduler.add_job(
                self._save_daily_snapshot,
                CronTrigger(
                    hour=6,
                    minute=5,
                    timezone='Asia/Seoul'
                ),
                id='daily_snapshot',
                name='Daily Portfolio Snapshot',
                replace_existing=True
            )

            self.scheduler.start()
            self.is_running = True

            logger.info("Scheduler started successfully")
            logger.info(f"Scheduled {len(self.scheduler.get_jobs())} jobs")

            return True

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False

    def stop(self) -> bool:
        """
        Stop the scheduler

        Returns:
            True if stopped successfully
        """
        try:
            if not self.is_running:
                logger.warning("Scheduler is not running")
                return False

            self.scheduler.shutdown(wait=False)
            self.is_running = False

            logger.info("Scheduler stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            return False

    def get_status(self) -> Dict:
        """
        Get scheduler status

        Returns:
            Status dictionary
        """
        jobs = []

        if self.is_running:
            for job in self.scheduler.get_jobs():
                next_run = job.next_run_time
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': next_run.isoformat() if next_run else None
                })

        return {
            'is_running': self.is_running,
            'job_count': len(jobs),
            'jobs': jobs,
            'timezone': 'Asia/Seoul'
        }

    async def _execute_pre_market(self):
        """Execute PRE_MARKET trading session"""
        logger.info("="*60)
        logger.info("Starting PRE_MARKET trading session")
        logger.info("="*60)

        try:
            result = await self.trading_engine.execute_trading_session(
                decision_type='PRE_MARKET'
            )

            if result.get('success'):
                logger.info(f"PRE_MARKET session completed: {result.get('successful_trades')} trades executed")
            else:
                logger.error(f"PRE_MARKET session failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"PRE_MARKET session error: {e}")

    async def _execute_mid_session(self):
        """Execute MID_SESSION trading session"""
        logger.info("="*60)
        logger.info("Starting MID_SESSION trading session")
        logger.info("="*60)

        try:
            result = await self.trading_engine.execute_trading_session(
                decision_type='MID_SESSION'
            )

            if result.get('success'):
                logger.info(f"MID_SESSION session completed: {result.get('successful_trades')} trades executed")
            else:
                logger.error(f"MID_SESSION session failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"MID_SESSION session error: {e}")

    async def _execute_pre_close(self):
        """Execute PRE_CLOSE trading session"""
        logger.info("="*60)
        logger.info("Starting PRE_CLOSE trading session")
        logger.info("="*60)

        try:
            result = await self.trading_engine.execute_trading_session(
                decision_type='PRE_CLOSE'
            )

            if result.get('success'):
                logger.info(f"PRE_CLOSE session completed: {result.get('successful_trades')} trades executed")
            else:
                logger.error(f"PRE_CLOSE session failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"PRE_CLOSE session error: {e}")

    async def _check_stop_losses(self):
        """Check for stop-loss triggers"""
        logger.debug("Checking stop-loss triggers")

        try:
            result = await self.trading_engine.check_and_execute_stop_losses()

            if result.get('triggered_count', 0) > 0:
                logger.warning(f"Stop-loss check: {result.get('executed_count')} positions closed")

        except Exception as e:
            logger.error(f"Stop-loss check error: {e}")

    async def _save_daily_snapshot(self):
        """Save daily portfolio snapshot"""
        logger.info("Saving daily portfolio snapshot")

        try:
            await self.trading_engine.portfolio.save_snapshot()
            logger.info("Daily snapshot saved successfully")

        except Exception as e:
            logger.error(f"Failed to save daily snapshot: {e}")

    def execute_now(self, decision_type: str) -> bool:
        """
        Execute a trading session immediately (manual trigger)

        Args:
            decision_type: PRE_MARKET, MID_SESSION, or PRE_CLOSE

        Returns:
            True if scheduled successfully
        """
        try:
            if decision_type == 'PRE_MARKET':
                self.scheduler.add_job(
                    self._execute_pre_market,
                    'date',
                    id=f'manual_pre_market_{datetime.now().timestamp()}',
                    name='Manual PRE_MARKET Session'
                )
            elif decision_type == 'MID_SESSION':
                self.scheduler.add_job(
                    self._execute_mid_session,
                    'date',
                    id=f'manual_mid_session_{datetime.now().timestamp()}',
                    name='Manual MID_SESSION Session'
                )
            elif decision_type == 'PRE_CLOSE':
                self.scheduler.add_job(
                    self._execute_pre_close,
                    'date',
                    id=f'manual_pre_close_{datetime.now().timestamp()}',
                    name='Manual PRE_CLOSE Session'
                )
            else:
                logger.error(f"Invalid decision type: {decision_type}")
                return False

            logger.info(f"Manually triggered {decision_type} session")
            return True

        except Exception as e:
            logger.error(f"Failed to execute manual session: {e}")
            return False
