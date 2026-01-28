"""
Market Data Aggregation Service
Collects data from Reddit WSB, Yahoo Finance, and TipRanks
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import praw
import yfinance as yf
import aiohttp
from bs4 import BeautifulSoup

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
        Get trending stocks from r/wallstreetbets

        Returns:
            List of dicts with {ticker, mentions, sentiment}
        """
        cache_key = f"wsb_trending_{limit}"
        if self._is_cache_valid(cache_key):
            logger.info("[MARKET] 📦 Using cached WSB data")
            return self.cache[cache_key]

        logger.info("[MARKET] 🔍 Fetching trending stocks from r/wallstreetbets...")

        if not self.settings.reddit_client_id or not self.settings.reddit_client_secret:
            logger.warning("[MARKET] ❌ Reddit API credentials not configured")
            return []

        try:
            # Initialize Reddit API
            reddit = praw.Reddit(
                client_id=self.settings.reddit_client_id,
                client_secret=self.settings.reddit_client_secret,
                user_agent=self.settings.reddit_user_agent,
                check_for_async=False  # Disable async warning
            )

            # Get hot posts from WSB
            subreddit = reddit.subreddit('wallstreetbets')

            try:
                hot_posts = list(subreddit.hot(limit=50))
            except Exception as reddit_error:
                logger.error(f"[MARKET] 💥 Reddit API error: {reddit_error}")
                if "401" in str(reddit_error):
                    logger.error("[MARKET] 💥 Reddit credentials are invalid or expired")
                return []

            # Extract ticker mentions
            ticker_mentions = {}
            for post in hot_posts:
                title = post.title.upper()
                selftext = post.selftext.upper()
                text = f"{title} {selftext}"

                # Simple ticker extraction (common patterns)
                import re
                # Match $TICKER or standalone TICKER (2-5 uppercase letters)
                tickers = re.findall(r'\$?([A-Z]{2,5})(?:\s|$|[,.])', text)

                for ticker in tickers:
                    # Filter out common words
                    if ticker in ['WSB', 'YOLO', 'DD', 'CEO', 'IPO', 'ETF', 'USA', 'GDP']:
                        continue

                    if ticker not in ticker_mentions:
                        ticker_mentions[ticker] = {
                            'ticker': ticker,
                            'mentions': 0,
                            'posts': []
                        }

                    ticker_mentions[ticker]['mentions'] += 1
                    ticker_mentions[ticker]['posts'].append({
                        'title': post.title[:100],
                        'score': post.score,
                        'url': f"https://reddit.com{post.permalink}"
                    })

            # Sort by mentions and return top
            trending = sorted(
                ticker_mentions.values(),
                key=lambda x: x['mentions'],
                reverse=True
            )[:limit]

            logger.info(f"[MARKET] ✅ Found {len(trending)} trending stocks on WSB")

            self._set_cache(cache_key, trending)
            return trending

        except Exception as e:
            logger.error(f"[MARKET] 💥 Failed to fetch WSB data: {e}", exc_info=True)
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
