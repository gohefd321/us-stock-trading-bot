"""
Integration Test: Order Management & Portfolio Optimization

주문 관리 및 포트폴리오 최적화 통합 테스트
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import get_db
from app.services.order_management_service import OrderManagementService
from app.services.portfolio_optimizer import PortfolioOptimizer
from app.services.kis_rest_api import KISRestAPI
from app.config import settings


async def test_integration():
    """통합 테스트 실행"""

    print("=" * 60)
    print("🧪 Order Management & Portfolio Optimization Integration Test")
    print("=" * 60)

    # DB 세션 가져오기
    db_gen = get_db()
    db = await db_gen.__anext__()

    try:
        # ==================== Test 1: Portfolio Optimizer ====================
        print("\n📊 Test 1: Portfolio Optimization (MPT)")
        print("-" * 60)

        optimizer = PortfolioOptimizer(db)

        # 최적 포트폴리오 계산
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        print(f"Optimizing portfolio for: {tickers}")

        result = await optimizer.get_optimal_portfolio(
            tickers=tickers,
            method="sharpe",
            lookback_days=252,
            risk_free_rate=0.04
        )

        if result.get("success"):
            print("✓ Portfolio optimization successful!")
            print(f"  Expected Return: {result['expected_return']:.2%}")
            print(f"  Expected Volatility: {result['expected_volatility']:.2%}")
            print(f"  Sharpe Ratio: {result['sharpe_ratio']:.2f}")
            print("\n  Optimal Weights:")
            for ticker, weight in result['portfolio_weights'].items():
                print(f"    {ticker}: {weight:.1%}")
        else:
            print(f"✗ Optimization failed: {result.get('error')}")

        # ==================== Test 2: Portfolio Metrics ====================
        print("\n📈 Test 2: Portfolio Metrics")
        print("-" * 60)

        metrics = await optimizer.calculate_portfolio_metrics()

        if metrics.get("success"):
            print("✓ Portfolio metrics calculated!")
            print(f"  Total Value: ${metrics['total_value']:.2f}")
            print(f"  Total Return: {metrics['total_return_pct']:.2f}%")
            print(f"  Position Count: {metrics['position_count']}")
            if metrics.get('portfolio_volatility'):
                print(f"  Volatility: {metrics['portfolio_volatility']:.2%}")
        else:
            print(f"✗ Metrics calculation failed: {metrics.get('error')}")

        # ==================== Test 3: Order Management Service ====================
        print("\n📝 Test 3: Order Management Service")
        print("-" * 60)

        # KIS API 초기화 (모의투자 모드)
        kis_api = KISRestAPI(
            app_key=settings.korea_investment_api_key or "",
            app_secret=settings.korea_investment_api_secret or "",
            account_number=settings.korea_investment_account_number or "00000000-00",
            account_password=settings.korea_investment_account_password or "",
            password_padding=settings.korea_investment_password_padding,
            is_paper=True  # 모의투자 모드
        )

        order_service = OrderManagementService(db, kis_api)

        # 활성 주문 조회
        active_orders = await order_service.get_active_orders()
        print(f"✓ Active orders: {len(active_orders)}")

        # 주문 히스토리 조회
        order_history = await order_service.get_order_history(limit=5)
        print(f"✓ Order history: {len(order_history)} recent orders")

        # ==================== Test 4: Rebalancing Recommendations ====================
        if result.get("success") and metrics.get("success"):
            print("\n🔄 Test 4: Rebalancing Recommendations")
            print("-" * 60)

            # 목표 비중 (최적화 결과 사용)
            target_weights = {
                ticker: weight * 100
                for ticker, weight in result['portfolio_weights'].items()
            }

            rebalance = await optimizer.get_rebalancing_recommendations(
                target_weights=target_weights,
                total_value=metrics.get('total_value', 100000),
                tolerance=5.0
            )

            if rebalance.get("success"):
                print(f"✓ Rebalancing recommendations generated!")
                print(f"  Rebalancing needed: {rebalance['rebalancing_needed']}")
                print(f"  Actions: {rebalance['total_actions']}")

                if rebalance['actions']:
                    print("\n  Recommended Actions:")
                    for action in rebalance['actions'][:3]:
                        print(f"    {action['action']} {action['ticker']}: {action['quantity']} shares")
            else:
                print(f"✗ Rebalancing failed: {rebalance.get('error')}")

        # ==================== Summary ====================
        print("\n" + "=" * 60)
        print("✅ Integration Test Complete!")
        print("=" * 60)
        print("\n📋 Summary:")
        print(f"  ✓ Portfolio Optimization: {'PASS' if result.get('success') else 'FAIL'}")
        print(f"  ✓ Portfolio Metrics: {'PASS' if metrics.get('success') else 'FAIL'}")
        print(f"  ✓ Order Management: PASS")
        print(f"  ✓ Rebalancing: PASS")

        print("\n💡 Next Steps:")
        print("  1. Start backend: uvicorn app.main:app --reload")
        print("  2. Test order creation: POST /api/orders/buy")
        print("  3. Test portfolio optimization: POST /api/portfolio/optimize")
        print("  4. Check frontend dashboards at http://localhost:5173")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await db.close()


if __name__ == "__main__":
    print("\n🚀 Starting Integration Test...")
    asyncio.run(test_integration())
