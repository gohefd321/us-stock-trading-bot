"""
FastAPI Main Application
US Stock Trading Bot
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from .config import settings
from .database import init_db
from .utils.logging_config import setup_logging
from .dependencies import init_services
from .routes import (
    scheduler_router,
    trading_router,
    portfolio_router,
    signals_router,
    settings_router
)

# Setup logging
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

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
app.include_router(scheduler_router)
app.include_router(trading_router)
app.include_router(portfolio_router)
app.include_router(signals_router)
app.include_router(settings_router)


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
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

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down US Stock Trading Bot...")
    # Cleanup tasks will be added here
    logger.info("Application shutdown complete")


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "message": "US Stock Trading Bot API",
        "version": settings.app_version,
        "status": "running"
    }


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
