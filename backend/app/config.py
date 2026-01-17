"""
Configuration Management
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/trading_bot.db"

    # API Configuration
    korea_investment_api_key: Optional[str] = None
    korea_investment_api_secret: Optional[str] = None
    korea_investment_account_number: Optional[str] = None
    gemini_api_key: Optional[str] = None
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: str = "TradingBot/1.0"
    kakao_rest_api_key: Optional[str] = None

    # Application
    app_name: str = "US Stock Trading Bot"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    frontend_url: str = "http://localhost:5173"

    # Trading Parameters
    initial_capital_krw: int = 1000000
    max_position_size_pct: int = 40
    daily_loss_limit_pct: int = 20
    stop_loss_pct: int = 30

    # CORS Origins
    cors_origins: list = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
