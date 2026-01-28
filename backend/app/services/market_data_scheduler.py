"""
Market Data Scheduler
Automatically collects market data at regular intervals
"""

import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .market_data_service import MarketDataService
from ..config import Settings

logger = logging.getLogger(__name__)


class MarketDataScheduler:
    """Scheduler for automatic market data collection"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.market_data_service = MarketDataService(settings)
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("[SCHEDULER] 📅 Market data scheduler already running")
            return

        logger.info("[SCHEDULER] 🚀 Starting market data scheduler...")

        # Collect market data every 30 minutes during market hours (9:30 AM - 4:00 PM EST)
        # In UTC: 14:30 - 21:00 (standard time) or 13:30 - 20:00 (daylight saving)
        self.scheduler.add_job(
            self._collect_market_data,
            CronTrigger(
                day_of_week='mon-fri',  # Weekdays only
                hour='14-21',  # Market hours in UTC (approximate)
                minute='*/30'  # Every 30 minutes
            ),
            id='market_data_collection',
            name='Market Data Collection',
            replace_existing=True
        )

        # Also run once at startup
        self.scheduler.add_job(
            self._collect_market_data,
            'date',
            run_date=datetime.now(),
            id='market_data_startup',
            name='Market Data Startup Collection'
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("[SCHEDULER] ✅ Market data scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            logger.warning("[SCHEDULER] 📅 Market data scheduler not running")
            return

        logger.info("[SCHEDULER] 🛑 Stopping market data scheduler...")
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        logger.info("[SCHEDULER] ✅ Market data scheduler stopped")

    async def _collect_market_data(self):
        """Collect market data from all sources"""
        try:
            logger.info("[SCHEDULER] 📊 Starting scheduled market data collection...")

            # Collect market summary
            summary = await self.market_data_service.get_market_summary()

            trending_count = len(summary.get('wsb_trending', []))
            detailed_count = len(summary.get('detailed_stocks', []))

            logger.info(f"[SCHEDULER] ✅ Market data collected: {trending_count} WSB stocks, {detailed_count} detailed")

            # Log summary
            if summary.get('summary_text'):
                logger.info(f"[SCHEDULER] 📰 Market Summary:\n{summary['summary_text'][:500]}...")

        except Exception as e:
            logger.error(f"[SCHEDULER] 💥 Failed to collect market data: {e}", exc_info=True)

    def get_status(self) -> dict:
        """Get scheduler status"""
        jobs = []
        if self.is_running:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                })

        return {
            'is_running': self.is_running,
            'jobs': jobs,
            'job_count': len(jobs)
        }
