"""
Signal Aggregator Service
Aggregates signals from multiple sources (WSB, Yahoo Finance, TipRanks)
"""

import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import json

from ..models import Signal
from .wsb_scraper import WSBScraper
from .yahoo_finance_service import YahooFinanceService
from .tipranks_service import TipRanksService

logger = logging.getLogger(__name__)


class SignalAggregator:
    """Service for aggregating market signals from multiple sources"""

    def __init__(
        self,
        db: AsyncSession,
        wsb_scraper: Optional[WSBScraper] = None,
        yahoo_service: Optional[YahooFinanceService] = None,
        tipranks_service: Optional[TipRanksService] = None
    ):
        """
        Initialize signal aggregator

        Args:
            db: Database session
            wsb_scraper: WallStreetBets scraper instance
            yahoo_service: Yahoo Finance service instance
            tipranks_service: TipRanks service instance
        """
        self.db = db
        self.wsb_scraper = wsb_scraper or WSBScraper()
        self.yahoo_service = yahoo_service or YahooFinanceService()
        self.tipranks_service = tipranks_service or TipRanksService()

    async def aggregate_signals_for_ticker(self, ticker: str) -> Dict:
        """
        Collect and aggregate signals for specific ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with aggregated signals
        """
        try:
            logger.info(f"Aggregating signals for {ticker}")

            # Fetch from all sources in parallel
            wsb_task = self.wsb_scraper.get_ticker_sentiment(ticker)
            yahoo_task = self.yahoo_service.get_ticker_data(ticker)
            tipranks_task = self.tipranks_service.get_ticker_analysis(ticker)

            wsb_data, yahoo_data, tipranks_data = await asyncio.gather(
                wsb_task,
                yahoo_task,
                tipranks_task,
                return_exceptions=True
            )

            # Process each source
            wsb_signal = self._process_wsb_signal(wsb_data) if not isinstance(wsb_data, Exception) else {}
            yahoo_signal = self._process_yahoo_signal(yahoo_data) if not isinstance(yahoo_data, Exception) else {}
            tipranks_signal = self._process_tipranks_signal(tipranks_data) if not isinstance(tipranks_data, Exception) else {}

            # Calculate composite sentiment
            composite_sentiment = self._calculate_composite_sentiment(
                wsb_signal, yahoo_signal, tipranks_signal
            )

            # Calculate overall strength
            strength = self._calculate_signal_strength(wsb_signal, yahoo_signal, tipranks_signal)

            result = {
                'ticker': ticker,
                'wsb': wsb_signal,
                'yahoo': yahoo_signal,
                'tipranks': tipranks_signal,
                'composite_sentiment': composite_sentiment,
                'signal_strength': strength,
                'recommendation': self._generate_recommendation(composite_sentiment, strength),
                'timestamp': datetime.now().isoformat()
            }

            # Save to database
            await self._save_signals(ticker, wsb_signal, yahoo_signal, tipranks_signal)

            logger.info(f"Aggregated signals for {ticker}: sentiment={composite_sentiment:.2f}, strength={strength:.2f}")
            return result

        except Exception as e:
            logger.error(f"Failed to aggregate signals for {ticker}: {e}")
            return {
                'ticker': ticker,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _process_wsb_signal(self, data: Optional[Dict]) -> Dict:
        """Process WallStreetBets signal"""
        if not data:
            return {'available': False}

        return {
            'available': True,
            'mentions': data.get('mention_count', 0),
            'sentiment': data.get('sentiment_score', 0),
            'popularity': min(data.get('mention_count', 0) / 10, 1.0),  # Normalize to 0-1
            'top_post': data.get('top_post', {})
        }

    def _process_yahoo_signal(self, data: Optional[Dict]) -> Dict:
        """Process Yahoo Finance signal"""
        if not data:
            return {'available': False}

        indicators = data.get('technical_indicators', {})

        # Calculate technical score
        tech_score = 0
        signals = 0

        if indicators.get('rsi_signal') == 'oversold':
            tech_score += 1
            signals += 1
        elif indicators.get('rsi_signal') == 'overbought':
            tech_score -= 1
            signals += 1

        if indicators.get('macd_signal') == 'bullish':
            tech_score += 1
            signals += 1
        elif indicators.get('macd_signal') == 'bearish':
            tech_score -= 1
            signals += 1

        if indicators.get('ma_signal') == 'bullish':
            tech_score += 1
            signals += 1
        elif indicators.get('ma_signal') == 'bearish':
            tech_score -= 1
            signals += 1

        technical_sentiment = (tech_score / signals) if signals > 0 else 0

        # News sentiment
        news = data.get('news', [])
        positive_news = sum(1 for n in news if n.get('sentiment') == 'positive')
        negative_news = sum(1 for n in news if n.get('sentiment') == 'negative')
        total_news = len(news)

        news_sentiment = 0
        if total_news > 0:
            news_sentiment = (positive_news - negative_news) / total_news

        return {
            'available': True,
            'price': data.get('current_price'),
            'price_change_pct': data.get('price_change_pct', 0),
            'volume_surge': data.get('volume_surge', 1.0),
            'technical_sentiment': technical_sentiment,
            'news_sentiment': news_sentiment,
            'indicators': indicators,
            'news_count': total_news
        }

    def _process_tipranks_signal(self, data: Optional[Dict]) -> Dict:
        """Process TipRanks signal"""
        if not data:
            return {'available': False}

        # Convert consensus to numeric score
        consensus = data.get('analyst_consensus', 'N/A')
        consensus_score = 0

        if consensus == 'BUY':
            consensus_score = 1
        elif consensus == 'SELL':
            consensus_score = -1
        elif consensus == 'HOLD':
            consensus_score = 0

        return {
            'available': True,
            'consensus': consensus,
            'consensus_score': consensus_score,
            'price_target': data.get('price_target'),
            'upside_pct': data.get('price_target_upside_pct'),
            'smart_money': data.get('smart_money_signal', 'neutral')
        }

    def _calculate_composite_sentiment(
        self,
        wsb: Dict,
        yahoo: Dict,
        tipranks: Dict
    ) -> float:
        """
        Calculate composite sentiment score from all sources

        Returns:
            Sentiment score from -1 (very bearish) to 1 (very bullish)
        """
        total_weight = 0
        weighted_sentiment = 0

        # WSB sentiment (weight: 0.3)
        if wsb.get('available'):
            weight = 0.3 * wsb.get('popularity', 0.5)  # Adjust by popularity
            weighted_sentiment += wsb.get('sentiment', 0) * weight
            total_weight += weight

        # Yahoo technical + news sentiment (weight: 0.4)
        if yahoo.get('available'):
            weight = 0.4
            tech_sentiment = yahoo.get('technical_sentiment', 0)
            news_sentiment = yahoo.get('news_sentiment', 0)
            combined = (tech_sentiment * 0.6 + news_sentiment * 0.4)  # Tech weighted more
            weighted_sentiment += combined * weight
            total_weight += weight

        # TipRanks analyst consensus (weight: 0.3)
        if tipranks.get('available'):
            weight = 0.3
            weighted_sentiment += tipranks.get('consensus_score', 0) * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        composite = weighted_sentiment / total_weight
        return round(composite, 3)

    def _calculate_signal_strength(
        self,
        wsb: Dict,
        yahoo: Dict,
        tipranks: Dict
    ) -> float:
        """
        Calculate overall signal strength (confidence)

        Returns:
            Strength from 0 (weak) to 1 (strong)
        """
        strength = 0.0
        sources = 0

        if wsb.get('available'):
            # Strong if high mentions and clear sentiment
            wsb_strength = min(wsb.get('popularity', 0) * abs(wsb.get('sentiment', 0)), 1.0)
            strength += wsb_strength
            sources += 1

        if yahoo.get('available'):
            # Strong if multiple indicators agree
            volume_strength = min(yahoo.get('volume_surge', 1.0) / 2, 1.0)  # High volume = strong
            tech_strength = abs(yahoo.get('technical_sentiment', 0))
            yahoo_strength = (volume_strength + tech_strength) / 2
            strength += yahoo_strength
            sources += 1

        if tipranks.get('available'):
            # Strong if clear analyst consensus
            tipranks_strength = abs(tipranks.get('consensus_score', 0))
            strength += tipranks_strength
            sources += 1

        if sources == 0:
            return 0.0

        return round(strength / sources, 3)

    def _generate_recommendation(self, sentiment: float, strength: float) -> str:
        """
        Generate trading recommendation

        Args:
            sentiment: Composite sentiment (-1 to 1)
            strength: Signal strength (0 to 1)

        Returns:
            'STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'
        """
        if strength < 0.3:
            return 'HOLD'  # Weak signals

        if sentiment > 0.6:
            return 'STRONG_BUY' if strength > 0.7 else 'BUY'
        elif sentiment > 0.2:
            return 'BUY' if strength > 0.6 else 'HOLD'
        elif sentiment < -0.6:
            return 'STRONG_SELL' if strength > 0.7 else 'SELL'
        elif sentiment < -0.2:
            return 'SELL' if strength > 0.6 else 'HOLD'
        else:
            return 'HOLD'

    async def _save_signals(
        self,
        ticker: str,
        wsb: Dict,
        yahoo: Dict,
        tipranks: Dict
    ):
        """Save signals to database"""
        try:
            now = datetime.now()
            expires_at = now + timedelta(hours=24)

            # Save WSB signal
            if wsb.get('available'):
                signal = Signal(
                    ticker=ticker,
                    source='WSB',
                    signal_type='SENTIMENT',
                    signal_data=json.dumps(wsb),
                    sentiment_score=wsb.get('sentiment', 0),
                    strength=wsb.get('popularity', 0),
                    expires_at=expires_at,
                    is_active=True
                )
                self.db.add(signal)

            # Save Yahoo signal
            if yahoo.get('available'):
                signal = Signal(
                    ticker=ticker,
                    source='YAHOO',
                    signal_type='TECHNICAL',
                    signal_data=json.dumps(yahoo),
                    sentiment_score=(yahoo.get('technical_sentiment', 0) + yahoo.get('news_sentiment', 0)) / 2,
                    strength=yahoo.get('volume_surge', 1.0) / 2,
                    expires_at=expires_at,
                    is_active=True
                )
                self.db.add(signal)

            # Save TipRanks signal
            if tipranks.get('available'):
                signal = Signal(
                    ticker=ticker,
                    source='TIPRANKS',
                    signal_type='ANALYST_RATING',
                    signal_data=json.dumps(tipranks),
                    sentiment_score=tipranks.get('consensus_score', 0),
                    strength=abs(tipranks.get('consensus_score', 0)),
                    expires_at=expires_at,
                    is_active=True
                )
                self.db.add(signal)

            await self.db.commit()
            logger.debug(f"Saved signals for {ticker}")

        except Exception as e:
            logger.error(f"Failed to save signals: {e}")
            await self.db.rollback()

    async def get_recent_signals(self, ticker: str, hours_back: int = 24) -> List[Dict]:
        """
        Get recent signals for ticker from database

        Args:
            ticker: Stock ticker symbol
            hours_back: Hours to look back

        Returns:
            List of signal dictionaries
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)

            stmt = select(Signal).where(
                and_(
                    Signal.ticker == ticker,
                    Signal.created_at >= cutoff_time,
                    Signal.is_active == True
                )
            ).order_by(Signal.created_at.desc())

            result = await self.db.execute(stmt)
            signals = result.scalars().all()

            return [
                {
                    'id': sig.id,
                    'ticker': sig.ticker,
                    'source': sig.source,
                    'type': sig.signal_type,
                    'data': json.loads(sig.signal_data),
                    'sentiment_score': sig.sentiment_score,
                    'strength': sig.strength,
                    'created_at': sig.created_at.isoformat()
                }
                for sig in signals
            ]

        except Exception as e:
            logger.error(f"Failed to get recent signals: {e}")
            return []
