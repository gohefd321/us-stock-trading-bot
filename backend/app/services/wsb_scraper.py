"""
WallStreetBets Scraper Service
Scrapes sentiment and trending stocks from r/wallstreetbets
"""

import logging
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import Counter
import praw
from praw.exceptions import PRAWException

logger = logging.getLogger(__name__)


class WSBScraper:
    """Service for scraping WallStreetBets data"""

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, user_agent: str = "TradingBot/1.0"):
        """
        Initialize WSB scraper

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: User agent string
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.reddit = None

        # Stock ticker regex pattern (2-5 uppercase letters)
        self.ticker_pattern = re.compile(r'\b[A-Z]{2,5}\b')

        # Common words to exclude from ticker detection
        self.exclude_words = {
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN',
            'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM',
            'HOW', 'MAN', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WAY', 'WHO',
            'BOY', 'DID', 'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE',
            'WSB', 'DD', 'YOLO', 'CEO', 'IPO', 'ETF', 'FDA', 'PM', 'AM',
            'USA', 'USD', 'CEO', 'CFO', 'EOD', 'AH', 'PM', 'IMO', 'IMHO'
        }

        if client_id and client_secret:
            self._initialize_reddit()

    def _initialize_reddit(self):
        """Initialize Reddit API client"""
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                check_for_async=False
            )
            logger.info("Reddit API initialized successfully")
        except PRAWException as e:
            logger.error(f"Failed to initialize Reddit API: {e}")
            self.reddit = None

    async def get_trending_tickers(self, limit: int = 100, hours_back: int = 24) -> List[Dict]:
        """
        Get trending stock tickers from WSB

        Args:
            limit: Number of posts to analyze
            hours_back: Look back this many hours

        Returns:
            List of ticker dictionaries with mentions and sentiment
        """
        if not self.reddit:
            logger.warning("Reddit API not initialized")
            return []

        try:
            subreddit = self.reddit.subreddit('wallstreetbets')
            ticker_mentions = Counter()
            ticker_sentiments = {}
            ticker_posts = {}

            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

            # Analyze hot posts
            for post in subreddit.hot(limit=limit):
                post_time = datetime.utcfromtimestamp(post.created_utc)

                if post_time < cutoff_time:
                    continue

                # Extract tickers from title and body
                text = f"{post.title} {post.selftext}"
                tickers = self._extract_tickers(text)

                # Count mentions
                for ticker in tickers:
                    ticker_mentions[ticker] += 1

                    # Store top post for each ticker
                    if ticker not in ticker_posts or post.score > ticker_posts[ticker]['score']:
                        ticker_posts[ticker] = {
                            'title': post.title,
                            'score': post.score,
                            'url': f"https://reddit.com{post.permalink}",
                            'comments': post.num_comments
                        }

                    # Calculate sentiment (basic)
                    sentiment = self._calculate_sentiment(text)
                    if ticker in ticker_sentiments:
                        ticker_sentiments[ticker].append(sentiment)
                    else:
                        ticker_sentiments[ticker] = [sentiment]

            # Build result
            trending = []
            for ticker, count in ticker_mentions.most_common(20):  # Top 20
                avg_sentiment = sum(ticker_sentiments[ticker]) / len(ticker_sentiments[ticker])

                trending.append({
                    'ticker': ticker,
                    'mentions': count,
                    'sentiment_score': round(avg_sentiment, 3),
                    'top_post': ticker_posts.get(ticker, {}),
                    'source': 'WSB',
                    'timestamp': datetime.now().isoformat()
                })

            logger.info(f"Found {len(trending)} trending tickers on WSB")
            return trending

        except Exception as e:
            logger.error(f"Failed to get trending tickers: {e}")
            return []

    def _extract_tickers(self, text: str) -> List[str]:
        """
        Extract stock tickers from text

        Args:
            text: Text to extract tickers from

        Returns:
            List of ticker symbols
        """
        # Find all potential tickers
        matches = self.ticker_pattern.findall(text)

        # Filter out common words
        tickers = [
            ticker for ticker in matches
            if ticker not in self.exclude_words
        ]

        return list(set(tickers))  # Remove duplicates

    def _calculate_sentiment(self, text: str) -> float:
        """
        Calculate basic sentiment score from text

        Args:
            text: Text to analyze

        Returns:
            Sentiment score (-1 to 1)
        """
        text_lower = text.lower()

        # Positive keywords
        positive_words = [
            'bullish', 'moon', 'rocket', 'calls', 'buy', 'long',
            'gainz', 'tendies', 'pump', 'rally', 'surge', 'breakout',
            'profit', 'green', 'up', 'bull', 'gains', 'winning'
        ]

        # Negative keywords
        negative_words = [
            'bearish', 'crash', 'puts', 'sell', 'short', 'loss',
            'dump', 'drop', 'fall', 'red', 'down', 'bear', 'losing',
            'plummet', 'tank', 'collapse', 'bankruptcy'
        ]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        sentiment = (positive_count - negative_count) / total
        return sentiment

    async def get_ticker_sentiment(self, ticker: str, limit: int = 50) -> Optional[Dict]:
        """
        Get sentiment for specific ticker

        Args:
            ticker: Stock ticker symbol
            limit: Number of posts to analyze

        Returns:
            Sentiment dictionary or None
        """
        if not self.reddit:
            logger.warning("Reddit API not initialized")
            return None

        try:
            subreddit = self.reddit.subreddit('wallstreetbets')

            # Search for ticker mentions
            query = f"${ticker} OR {ticker}"
            posts = list(subreddit.search(query, limit=limit, time_filter='day'))

            if not posts:
                return None

            sentiments = []
            total_score = 0
            top_post = None

            for post in posts:
                text = f"{post.title} {post.selftext}"
                sentiment = self._calculate_sentiment(text)
                sentiments.append(sentiment)
                total_score += post.score

                if not top_post or post.score > top_post['score']:
                    top_post = {
                        'title': post.title,
                        'score': post.score,
                        'url': f"https://reddit.com{post.permalink}",
                        'comments': post.num_comments
                    }

            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

            return {
                'ticker': ticker,
                'mention_count': len(posts),
                'sentiment_score': round(avg_sentiment, 3),
                'total_upvotes': total_score,
                'top_post': top_post,
                'source': 'WSB',
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get sentiment for {ticker}: {e}")
            return None
