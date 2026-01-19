"""
Configuration Management
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from pathlib import Path


# Get project root directory (2 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = f"sqlite+aiosqlite:///{PROJECT_ROOT}/data/trading_bot.db"

    # API Configuration
    korea_investment_api_key: Optional[str] = None
    korea_investment_api_secret: Optional[str] = None
    korea_investment_account_number: Optional[str] = None
    korea_investment_account_password: Optional[str] = None  # Account password for overseas stock trading
    korea_investment_password_padding: bool = False  # Enable 8-char password padding
    korea_investment_paper_mode: bool = False  # Paper trading mode (simulation)
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
    backend_url: str = "http://localhost:8000"  # Backend URL for CORS

    # Trading Parameters
    initial_capital_krw: int = 1000000
    max_position_size_pct: int = 40
    daily_loss_limit_pct: int = 20
    stop_loss_pct: int = 30

    # CORS Origins (comma-separated string from env, converted to list)
    # Set to "*" to allow all origins, or specify your domain
    cors_origins: str = "http://localhost:5173,http://localhost:3000,https://stocking.daechanserver.com,http://stocking.daechanserver.com"

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS origins string to list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
