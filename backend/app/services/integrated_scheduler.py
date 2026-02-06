"""
Integrated Scheduler Service

통합 스케줄러 - Phase 1-3 자동화
- Phase 1: 시장 데이터 수집 (Market Screener, Fundamentals, News)
- Phase 2: 실시간 데이터 유지
- Phase 3: 기술적 지표 계산 및 신호 생성
"""

import logging
import asyncio
from datetime import datetime, time as dtime
from typing import List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .market_screener_service import MarketScreenerService
from .fundamental_service import FundamentalService
from .news_event_service import NewsEventService
from .technical_indicator_service import TechnicalIndicatorService
from .signal_generator import SignalGenerator

logger = logging.getLogger(__name__)


class IntegratedScheduler:
    """통합 스케줄러"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

        # 모니터링할 종목 리스트
        self.watchlist = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
            "BRK.B", "JPM", "V", "MA", "UNH", "JNJ", "WMT", "PG"
        ]

    def start(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        logger.info("🚀 Starting Integrated Scheduler...")

        # Phase 1: 데이터 수집 스케줄
        # 1. 시장 스크리너 - 매 1시간마다
        self.scheduler.add_job(
            self._run_market_scan,
            CronTrigger(minute=0),  # 매 시간 정각
            id="market_scan",
            name="Market Screener Scan",
            replace_existing=True
        )

        # 2. 재무 데이터 업데이트 - 매일 오전 9시 (장 시작 전)
        self.scheduler.add_job(
            self._update_fundamentals,
            CronTrigger(hour=9, minute=0),
            id="fundamentals_update",
            name="Fundamentals Data Update",
            replace_existing=True
        )

        # 3. 뉴스 수집 - 매 30분마다
        self.scheduler.add_job(
            self._collect_news,
            CronTrigger(minute="0,30"),
            id="news_collection",
            name="News Collection",
            replace_existing=True
        )

        # 4. LLM 일일 리포트 - 매일 오전 8시
        self.scheduler.add_job(
            self._generate_daily_report,
            CronTrigger(hour=8, minute=0),
            id="daily_report",
            name="LLM Daily Report",
            replace_existing=True
        )

        # Phase 3: 기술적 지표 및 신호 생성
        # 5. 기술적 지표 계산 - 매 15분마다 (장중)
        self.scheduler.add_job(
            self._calculate_indicators,
            CronTrigger(minute="*/15", hour="9-16"),  # 9AM-4PM
            id="indicators_calculation",
            name="Technical Indicators Calculation",
            replace_existing=True
        )

        # 6. 트레이딩 신호 생성 - 매 30분마다 (장중)
        self.scheduler.add_job(
            self._generate_trading_signals,
            CronTrigger(minute="0,30", hour="9-16"),
            id="signal_generation",
            name="Trading Signal Generation",
            replace_existing=True
        )

        # 스케줄러 시작
        self.scheduler.start()
        self.is_running = True

        logger.info("✅ Integrated Scheduler started successfully")
        self._print_scheduled_jobs()

    def stop(self):
        """스케줄러 중지"""
        if not self.is_running:
            logger.warning("Scheduler not running")
            return

        logger.info("🛑 Stopping Integrated Scheduler...")
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("✅ Scheduler stopped")

    def _print_scheduled_jobs(self):
        """예약된 작업 출력"""
        jobs = self.scheduler.get_jobs()
        logger.info(f"📅 Scheduled Jobs ({len(jobs)}):")
        for job in jobs:
            logger.info(f"  - {job.name} (ID: {job.id})")
            logger.info(f"    Next run: {job.next_run_time}")

    async def _get_db_session(self):
        """DB 세션 가져오기"""
        async for db in get_db():
            return db

    async def _run_market_scan(self):
        """Phase 1.1: 시장 스크리너 실행"""
        try:
            logger.info("📊 Running market scan...")
            db = await self._get_db_session()

            screener = MarketScreenerService(db)
            result = await screener.scan_all()

            if result.get('success'):
                logger.info(f"✅ Market scan completed: {result.get('updated_count')} stocks updated")
            else:
                logger.error(f"❌ Market scan failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error in market scan: {e}")

    async def _update_fundamentals(self):
        """Phase 1.2: 재무 데이터 업데이트"""
        try:
            logger.info("💰 Updating fundamental data...")
            db = await self._get_db_session()

            fundamental_service = FundamentalService(db)
            result = await fundamental_service.update_all(self.watchlist)

            logger.info(f"✅ Fundamentals updated: {result.get('updated')}/{result.get('total')}")

        except Exception as e:
            logger.error(f"Error updating fundamentals: {e}")

    async def _collect_news(self):
        """Phase 1.3: 뉴스 수집"""
        try:
            logger.info("📰 Collecting news...")
            db = await self._get_db_session()

            news_service = NewsEventService(db)
            total_collected = 0

            for ticker in self.watchlist[:5]:  # 상위 5개만 수집 (API 제한)
                count = await news_service.fetch_and_store_news(ticker)
                total_collected += count
                await asyncio.sleep(1)  # Rate limiting

            logger.info(f"✅ News collected: {total_collected} articles")

        except Exception as e:
            logger.error(f"Error collecting news: {e}")

    async def _generate_daily_report(self):
        """Phase 1.4: LLM 일일 리포트 생성"""
        try:
            logger.info("📝 Generating daily report...")
            db = await self._get_db_session()

            from .daily_report_service import DailyReportService
            report_service = DailyReportService(db)
            result = await report_service.generate_daily_report()

            if result.get('success'):
                recommended = len(result.get('recommended_stocks', []))
                logger.info(f"✅ Daily report generated: {recommended} stocks recommended")
            else:
                logger.error(f"❌ Daily report failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error generating daily report: {e}")

    async def _calculate_indicators(self):
        """Phase 3.1: 기술적 지표 계산"""
        try:
            logger.info("📈 Calculating technical indicators...")
            db = await self._get_db_session()

            indicator_service = TechnicalIndicatorService(db)
            success_count = 0

            for ticker in self.watchlist:
                result = await indicator_service.calculate_indicators(ticker, '1h', 200)
                if result.get('success'):
                    success_count += 1

                await asyncio.sleep(0.5)  # Rate limiting

            logger.info(f"✅ Indicators calculated: {success_count}/{len(self.watchlist)} stocks")

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")

    async def _generate_trading_signals(self):
        """Phase 3.4: 트레이딩 신호 생성"""
        try:
            logger.info("🎯 Generating trading signals...")
            db = await self._get_db_session()

            signal_generator = SignalGenerator(db)

            # 기본 전략 조합 사용
            strategies = ["MA_CROSS", "RSI", "MACD"]

            result = await signal_generator.scan_multiple_tickers(
                tickers=self.watchlist,
                timeframe='1h',
                strategy_names=strategies
            )

            if result.get('success'):
                buy_count = len(result.get('buy_signals', []))
                sell_count = len(result.get('sell_signals', []))
                logger.info(f"✅ Signals generated: {buy_count} BUY, {sell_count} SELL")

                # 강한 매수 신호 로깅
                for signal in result.get('buy_signals', [])[:3]:
                    ticker = signal['ticker']
                    strength = signal['signal']['strength']
                    logger.info(f"  🟢 Strong BUY: {ticker} (strength: {strength:.2f})")

            else:
                logger.error("❌ Signal generation failed")

        except Exception as e:
            logger.error(f"Error generating signals: {e}")

    def add_to_watchlist(self, ticker: str):
        """워치리스트에 종목 추가"""
        if ticker not in self.watchlist:
            self.watchlist.append(ticker)
            logger.info(f"Added {ticker} to watchlist")

    def remove_from_watchlist(self, ticker: str):
        """워치리스트에서 종목 제거"""
        if ticker in self.watchlist:
            self.watchlist.remove(ticker)
            logger.info(f"Removed {ticker} from watchlist")

    def get_watchlist(self) -> List[str]:
        """워치리스트 조회"""
        return self.watchlist.copy()

    def get_status(self) -> dict:
        """스케줄러 상태 조회"""
        jobs = self.scheduler.get_jobs()

        return {
            "is_running": self.is_running,
            "watchlist_count": len(self.watchlist),
            "scheduled_jobs": len(jobs),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                }
                for job in jobs
            ]
        }


# Global instance
_integrated_scheduler: Optional[IntegratedScheduler] = None


def get_integrated_scheduler() -> IntegratedScheduler:
    """통합 스케줄러 싱글톤"""
    global _integrated_scheduler
    if _integrated_scheduler is None:
        _integrated_scheduler = IntegratedScheduler()
    return _integrated_scheduler
