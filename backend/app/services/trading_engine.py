"""
Trading Engine
Orchestrates the entire trading workflow: signals → Gemini → execution → logging
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import json

from .gemini_service import GeminiService
from .signal_aggregator import SignalAggregator
from .portfolio_manager import PortfolioManager
from .risk_manager import RiskManager
from ..models import LLMDecision

logger = logging.getLogger(__name__)


class TradingEngine:
    """Main trading engine that orchestrates all components"""

    def __init__(
        self,
        gemini_service: GeminiService,
        signal_aggregator: SignalAggregator,
        portfolio_manager: PortfolioManager,
        risk_manager: RiskManager,
        db: AsyncSession
    ):
        """
        Initialize trading engine

        Args:
            gemini_service: Gemini AI service
            signal_aggregator: Signal aggregator service
            portfolio_manager: Portfolio manager
            risk_manager: Risk manager
            db: Database session
        """
        self.gemini = gemini_service
        self.signals = signal_aggregator
        self.portfolio = portfolio_manager
        self.risk = risk_manager
        self.db = db

        logger.info("Trading engine initialized")

    async def execute_trading_session(
        self,
        decision_type: str,
        target_tickers: Optional[List[str]] = None
    ) -> Dict:
        """
        Execute a complete trading session

        Args:
            decision_type: PRE_MARKET, MID_SESSION, or PRE_CLOSE
            target_tickers: Specific tickers to analyze (optional)

        Returns:
            Session summary dictionary
        """
        try:
            logger.info(f"Starting {decision_type} trading session")
            session_start = datetime.now()

            # Step 1: Check if trading is allowed
            can_trade, reason = await self.risk.can_trade_now()
            if not can_trade:
                logger.warning(f"Trading not allowed: {reason}")
                return {
                    'success': False,
                    'decision_type': decision_type,
                    'error': reason,
                    'circuit_breaker': True,
                    'timestamp': session_start.isoformat()
                }

            # Step 2: Get current portfolio state
            portfolio_state = await self.portfolio.get_current_state()
            logger.info(f"Portfolio: {portfolio_state['total_value']:,.0f} KRW, "
                       f"{portfolio_state['position_count']} positions, "
                       f"Daily P/L: {portfolio_state['daily_pnl_pct']:.2f}%")

            # Step 3: Collect market signals
            if target_tickers:
                # Analyze specific tickers
                signals = []
                for ticker in target_tickers:
                    signal = await self.signals.aggregate_signals_for_ticker(ticker)
                    signals.append(signal)
            else:
                # Get trending tickers from WSB for PRE_MARKET
                if decision_type == "PRE_MARKET":
                    trending = await self.signals.wsb_scraper.get_trending_tickers(limit=50)
                    # Get top 10 trending tickers
                    target_tickers = [t['ticker'] for t in trending[:10]]
                    signals = []
                    for ticker in target_tickers:
                        signal = await self.signals.aggregate_signals_for_ticker(ticker)
                        if signal.get('composite_sentiment'):  # Valid signal
                            signals.append(signal)
                else:
                    # For MID_SESSION and PRE_CLOSE, analyze current positions
                    target_tickers = [pos['ticker'] for pos in portfolio_state['positions']]
                    signals = []
                    for ticker in target_tickers:
                        signal = await self.signals.aggregate_signals_for_ticker(ticker)
                        signals.append(signal)

            logger.info(f"Collected {len(signals)} market signals")

            # Step 4: Make trading decision with Gemini
            decision_result = await self.gemini.make_trading_decision(
                decision_type=decision_type,
                portfolio_state=portfolio_state,
                market_signals=signals,
                additional_context=None
            )

            if not decision_result.get('success'):
                logger.error(f"Gemini decision failed: {decision_result.get('error')}")
                return decision_result

            # Step 5: Log decision to database
            decision_id = await self._save_decision(
                decision_type=decision_type,
                decision_result=decision_result,
                portfolio_state=portfolio_state,
                signals=signals
            )

            # Step 6: Update portfolio snapshot
            await self.portfolio.save_snapshot()

            session_end = datetime.now()
            duration = (session_end - session_start).total_seconds()

            summary = {
                'success': True,
                'decision_type': decision_type,
                'decision_id': decision_id,
                'executed_trades': decision_result.get('executed_trades', 0),
                'successful_trades': decision_result.get('successful_trades', 0),
                'confidence_score': decision_result.get('confidence_score', 0),
                'signals_analyzed': len(signals),
                'portfolio_value': portfolio_state['total_value'],
                'daily_pnl_pct': portfolio_state['daily_pnl_pct'],
                'duration_seconds': duration,
                'timestamp': session_end.isoformat()
            }

            logger.info(f"Session completed: {summary['successful_trades']}/{summary['executed_trades']} trades, "
                       f"confidence: {summary['confidence_score']:.2f}, duration: {duration:.1f}s")

            return summary

        except Exception as e:
            logger.error(f"Trading session failed: {e}")
            return {
                'success': False,
                'decision_type': decision_type,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def _save_decision(
        self,
        decision_type: str,
        decision_result: Dict,
        portfolio_state: Dict,
        signals: List[Dict]
    ) -> int:
        """
        Save LLM decision to database

        Args:
            decision_type: Decision type
            decision_result: Gemini's decision result
            portfolio_state: Portfolio state at decision time
            signals: Market signals used

        Returns:
            Decision ID
        """
        try:
            # Create prompt (simplified version for storage)
            prompt = f"{decision_type} decision for portfolio with {portfolio_state['position_count']} positions"

            # Extract response text
            response = decision_result.get('reasoning', '')

            # Create decision record
            decision = LLMDecision(
                decision_type=decision_type,
                prompt=prompt,
                response=response,
                reasoning=decision_result.get('reasoning', ''),
                confidence_score=decision_result.get('confidence_score', 0),
                function_calls=json.dumps(decision_result.get('function_calls', [])),
                signals_used=json.dumps([
                    {
                        'ticker': s.get('ticker'),
                        'sentiment': s.get('composite_sentiment'),
                        'strength': s.get('signal_strength'),
                        'recommendation': s.get('recommendation')
                    }
                    for s in signals
                ]),
                portfolio_state=json.dumps({
                    'total_value': portfolio_state['total_value'],
                    'cash_balance': portfolio_state['cash_balance'],
                    'position_count': portfolio_state['position_count'],
                    'daily_pnl_pct': portfolio_state['daily_pnl_pct']
                })
            )

            self.db.add(decision)
            await self.db.commit()
            await self.db.refresh(decision)

            logger.info(f"Saved decision {decision.id} to database")
            return decision.id

        except Exception as e:
            logger.error(f"Failed to save decision: {e}")
            await self.db.rollback()
            return 0

    async def check_and_execute_stop_losses(self) -> Dict:
        """
        Check all positions for stop-loss triggers and execute sells

        Returns:
            Summary of stop-loss actions
        """
        try:
            logger.info("Checking for stop-loss triggers")

            triggered = await self.risk.check_all_stop_losses()

            if not triggered:
                logger.debug("No stop-loss triggers found")
                return {
                    'success': True,
                    'triggered_count': 0,
                    'executed_count': 0,
                    'timestamp': datetime.now().isoformat()
                }

            # Execute stop-loss sells
            executed_count = 0
            for position in triggered:
                ticker = position['ticker']
                quantity = position['quantity']

                logger.warning(f"Executing stop-loss for {ticker}: {quantity} shares at {position['pnl_pct']:.2f}% loss")

                result = await self.risk.execute_stop_loss_sell(ticker, quantity)

                if result.get('success'):
                    executed_count += 1

            summary = {
                'success': True,
                'triggered_count': len(triggered),
                'executed_count': executed_count,
                'positions': triggered,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Stop-loss check complete: {executed_count}/{len(triggered)} executed")
            return summary

        except Exception as e:
            logger.error(f"Stop-loss check failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def analyze_ticker_on_demand(self, ticker: str) -> Dict:
        """
        Analyze a specific ticker on demand (for chatbot queries)

        Args:
            ticker: Stock ticker symbol

        Returns:
            Analysis result
        """
        try:
            logger.info(f"Analyzing {ticker} on demand")

            # Get signals
            signals = await self.signals.aggregate_signals_for_ticker(ticker)

            # Get current position if exists
            position = await self.portfolio.get_position(ticker)

            # Get portfolio state
            portfolio_state = await self.portfolio.get_current_state()

            # Ask Gemini for analysis
            analysis_prompt = f"""
Analyze {ticker} for potential trade:

CURRENT POSITION: {json.dumps(position) if position else 'No position'}

MARKET SIGNALS:
- Composite Sentiment: {signals.get('composite_sentiment', 0):.2f}
- Signal Strength: {signals.get('signal_strength', 0):.2f}
- Recommendation: {signals.get('recommendation', 'N/A')}
- WSB: {json.dumps(signals.get('wsb', {}))}
- Yahoo: {json.dumps(signals.get('yahoo', {}))}
- TipRanks: {json.dumps(signals.get('tipranks', {}))}

PORTFOLIO:
- Available Cash: {portfolio_state['cash_balance']:,.0f} KRW
- Total Value: {portfolio_state['total_value']:,.0f} KRW

Should we trade {ticker}? If yes, BUY or SELL? How much? Provide clear reasoning.
"""

            decision = await self.gemini.make_trading_decision(
                decision_type="ON_DEMAND",
                portfolio_state=portfolio_state,
                market_signals=[signals],
                additional_context=analysis_prompt
            )

            return {
                'success': True,
                'ticker': ticker,
                'signals': signals,
                'position': position,
                'analysis': decision,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to analyze {ticker}: {e}")
            return {
                'success': False,
                'ticker': ticker,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
