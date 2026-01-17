"""
Settings API Routes
Manage API keys and system preferences
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Optional
from pydantic import BaseModel
import logging

from ..database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import APIKey, UserPreference
from ..services.encryption_service import EncryptionService

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger(__name__)


class APIKeyRequest(BaseModel):
    """Request model for saving API keys"""
    key_name: str
    key_value: str


class PreferenceRequest(BaseModel):
    """Request model for user preferences"""
    key: str
    value: str


@router.get("/api-keys")
async def get_api_keys(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Get list of configured API keys (values are masked)

    Returns:
        List of API key names and status
    """
    try:
        stmt = select(APIKey)
        result = await db.execute(stmt)
        keys = result.scalars().all()

        key_list = [
            {
                'id': k.id,
                'key_name': k.key_name,
                'is_active': k.is_active,
                'created_at': k.created_at.isoformat() if k.created_at else None,
                'value': '***' + k.encrypted_value[-10:] if k.encrypted_value else None
            }
            for k in keys
        ]

        return {
            'success': True,
            'api_keys': key_list,
            'count': len(key_list)
        }

    except Exception as e:
        logger.error(f"Failed to get API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api-keys")
async def save_api_key(
    request: APIKeyRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Save or update an API key

    Args:
        request: API key name and value

    Returns:
        Success status
    """
    try:
        encryption = EncryptionService()

        # Check if key already exists
        stmt = select(APIKey).where(APIKey.key_name == request.key_name)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        encrypted_value = encryption.encrypt(request.key_value)

        if existing:
            # Update existing key
            existing.encrypted_value = encrypted_value
            existing.is_active = True
            message = f"API key '{request.key_name}' updated"
        else:
            # Create new key
            new_key = APIKey(
                key_name=request.key_name,
                encrypted_value=encrypted_value,
                is_active=True
            )
            db.add(new_key)
            message = f"API key '{request.key_name}' created"

        await db.commit()

        logger.info(message)

        return {
            'success': True,
            'message': message
        }

    except Exception as e:
        logger.error(f"Failed to save API key: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api-keys/{key_name}")
async def delete_api_key(
    key_name: str,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Delete an API key

    Args:
        key_name: Name of the API key to delete

    Returns:
        Success status
    """
    try:
        stmt = select(APIKey).where(APIKey.key_name == key_name)
        result = await db.execute(stmt)
        key = result.scalar_one_or_none()

        if not key:
            raise HTTPException(status_code=404, detail=f"API key '{key_name}' not found")

        await db.delete(key)
        await db.commit()

        logger.info(f"API key '{key_name}' deleted")

        return {
            'success': True,
            'message': f"API key '{key_name}' deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences")
async def get_preferences(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Get all user preferences

    Returns:
        Dictionary of preferences
    """
    try:
        stmt = select(UserPreference)
        result = await db.execute(stmt)
        prefs = result.scalars().all()

        preferences = {p.key: p.value for p in prefs}

        return {
            'success': True,
            'preferences': preferences
        }

    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preferences")
async def save_preference(
    request: PreferenceRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Save or update a user preference

    Args:
        request: Preference key and value

    Returns:
        Success status
    """
    try:
        # Check if preference exists
        stmt = select(UserPreference).where(UserPreference.key == request.key)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.value = request.value
            message = f"Preference '{request.key}' updated"
        else:
            # Create new
            new_pref = UserPreference(
                key=request.key,
                value=request.value
            )
            db.add(new_pref)
            message = f"Preference '{request.key}' created"

        await db.commit()

        logger.info(message)

        return {
            'success': True,
            'message': message
        }

    except Exception as e:
        logger.error(f"Failed to save preference: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-params")
async def get_risk_params(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Get current risk management parameters

    Returns:
        Risk parameters
    """
    try:
        from ..config import settings

        return {
            'success': True,
            'risk_params': {
                'initial_capital_krw': settings.initial_capital_krw,
                'max_position_size_pct': settings.max_position_size_pct,
                'daily_loss_limit_pct': settings.daily_loss_limit_pct,
                'stop_loss_pct': settings.stop_loss_pct
            }
        }

    except Exception as e:
        logger.error(f"Failed to get risk params: {e}")
        raise HTTPException(status_code=500, detail=str(e))
