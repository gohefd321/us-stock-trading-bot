"""
FastAPI Main Application
US Stock Trading Bot
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import asyncio

from .config import settings
from .database import init_db
from .utils.logging_config import setup_logging
from .dependencies import init_services, get_broker_service, get_market_data_scheduler
from .routes import (
    scheduler_router,
    trading_router,
    portfolio_router,
    signals_router,
    settings_router
)
from .routes.web import router as web_router
from .routes.chat import router as chat_router
from .routes.recommendations import router as recommendations_router
from .routes.api_test import router as api_test_router

# Setup logging
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Background task for token refresh
_token_refresh_task = None

# Market data scheduler
_market_data_scheduler = None

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Automated US Stock Trading Bot powered by Gemini AI",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(web_router)  # Web UI routes (HTML templates)
app.include_router(chat_router)  # Chat API routes
app.include_router(scheduler_router)
app.include_router(trading_router)
app.include_router(portfolio_router)
app.include_router(signals_router)
app.include_router(settings_router)
app.include_router(recommendations_router)  # AI recommendations routes
app.include_router(api_test_router)  # API test routes


async def token_refresh_loop():
    """Background task to refresh access token every 22 hours"""
    global _token_refresh_task

    while True:
        try:
            # Wait 22 hours (79200 seconds)
            await asyncio.sleep(22 * 60 * 60)

            # Get broker service and refresh token
            broker = await get_broker_service()
            if broker and broker.needs_token_refresh():
                logger.info("22 hours elapsed, refreshing access token...")
                success = broker.refresh_token()
                if success:
                    logger.info("✓ Access token refreshed successfully")
                else:
                    logger.error("✗ Failed to refresh access token")

        except asyncio.CancelledError:
            logger.info("Token refresh task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in token refresh loop: {e}")
            # Continue loop even on error


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    global _token_refresh_task, _market_data_scheduler

    logger.info("Starting US Stock Trading Bot...")
    logger.info(f"Environment: {settings.app_name} v{settings.app_version}")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Initialize services
    try:
        init_services(settings)
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    # Start token refresh background task
    _token_refresh_task = asyncio.create_task(token_refresh_loop())
    logger.info("Started access token refresh task (every 22 hours)")

    # Start market data scheduler
    try:
        _market_data_scheduler = await get_market_data_scheduler()
        _market_data_scheduler.start()
        logger.info("Started market data scheduler with AI recommendations")
    except Exception as e:
        logger.error(f"Failed to start market data scheduler: {e}")
        # Continue without market data scheduler

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    global _token_refresh_task, _market_data_scheduler

    logger.info("Shutting down US Stock Trading Bot...")

    # Cancel token refresh task
    if _token_refresh_task:
        _token_refresh_task.cancel()
        try:
            await _token_refresh_task
        except asyncio.CancelledError:
            pass

    # Stop market data scheduler
    if _market_data_scheduler:
        _market_data_scheduler.stop()

    logger.info("Application shutdown complete")


# Root endpoint removed - now handled by web_router


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version
    }


@app.get("/api/info")
async def api_info():
    """API information endpoint"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "trading_params": {
            "initial_capital_krw": settings.initial_capital_krw,
            "max_position_size_pct": settings.max_position_size_pct,
            "daily_loss_limit_pct": settings.daily_loss_limit_pct,
            "stop_loss_pct": settings.stop_loss_pct,
        }
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
