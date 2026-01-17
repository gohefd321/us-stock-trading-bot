"""
Dependency Injection
FastAPI dependencies for services
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from .database import AsyncSessionLocal
from .config import Settings
from .services.broker_service import BrokerService
from .services.portfolio_manager import PortfolioManager
from .services.signal_aggregator import SignalAggregator
from .services.wsb_scraper import WSBScraper
from .services.yahoo_finance_service import YahooFinanceService
from .services.tipranks_service import TipRanksService
from .services.risk_manager import RiskManager
from .services.gemini_service import GeminiService
from .services.trading_engine import TradingEngine
from .services.scheduler_service import SchedulerService
from .gemini_functions.function_handlers import FunctionHandler

# Global service instances (initialized on startup)
_broker_service = None
_portfolio_manager = None
_signal_aggregator = None
_risk_manager = None
_gemini_service = None
_function_handler = None
_trading_engine = None
_scheduler_service = None
_settings = None


def init_services(settings: Settings):
    """
    Initialize all services (called on app startup)

    Args:
        settings: Application settings
    """
    global _broker_service, _portfolio_manager, _signal_aggregator
    global _risk_manager, _gemini_service, _function_handler
    global _trading_engine, _scheduler_service, _settings

    _settings = settings

    # Initialize broker
    _broker_service = BrokerService(settings)

    # Initialize portfolio manager (without db for now)
    _portfolio_manager = PortfolioManager(_broker_service, settings)

    # Initialize signal services
    wsb_scraper = WSBScraper(settings)
    yahoo_service = YahooFinanceService()
    tipranks_service = TipRanksService()
    _signal_aggregator = SignalAggregator(wsb_scraper, yahoo_service, tipranks_service)

    # Initialize risk manager
    _risk_manager = RiskManager(_portfolio_manager, _broker_service, settings)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_settings() -> Settings:
    """Get application settings"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


async def get_broker_service() -> BrokerService:
    """Get broker service instance"""
    global _broker_service
    if _broker_service is None:
        settings = await get_settings()
        _broker_service = BrokerService(settings)
    return _broker_service


async def get_portfolio_manager() -> PortfolioManager:
    """Get portfolio manager instance"""
    global _portfolio_manager
    if _portfolio_manager is None:
        broker = await get_broker_service()
        settings = await get_settings()
        _portfolio_manager = PortfolioManager(broker, settings)
    return _portfolio_manager


async def get_signal_aggregator() -> SignalAggregator:
    """Get signal aggregator instance"""
    global _signal_aggregator
    if _signal_aggregator is None:
        settings = await get_settings()
        wsb_scraper = WSBScraper(settings)
        yahoo_service = YahooFinanceService()
        tipranks_service = TipRanksService()
        _signal_aggregator = SignalAggregator(wsb_scraper, yahoo_service, tipranks_service)
    return _signal_aggregator


async def get_risk_manager() -> RiskManager:
    """Get risk manager instance"""
    global _risk_manager
    if _risk_manager is None:
        portfolio = await get_portfolio_manager()
        broker = await get_broker_service()
        settings = await get_settings()
        _risk_manager = RiskManager(portfolio, broker, settings)
    return _risk_manager


def get_function_handler() -> FunctionHandler:
    """Get function handler instance (requires db session)"""
    # This is called with db session in routes
    pass


async def get_gemini_service() -> GeminiService:
    """Get Gemini service instance"""
    global _gemini_service
    if _gemini_service is None:
        # Initialize with mock handler for now
        # Real handler is created per-request with db session
        pass
    return _gemini_service


async def get_trading_engine() -> TradingEngine:
    """Get trading engine instance"""
    global _trading_engine
    if _trading_engine is None:
        # Trading engine requires db session, created per-request
        pass
    return _trading_engine


async def get_scheduler_service() -> SchedulerService:
    """Get scheduler service instance"""
    global _scheduler_service
    if _scheduler_service is None:
        # Scheduler requires trading engine
        pass
    return _scheduler_service
