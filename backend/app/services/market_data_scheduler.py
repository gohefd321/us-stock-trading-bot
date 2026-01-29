"""
Market Data Scheduler
Automatically collects market data and generates trading recommendations at market phases
"""

import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .market_data_service import MarketDataService
from .trading_recommendation_service import TradingRecommendationService
from ..config import Settings

logger = logging.getLogger(__name__)


class MarketDataScheduler:
    """Scheduler for automatic market data collection and trading recommendations"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.market_data_service = MarketDataService(settings)
        self.recommendation_service = TradingRecommendationService(settings, self.market_data_service)
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.latest_recommendation = None  # Store latest recommendation

    def _run_async_job(self, coro):
        """Helper to run async coroutine in scheduler"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    def start(self):
        """Start the scheduler with market phase-based collection"""
        if self.is_running:
            logger.warning("[SCHEDULER] 📅 Market data scheduler already running")
            return

        logger.info("[SCHEDULER] 🚀 Starting enhanced market data scheduler...")

        # 1. Server startup - collect data immediately
        self.scheduler.add_job(
            lambda: self._run_async_job(self._collect_with_recommendation('startup')),
            'date',
            run_date=datetime.now(),
            id='startup_collection',
            name='Startup Collection'
        )

        # 2. Market open (9:30 AM EST = 14:30 UTC standard time)
        self.scheduler.add_job(
            lambda: self._run_async_job(self._collect_with_recommendation('market_open')),
            CronTrigger(
                day_of_week='mon-fri',
                hour=14,
                minute=30
            ),
            id='market_open_collection',
            name='Market Open Collection',
            replace_existing=True
        )

        # 3. Mid-session (12:30 PM EST = 17:30 UTC)
        self.scheduler.add_job(
            lambda: self._run_async_job(self._collect_with_recommendation('mid_session')),
            CronTrigger(
                day_of_week='mon-fri',
                hour=17,
                minute=30
            ),
            id='mid_session_collection',
            name='Mid-Session Collection',
            replace_existing=True
        )

        # 4. Near market close (3:30 PM EST = 20:30 UTC)
        self.scheduler.add_job(
            lambda: self._run_async_job(self._collect_with_recommendation('market_close')),
            CronTrigger(
                day_of_week='mon-fri',
                hour=20,
                minute=30
            ),
            id='market_close_collection',
            name='Market Close Collection',
            replace_existing=True
        )

        # 5. General data collection every 30 minutes during market hours
        self.scheduler.add_job(
            lambda: self._run_async_job(self._collect_market_data()),
            CronTrigger(
                day_of_week='mon-fri',
                hour='14-21',
                minute='0,30'
            ),
            id='general_collection',
            name='General Data Collection',
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("[SCHEDULER] ✅ Enhanced market data scheduler started with 4 market phases")

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

            logger.info(f"[SCHEDULER] ✅ Market data collected: {trending_count} stocks, {detailed_count} detailed")

            # Log summary
            if summary.get('summary_text'):
                logger.info(f"[SCHEDULER] 📰 Market Summary:\n{summary['summary_text'][:500]}...")

        except Exception as e:
            logger.error(f"[SCHEDULER] 💥 Failed to collect market data: {e}", exc_info=True)

    async def _collect_with_recommendation(self, market_phase: str):
        """Collect market data and generate trading recommendations"""
        try:
            logger.info(f"[SCHEDULER] 🎯 Starting {market_phase} collection with recommendations...")

            # Collect market data
            await self._collect_market_data()

            # Get market summary
            market_summary = await self.market_data_service.get_market_summary()

            # Get portfolio state
            from ..dependencies import get_portfolio_manager
            try:
                portfolio_manager = await get_portfolio_manager()
                portfolio_state = await portfolio_manager.get_current_state()
            except Exception as e:
                logger.warning(f"[SCHEDULER] ⚠️ Could not get portfolio state: {e}")
                portfolio_state = {
                    'total_value': 0,
                    'cash_balance': 0,
                    'daily_pnl_pct': 0,
                    'total_pnl_pct': 0,
                    'position_count': 0,
                    'positions': []
                }

            # Get database session for user preferences
            from ..database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                # Generate recommendations with user preferences
                logger.info(f"[SCHEDULER] 🤖 Generating AI recommendations for {market_phase}...")
                recommendations = await self.recommendation_service.generate_trading_recommendations(
                    portfolio_state,
                    market_summary,
                    market_phase,
                    db
                )

            # Store latest recommendation
            self.latest_recommendation = recommendations

            logger.info(f"[SCHEDULER] ✅ {market_phase} complete: {len(recommendations.get('recommendations', []))} recommendations generated")

            # Log recommendations summary
            if recommendations.get('summary'):
                logger.info(f"[SCHEDULER] 💡 Recommendations: {recommendations['summary'][:200]}...")

        except Exception as e:
            logger.error(f"[SCHEDULER] 💥 Failed {market_phase} collection: {e}", exc_info=True)

    def get_latest_recommendation(self) -> dict:
        """Get the latest trading recommendation"""
        return self.latest_recommendation or {
            'recommendations': [],
            'summary': '아직 추천이 생성되지 않았습니다.',
            'timestamp': datetime.now().isoformat()
        }

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
