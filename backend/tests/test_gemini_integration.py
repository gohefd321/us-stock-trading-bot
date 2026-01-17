"""
Test Gemini AI Integration
Simple test script to verify Gemini function calling works
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Settings
from app.services.broker_service import BrokerService
from app.services.portfolio_manager import PortfolioManager
from app.services.signal_aggregator import SignalAggregator
from app.services.wsb_scraper import WSBScraper
from app.services.yahoo_finance_service import YahooFinanceService
from app.services.tipranks_service import TipRanksService
from app.services.risk_manager import RiskManager
from app.services.gemini_service import GeminiService
from app.gemini_functions.function_handlers import FunctionHandler
from app.database import engine, AsyncSessionLocal
from app.utils.logging_config import setup_logging


async def test_gemini_functions():
    """Test individual Gemini functions"""
    print("\n" + "="*60)
    print("Testing Gemini Function Handlers")
    print("="*60)

    # Setup
    settings = Settings()

    # Initialize services (with mock broker for testing)
    class MockBroker:
        async def get_balance(self):
            return {
                'cash_balance': 800000,
                'total_value': 1050000,
                'timestamp': '2024-01-01T12:00:00'
            }

        async def get_us_stock_price(self, ticker):
            prices = {'AAPL': 185.50, 'TSLA': 245.30, 'NVDA': 495.75}
            return prices.get(ticker, 150.00)

        async def get_us_positions(self):
            return [
                {
                    'ticker': 'AAPL',
                    'quantity': 5,
                    'avg_cost': 180.00,
                    'current_price': 185.50,
                    'total_value': 927.50,
                    'unrealized_pnl': 27.50
                }
            ]

        async def place_us_order(self, ticker, action, quantity, order_type, limit_price=None):
            return {
                'success': True,
                'order_id': 'TEST_ORDER_123',
                'ticker': ticker,
                'action': action,
                'quantity': quantity
            }

    broker = MockBroker()
    portfolio_manager = PortfolioManager(broker, settings)

    # Initialize signal services
    wsb_scraper = WSBScraper(settings)
    yahoo_service = YahooFinanceService()
    tipranks_service = TipRanksService()
    signal_aggregator = SignalAggregator(wsb_scraper, yahoo_service, tipranks_service)

    risk_manager = RiskManager(portfolio_manager, broker, settings)

    # Create database session
    async with AsyncSessionLocal() as db:
        function_handler = FunctionHandler(
            broker=broker,
            portfolio_manager=portfolio_manager,
            signal_aggregator=signal_aggregator,
            risk_manager=risk_manager,
            db=db
        )

        # Test 1: Check Balance
        print("\n1. Testing check_balance()")
        result = await function_handler.check_balance()
        print(f"   Result: {result}")
        assert result['success'] == True

        # Test 2: Get Current Price
        print("\n2. Testing get_current_price('AAPL')")
        result = await function_handler.get_current_price(ticker='AAPL')
        print(f"   Result: {result}")
        assert result['success'] == True
        assert result['ticker'] == 'AAPL'

        # Test 3: Get Portfolio Status
        print("\n3. Testing get_portfolio_status()")
        result = await function_handler.get_portfolio_status()
        print(f"   Result: {result}")
        assert result['success'] == True

        # Test 4: Calculate Position Size
        print("\n4. Testing calculate_position_size()")
        result = await function_handler.calculate_position_size(
            ticker='NVDA',
            confidence=0.8,
            price=495.75
        )
        print(f"   Result: {result}")
        assert result['success'] == True
        assert result['recommended_quantity'] >= 0

        # Test 5: Analyze Signals (may take a while with real API calls)
        print("\n5. Testing analyze_signals('AAPL')")
        print("   (This may take 10-30 seconds with real API calls...)")
        result = await function_handler.analyze_signals(ticker='AAPL', hours_back=24)
        print(f"   Result: {result}")
        assert result['success'] == True

        print("\n" + "="*60)
        print("All function tests passed! ✓")
        print("="*60)


async def test_gemini_decision():
    """Test full Gemini trading decision"""
    print("\n" + "="*60)
    print("Testing Gemini Trading Decision")
    print("="*60)

    # Check if Gemini API key is set
    settings = Settings()
    if not settings.gemini_api_key or settings.gemini_api_key == 'your_gemini_api_key_here':
        print("\n⚠️  WARNING: GEMINI_API_KEY not set in .env file")
        print("Please add your Gemini API key to .env to test AI decisions")
        print("Get your API key from: https://aistudio.google.com/app/apikey")
        return

    print(f"\n✓ Gemini API key found: {settings.gemini_api_key[:10]}...")

    # Setup services
    class MockBroker:
        async def get_balance(self):
            return {'cash_balance': 1000000, 'total_value': 1000000}

        async def get_us_stock_price(self, ticker):
            return 150.00

        async def get_us_positions(self):
            return []

        async def place_us_order(self, ticker, action, quantity, order_type, limit_price=None):
            return {'success': True, 'order_id': f'TEST_{ticker}_{action}'}

    broker = MockBroker()
    portfolio_manager = PortfolioManager(broker, settings)
    wsb_scraper = WSBScraper(settings)
    yahoo_service = YahooFinanceService()
    tipranks_service = TipRanksService()
    signal_aggregator = SignalAggregator(wsb_scraper, yahoo_service, tipranks_service)
    risk_manager = RiskManager(portfolio_manager, broker, settings)

    async with AsyncSessionLocal() as db:
        function_handler = FunctionHandler(
            broker=broker,
            portfolio_manager=portfolio_manager,
            signal_aggregator=signal_aggregator,
            risk_manager=risk_manager,
            db=db
        )

        gemini_service = GeminiService(function_handler, settings)

        # Mock portfolio state
        portfolio_state = {
            'total_value_krw': 1000000,
            'cash_balance_krw': 1000000,
            'holdings_value_krw': 0,
            'position_count': 0,
            'daily_pnl_krw': 0,
            'daily_pnl_pct': 0.0,
            'total_pnl_krw': 0,
            'total_pnl_pct': 0.0
        }

        # Mock signals
        market_signals = [
            {
                'ticker': 'AAPL',
                'composite_sentiment': 0.65,
                'signal_strength': 0.75,
                'recommendation': 'BUY'
            },
            {
                'ticker': 'TSLA',
                'composite_sentiment': -0.30,
                'signal_strength': 0.60,
                'recommendation': 'SELL'
            }
        ]

        print("\nMaking PRE_MARKET trading decision with Gemini...")
        print("(This will make actual Gemini API calls)\n")

        decision = await gemini_service.make_trading_decision(
            decision_type='PRE_MARKET',
            portfolio_state=portfolio_state,
            market_signals=market_signals,
            additional_context='This is a test decision'
        )

        print("\n" + "-"*60)
        print("Decision Result:")
        print("-"*60)
        print(f"Success: {decision.get('success')}")
        print(f"Decision Type: {decision.get('decision_type')}")
        print(f"Confidence: {decision.get('confidence_score', 0):.2f}")
        print(f"Executed Trades: {decision.get('executed_trades', 0)}")
        print(f"Successful Trades: {decision.get('successful_trades', 0)}")
        print(f"\nReasoning:")
        print(decision.get('reasoning', 'No reasoning provided')[:500])
        print("\n" + "-"*60)

        if decision.get('success'):
            print("\n✓ Gemini decision test passed!")
        else:
            print(f"\n✗ Gemini decision test failed: {decision.get('error')}")


async def main():
    """Run all tests"""
    # Setup logging
    setup_logging()

    print("\n" + "="*60)
    print("US Stock Trading Bot - Gemini AI Integration Test")
    print("="*60)

    try:
        # Test 1: Function handlers
        await test_gemini_functions()

        # Test 2: Full Gemini decision
        await test_gemini_decision()

        print("\n" + "="*60)
        print("All tests completed successfully! ✓")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
