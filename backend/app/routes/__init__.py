"""
API Routes Module
"""

from .scheduler import router as scheduler_router
from .trading import router as trading_router
from .portfolio import router as portfolio_router
from .signals import router as signals_router
from .settings import router as settings_router

__all__ = [
    'scheduler_router',
    'trading_router',
    'portfolio_router',
    'signals_router',
    'settings_router'
]
