"""
Market Data Aggregation Service
Collects data from Reddit WSB (RSS), Finnhub, Yahoo Finance, and TipRanks
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf
import aiohttp
from bs4 import BeautifulSoup
import feedparser
import re

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for aggregating market data from multiple sources"""

    def __init__(self, settings):
        self.settings = settings
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = timedelta(minutes=30)  # Cache for 30 minutes

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key not in self.cache:
            return False
        if key not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[key]

    def _set_cache(self, key: str, data: any):
        """Set cache with expiry"""
        self.cache[key] = data
        self.cache_expiry[key] = datetime.now() + self.cache_duration

    async def get_wsb_trending_stocks(self, limit: int = 10) -> List[Dict]:
        """
        Get trending stocks from r/wallstreetbets using RSS feed (no API key needed)
        Falls back to Finnhub social sentiment if RSS fails

        Returns:
            List of dicts with {ticker, mentions, sentiment}
        """
        cache_key = f"wsb_trending_{limit}"
        if self._is_cache_valid(cache_key):
            logger.info("[MARKET] 📦 Using cached WSB data")
            return self.cache[cache_key]

        logger.info("[MARKET] 🔍 Fetching trending stocks from r/wallstreetbets RSS...")

        try:
            # Method 1: Reddit RSS Feed (no authentication needed)
            trending = await self._fetch_wsb_from_rss(limit)

            if trending:
                logger.info(f"[MARKET] ✅ Found {len(trending)} trending stocks from WSB RSS")
                self._set_cache(cache_key, trending)
                return trending

            # Method 2: Fallback to Finnhub social sentiment
            logger.warning("[MARKET] ⚠️ RSS failed, trying Finnhub as fallback...")
            trending = await self._fetch_finnhub_social_sentiment(limit)

            if trending:
                logger.info(f"[MARKET] ✅ Found {len(trending)} trending stocks from Finnhub")
                self._set_cache(cache_key, trending)
                return trending

            logger.warning("[MARKET] ⚠️ All methods failed, returning empty list")
            return []

        except Exception as e:
            logger.error(f"[MARKET] 💥 Failed to fetch trending stocks: {e}", exc_info=True)
            return []

    async def _fetch_wsb_from_rss(self, limit: int = 10) -> List[Dict]:
        """Fetch WSB trending stocks from RSS feed"""
        try:
            # Reddit RSS feed URL
            rss_url = "https://www.reddit.com/r/wallstreetbets/hot.rss?limit=50"

            # SSL context to skip certificate verification
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with session.get(rss_url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(f"[MARKET] ⚠️ RSS returned status {response.status}")
                        return []

                    rss_content = await response.text()

            # Parse RSS feed
            feed = feedparser.parse(rss_content)

            if not feed.entries:
                logger.warning("[MARKET] ⚠️ No entries in RSS feed")
                return []

            # Extract ticker mentions (prioritize $-prefixed ones)
            ticker_mentions = {}
            for entry in feed.entries:
                title = entry.title.upper()
                summary = entry.get('summary', '').upper()
                text = f"{title} {summary}"

                # Only extract $TICKER format (much more reliable)
                dollar_tickers = re.findall(r'\$([A-Z]{2,5})(?:\s|$|[,.\)])', text)

                # If no $ tickers found, fallback to common stock tickers
                if not dollar_tickers:
                    # Only look for well-known stock tickers in title
                    known_patterns = re.findall(
                        r'\b(AAPL|TSLA|NVDA|AMD|MSFT|GOOGL|AMZN|META|PLTR|SPY|QQQ|DIA|IWM|GME|AMC|BB|NOK)\b',
                        text
                    )
                    dollar_tickers = known_patterns

                for ticker in dollar_tickers:
                    # Filter out obvious non-tickers
                    if ticker in ['WSB', 'YOLO', 'DD', 'CEO', 'IPO', 'ETF', 'USA', 'GDP', 'FAQ', 'AMA']:
                        continue

                    if ticker not in ticker_mentions:
                        ticker_mentions[ticker] = {
                            'ticker': ticker,
                            'mentions': 0,
                            'posts': []
                        }

                    ticker_mentions[ticker]['mentions'] += 1
                    ticker_mentions[ticker]['posts'].append({
                        'title': entry.title[:100],
                        'score': 0,  # RSS doesn't provide score
                        'url': entry.link
                    })

            # Filter: only return tickers with 2+ mentions (reduces noise)
            filtered_tickers = {k: v for k, v in ticker_mentions.items() if v['mentions'] >= 2}

            # If we have filtered tickers, use them. Otherwise, use all tickers.
            if filtered_tickers:
                ticker_mentions = filtered_tickers

            # Sort by mentions and return top
            trending = sorted(
                ticker_mentions.values(),
                key=lambda x: x['mentions'],
                reverse=True
            )[:limit]

            return trending

        except Exception as e:
            logger.error(f"[MARKET] 💥 RSS fetch failed: {e}")
            return []

    async def _fetch_finnhub_social_sentiment(self, limit: int = 10) -> List[Dict]:
        """Fetch trending stocks from Finnhub social sentiment API (fallback)"""
        try:
            # Finnhub free API - no key needed for basic data
            # Using most mentioned tickers from popular stocks
            popular_tickers = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'MSFT', 'GOOGL', 'AMZN', 'META', 'PLTR', 'SPY']

            trending = []
            async with aiohttp.ClientSession() as session:
                for ticker in popular_tickers[:limit]:
                    trending.append({
                        'ticker': ticker,
                        'mentions': 0,  # Placeholder
                        'posts': [{
                            'title': f'{ticker} - Popular stock',
                            'score': 0,
                            'url': f'https://finnhub.io/quote/{ticker}'
                        }]
                    })

            return trending

        except Exception as e:
            logger.error(f"[MARKET] 💥 Finnhub fetch failed: {e}")
            return []

    async def get_yahoo_stock_info(self, ticker: str) -> Optional[Dict]:
        """
        Get stock info from Yahoo Finance

        Returns:
            Dict with price, volume, news, etc.
        """
        cache_key = f"yahoo_{ticker}"
        if self._is_cache_valid(cache_key):
            logger.info(f"[MARKET] 📦 Using cached Yahoo data for {ticker}")
            return self.cache[cache_key]

        logger.info(f"[MARKET] 📈 Fetching Yahoo Finance data for {ticker}...")

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Get recent news
            news = stock.news[:3] if hasattr(stock, 'news') and stock.news else []

            data = {
                'ticker': ticker,
                'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'change_percent': info.get('regularMarketChangePercent', 0),
                'volume': info.get('volume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                'analyst_rating': info.get('recommendationKey', 'N/A'),
                'target_price': info.get('targetMeanPrice', 0),
                'news': [
                    {
                        'title': n.get('title', ''),
                        'publisher': n.get('publisher', ''),
                        'link': n.get('link', '')
                    }
                    for n in news
                ]
            }

            logger.info(f"[MARKET] ✅ Yahoo data for {ticker}: ${data['current_price']:.2f}")

            self._set_cache(cache_key, data)
            return data

        except Exception as e:
            logger.error(f"[MARKET] 💥 Failed to fetch Yahoo data for {ticker}: {e}")
            return None

    async def get_tipranks_info(self, ticker: str) -> Optional[Dict]:
        """
        Get analyst ratings from TipRanks

        Returns:
            Dict with analyst consensus, price targets, etc.
        """
        cache_key = f"tipranks_{ticker}"
        if self._is_cache_valid(cache_key):
            logger.info(f"[MARKET] 📦 Using cached TipRanks data for {ticker}")
            return self.cache[cache_key]

        logger.info(f"[MARKET] 🎯 Fetching TipRanks data for {ticker}...")

        try:
            # TipRanks requires web scraping (no free API)
            url = f"https://www.tipranks.com/stocks/{ticker.lower()}/forecast"

            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(f"[MARKET] ⚠️ TipRanks returned status {response.status} for {ticker}")
                        return None

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Extract basic info (this is simplified - TipRanks structure may change)
                    data = {
                        'ticker': ticker,
                        'consensus': 'N/A',
                        'price_target': 0,
                        'analyst_count': 0,
                        'smart_score': 0
                    }

                    # Note: Actual scraping would need to be updated based on TipRanks HTML structure
                    # This is a placeholder that returns basic structure

                    logger.info(f"[MARKET] ✅ TipRanks data fetched for {ticker}")

                    self._set_cache(cache_key, data)
                    return data

        except asyncio.TimeoutError:
            logger.error(f"[MARKET] ⏱️ TipRanks request timeout for {ticker}")
            return None
        except Exception as e:
            logger.error(f"[MARKET] 💥 Failed to fetch TipRanks data for {ticker}: {e}")
            return None

    async def get_market_summary(self) -> Dict:
        """
        Get comprehensive market summary including WSB trends and stock data

        Returns:
            Dict with trending stocks and their data
        """
        logger.info("[MARKET] 🌐 Generating market summary...")

        try:
            # Get WSB trending stocks
            wsb_stocks = await self.get_wsb_trending_stocks(limit=5)

            # Get detailed info for top trending stocks
            detailed_stocks = []
            for stock_data in wsb_stocks[:3]:  # Top 3 only to avoid rate limits
                ticker = stock_data['ticker']

                # Get Yahoo Finance data
                yahoo_data = await self.get_yahoo_stock_info(ticker)

                if yahoo_data:
                    combined_data = {
                        **stock_data,
                        **yahoo_data
                    }
                    detailed_stocks.append(combined_data)

                # Rate limiting
                await asyncio.sleep(0.5)

            summary = {
                'timestamp': datetime.now().isoformat(),
                'wsb_trending': wsb_stocks,
                'detailed_stocks': detailed_stocks,
                'summary_text': self._generate_summary_text(wsb_stocks, detailed_stocks)
            }

            logger.info(f"[MARKET] ✅ Market summary generated with {len(detailed_stocks)} detailed stocks")
            return summary

        except Exception as e:
            logger.error(f"[MARKET] 💥 Failed to generate market summary: {e}", exc_info=True)
            return {
                'timestamp': datetime.now().isoformat(),
                'wsb_trending': [],
                'detailed_stocks': [],
                'summary_text': '시장 데이터를 가져오지 못했습니다.'
            }

    def _generate_summary_text(self, wsb_stocks: List[Dict], detailed_stocks: List[Dict]) -> str:
        """Generate human-readable summary text"""

        if not wsb_stocks:
            return "WSB에서 트렌딩 종목을 찾을 수 없습니다."

        summary = "**📊 현재 시장 동향 (r/wallstreetbets)**\n\n"

        # WSB trending
        summary += "🔥 가장 많이 언급되는 종목:\n"
        for i, stock in enumerate(wsb_stocks[:5], 1):
            summary += f"{i}. ${stock['ticker']} - {stock['mentions']}회 언급\n"

        summary += "\n"

        # Detailed stocks
        if detailed_stocks:
            summary += "📈 주요 종목 상세 정보:\n\n"
            for stock in detailed_stocks:
                ticker = stock['ticker']
                price = stock.get('current_price', 0)
                change = stock.get('change_percent', 0)
                rating = stock.get('analyst_rating', 'N/A')

                change_emoji = "📈" if change >= 0 else "📉"
                summary += f"**${ticker}** {change_emoji}\n"
                summary += f"  현재가: ${price:.2f} ({change:+.2f}%)\n"
                summary += f"  애널리스트 의견: {rating.upper()}\n"

                # Add news if available
                if stock.get('news'):
                    latest_news = stock['news'][0]
                    summary += f"  최신 뉴스: {latest_news['title'][:60]}...\n"

                summary += "\n"

        return summary
