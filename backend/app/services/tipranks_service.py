"""
TipRanks Service
Fetches analyst ratings and smart money data
Note: This uses web scraping as TipRanks API requires paid subscription
"""

import logging
from typing import Dict, Optional
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class TipRanksService:
    """Service for fetching data from TipRanks"""

    def __init__(self):
        """Initialize TipRanks service"""
        self.base_url = "https://www.tipranks.com/stocks"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        logger.info("TipRanks service initialized")

    async def get_ticker_analysis(self, ticker: str) -> Optional[Dict]:
        """
        Get analyst ratings and smart money analysis for ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with analyst consensus and smart money signals
        """
        try:
            url = f"{self.base_url}/{ticker.lower()}/forecast"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(f"TipRanks returned status {response.status} for {ticker}")
                        return None

                    html = await response.text()

            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')

            # Extract analyst consensus (this is a simplified version)
            # In production, you'd want to use TipRanks API or more robust scraping
            result = await self._parse_page(soup, ticker)

            if result:
                result['ticker'] = ticker
                result['source'] = 'TIPRANKS'
                result['timestamp'] = datetime.now().isoformat()
                logger.info(f"Fetched TipRanks data for {ticker}")

            return result

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching TipRanks data for {ticker}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch TipRanks data for {ticker}: {e}")
            return None

    async def _parse_page(self, soup: BeautifulSoup, ticker: str) -> Optional[Dict]:
        """
        Parse TipRanks page HTML

        Args:
            soup: BeautifulSoup object
            ticker: Stock ticker

        Returns:
            Parsed data dictionary
        """
        try:
            # This is a simplified parser
            # TipRanks structure changes frequently, so this may need updates

            result = {
                'analyst_consensus': 'N/A',
                'price_target': None,
                'price_target_upside_pct': None,
                'num_analysts': None,
                'smart_money_signal': 'neutral',
                'hedge_fund_trend': 'neutral'
            }

            # Try to find consensus rating
            # Note: Actual implementation would need to be updated based on current TipRanks HTML structure
            consensus_section = soup.find('div', {'class': re.compile(r'consensus', re.I)})
            if consensus_section:
                rating_text = consensus_section.get_text().lower()
                if 'buy' in rating_text or 'strong buy' in rating_text:
                    result['analyst_consensus'] = 'BUY'
                elif 'sell' in rating_text:
                    result['analyst_consensus'] = 'SELL'
                elif 'hold' in rating_text:
                    result['analyst_consensus'] = 'HOLD'

            # Try to find price target
            price_target_section = soup.find('div', {'class': re.compile(r'price.?target', re.I)})
            if price_target_section:
                # Extract numbers
                numbers = re.findall(r'\$?(\d+(?:\.\d+)?)', price_target_section.get_text())
                if numbers:
                    result['price_target'] = float(numbers[0])

            return result

        except Exception as e:
            logger.error(f"Failed to parse TipRanks page: {e}")
            return None

    async def get_smart_money_signal(self, ticker: str) -> Optional[str]:
        """
        Get smart money (hedge fund) signal for ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            'buying', 'selling', or 'neutral'
        """
        try:
            # Simplified implementation
            # In production, would parse hedge fund activity from TipRanks
            analysis = await self.get_ticker_analysis(ticker)

            if analysis:
                return analysis.get('smart_money_signal', 'neutral')

            return 'neutral'

        except Exception as e:
            logger.error(f"Failed to get smart money signal for {ticker}: {e}")
            return 'neutral'

    async def get_analyst_count(self, ticker: str) -> Optional[int]:
        """
        Get number of analysts covering ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Number of analysts or None
        """
        try:
            analysis = await self.get_ticker_analysis(ticker)

            if analysis:
                return analysis.get('num_analysts')

            return None

        except Exception as e:
            logger.error(f"Failed to get analyst count for {ticker}: {e}")
            return None

    async def get_simple_rating(self, ticker: str) -> str:
        """
        Get simplified rating (BUY/HOLD/SELL) for ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            'BUY', 'HOLD', 'SELL', or 'N/A'
        """
        try:
            analysis = await self.get_ticker_analysis(ticker)

            if analysis:
                return analysis.get('analyst_consensus', 'N/A')

            return 'N/A'

        except Exception as e:
            logger.error(f"Failed to get rating for {ticker}: {e}")
            return 'N/A'
