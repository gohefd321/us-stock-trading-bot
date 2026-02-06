"""
News & Events Service

뉴스 및 이벤트 수집 서비스
- Google News RSS
- Yahoo Finance 뉴스
- SEC EDGAR API (8-K, 10-Q, 10-K)

"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import feedparser
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import asyncio

from ..models.news_event import NewsEvent

logger = logging.getLogger(__name__)


class NewsEventService:
    """뉴스 & 이벤트 수집 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.sec_api_base = "https://data.sec.gov"
        self.google_news_base = "https://news.google.com/rss/search"

    async def get_latest_news(self, ticker: str, limit: int = 10) -> List[Dict]:
        """
        특정 종목의 최신 뉴스 조회 (DB에서)

        Args:
            ticker: 종목 코드
            limit: 조회할 뉴스 수

        Returns:
            뉴스 리스트
        """
        try:
            stmt = (
                select(NewsEvent)
                .where(NewsEvent.ticker == ticker)
                .where(NewsEvent.event_type == 'news')
                .order_by(desc(NewsEvent.published_at))
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            news_list = result.scalars().all()

            return [
                {
                    "id": n.id,
                    "ticker": n.ticker,
                    "title": n.title,
                    "summary": n.summary,
                    "url": n.url,
                    "source": n.source,
                    "sentiment": n.sentiment,
                    "sentiment_label": n.sentiment_label,
                    "published_at": n.published_at.isoformat() if n.published_at else None,
                }
                for n in news_list
            ]

        except Exception as e:
            logger.error(f"Failed to get latest news for {ticker}: {e}")
            return []

    async def get_sec_filings(self, ticker: str, limit: int = 10) -> List[Dict]:
        """
        특정 종목의 SEC 제출 서류 조회

        Args:
            ticker: 종목 코드
            limit: 조회할 서류 수

        Returns:
            SEC 서류 리스트
        """
        try:
            stmt = (
                select(NewsEvent)
                .where(NewsEvent.ticker == ticker)
                .where(NewsEvent.event_type == 'sec_filing')
                .order_by(desc(NewsEvent.filing_date))
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            filings = result.scalars().all()

            return [
                {
                    "id": f.id,
                    "ticker": f.ticker,
                    "filing_type": f.filing_type,
                    "title": f.title,
                    "url": f.url,
                    "filing_date": f.filing_date.isoformat() if f.filing_date else None,
                }
                for f in filings
            ]

        except Exception as e:
            logger.error(f"Failed to get SEC filings for {ticker}: {e}")
            return []

    async def get_recent_news_all_sources(self, ticker: str, hours: int = 24) -> List[Dict]:
        """
        여러 소스에서 최근 뉴스 수집 (실시간)

        Args:
            ticker: 종목 코드
            hours: 조회 기간 (시간)

        Returns:
            뉴스 리스트
        """
        try:
            logger.info(f"📰 Fetching recent news for {ticker} from all sources...")

            # 병렬로 수집
            loop = asyncio.get_event_loop()
            google_news_task = loop.run_in_executor(None, self._fetch_google_news, ticker, hours)
            yahoo_news_task = loop.run_in_executor(None, self._fetch_yahoo_news, ticker)

            google_news, yahoo_news = await asyncio.gather(google_news_task, yahoo_news_task)

            # 합치기
            all_news = google_news + yahoo_news

            # 중복 제거 (제목 기준)
            seen_titles = set()
            unique_news = []
            for news in all_news:
                if news['title'] not in seen_titles:
                    seen_titles.add(news['title'])
                    unique_news.append(news)

            # 시간순 정렬
            unique_news.sort(key=lambda x: x['published_at'], reverse=True)

            logger.info(f"✓ Found {len(unique_news)} unique news items for {ticker}")
            return unique_news

        except Exception as e:
            logger.error(f"Failed to fetch news for {ticker}: {e}")
            return []

    async def fetch_and_store_news(self, ticker: str) -> int:
        """
        뉴스 수집 후 DB 저장

        Args:
            ticker: 종목 코드

        Returns:
            저장된 뉴스 수
        """
        try:
            news_list = await self.get_recent_news_all_sources(ticker, hours=48)

            stored_count = 0
            for news in news_list:
                # 중복 체크 (같은 제목, 같은 날짜)
                existing = await self.db.execute(
                    select(NewsEvent)
                    .where(NewsEvent.ticker == ticker)
                    .where(NewsEvent.title == news['title'])
                )
                if existing.scalar_one_or_none():
                    continue

                # 저장
                news_event = NewsEvent(
                    ticker=ticker,
                    event_type='news',
                    title=news['title'],
                    summary=news.get('summary'),
                    url=news.get('url'),
                    source=news.get('source'),
                    published_at=news['published_at'],
                )

                self.db.add(news_event)
                stored_count += 1

            await self.db.commit()
            logger.info(f"✓ Stored {stored_count} news items for {ticker}")
            return stored_count

        except Exception as e:
            logger.error(f"Failed to fetch and store news for {ticker}: {e}")
            await self.db.rollback()
            return 0

    async def fetch_and_store_sec_filings(self, ticker: str) -> int:
        """
        SEC 서류 수집 후 DB 저장

        Args:
            ticker: 종목 코드

        Returns:
            저장된 서류 수
        """
        try:
            loop = asyncio.get_event_loop()
            filings = await loop.run_in_executor(None, self._fetch_sec_filings, ticker)

            stored_count = 0
            for filing in filings:
                # 중복 체크
                existing = await self.db.execute(
                    select(NewsEvent)
                    .where(NewsEvent.ticker == ticker)
                    .where(NewsEvent.filing_type == filing['filing_type'])
                    .where(NewsEvent.filing_date == filing['filing_date'])
                )
                if existing.scalar_one_or_none():
                    continue

                # 저장
                news_event = NewsEvent(
                    ticker=ticker,
                    event_type='sec_filing',
                    filing_type=filing['filing_type'],
                    title=filing['title'],
                    url=filing['url'],
                    filing_date=filing['filing_date'],
                    published_at=filing['filing_date'],
                )

                self.db.add(news_event)
                stored_count += 1

            await self.db.commit()
            logger.info(f"✓ Stored {stored_count} SEC filings for {ticker}")
            return stored_count

        except Exception as e:
            logger.error(f"Failed to fetch and store SEC filings for {ticker}: {e}")
            await self.db.rollback()
            return 0

    def _fetch_google_news(self, ticker: str, hours: int = 24) -> List[Dict]:
        """
        Google News RSS에서 뉴스 수집 (동기 함수)

        Args:
            ticker: 종목 코드
            hours: 조회 기간 (시간)

        Returns:
            뉴스 리스트
        """
        try:
            # Google News RSS URL
            query = f"{ticker} stock"
            url = f"{self.google_news_base}?q={query}&hl=en-US&gl=US&ceid=US:en"

            # RSS 파싱
            feed = feedparser.parse(url)

            news_list = []
            cutoff_time = datetime.now() - timedelta(hours=hours)

            for entry in feed.entries[:20]:  # 최대 20개
                try:
                    # 발행 시간 파싱
                    published = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %Z')

                    if published < cutoff_time:
                        continue

                    news_list.append({
                        "title": entry.title,
                        "summary": entry.summary if hasattr(entry, 'summary') else None,
                        "url": entry.link,
                        "source": "Google News",
                        "published_at": published,
                    })

                except Exception as e:
                    logger.debug(f"Failed to parse Google News entry: {e}")
                    continue

            logger.debug(f"✓ Fetched {len(news_list)} items from Google News for {ticker}")
            return news_list

        except Exception as e:
            logger.warning(f"Failed to fetch Google News for {ticker}: {e}")
            return []

    def _fetch_yahoo_news(self, ticker: str) -> List[Dict]:
        """
        Yahoo Finance에서 뉴스 수집 (동기 함수)

        Args:
            ticker: 종목 코드

        Returns:
            뉴스 리스트
        """
        try:
            stock = yf.Ticker(ticker)
            news = stock.news

            news_list = []
            for item in news[:10]:  # 최대 10개
                try:
                    published = datetime.fromtimestamp(item['providerPublishTime'])

                    news_list.append({
                        "title": item['title'],
                        "summary": item.get('summary'),
                        "url": item['link'],
                        "source": item.get('publisher', 'Yahoo Finance'),
                        "published_at": published,
                    })

                except Exception as e:
                    logger.debug(f"Failed to parse Yahoo News item: {e}")
                    continue

            logger.debug(f"✓ Fetched {len(news_list)} items from Yahoo Finance for {ticker}")
            return news_list

        except Exception as e:
            logger.warning(f"Failed to fetch Yahoo News for {ticker}: {e}")
            return []

    def _fetch_sec_filings(self, ticker: str, limit: int = 10) -> List[Dict]:
        """
        SEC EDGAR API에서 서류 수집 (동기 함수)

        Args:
            ticker: 종목 코드
            limit: 조회할 서류 수

        Returns:
            SEC 서류 리스트
        """
        try:
            # SEC API: 최근 제출 서류 조회
            url = f"{self.sec_api_base}/submissions/CIK{self._get_cik(ticker)}.json"

            headers = {
                "User-Agent": "TradingBot/1.0 (contact@example.com)"  # SEC API 요구사항
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            filings = []
            recent_filings = data.get('filings', {}).get('recent', {})

            if not recent_filings:
                return []

            # 8-K, 10-Q, 10-K만 필터링
            for i in range(min(limit, len(recent_filings.get('form', [])))):
                form = recent_filings['form'][i]

                if form not in ['8-K', '10-Q', '10-K']:
                    continue

                filing_date = datetime.strptime(recent_filings['filingDate'][i], '%Y-%m-%d')
                accession_number = recent_filings['accessionNumber'][i].replace('-', '')

                filings.append({
                    "filing_type": form,
                    "title": f"{form} Filing",
                    "url": f"{self.sec_api_base}/Archives/edgar/data/{self._get_cik(ticker)}/{accession_number}/{recent_filings['primaryDocument'][i]}",
                    "filing_date": filing_date,
                })

            logger.debug(f"✓ Fetched {len(filings)} SEC filings for {ticker}")
            return filings

        except Exception as e:
            logger.warning(f"Failed to fetch SEC filings for {ticker}: {e}")
            return []

    @staticmethod
    def _get_cik(ticker: str) -> str:
        """
        종목 코드로 CIK (Central Index Key) 조회

        Note: 실제로는 별도 CIK 매핑 테이블 필요
        임시로 ticker를 그대로 사용
        """
        # TODO: 실제 CIK 매핑 구현
        # For now, return a placeholder
        return "0000000000"  # 실제로는 CIK 매핑 필요
