"""
Yahoo Finance Service
Fetches stock data, news, and technical indicators from Yahoo Finance
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class YahooFinanceService:
    """Service for fetching data from Yahoo Finance"""

    def __init__(self):
        """Initialize Yahoo Finance service"""
        logger.info("Yahoo Finance service initialized")

    async def get_ticker_data(self, ticker: str) -> Optional[Dict]:
        """
        Get comprehensive data for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with price, volume, news, and technical indicators
        """
        try:
            stock = yf.Ticker(ticker)

            # Get current price info
            info = stock.info
            history = stock.history(period="1mo")

            if history.empty:
                logger.warning(f"No data available for {ticker}")
                return None

            current_price = history['Close'].iloc[-1]
            prev_close = history['Close'].iloc[-2] if len(history) > 1 else current_price
            price_change = current_price - prev_close
            price_change_pct = (price_change / prev_close) * 100

            # Get news
            news = await self._get_news(stock)

            # Calculate technical indicators
            indicators = await self._calculate_indicators(history)

            # Volume analysis
            current_volume = history['Volume'].iloc[-1]
            avg_volume = history['Volume'].mean()
            volume_surge = (current_volume / avg_volume) if avg_volume > 0 else 1.0

            result = {
                'ticker': ticker,
                'current_price': float(current_price),
                'price_change': float(price_change),
                'price_change_pct': float(price_change_pct),
                'volume': int(current_volume),
                'avg_volume': int(avg_volume),
                'volume_surge': float(volume_surge),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'news': news,
                'technical_indicators': indicators,
                'source': 'YAHOO',
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Fetched data for {ticker}: ${current_price:.2f} ({price_change_pct:+.2f}%)")
            return result

        except Exception as e:
            logger.error(f"Failed to fetch data for {ticker}: {e}")
            return None

    async def _get_news(self, stock: yf.Ticker, limit: int = 5) -> List[Dict]:
        """
        Get latest news for stock

        Args:
            stock: yfinance Ticker object
            limit: Number of news items to fetch

        Returns:
            List of news dictionaries
        """
        try:
            news_items = stock.news[:limit] if hasattr(stock, 'news') else []

            news = []
            for item in news_items:
                news.append({
                    'title': item.get('title', ''),
                    'publisher': item.get('publisher', ''),
                    'link': item.get('link', ''),
                    'published': item.get('providerPublishTime', 0),
                    'sentiment': self._analyze_headline_sentiment(item.get('title', ''))
                })

            return news

        except Exception as e:
            logger.error(f"Failed to fetch news: {e}")
            return []

    def _analyze_headline_sentiment(self, headline: str) -> str:
        """
        Analyze sentiment from headline

        Args:
            headline: News headline

        Returns:
            'positive', 'negative', or 'neutral'
        """
        headline_lower = headline.lower()

        positive_words = [
            'surge', 'rally', 'gain', 'rise', 'jump', 'soar', 'climb',
            'profit', 'beat', 'strong', 'growth', 'boost', 'upgrade',
            'outperform', 'win', 'success', 'breakthrough', 'record'
        ]

        negative_words = [
            'fall', 'drop', 'plunge', 'decline', 'loss', 'miss', 'weak',
            'crash', 'slump', 'tumble', 'downgrade', 'concern', 'risk',
            'warning', 'disappointing', 'fail', 'struggle', 'trouble'
        ]

        positive_count = sum(1 for word in positive_words if word in headline_lower)
        negative_count = sum(1 for word in negative_words if word in headline_lower)

        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'

    async def _calculate_indicators(self, history: pd.DataFrame) -> Dict:
        """
        Calculate technical indicators

        Args:
            history: Price history DataFrame

        Returns:
            Dictionary of technical indicators
        """
        try:
            if len(history) < 20:
                return {}

            close_prices = history['Close']

            # RSI (Relative Strength Index)
            rsi = self._calculate_rsi(close_prices)

            # MACD
            macd, signal, histogram = self._calculate_macd(close_prices)

            # Moving Averages
            sma_20 = close_prices.rolling(window=20).mean().iloc[-1]
            sma_50 = close_prices.rolling(window=50).mean().iloc[-1] if len(history) >= 50 else None

            current_price = close_prices.iloc[-1]

            # Moving Average signals
            ma_signal = 'neutral'
            if sma_50:
                if current_price > sma_20 > sma_50:
                    ma_signal = 'bullish'
                elif current_price < sma_20 < sma_50:
                    ma_signal = 'bearish'

            # MACD signal
            macd_signal = 'neutral'
            if macd > signal:
                macd_signal = 'bullish'
            elif macd < signal:
                macd_signal = 'bearish'

            # RSI signal
            rsi_signal = 'neutral'
            if rsi < 30:
                rsi_signal = 'oversold'  # Buy signal
            elif rsi > 70:
                rsi_signal = 'overbought'  # Sell signal

            return {
                'rsi': float(rsi) if not np.isnan(rsi) else None,
                'rsi_signal': rsi_signal,
                'macd': float(macd) if not np.isnan(macd) else None,
                'macd_signal': macd_signal,
                'sma_20': float(sma_20) if not np.isnan(sma_20) else None,
                'sma_50': float(sma_50) if sma_50 and not np.isnan(sma_50) else None,
                'ma_signal': ma_signal
            }

        except Exception as e:
            logger.error(f"Failed to calculate indicators: {e}")
            return {}

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1]

    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9):
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()

        macd = ema_fast - ema_slow
        signal = macd.ewm(span=signal_period).mean()
        histogram = macd - signal

        return macd.iloc[-1], signal.iloc[-1], histogram.iloc[-1]

    async def get_multiple_tickers(self, tickers: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Get data for multiple tickers

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to data
        """
        results = {}

        for ticker in tickers:
            results[ticker] = await self.get_ticker_data(ticker)

        return results

    async def get_price(self, ticker: str) -> Optional[float]:
        """
        Get current price for ticker (quick method)

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current price or None
        """
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d")

            if not data.empty:
                return float(data['Close'].iloc[-1])

            return None

        except Exception as e:
            logger.error(f"Failed to get price for {ticker}: {e}")
            return None
