"""
Trading Recommendation Service
AI-powered trading recommendations based on market data and portfolio analysis
"""

import logging
import google.generativeai as genai
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class TradingRecommendationService:
    """Service for generating AI-powered trading recommendations"""

    def __init__(self, settings, market_data_service):
        self.settings = settings
        self.market_data_service = market_data_service

    async def generate_trading_recommendations(
        self,
        portfolio_state: Dict,
        market_summary: Dict,
        market_phase: str = "general",
        db=None
    ) -> Dict:
        """
        Generate trading recommendations using AI

        Args:
            portfolio_state: Current portfolio state
            market_summary: Market data summary
            market_phase: "market_open", "mid_session", "market_close", or "general"

        Returns:
            Dict with recommendations: {
                'recommendations': [
                    {
                        'action': 'BUY' | 'SELL' | 'HOLD',
                        'ticker': str,
                        'percentage': float (0-100),
                        'rationale': str,
                        'confidence': float (0-100)
                    }
                ],
                'summary': str,
                'timestamp': str
            }
        """
        logger.info(f"[RECOMMEND] 🤖 Generating trading recommendations for {market_phase}...")

        if not self.settings.gemini_api_key:
            logger.warning("[RECOMMEND] ❌ Gemini API key not configured")
            return {
                'recommendations': [],
                'summary': 'Gemini API 키가 설정되지 않았습니다.',
                'timestamp': datetime.now().isoformat()
            }

        try:
            # Configure Gemini
            genai.configure(api_key=self.settings.gemini_api_key)
            model = genai.GenerativeModel('gemini-3-flash-preview')

            # Load user preferences
            user_prefs = await self._load_user_preferences(db) if db else None

            # Build context
            context = self._build_recommendation_context(
                portfolio_state,
                market_summary,
                market_phase,
                user_prefs
            )

            # Generate recommendations
            response = await self._call_gemini_with_retry(model, context)

            if not response or not response.text:
                return {
                    'recommendations': [],
                    'summary': 'AI 응답을 생성하지 못했습니다.',
                    'timestamp': datetime.now().isoformat()
                }

            # Parse recommendations
            parsed = self._parse_recommendations(response.text)

            logger.info(f"[RECOMMEND] ✅ Generated {len(parsed['recommendations'])} recommendations")

            return {
                **parsed,
                'timestamp': datetime.now().isoformat(),
                'market_phase': market_phase
            }

        except Exception as e:
            logger.error(f"[RECOMMEND] 💥 Failed to generate recommendations: {e}", exc_info=True)
            return {
                'recommendations': [],
                'summary': f'추천 생성 실패: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }

    async def _load_user_preferences(self, db):
        """Load user investment preferences from database"""
        try:
            if not db:
                return None

            from ..models import InvestmentPreference
            from sqlalchemy import select

            stmt = select(InvestmentPreference).limit(1)
            result = await db.execute(stmt)
            prefs = result.scalar_one_or_none()

            if prefs:
                logger.info(f"[RECOMMEND] 💾 Loaded user preferences: {prefs.risk_appetite}, {prefs.investment_style}")
            return prefs
        except Exception as e:
            logger.warning(f"[RECOMMEND] Failed to load user preferences: {e}")
            return None

    def _build_recommendation_context(
        self,
        portfolio_state: Dict,
        market_summary: Dict,
        market_phase: str,
        user_prefs=None
    ) -> str:
        """Build context for AI recommendation generation"""

        phase_descriptions = {
            'market_open': '장 시작 직후 - 오전 9시 30분 (EST)',
            'mid_session': '장 중반 - 오후 12시 30분 (EST)',
            'market_close': '장 마감 30분 전 - 오후 3시 30분 (EST)',
            'general': '일반 분석'
        }

        context = f"""
당신은 전문 주식 트레이더이며 데이터 기반 투자 분석가입니다.
현재 시각: {phase_descriptions.get(market_phase, '일반')}

## 현재 포트폴리오 상태:
- 총 자산: ${portfolio_state.get('total_value', 0):.2f}
- 현금 잔고: ${portfolio_state.get('cash_balance', 0):.2f}
- 일일 손익: {portfolio_state.get('daily_pnl_pct', 0):.2f}%
- 총 손익: {portfolio_state.get('total_pnl_pct', 0):.2f}%
- 보유 포지션 수: {portfolio_state.get('position_count', 0)}개

## 보유 종목:
"""

        positions = portfolio_state.get('positions', [])
        if positions:
            for pos in positions:
                context += f"""
- ${pos.get('ticker')}: {pos.get('quantity')}주
  평단가: ${pos.get('avg_cost', 0):.2f}
  현재가: ${pos.get('current_price', 0):.2f}
  손익률: {pos.get('unrealized_pnl_pct', 0):.2f}%
"""
        else:
            context += "- 보유 중인 종목이 없습니다.\n"

        # Add market summary
        context += f"\n\n## 시장 동향 (다중 소스 통합):\n{market_summary.get('summary_text', '')}\n"

        # Add user preferences
        if user_prefs:
            context += "\n\n## 사용자 투자 선호도 (반드시 고려):\n"

            # Risk appetite
            risk_map = {
                'conservative': '보수적 (안전한 투자 선호)',
                'moderate': '중립적 (균형 잡힌 투자)',
                'aggressive': '공격적 (고위험 고수익 추구)'
            }
            context += f"- 위험 성향: {risk_map.get(user_prefs.risk_appetite, user_prefs.risk_appetite)}\n"

            # Investment style
            style_map = {
                'growth': '성장주 선호',
                'value': '가치주 선호',
                'dividend': '배당주 선호',
                'balanced': '균형 잡힌 포트폴리오'
            }
            context += f"- 투자 스타일: {style_map.get(user_prefs.investment_style, user_prefs.investment_style)}\n"

            # Preferred sectors
            if user_prefs.preferred_sectors:
                sectors = user_prefs.preferred_sectors.split(',')
                context += f"- 선호 섹터: {', '.join(filter(None, sectors))}\n"

            # Avoided sectors
            if user_prefs.avoided_sectors:
                sectors = user_prefs.avoided_sectors.split(',')
                context += f"- 회피 섹터: {', '.join(filter(None, sectors))}\n"

            # Preferred tickers
            if user_prefs.preferred_tickers:
                tickers = user_prefs.preferred_tickers.split(',')
                context += f"- 선호 종목: {', '.join(filter(None, tickers))}\n"

            # Avoided tickers
            if user_prefs.avoided_tickers:
                tickers = user_prefs.avoided_tickers.split(',')
                context += f"- 회피 종목: {', '.join(filter(None, tickers))}\n"

            # Strategy preferences
            if user_prefs.prefer_diversification:
                context += "- 분산 투자 선호\n"

            if user_prefs.prefer_dip_buying:
                context += "- 하락장 매수 선호 (저점 매수)\n"

            if user_prefs.prefer_momentum:
                context += "- 모멘텀 투자 선호 (상승 추세 종목)\n"

            # Custom instructions
            if user_prefs.custom_instructions:
                context += f"\n### 추가 투자 지침:\n{user_prefs.custom_instructions}\n"

            context += "\n**중요**: 위 사용자 선호도를 최대한 반영하여 추천을 생성하세요.\n"

        context += f"""

## 임무:
위 데이터를 기반으로 다음 형식으로 매매 추천을 제공하세요:

### 추천 형식 (반드시 이 형식을 따라주세요):
```
RECOMMENDATION:
ACTION: BUY|SELL|HOLD
TICKER: 종목코드
PERCENTAGE: 0-100 (포트폴리오 대비 비율)
CONFIDENCE: 0-100
RATIONALE: 근거 설명 (한 줄로)
---
```

### 가이드라인:
1. 최대 3-5개의 추천만 제공하세요
2. BUY: 새로 매수하거나 보유 종목 추가 매수
3. SELL: 보유 종목 매도 (일부 또는 전체)
4. HOLD: 현재 포지션 유지
5. PERCENTAGE:
   - BUY: 현금의 몇 %를 투자할지 (예: 30 = 현금의 30%)
   - SELL: 보유량의 몇 %를 매도할지 (예: 50 = 보유량의 50%)
   - HOLD: 0
6. CONFIDENCE: 추천의 확신도 (높을수록 확실)

마지막에 **SUMMARY:**로 시작하는 전체 요약을 한 문단으로 작성해주세요.

**중요**: 이는 참고용이며 최종 결정은 사용자가 합니다.
"""

        return context

    async def _call_gemini_with_retry(self, model, context, max_retries=2):
        """Call Gemini API with retry logic"""
        import asyncio

        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, context),
                    timeout=30.0
                )
                return response
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.warning(f"[RECOMMEND] ⏱️ Timeout, retrying... (attempt {attempt + 1})")
                    await asyncio.sleep(2)
                else:
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[RECOMMEND] ⚠️ Error, retrying... (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(2)
                else:
                    raise

    def _parse_recommendations(self, text: str) -> Dict:
        """Parse AI response into structured recommendations"""
        recommendations = []
        summary = ""

        # Split by RECOMMENDATION: or ---
        parts = text.split('RECOMMENDATION:')

        for part in parts[1:]:  # Skip first empty part
            lines = part.strip().split('\n')
            rec = {}

            for line in lines:
                line = line.strip()
                if line.startswith('ACTION:'):
                    rec['action'] = line.split(':', 1)[1].strip().upper()
                elif line.startswith('TICKER:'):
                    rec['ticker'] = line.split(':', 1)[1].strip().upper().replace('$', '')
                elif line.startswith('PERCENTAGE:'):
                    try:
                        rec['percentage'] = float(line.split(':', 1)[1].strip().split()[0])
                    except:
                        rec['percentage'] = 0
                elif line.startswith('CONFIDENCE:'):
                    try:
                        rec['confidence'] = float(line.split(':', 1)[1].strip().split()[0])
                    except:
                        rec['confidence'] = 50
                elif line.startswith('RATIONALE:'):
                    rec['rationale'] = line.split(':', 1)[1].strip()
                elif line == '---':
                    break

            if rec.get('action') and rec.get('ticker'):
                recommendations.append(rec)

        # Extract summary
        if 'SUMMARY:' in text:
            summary = text.split('SUMMARY:')[1].strip()

        return {
            'recommendations': recommendations,
            'summary': summary or "추천이 생성되었습니다."
        }
