"""
Daily Report Service

LLM 기반 일일 시장 리포트 생성 서비스
- Phase 1.1-1.3 데이터 통합
- Gemini API로 종목 추천 및 분석
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, date
import json
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.market_screener_service import MarketScreenerService
from ..services.fundamental_service import FundamentalService
from ..services.news_event_service import NewsEventService
from ..services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class DailyReportService:
    """일일 시장 리포트 생성 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.screener = MarketScreenerService(db)
        self.fundamentals = FundamentalService(db)
        self.news = NewsEventService(db)
        self.gemini = GeminiService()

    async def generate_daily_report(self) -> Dict:
        """
        일일 시장 리포트 생성

        Returns:
            리포트 데이터 (추천 종목, 시장 요약 등)
        """
        try:
            logger.info("📊 Generating daily market report...")

            # 1. 데이터 수집
            market_data = await self._collect_market_data()

            # 2. Gemini에게 분석 요청
            report = await self._generate_llm_analysis(market_data)

            logger.info(f"✅ Daily report generated: {len(report.get('recommended_stocks', []))} stocks")

            return {
                "success": True,
                "report_date": date.today().isoformat(),
                "market_summary": report.get('market_summary'),
                "recommended_stocks": report.get('recommended_stocks', []),
                "market_data": market_data,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_at": datetime.now().isoformat(),
            }

    async def _collect_market_data(self) -> Dict:
        """
        Phase 1.1-1.3 데이터 수집

        Returns:
            수집된 시장 데이터
        """
        logger.info("📥 Collecting market data from all sources...")

        # Phase 1.1: Market Screener
        top_gainers = await self.screener.get_top_gainers(10)
        top_losers = await self.screener.get_top_losers(10)
        volume_surge = await self.screener.get_volume_surge(10)
        market_cap_leaders = await self.screener.get_market_cap_leaders(20)
        extremes_52w = await self.screener.get_52w_extremes()

        # Phase 1.2: Fundamentals
        top_roe = await self.fundamentals.get_top_by_roe(15)
        upcoming_earnings = await self.fundamentals.get_upcoming_earnings(7)

        # 수집된 데이터 정리
        data = {
            "screener": {
                "top_gainers": top_gainers,
                "top_losers": top_losers,
                "volume_surge": volume_surge,
                "market_cap_leaders": market_cap_leaders,
                "52w_highs": extremes_52w.get('highs', []),
                "52w_lows": extremes_52w.get('lows', []),
            },
            "fundamentals": {
                "top_roe": top_roe,
                "upcoming_earnings": upcoming_earnings,
            },
        }

        logger.info("✓ Market data collected")
        return data

    async def _generate_llm_analysis(self, market_data: Dict) -> Dict:
        """
        Gemini API로 시장 분석 및 종목 추천

        Args:
            market_data: 수집된 시장 데이터

        Returns:
            LLM 분석 결과
        """
        logger.info("🤖 Generating LLM analysis...")

        # 프롬프트 구성
        prompt = self._build_analysis_prompt(market_data)

        # Gemini API 호출
        response = await self.gemini.generate_content_async(prompt)

        # 응답 파싱
        try:
            # JSON 형식으로 응답 받기
            analysis = json.loads(response)

            return {
                "market_summary": analysis.get('market_summary', 'N/A'),
                "recommended_stocks": analysis.get('recommended_stocks', []),
            }

        except json.JSONDecodeError:
            # JSON 파싱 실패 시 텍스트 응답 사용
            logger.warning("Failed to parse JSON response, using text response")
            return {
                "market_summary": response,
                "recommended_stocks": [],
            }

    def _build_analysis_prompt(self, market_data: Dict) -> str:
        """
        Gemini API 프롬프트 구성

        Args:
            market_data: 시장 데이터

        Returns:
            프롬프트 문자열
        """
        screener = market_data.get('screener', {})
        fundamentals = market_data.get('fundamentals', {})

        # Top 종목 추출 (gainers, volume surge, ROE)
        top_gainers_str = ", ".join([f"{s['ticker']} (+{s['price_change_pct']:.1f}%)" for s in screener.get('top_gainers', [])[:5]])
        volume_surge_str = ", ".join([f"{s['ticker']} ({s['volume_change_pct']:.0f}%)" for s in screener.get('volume_surge', [])[:5]])
        top_roe_str = ", ".join([f"{s['ticker']} (ROE: {s['roe']:.1f}%)" for s in fundamentals.get('top_roe', [])[:5]])

        # 52w extremes
        highs_str = ", ".join([s['ticker'] for s in screener.get('52w_highs', [])[:5]])
        lows_str = ", ".join([s['ticker'] for s in screener.get('52w_lows', [])[:5]])

        # Upcoming earnings
        earnings_str = ", ".join([f"{s['ticker']} ({s['next_earnings_date']})" for s in fundamentals.get('upcoming_earnings', [])[:5]])

        prompt = f"""
당신은 퀀트 트레이딩 전문가입니다. 다음 시장 데이터를 분석하여 알고리즘 트레이딩에 적합한 종목 3-5개를 추천하세요.

## 시장 데이터 (오늘: {date.today().isoformat()})

### 1. 시장 스크리너
- **급등주 (Top 5)**: {top_gainers_str}
- **거래량 급증 (Top 5)**: {volume_surge_str}
- **52주 신고가**: {highs_str}
- **52주 신저가**: {lows_str}

### 2. 재무 데이터
- **ROE 상위 (Top 5)**: {top_roe_str}
- **실적 발표 예정 (7일 이내)**: {earnings_str}

## 추천 기준
1. **단기 모멘텀**: 1-3일 내 가격 변동 가능성
2. **유동성**: 일평균 거래량 1M+ (거래량 급증 종목 우선)
3. **변동성**: 적정 수준의 ATR (너무 높거나 낮지 않은)
4. **펀더멘털**: EPS 성장, 합리적인 P/E 비율
5. **이벤트**: 실적 발표, 뉴스 등 단기 촉매제

## 출력 형식 (JSON)
```json
{{
  "market_summary": "오늘 시장은...",
  "recommended_stocks": [
    {{
      "ticker": "NVDA",
      "score": 85,
      "momentum_score": 90,
      "fundamental_score": 80,
      "technical_score": 85,
      "rationale": "거래량 급증 (+250%), 52주 신고가 근접, 다음 주 실적 발표 예정. 단기 모멘텀 강세.",
      "suggested_strategies": ["MA_CROSS", "RSI", "VWAP"],
      "risk_level": "MEDIUM"
    }}
  ]
}}
```

**중요**: 반드시 위 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.
"""

        return prompt

    async def get_latest_report(self) -> Optional[Dict]:
        """
        가장 최근 생성된 리포트 조회 (캐시)

        Returns:
            최근 리포트 또는 None
        """
        # TODO: 캐시 구현 (Redis 또는 DB)
        logger.warning("get_latest_report not implemented, generating new report")
        return await self.generate_daily_report()
