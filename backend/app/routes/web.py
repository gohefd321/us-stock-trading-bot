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


# Dependency: Get services
async def get_services(db: AsyncSession = Depends(get_db)):
    """Get initialized services"""
    settings = Settings()
    broker = BrokerService(settings)
    portfolio = PortfolioManager(broker, settings, db)
    encryption = EncryptionService()  # Uses default key file path

    return {
        'settings': settings,
        'broker': broker,
        'portfolio': portfolio,
        'encryption': encryption,
        'db': db
    }


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, services: dict = Depends(get_services)):
    """Render dashboard page"""
    try:
        # Get portfolio state
        portfolio_state = await services['portfolio'].get_current_state()

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "portfolio": portfolio_state,
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
            "error": str(e)
        })


@router.get("/api-test", response_class=HTMLResponse)
async def api_test_page(request: Request, services: dict = Depends(get_services)):
    """Render API test page"""
    try:
        settings = services['settings']

        return templates.TemplateResponse("api_test.html", {
            "request": request,
            "paper_mode": settings.korea_investment_paper_mode
        })

    except Exception as e:
        logger.error(f"Failed to render API test page: {e}")
        return templates.TemplateResponse("api_test.html", {
            "request": request,
            "paper_mode": True,
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
        from ..models import APIKey, RiskParameter, UserPreference

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

        # Load auto trading preference
        stmt = select(UserPreference).where(UserPreference.key == 'auto_trading_enabled')
        result = await db.execute(stmt)
        auto_trading_pref = result.scalar_one_or_none()
        auto_trading_enabled = auto_trading_pref.value == 'true' if auto_trading_pref else False

        # Load risk parameters
        stmt = select(RiskParameter).limit(1)
        result = await db.execute(stmt)
        risk_param = result.scalar_one_or_none()

        if not risk_param:
            # Default risk parameters
            risk_params = {
                'initial_capital_usd': settings.initial_capital_usd,
                'max_positions': 5,
                'max_position_size_pct': 20.0,
                'stop_loss_pct': 10.0,
                'take_profit_pct': 20.0,
                'daily_loss_limit_pct': 20.0
            }
        else:
            risk_params = {
                'initial_capital_usd': getattr(risk_param, 'initial_capital_usd', settings.initial_capital_usd),
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
            "password_padding": api_keys.get('password_padding') == 'true',
            "auto_trading_enabled": auto_trading_enabled,
            "success": request.query_params.get('success'),
            "error": request.query_params.get('error')
        })

    except Exception as e:
        logger.error(f"Failed to render settings: {e}")
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "api_keys": {},
            "risk_params": {
                'initial_capital_usd': 1000.0,
                'max_positions': 5,
                'max_position_size_pct': 20.0,
                'stop_loss_pct': 10.0,
                'take_profit_pct': 20.0,
                'daily_loss_limit_pct': 20.0
            },
            "paper_mode": True,
            "error": str(e)
        })


@router.post("/settings/save-keys")
async def save_api_keys(
    app_key: str = Form(""),
    app_secret: str = Form(""),
    account_number: str = Form(""),
    account_password: str = Form(""),
    password_padding: str = Form("false"),
    paper_mode: str = Form("false"),
    gemini_api_key: str = Form(""),
    reddit_client_id: str = Form(""),
    reddit_client_secret: str = Form(""),
    reddit_user_agent: str = Form(""),
    auto_trading_enabled: str = Form("false"),
    services: dict = Depends(get_services)
):
    """Save API keys and redirect to settings"""
    try:
        db = services['db']
        encryption = services['encryption']

        from sqlalchemy import select, update
        from ..models import APIKey, UserPreference

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
        await save_key('account_password', account_password)
        await save_key('password_padding', password_padding)
        await save_key('gemini_api_key', gemini_api_key)
        await save_key('reddit_client_id', reddit_client_id)
        await save_key('reddit_client_secret', reddit_client_secret)
        await save_key('reddit_user_agent', reddit_user_agent)

        # Save API keys and settings to .env file
        import os
        from ..config import PROJECT_ROOT
        env_path = PROJECT_ROOT / '.env'

        # Read existing .env
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
        else:
            lines = []

        # Helper to update or add env variable
        def update_env_var(lines, key, value):
            if not value or not value.strip():
                return lines
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f'{key}='):
                    lines[i] = f'{key}={value}\n'
                    found = True
                    break
            if not found:
                lines.append(f'{key}={value}\n')
            return lines

        # Update all keys
        lines = update_env_var(lines, 'KOREA_INVESTMENT_API_KEY', app_key)
        lines = update_env_var(lines, 'KOREA_INVESTMENT_API_SECRET', app_secret)
        lines = update_env_var(lines, 'KOREA_INVESTMENT_ACCOUNT_NUMBER', account_number)
        lines = update_env_var(lines, 'KOREA_INVESTMENT_ACCOUNT_PASSWORD', account_password)
        lines = update_env_var(lines, 'KOREA_INVESTMENT_PASSWORD_PADDING', 'true' if password_padding == 'true' else 'false')
        lines = update_env_var(lines, 'KOREA_INVESTMENT_PAPER_MODE', 'true' if paper_mode == 'true' else 'false')
        lines = update_env_var(lines, 'GEMINI_API_KEY', gemini_api_key)
        lines = update_env_var(lines, 'REDDIT_CLIENT_ID', reddit_client_id)
        lines = update_env_var(lines, 'REDDIT_CLIENT_SECRET', reddit_client_secret)
        lines = update_env_var(lines, 'REDDIT_USER_AGENT', reddit_user_agent)

        # Write back to .env
        with open(env_path, 'w') as f:
            f.writelines(lines)

        # Save auto trading preference
        stmt = select(UserPreference).where(UserPreference.key == 'auto_trading_enabled')
        result = await db.execute(stmt)
        pref = result.scalar_one_or_none()

        if pref:
            pref.value = 'true' if auto_trading_enabled == 'true' else 'false'
        else:
            pref = UserPreference(
                key='auto_trading_enabled',
                value='true' if auto_trading_enabled == 'true' else 'false'
            )
            db.add(pref)

        await db.commit()

        # Reload broker with new credentials if provided
        if app_key and app_secret and account_number:
            try:
                broker = services['broker']
                broker.reload_credentials(
                    api_key=app_key,
                    api_secret=app_secret,
                    account_number=account_number,
                    account_password=account_password,
                    password_padding=(password_padding == 'true'),
                    is_paper=(paper_mode == 'true')
                )
                logger.info("Broker reloaded with new credentials")
            except Exception as e:
                logger.error(f"Failed to reload broker: {e}")

        return RedirectResponse(url="/settings?success=API 키가 저장되고 브로커가 리로드되었습니다", status_code=303)

    except Exception as e:
        logger.error(f"Failed to save API keys: {e}")
        await db.rollback()
        return RedirectResponse(url=f"/settings?error=저장 실패: {str(e)}", status_code=303)


@router.post("/settings/save-risk-params")
async def save_risk_params(
    initial_capital_usd: float = Form(...),
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
        settings = services['settings']

        from sqlalchemy import select
        from ..models import RiskParameter

        # Check if risk parameters exist
        stmt = select(RiskParameter).limit(1)
        result = await db.execute(stmt)
        risk_param = result.scalar_one_or_none()

        if risk_param:
            # Update existing
            risk_param.initial_capital_usd = initial_capital_usd
            risk_param.max_positions = max_positions
            risk_param.max_position_size_pct = max_position_size_pct
            risk_param.stop_loss_pct = stop_loss_pct
            risk_param.take_profit_pct = take_profit_pct
            risk_param.daily_loss_limit_pct = daily_loss_limit_pct
        else:
            # Create new
            risk_param = RiskParameter(
                initial_capital_usd=initial_capital_usd,
                max_positions=max_positions,
                max_position_size_pct=max_position_size_pct,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                daily_loss_limit_pct=daily_loss_limit_pct
            )
            db.add(risk_param)

        await db.commit()

        # Update settings in .env file
        import os
        from ..config import PROJECT_ROOT
        env_path = PROJECT_ROOT / '.env'

        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
        else:
            lines = []

        # Update INITIAL_CAPITAL_USD
        found = False
        for i, line in enumerate(lines):
            if line.startswith('INITIAL_CAPITAL_USD='):
                lines[i] = f'INITIAL_CAPITAL_USD={initial_capital_usd}\n'
                found = True
                break
        if not found:
            lines.append(f'INITIAL_CAPITAL_USD={initial_capital_usd}\n')

        with open(env_path, 'w') as f:
            f.writelines(lines)

        return RedirectResponse(url="/settings?success=리스크 파라미터가 저장되었습니다", status_code=303)

    except Exception as e:
        logger.error(f"Failed to save risk parameters: {e}")
        await db.rollback()
        return RedirectResponse(url=f"/settings?error=저장 실패: {str(e)}", status_code=303)
