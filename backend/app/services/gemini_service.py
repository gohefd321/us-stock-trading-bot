"""
Gemini AI Service
Google Gemini 3.0 integration with Function Calling for trading decisions
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool, GenerateContentResponse

from ..config import Settings
from ..gemini_functions import TRADING_FUNCTIONS, FunctionHandler

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for Gemini AI trading decisions with function calling"""

    def __init__(
        self,
        function_handler: FunctionHandler,
        settings: Settings
    ):
        """
        Initialize Gemini service

        Args:
            function_handler: Function handler for executing function calls
            settings: Application settings
        """
        self.function_handler = function_handler
        self.settings = settings

        # Configure Gemini API
        if not settings.gemini_api_key:
            logger.error("Gemini API key not configured!")
            raise ValueError("GEMINI_API_KEY must be set in environment")

        genai.configure(api_key=settings.gemini_api_key)

        # Initialize model with function calling
        self.model_name = "gemini-2.0-flash-exp"

        # Convert function definitions to Gemini format
        self.tools = self._create_tools()

        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            tools=self.tools
        )

        logger.info(f"Gemini service initialized with model: {self.model_name}")

    def _create_tools(self) -> List[Tool]:
        """
        Convert function definitions to Gemini Tool format

        Returns:
            List of Gemini Tool objects
        """
        function_declarations = []

        for func_def in TRADING_FUNCTIONS:
            # Convert to Gemini FunctionDeclaration
            declaration = FunctionDeclaration(
                name=func_def["name"],
                description=func_def["description"],
                parameters=func_def["parameters"]
            )
            function_declarations.append(declaration)

        tool = Tool(function_declarations=function_declarations)
        logger.debug(f"Created {len(function_declarations)} function declarations for Gemini")

        return [tool]

    async def make_trading_decision(
        self,
        decision_type: str,
        portfolio_state: Dict,
        market_signals: List[Dict],
        additional_context: Optional[str] = None
    ) -> Dict:
        """
        Make trading decision using Gemini AI

        Args:
            decision_type: Type of decision (PRE_MARKET, MID_SESSION, PRE_CLOSE)
            portfolio_state: Current portfolio status
            market_signals: List of market signals from all sources
            additional_context: Additional context for decision

        Returns:
            Dictionary with decision, reasoning, function calls, and confidence
        """
        try:
            logger.info(f"Making {decision_type} trading decision with Gemini")

            # Build prompt
            prompt = self._build_prompt(
                decision_type=decision_type,
                portfolio_state=portfolio_state,
                market_signals=market_signals,
                additional_context=additional_context
            )

            # Start chat session
            chat = self.model.start_chat(enable_automatic_function_calling=False)

            # Send initial prompt
            response = chat.send_message(prompt)

            # Track all function calls and results
            function_calls_log = []
            max_iterations = 10  # Prevent infinite loops
            iteration = 0

            # Process function calls iteratively
            while iteration < max_iterations:
                # Check if model wants to call functions
                if not response.candidates[0].content.parts:
                    break

                function_call_parts = [
                    part for part in response.candidates[0].content.parts
                    if hasattr(part, 'function_call')
                ]

                if not function_call_parts:
                    # No more function calls, get final response
                    break

                # Execute all function calls in this response
                function_responses = []

                for part in function_call_parts:
                    function_call = part.function_call
                    function_name = function_call.name
                    function_args = dict(function_call.args)

                    logger.info(f"Gemini calling function: {function_name} with args: {function_args}")

                    # Execute function
                    function_result = await self.function_handler.handle_function_call(
                        function_name=function_name,
                        arguments=function_args
                    )

                    # Log function call
                    function_calls_log.append({
                        'function_name': function_name,
                        'arguments': function_args,
                        'result': function_result,
                        'timestamp': datetime.now().isoformat()
                    })

                    # Create function response for Gemini
                    function_responses.append({
                        'function_call': {
                            'name': function_name,
                            'args': function_args
                        },
                        'function_response': {
                            'name': function_name,
                            'response': function_result
                        }
                    })

                # Send function results back to Gemini
                if function_responses:
                    # Format function responses for Gemini
                    response_parts = []
                    for fr in function_responses:
                        response_parts.append({
                            'function_response': {
                                'name': fr['function_response']['name'],
                                'response': fr['function_response']['response']
                            }
                        })

                    response = chat.send_message(response_parts)

                iteration += 1

            # Extract final decision from response
            final_text = response.text if hasattr(response, 'text') else ""

            # Parse decision from text
            decision_result = self._parse_decision(
                response_text=final_text,
                function_calls=function_calls_log,
                decision_type=decision_type
            )

            logger.info(f"Decision completed: {decision_result.get('summary', 'No summary')}")

            return decision_result

        except Exception as e:
            logger.error(f"Failed to make trading decision: {e}")
            return {
                'success': False,
                'error': str(e),
                'decision_type': decision_type,
                'timestamp': datetime.now().isoformat()
            }

    def _build_prompt(
        self,
        decision_type: str,
        portfolio_state: Dict,
        market_signals: List[Dict],
        additional_context: Optional[str] = None
    ) -> str:
        """
        Build prompt for Gemini based on decision type

        Args:
            decision_type: PRE_MARKET, MID_SESSION, or PRE_CLOSE
            portfolio_state: Current portfolio status
            market_signals: Market signals from all sources
            additional_context: Additional context

        Returns:
            Formatted prompt string
        """
        # Base system instructions
        system_prompt = """
You are an expert AI trading assistant managing a US stock portfolio with 1,000,000 KRW capital.

RISK LIMITS (STRICTLY ENFORCED):
- Maximum position size: 40% of total assets per ticker
- Daily loss circuit breaker: -20% (trading halts if triggered)
- Stop-loss: -30% from purchase price (automatic sell)

YOUR GOALS:
1. Maximize returns while respecting risk limits
2. Make data-driven decisions based on multiple signal sources
3. Be conservative - only trade when confidence is high
4. Explain your reasoning clearly

AVAILABLE FUNCTIONS:
You have access to 8 trading functions:
- check_balance(): Get account balance
- get_current_price(ticker): Get real-time stock price
- get_portfolio_status(): Get all positions and P/L
- execute_trade(ticker, action, quantity, order_type): Execute actual trades
- analyze_signals(ticker): Get WSB, Yahoo, TipRanks signals
- calculate_position_size(ticker, confidence, price): Calculate optimal position
- check_stop_loss_triggers(): Check for stop-loss conditions
- get_trading_history(days_back): Review past trades

DECISION PROCESS:
1. Use functions to gather current portfolio and market data
2. Analyze signals and identify opportunities
3. Calculate position sizes based on confidence
4. Execute trades if conditions are favorable
5. Provide clear reasoning for all decisions
"""

        # Decision-type-specific instructions
        if decision_type == "PRE_MARKET":
            specific_instructions = """
DECISION TYPE: PRE-MARKET (10 minutes before market open)

OBJECTIVES:
- Review overnight signals from WSB, news, analyst reports
- Identify strong entry opportunities for today
- Plan opening positions based on signal strength
- Set up positions for intraday or swing trades

APPROACH:
1. Check portfolio status and available cash
2. Review trending tickers from WSB
3. Analyze technical indicators and news sentiment
4. Identify 2-3 high-conviction opportunities
5. Calculate position sizes (confidence × 40% max)
6. Execute BUY orders for selected tickers
"""

        elif decision_type == "MID_SESSION":
            specific_instructions = """
DECISION TYPE: MID-SESSION (2 hours after market open)

OBJECTIVES:
- Review current positions and P/L
- Check for profit-taking opportunities
- Identify new signals that emerged during trading
- Adjust positions if needed

APPROACH:
1. Check portfolio performance so far today
2. Review each position's P/L percentage
3. Consider selling positions with +10% or more gain
4. Check for stop-loss triggers
5. Analyze new signals for additional opportunities
6. Execute trades as needed (BUY or SELL)
"""

        elif decision_type == "PRE_CLOSE":
            specific_instructions = """
DECISION TYPE: PRE-CLOSE (10 minutes before market close)

OBJECTIVES:
- Review daily performance
- Decide which positions to hold overnight
- Close risky or low-conviction positions
- Secure profits from successful trades

APPROACH:
1. Review all open positions and daily P/L
2. Check news and after-hours catalysts
3. Decide position-by-position: HOLD or SELL
4. Close positions with weak signals or high risk
5. Keep high-conviction positions for swing trades
6. Execute SELL orders for positions to close
"""

        else:
            specific_instructions = "Analyze the situation and make appropriate trading decisions."

        # Format portfolio state
        portfolio_summary = f"""
CURRENT PORTFOLIO:
- Total Value: {portfolio_state.get('total_value_krw', 0):,.0f} KRW
- Cash Balance: {portfolio_state.get('cash_balance_krw', 0):,.0f} KRW
- Holdings Value: {portfolio_state.get('holdings_value_krw', 0):,.0f} KRW
- Daily P/L: {portfolio_state.get('daily_pnl_krw', 0):,.0f} KRW ({portfolio_state.get('daily_pnl_pct', 0):.2f}%)
- Total P/L: {portfolio_state.get('total_pnl_krw', 0):,.0f} KRW ({portfolio_state.get('total_pnl_pct', 0):.2f}%)
- Open Positions: {portfolio_state.get('position_count', 0)}
"""

        # Format market signals
        signals_summary = "MARKET SIGNALS:\n"
        for signal in market_signals[:10]:  # Limit to top 10
            ticker = signal.get('ticker', 'UNKNOWN')
            sentiment = signal.get('composite_sentiment', 0)
            strength = signal.get('signal_strength', 0)
            recommendation = signal.get('recommendation', 'HOLD')

            signals_summary += f"- {ticker}: {recommendation} (sentiment: {sentiment:.2f}, strength: {strength:.2f})\n"

        # Add additional context if provided
        context_section = ""
        if additional_context:
            context_section = f"\nADDITIONAL CONTEXT:\n{additional_context}\n"

        # Combine all sections
        full_prompt = f"""
{system_prompt}

{specific_instructions}

{portfolio_summary}

{signals_summary}

{context_section}

Now, use the available functions to make your trading decision. Think step-by-step:
1. Gather current data (balance, portfolio, prices)
2. Analyze signals for each potential trade
3. Calculate appropriate position sizes
4. Execute trades with clear reasoning
5. Summarize your decisions and confidence level

Begin your analysis:
"""

        return full_prompt

    def _parse_decision(
        self,
        response_text: str,
        function_calls: List[Dict],
        decision_type: str
    ) -> Dict:
        """
        Parse Gemini's response into structured decision

        Args:
            response_text: Final response text from Gemini
            function_calls: List of function calls made
            decision_type: Type of decision

        Returns:
            Structured decision dictionary
        """
        # Extract executed trades from function calls
        executed_trades = [
            fc for fc in function_calls
            if fc['function_name'] == 'execute_trade'
        ]

        # Count successful trades
        successful_trades = [
            t for t in executed_trades
            if t['result'].get('success', False)
        ]

        # Extract reasoning and confidence from response text
        reasoning = response_text

        # Estimate confidence based on language used
        confidence = 0.5  # Default
        if any(word in response_text.lower() for word in ['high confidence', 'strong signal', 'very bullish']):
            confidence = 0.8
        elif any(word in response_text.lower() for word in ['moderate', 'cautious', 'uncertain']):
            confidence = 0.5
        elif any(word in response_text.lower() for word in ['low confidence', 'weak signal', 'risky']):
            confidence = 0.3

        return {
            'success': True,
            'decision_type': decision_type,
            'reasoning': reasoning,
            'confidence_score': confidence,
            'function_calls': function_calls,
            'executed_trades': len(executed_trades),
            'successful_trades': len(successful_trades),
            'summary': f"Executed {len(successful_trades)}/{len(executed_trades)} trades with {confidence:.0%} confidence",
            'timestamp': datetime.now().isoformat()
        }

    async def chat_with_user(self, user_message: str, conversation_history: List[Dict] = None) -> str:
        """
        Handle chatbot conversation with user

        Args:
            user_message: User's message
            conversation_history: Previous conversation (optional)

        Returns:
            Gemini's response
        """
        try:
            logger.info(f"Chatbot query: {user_message[:100]}...")

            # Build context from conversation history
            chat = self.model.start_chat(
                history=conversation_history or [],
                enable_automatic_function_calling=True
            )

            # Send user message
            response = chat.send_message(user_message)

            return response.text

        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return f"죄송합니다. 오류가 발생했습니다: {str(e)}"
