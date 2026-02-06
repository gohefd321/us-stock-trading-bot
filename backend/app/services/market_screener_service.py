"""
Market Screener Service

시장 스크리너 서비스
- 시가총액 순위
- 거래량 급증 종목
- 급등락 종목
- 52주 신고가/신저가

데이터 소스: Yahoo Finance (yfinance)
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import yfinance as yf
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
import asyncio

from ..models.market_screener import MarketScreener

logger = logging.getLogger(__name__)


# S&P 500 주요 종목 (처음엔 20개로 시작, 점진적으로 확대)
SP500_TOP_TICKERS = [
    # Tech Giants
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO",
    # Finance
    "BRK.B", "JPM", "V", "MA",
    # Healthcare
    "UNH", "JNJ", "LLY", "ABBV",
    # Consumer
    "WMT", "PG", "KO", "COST",
]

# 나중에 활성화할 전체 100개 리스트
SP500_FULL_LIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "UNH", "JNJ",
    "V", "XOM", "WMT", "JPM", "PG", "MA", "HD", "CVX", "MRK", "ABBV",
    "KO", "PEP", "AVGO", "COST", "TMO", "MCD", "CSCO", "ACN", "ABT", "DHR",
    "LIN", "ADBE", "VZ", "NKE", "TXN", "PM", "DIS", "CMCSA", "NFLX", "AMD",
    "CRM", "INTC", "ORCL", "NEE", "WFC", "UPS", "HON", "QCOM", "BMY", "RTX",
    "INTU", "T", "LOW", "UNP", "BA", "SPGI", "LMT", "CAT", "SBUX", "DE",
    "GS", "ELV", "AXP", "BLK", "MDT", "GILD", "SYK", "ADP", "ADI", "BKNG",
    "MDLZ", "MMC", "CI", "CVS", "TJX", "VRTX", "SCHW", "PLD", "AMT", "C",
    "ZTS", "MO", "ISRG", "SLB", "TMUS", "CB", "EOG", "DUK", "SO", "NOC",
    "BDX", "REGN", "ITW", "PGR", "USB", "APD", "MMM", "CL", "GE", "BSX"
]


class MarketScreenerService:
    """시장 스크리너 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tickers = SP500_TOP_TICKERS

    async def get_top_gainers(self, limit: int = 20) -> List[Dict]:
        """
        급등 종목 조회 (가격 상승률 순)

        Args:
            limit: 조회할 종목 수

        Returns:
            급등 종목 리스트
        """
        try:
            logger.info(f"📈 Fetching top {limit} gainers...")

            stmt = (
                select(MarketScreener)
                .where(MarketScreener.price_change_pct > 0)
                .order_by(MarketScreener.price_change_pct.desc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            gainers = result.scalars().all()

            return [
                {
                    "ticker": g.ticker,
                    "price": g.current_price,
                    "change_pct": g.price_change_pct,
                    "market_cap": g.market_cap,
                    "volume_change_pct": g.volume_change_pct,
                    "is_52w_high": g.is_52w_high,
                }
                for g in gainers
            ]

        except Exception as e:
            logger.error(f"Failed to get top gainers: {e}")
            return []

    async def get_top_losers(self, limit: int = 20) -> List[Dict]:
        """
        급락 종목 조회 (가격 하락률 순)

        Args:
            limit: 조회할 종목 수

        Returns:
            급락 종목 리스트
        """
        try:
            logger.info(f"📉 Fetching top {limit} losers...")

            stmt = (
                select(MarketScreener)
                .where(MarketScreener.price_change_pct < 0)
                .order_by(MarketScreener.price_change_pct.asc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            losers = result.scalars().all()

            return [
                {
                    "ticker": l.ticker,
                    "price": l.current_price,
                    "change_pct": l.price_change_pct,
                    "market_cap": l.market_cap,
                    "volume_change_pct": l.volume_change_pct,
                    "is_52w_low": l.is_52w_low,
                }
                for l in losers
            ]

        except Exception as e:
            logger.error(f"Failed to get top losers: {e}")
            return []

    async def get_volume_surge(self, limit: int = 20, threshold: float = 200.0) -> List[Dict]:
        """
        거래량 급증 종목 조회

        Args:
            limit: 조회할 종목 수
            threshold: 거래량 증가 기준 (%, 기본 200%)

        Returns:
            거래량 급증 종목 리스트
        """
        try:
            logger.info(f"📊 Fetching top {limit} volume surge stocks (threshold: {threshold}%)...")

            stmt = (
                select(MarketScreener)
                .where(MarketScreener.volume_change_pct >= threshold)
                .order_by(MarketScreener.volume_change_pct.desc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            surge_stocks = result.scalars().all()

            return [
                {
                    "ticker": s.ticker,
                    "price": s.current_price,
                    "price_change_pct": s.price_change_pct,
                    "volume_change_pct": s.volume_change_pct,
                    "avg_volume_10d": s.avg_volume_10d,
                    "market_cap": s.market_cap,
                }
                for s in surge_stocks
            ]

        except Exception as e:
            logger.error(f"Failed to get volume surge stocks: {e}")
            return []

    async def get_market_cap_leaders(self, limit: int = 50) -> List[Dict]:
        """
        시가총액 상위 종목 조회

        Args:
            limit: 조회할 종목 수

        Returns:
            시가총액 상위 종목 리스트
        """
        try:
            logger.info(f"💰 Fetching top {limit} market cap leaders...")

            stmt = (
                select(MarketScreener)
                .where(MarketScreener.market_cap.isnot(None))
                .order_by(MarketScreener.market_cap.desc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            leaders = result.scalars().all()

            return [
                {
                    "ticker": l.ticker,
                    "market_cap": l.market_cap,
                    "price": l.current_price,
                    "price_change_pct": l.price_change_pct,
                    "volume_rank": l.volume_rank,
                }
                for l in leaders
            ]

        except Exception as e:
            logger.error(f"Failed to get market cap leaders: {e}")
            return []

    async def get_52w_extremes(self) -> Dict[str, List[Dict]]:
        """
        52주 신고가/신저가 종목 조회

        Returns:
            {"highs": [...], "lows": [...]}
        """
        try:
            logger.info("🔝 Fetching 52-week extremes...")

            # 52주 신고가
            highs_stmt = select(MarketScreener).where(MarketScreener.is_52w_high == True)
            highs_result = await self.db.execute(highs_stmt)
            highs = highs_result.scalars().all()

            # 52주 신저가
            lows_stmt = select(MarketScreener).where(MarketScreener.is_52w_low == True)
            lows_result = await self.db.execute(lows_stmt)
            lows = lows_result.scalars().all()

            return {
                "highs": [
                    {
                        "ticker": h.ticker,
                        "price": h.current_price,
                        "market_cap": h.market_cap,
                        "price_change_pct": h.price_change_pct,
                    }
                    for h in highs
                ],
                "lows": [
                    {
                        "ticker": l.ticker,
                        "price": l.current_price,
                        "market_cap": l.market_cap,
                        "price_change_pct": l.price_change_pct,
                    }
                    for l in lows
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get 52w extremes: {e}")
            return {"highs": [], "lows": []}

    async def scan_all(self) -> Dict:
        """
        전체 스크리너 실행 및 DB 업데이트

        Returns:
            스캔 결과 요약
        """
        try:
            logger.info("🔍 Starting full market scan...")

            # 데이터 수집
            scan_results = await self._fetch_market_data()

            # DB 업데이트
            updated_count = await self._update_database(scan_results)

            logger.info(f"✅ Market scan complete: {updated_count} stocks updated")

            return {
                "success": True,
                "updated_count": updated_count,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Market scan failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _fetch_market_data(self) -> List[Dict]:
        """
        Yahoo Finance에서 시장 데이터 수집

        Returns:
            수집된 데이터 리스트
        """
        logger.info(f"📥 Fetching data for {len(self.tickers)} stocks...")

        # 비동기로 처리하기 위해 thread pool 사용
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, self._fetch_yfinance_data)

        logger.info(f"✓ Fetched data for {len(results)} stocks")
        return results

    def _fetch_yfinance_data(self) -> List[Dict]:
        """
        yfinance로 데이터 수집 (동기 함수)

        Returns:
            수집된 데이터 리스트
        """
        results = []

        for ticker in self.tickers:
            try:
                # Rate limiting: 1 second delay between requests
                time.sleep(1.0)

                stock = yf.Ticker(ticker)

                # 기본 정보
                info = stock.info
                if not info:
                    logger.warning(f"No data for {ticker}")
                    continue

                # 과거 데이터 (10일)
                hist = stock.history(period="10d")
                if hist.empty:
                    logger.warning(f"No history for {ticker}")
                    continue

                # 52주 데이터
                hist_52w = stock.history(period="1y")
                if hist_52w.empty:
                    hist_52w = hist

                # 현재 가격
                current_price = hist['Close'].iloc[-1]

                # 전일 대비 변동률
                if len(hist) >= 2:
                    prev_close = hist['Close'].iloc[-2]
                    price_change_pct = ((current_price - prev_close) / prev_close) * 100
                else:
                    price_change_pct = 0.0

                # 거래량 변동률
                avg_volume = hist['Volume'].iloc[:-1].mean() if len(hist) > 1 else hist['Volume'].mean()
                current_volume = hist['Volume'].iloc[-1]

                if avg_volume > 0:
                    volume_change_pct = ((current_volume - avg_volume) / avg_volume) * 100
                else:
                    volume_change_pct = 0.0

                # 52주 신고가/신저가 체크
                year_high = hist_52w['High'].max()
                year_low = hist_52w['Low'].min()

                is_52w_high = abs(current_price - year_high) / year_high < 0.01  # 1% 이내
                is_52w_low = abs(current_price - year_low) / year_low < 0.01

                # 시가총액
                market_cap = info.get('marketCap', 0)

                results.append({
                    "ticker": ticker,
                    "market_cap": float(market_cap) if market_cap else None,
                    "price_change_pct": round(price_change_pct, 2),
                    "volume_change_pct": round(volume_change_pct, 2),
                    "is_52w_high": is_52w_high,
                    "is_52w_low": is_52w_low,
                    "avg_volume_10d": float(avg_volume),
                    "current_price": float(current_price),
                })

                logger.debug(f"✓ {ticker}: ${current_price:.2f} ({price_change_pct:+.2f}%)")

            except Exception as e:
                logger.warning(f"Failed to fetch {ticker}: {e}")
                continue

        return results

    async def _update_database(self, scan_results: List[Dict]) -> int:
        """
        스캔 결과를 DB에 저장

        Args:
            scan_results: 스캔 결과 리스트

        Returns:
            업데이트된 레코드 수
        """
        try:
            updated_count = 0

            for data in scan_results:
                # Upsert (INSERT or UPDATE)
                stmt = insert(MarketScreener).values(**data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker'],
                    set_={
                        'market_cap': stmt.excluded.market_cap,
                        'price_change_pct': stmt.excluded.price_change_pct,
                        'volume_change_pct': stmt.excluded.volume_change_pct,
                        'is_52w_high': stmt.excluded.is_52w_high,
                        'is_52w_low': stmt.excluded.is_52w_low,
                        'avg_volume_10d': stmt.excluded.avg_volume_10d,
                        'current_price': stmt.excluded.current_price,
                        'updated_at': func.now(),
                    }
                )

                await self.db.execute(stmt)
                updated_count += 1

            await self.db.commit()

            # 거래량 순위 계산 (별도 업데이트)
            await self._calculate_volume_ranks()

            return updated_count

        except Exception as e:
            logger.error(f"Database update failed: {e}")
            await self.db.rollback()
            raise

    async def _calculate_volume_ranks(self):
        """거래량 순위 계산 및 업데이트"""
        try:
            # 전체 종목을 거래량 변동률 기준으로 정렬
            stmt = select(MarketScreener).order_by(MarketScreener.volume_change_pct.desc())
            result = await self.db.execute(stmt)
            stocks = result.scalars().all()

            # 순위 업데이트
            for rank, stock in enumerate(stocks, start=1):
                update_stmt = (
                    update(MarketScreener)
                    .where(MarketScreener.ticker == stock.ticker)
                    .values(volume_rank=rank)
                )
                await self.db.execute(update_stmt)

            await self.db.commit()
            logger.info(f"✓ Volume ranks calculated for {len(stocks)} stocks")

        except Exception as e:
            logger.error(f"Failed to calculate volume ranks: {e}")
            await self.db.rollback()


# SQLite func 임포트 추가
from sqlalchemy.sql import func
