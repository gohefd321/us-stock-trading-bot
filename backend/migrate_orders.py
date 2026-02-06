"""
Database Migration: Order & Portfolio Position Tables

주문 및 포지션 테이블 생성
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, Base
from app.models.order import Order
from app.models.portfolio_position import PortfolioPosition

async def create_tables():
    """Create order and portfolio_position tables"""
    print("Creating order and portfolio_position tables...")

    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)

    print("✓ Tables created successfully!")
    print("  - orders")
    print("  - portfolio_positions")

if __name__ == "__main__":
    asyncio.run(create_tables())
