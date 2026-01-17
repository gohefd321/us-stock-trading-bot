"""
Scheduler API Routes
Control automated trading schedule
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
import logging

from ..services.scheduler_service import SchedulerService
from ..dependencies import get_scheduler_service

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_scheduler_status(
    scheduler: SchedulerService = Depends(get_scheduler_service)
) -> Dict:
    """
    Get scheduler status and upcoming jobs

    Returns:
        Scheduler status dictionary
    """
    try:
        status = scheduler.get_status()
        return {
            "success": True,
            **status
        }
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_scheduler(
    scheduler: SchedulerService = Depends(get_scheduler_service)
) -> Dict:
    """
    Start the automated trading scheduler

    Returns:
        Success status
    """
    try:
        if scheduler.is_running:
            return {
                "success": False,
                "message": "Scheduler is already running"
            }

        success = scheduler.start()

        if success:
            return {
                "success": True,
                "message": "Scheduler started successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start scheduler")

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler(
    scheduler: SchedulerService = Depends(get_scheduler_service)
) -> Dict:
    """
    Stop the automated trading scheduler

    Returns:
        Success status
    """
    try:
        if not scheduler.is_running:
            return {
                "success": False,
                "message": "Scheduler is not running"
            }

        success = scheduler.stop()

        if success:
            return {
                "success": True,
                "message": "Scheduler stopped successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to stop scheduler")

    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute/{decision_type}")
async def execute_trading_session(
    decision_type: str,
    scheduler: SchedulerService = Depends(get_scheduler_service)
) -> Dict:
    """
    Manually trigger a trading session

    Args:
        decision_type: PRE_MARKET, MID_SESSION, or PRE_CLOSE

    Returns:
        Execution status
    """
    try:
        valid_types = ['PRE_MARKET', 'MID_SESSION', 'PRE_CLOSE']

        if decision_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision_type. Must be one of: {valid_types}"
            )

        if not scheduler.is_running:
            raise HTTPException(
                status_code=400,
                detail="Scheduler must be running to execute sessions"
            )

        success = scheduler.execute_now(decision_type)

        if success:
            return {
                "success": True,
                "message": f"{decision_type} session triggered",
                "decision_type": decision_type
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to trigger session")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute trading session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
