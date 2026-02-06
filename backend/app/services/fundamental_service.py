"""
Fundamental Data Service

재무 데이터 수집 서비스
- Yahoo Finance (yfinance) - 주 데이터 소스
- Alpha Vantage (optional) - 상세 재무제표

데이터:
- EPS, P/E, ROE, Debt Ratio
- Earnings Calendar
- Analyst Ratings
- Sector/Industry Info
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, date
import time
import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
import asyncio

from ..models.fundamental_data import FundamentalData
from ..config import settings

logger = logging.getLogger(__name__)


class FundamentalService:
    """재무 데이터 수집 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.alpha_vantage_key = getattr(settings, 'alpha_vantage_api_key', None)

    async def get_fundamentals(self, ticker: str) -> Optional[Dict]:
        """
        특정 종목의 재무 데이터 조회

        Args:
            ticker: 종목 코드

        Returns:
            재무 데이터 딕셔너리
        """
        try:
            logger.info(f"📊 Fetching fundamentals for {ticker}...")

            stmt = select(FundamentalData).where(FundamentalData.ticker == ticker)
            result = await self.db.execute(stmt)
            data = result.scalar_one_or_none()

            if data:
                return {
                    "ticker": data.ticker,
                    "valuation": {
                        "eps": data.eps,
                        "pe_ratio": data.pe_ratio,
                        "pb_ratio": data.pb_ratio,
                        "market_cap": data.market_cap,
                    },
                    "profitability": {
                        "roe": data.roe,
                        "roa": data.roa,
                        "profit_margin": data.profit_margin,
                    },
                    "financial_health": {
                        "debt_to_equity": data.debt_to_equity,
                        "current_ratio": data.current_ratio,
                    },
                    "growth": {
                        "revenue_growth": data.revenue_growth,
                        "earnings_growth": data.earnings_growth,
                    },
                    "dividend": {
                        "yield": data.dividend_yield,
                        "payout_ratio": data.payout_ratio,
                    },
                    "analyst": {
                        "rating": data.analyst_rating,
                        "target_price": data.analyst_target_price,
                    },
                    "earnings_calendar": {
                        "next_date": data.next_earnings_date.isoformat() if data.next_earnings_date else None,
                        "last_date": data.last_earnings_date.isoformat() if data.last_earnings_date else None,
                    },
                    "company_info": {
                        "sector": data.sector,
                        "industry": data.industry,
                        "description": data.description,
                    },
                    "updated_at": data.updated_at.isoformat() if data.updated_at else None,
                }
            else:
                logger.warning(f"No fundamental data found for {ticker}")
                return None

        except Exception as e:
            logger.error(f"Failed to get fundamentals for {ticker}: {e}")
            return None

    async def get_earnings_calendar(self, ticker: str) -> Dict:
        """
        실적 발표 일정 조회

        Args:
            ticker: 종목 코드

        Returns:
            실적 발표 일정
        """
        try:
            stmt = select(FundamentalData).where(FundamentalData.ticker == ticker)
            result = await self.db.execute(stmt)
            data = result.scalar_one_or_none()

            if data:
                return {
                    "ticker": ticker,
                    "next_earnings_date": data.next_earnings_date.isoformat() if data.next_earnings_date else None,
                    "last_earnings_date": data.last_earnings_date.isoformat() if data.last_earnings_date else None,
                }
            return {"ticker": ticker, "next_earnings_date": None, "last_earnings_date": None}

        except Exception as e:
            logger.error(f"Failed to get earnings calendar for {ticker}: {e}")
            return {"ticker": ticker, "error": str(e)}

    async def get_top_by_roe(self, limit: int = 20) -> List[Dict]:
        """
        ROE 상위 종목 조회

        Args:
            limit: 조회할 종목 수

        Returns:
            ROE 상위 종목 리스트
        """
        try:
            stmt = (
                select(FundamentalData)
                .where(FundamentalData.roe.isnot(None))
                .order_by(FundamentalData.roe.desc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            stocks = result.scalars().all()

            return [
                {
                    "ticker": s.ticker,
                    "roe": s.roe,
                    "eps": s.eps,
                    "pe_ratio": s.pe_ratio,
                    "market_cap": s.market_cap,
                    "sector": s.sector,
                }
                for s in stocks
            ]

        except Exception as e:
            logger.error(f"Failed to get top ROE stocks: {e}")
            return []

    async def get_upcoming_earnings(self, days_ahead: int = 7) -> List[Dict]:
        """
        향후 N일 이내 실적 발표 예정 종목

        Args:
            days_ahead: 조회 기간 (일)

        Returns:
            실적 발표 예정 종목 리스트
        """
        try:
            today = date.today()
            target_date = date.fromordinal(today.toordinal() + days_ahead)

            stmt = (
                select(FundamentalData)
                .where(FundamentalData.next_earnings_date.isnot(None))
                .where(FundamentalData.next_earnings_date >= today)
                .where(FundamentalData.next_earnings_date <= target_date)
                .order_by(FundamentalData.next_earnings_date)
            )

            result = await self.db.execute(stmt)
            stocks = result.scalars().all()

            return [
                {
                    "ticker": s.ticker,
                    "next_earnings_date": s.next_earnings_date.isoformat(),
                    "sector": s.sector,
                    "market_cap": s.market_cap,
                    "analyst_rating": s.analyst_rating,
                }
                for s in stocks
            ]

        except Exception as e:
            logger.error(f"Failed to get upcoming earnings: {e}")
            return []

    async def update_fundamental(self, ticker: str) -> bool:
        """
        특정 종목의 재무 데이터 업데이트 (Yahoo Finance)

        Args:
            ticker: 종목 코드

        Returns:
            성공 여부
        """
        try:
            logger.info(f"Updating fundamentals for {ticker}...")

            # Yahoo Finance에서 데이터 수집
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._fetch_yfinance_fundamentals, ticker)

            if not data:
                return False

            # DB 업데이트 (Upsert)
            stmt = insert(FundamentalData).values(**data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker'],
                set_={k: getattr(stmt.excluded, k) for k in data.keys() if k != 'ticker'}
            )

            await self.db.execute(stmt)
            await self.db.commit()

            logger.info(f"✓ Updated fundamentals for {ticker}")
            return True

        except Exception as e:
            logger.error(f"Failed to update fundamentals for {ticker}: {e}")
            return False

    async def update_all(self, tickers: List[str]) -> Dict:
        """
        여러 종목의 재무 데이터 일괄 업데이트

        Args:
            tickers: 종목 코드 리스트

        Returns:
            업데이트 결과
        """
        logger.info(f"🔄 Updating fundamentals for {len(tickers)} stocks...")

        success_count = 0
        failed_tickers = []

        for ticker in tickers:
            # Rate limiting: 2초 대기
            await asyncio.sleep(2.0)

            success = await self.update_fundamental(ticker)
            if success:
                success_count += 1
            else:
                failed_tickers.append(ticker)

        logger.info(f"✅ Updated {success_count}/{len(tickers)} stocks")

        return {
            "success": True,
            "total": len(tickers),
            "updated": success_count,
            "failed": failed_tickers,
            "timestamp": datetime.now().isoformat(),
        }

    def _fetch_yfinance_fundamentals(self, ticker: str) -> Optional[Dict]:
        """
        Yahoo Finance에서 재무 데이터 수집 (동기 함수)

        Args:
            ticker: 종목 코드

        Returns:
            재무 데이터 딕셔너리
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info:
                logger.warning(f"No info for {ticker}")
                return None

            # 기본 데이터 추출
            data = {
                "ticker": ticker,
                "eps": self._safe_float(info.get('trailingEps')),
                "pe_ratio": self._safe_float(info.get('trailingPE')),
                "pb_ratio": self._safe_float(info.get('priceToBook')),
                "market_cap": self._safe_float(info.get('marketCap')),
                "roe": self._safe_float(info.get('returnOnEquity')) * 100 if info.get('returnOnEquity') else None,
                "roa": self._safe_float(info.get('returnOnAssets')) * 100 if info.get('returnOnAssets') else None,
                "profit_margin": self._safe_float(info.get('profitMargins')) * 100 if info.get('profitMargins') else None,
                "debt_to_equity": self._safe_float(info.get('debtToEquity')),
                "current_ratio": self._safe_float(info.get('currentRatio')),
                "revenue_growth": self._safe_float(info.get('revenueGrowth')) * 100 if info.get('revenueGrowth') else None,
                "earnings_growth": self._safe_float(info.get('earningsGrowth')) * 100 if info.get('earningsGrowth') else None,
                "dividend_yield": self._safe_float(info.get('dividendYield')) * 100 if info.get('dividendYield') else None,
                "payout_ratio": self._safe_float(info.get('payoutRatio')) * 100 if info.get('payoutRatio') else None,
                "analyst_rating": info.get('recommendationKey', 'N/A').upper(),
                "analyst_target_price": self._safe_float(info.get('targetMeanPrice')),
                "sector": info.get('sector'),
                "industry": info.get('industry'),
                "description": info.get('longBusinessSummary', '')[:500],  # 최대 500자
            }

            # Earnings Calendar (다음 실적 발표일)
            earnings_dates = stock.get_earnings_dates(limit=5)
            if earnings_dates is not None and not earnings_dates.empty:
                # 미래 날짜 찾기
                future_dates = earnings_dates[earnings_dates.index > datetime.now()]
                if not future_dates.empty:
                    next_date = future_dates.index[0].date()
                    data['next_earnings_date'] = next_date

                # 과거 날짜 찾기
                past_dates = earnings_dates[earnings_dates.index <= datetime.now()]
                if not past_dates.empty:
                    last_date = past_dates.index[0].date()
                    data['last_earnings_date'] = last_date

            logger.debug(f"✓ Fetched fundamentals for {ticker}")
            return data

        except Exception as e:
            logger.warning(f"Failed to fetch fundamentals for {ticker}: {e}")
            return None

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """안전하게 float 변환"""
        try:
            if value is None or value == 'N/A':
                return None
            return float(value)
        except (ValueError, TypeError):
            return None
