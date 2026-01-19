"""
Web Routes (HTML Template Rendering)
FastAPI routes that serve Jinja2 templates
"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import logging

from ..database import get_db
from ..services.portfolio_manager import PortfolioManager
from ..services.broker_service import BrokerService
from ..services.encryption_service import EncryptionService
from ..config import Settings

logger = logging.getLogger(__name__)

# Initialize templates
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


# Simple scheduler status holder (since SchedulerService requires TradingEngine)
class SchedulerStatus:
    """Simple scheduler status for web UI"""
    def __init__(self):
        self.is_running = False
        self.job_count = 0

    def get_status(self):
        return {
            'is_running': self.is_running,
            'job_count': self.job_count
        }

    def start(self):
        logger.info("Scheduler start requested")
        self.is_running = True
        return True

    def stop(self):
        logger.info("Scheduler stop requested")
        self.is_running = False
        return True


# Global scheduler status
_scheduler_status = SchedulerStatus()


# Dependency: Get services
async def get_services(db: AsyncSession = Depends(get_db)):
    """Get initialized services"""
    settings = Settings()
    broker = BrokerService(settings)
    portfolio = PortfolioManager(broker, settings, db)
    encryption = EncryptionService(settings)

    return {
        'settings': settings,
        'broker': broker,
        'portfolio': portfolio,
        'scheduler': _scheduler_status,
        'encryption': encryption,
        'db': db
    }


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, services: dict = Depends(get_services)):
    """Render dashboard page"""
    try:
        # Get portfolio state
        portfolio_state = await services['portfolio'].get_current_state()

        # Get scheduler status
        scheduler_status = services['scheduler'].get_status()

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "portfolio": portfolio_state,
            "scheduler": scheduler_status,
            "error": portfolio_state.get('error'),
            "warning": portfolio_state.get('warning')
        })

    except Exception as e:
        logger.error(f"Failed to render dashboard: {e}")
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "portfolio": {
                'cash_balance': 0,
                'total_value': 0,
                'positions': [],
                'position_count': 0,
                'daily_pnl': 0,
                'daily_pnl_pct': 0,
                'total_pnl': 0,
                'total_pnl_pct': 0
            },
            "scheduler": {
                'is_running': False,
                'job_count': 0
            },
            "error": str(e)
        })


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, services: dict = Depends(get_services)):
    """Render settings page"""
    try:
        db = services['db']
        encryption = services['encryption']
        settings = services['settings']

        # Load API keys
        from sqlalchemy import select
        from ..models import APIKey, RiskParameter

        stmt = select(APIKey).where(APIKey.is_active == True)
        result = await db.execute(stmt)
        api_keys_list = result.scalars().all()

        # Decrypt API keys
        api_keys = {}
        for key in api_keys_list:
            try:
                decrypted_value = encryption.decrypt(key.encrypted_value)
                api_keys[key.key_name] = decrypted_value
            except Exception as e:
                logger.error(f"Failed to decrypt {key.key_name}: {e}")

        # Load risk parameters
        stmt = select(RiskParameter).limit(1)
        result = await db.execute(stmt)
        risk_param = result.scalar_one_or_none()

        if not risk_param:
            # Default risk parameters
            risk_params = {
                'max_positions': 5,
                'max_position_size_pct': 20.0,
                'stop_loss_pct': 10.0,
                'take_profit_pct': 20.0,
                'daily_loss_limit_pct': 20.0
            }
        else:
            risk_params = {
                'max_positions': risk_param.max_positions,
                'max_position_size_pct': risk_param.max_position_size_pct,
                'stop_loss_pct': risk_param.stop_loss_pct,
                'take_profit_pct': risk_param.take_profit_pct,
                'daily_loss_limit_pct': risk_param.daily_loss_limit_pct
            }

        return templates.TemplateResponse("settings.html", {
            "request": request,
            "api_keys": api_keys,
            "risk_params": risk_params,
            "paper_mode": settings.korea_investment_paper_mode,
            "success": request.query_params.get('success'),
            "error": request.query_params.get('error')
        })

    except Exception as e:
        logger.error(f"Failed to render settings: {e}")
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "api_keys": {},
            "risk_params": {
                'max_positions': 5,
                'max_position_size_pct': 20.0,
                'stop_loss_pct': 10.0,
                'take_profit_pct': 20.0,
                'daily_loss_limit_pct': 20.0
            },
            "paper_mode": True,
            "error": str(e)
        })


@router.post("/scheduler/start")
async def start_scheduler(services: dict = Depends(get_services)):
    """Start scheduler and redirect to dashboard"""
    try:
        scheduler = services['scheduler']
        scheduler.start()
        return RedirectResponse(url="/?success=스케줄러가 시작되었습니다", status_code=303)
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        return RedirectResponse(url=f"/?error=스케줄러 시작 실패: {str(e)}", status_code=303)


@router.post("/scheduler/stop")
async def stop_scheduler(services: dict = Depends(get_services)):
    """Stop scheduler and redirect to dashboard"""
    try:
        scheduler = services['scheduler']
        scheduler.stop()
        return RedirectResponse(url="/?success=스케줄러가 중지되었습니다", status_code=303)
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")
        return RedirectResponse(url=f"/?error=스케줄러 중지 실패: {str(e)}", status_code=303)


@router.post("/settings/save-keys")
async def save_api_keys(
    app_key: str = Form(""),
    app_secret: str = Form(""),
    account_number: str = Form(""),
    paper_mode: str = Form("false"),
    services: dict = Depends(get_services)
):
    """Save API keys and redirect to settings"""
    try:
        db = services['db']
        encryption = services['encryption']

        from sqlalchemy import select, update
        from ..models import APIKey

        # Helper function to save or update key
        async def save_key(key_name: str, key_value: str):
            if not key_value or not key_value.strip():
                return

            # Check if key exists
            stmt = select(APIKey).where(APIKey.key_name == key_name)
            result = await db.execute(stmt)
            existing_key = result.scalar_one_or_none()

            encrypted_value = encryption.encrypt(key_value)

            if existing_key:
                # Update
                stmt = update(APIKey).where(
                    APIKey.key_name == key_name
                ).values(encrypted_value=encrypted_value)
                await db.execute(stmt)
            else:
                # Insert
                new_key = APIKey(
                    key_name=key_name,
                    encrypted_value=encrypted_value,
                    is_active=True
                )
                db.add(new_key)

        # Save each key
        await save_key('app_key', app_key)
        await save_key('app_secret', app_secret)
        await save_key('account_number', account_number)

        # Save paper mode to .env
        import os
        env_path = services['settings'].PROJECT_ROOT / '.env'

        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()

            # Update or add KOREA_INVESTMENT_PAPER_MODE
            found = False
            for i, line in enumerate(lines):
                if line.startswith('KOREA_INVESTMENT_PAPER_MODE='):
                    lines[i] = f'KOREA_INVESTMENT_PAPER_MODE={"true" if paper_mode == "true" else "false"}\n'
                    found = True
                    break

            if not found:
                lines.append(f'\nKOREA_INVESTMENT_PAPER_MODE={"true" if paper_mode == "true" else "false"}\n')

            with open(env_path, 'w') as f:
                f.writelines(lines)

        await db.commit()

        return RedirectResponse(url="/settings?success=API 키가 저장되었습니다", status_code=303)

    except Exception as e:
        logger.error(f"Failed to save API keys: {e}")
        await db.rollback()
        return RedirectResponse(url=f"/settings?error=저장 실패: {str(e)}", status_code=303)


@router.post("/settings/save-risk-params")
async def save_risk_params(
    max_positions: int = Form(...),
    max_position_size_pct: float = Form(...),
    stop_loss_pct: float = Form(...),
    take_profit_pct: float = Form(...),
    daily_loss_limit_pct: float = Form(...),
    services: dict = Depends(get_services)
):
    """Save risk parameters and redirect to settings"""
    try:
        db = services['db']

        from sqlalchemy import select
        from ..models import RiskParameter

        # Check if risk parameters exist
        stmt = select(RiskParameter).limit(1)
        result = await db.execute(stmt)
        risk_param = result.scalar_one_or_none()

        if risk_param:
            # Update existing
            risk_param.max_positions = max_positions
            risk_param.max_position_size_pct = max_position_size_pct
            risk_param.stop_loss_pct = stop_loss_pct
            risk_param.take_profit_pct = take_profit_pct
            risk_param.daily_loss_limit_pct = daily_loss_limit_pct
        else:
            # Create new
            risk_param = RiskParameter(
                max_positions=max_positions,
                max_position_size_pct=max_position_size_pct,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                daily_loss_limit_pct=daily_loss_limit_pct
            )
            db.add(risk_param)

        await db.commit()

        return RedirectResponse(url="/settings?success=리스크 파라미터가 저장되었습니다", status_code=303)

    except Exception as e:
        logger.error(f"Failed to save risk parameters: {e}")
        await db.rollback()
        return RedirectResponse(url=f"/settings?error=저장 실패: {str(e)}", status_code=303)
