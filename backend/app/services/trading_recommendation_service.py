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
            # Configure Gemini with Google Search Grounding enabled
            genai.configure(api_key=self.settings.gemini_api_key)

            # Create model with Google Search grounding tool
            from google.generativeai.types import Tool
            google_search_tool = Tool(google_search={})

            model = genai.GenerativeModel(
                'gemini-3-flash-preview',
                tools=[google_search_tool]  # Enable Google Search grounding
            )

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

        # Calculate available buying power and position values
        cash_balance = portfolio_state.get('cash_balance', 0)
        total_value = portfolio_state.get('total_value', 0)
        positions = portfolio_state.get('positions', [])

        context = f"""
당신은 20년 경력의 전문 주식 트레이더이자 포트폴리오 매니저입니다.
현재 시각: {phase_descriptions.get(market_phase, '일반')}

## 현재 계좌 상태:
- **총 자산**: ${total_value:.2f}
- **현금 잔고 (매수 가능)**: ${cash_balance:.2f}
- 일일 손익: {portfolio_state.get('daily_pnl_pct', 0):.2f}%
- 총 손익: {portfolio_state.get('total_pnl_pct', 0):.2f}%
- 보유 포지션 수: {portfolio_state.get('position_count', 0)}개

## 보유 종목 상세:
"""

        if positions:
            for pos in positions:
                ticker = pos.get('ticker')
                quantity = pos.get('quantity', 0)
                avg_cost = pos.get('avg_cost', 0)
                current_price = pos.get('current_price', 0)
                pnl_pct = pos.get('unrealized_pnl_pct', 0)
                position_value = quantity * current_price

                context += f"""
- **{ticker}**: {quantity}주 (평단가: ${avg_cost:.2f}, 현재가: ${current_price:.2f})
  포지션 가치: ${position_value:.2f}
  손익률: {pnl_pct:+.2f}%
"""
        else:
            context += "- 현재 보유 중인 종목이 없습니다. 신규 투자 기회를 찾아주세요.\n"

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

            # Trading behavior (NEW)
            if hasattr(user_prefs, 'prefer_day_trading') and user_prefs.prefer_day_trading:
                context += "- 단타 (당일 매매) 선호\n"

            if hasattr(user_prefs, 'prefer_swing_trading') and user_prefs.prefer_swing_trading:
                context += "- 스윙 트레이딩 (수일~수주) 선호\n"

            if hasattr(user_prefs, 'prefer_long_term') and user_prefs.prefer_long_term:
                context += "- 장기 투자 선호\n"

            # Price range (NEW)
            if hasattr(user_prefs, 'max_stock_price') and user_prefs.max_stock_price and user_prefs.max_stock_price > 0:
                context += f"- 선호 가격대: ${user_prefs.max_stock_price:.2f} 이하\n"

            # Investment goal (NEW)
            if hasattr(user_prefs, 'investment_goal') and user_prefs.investment_goal:
                context += f"- 투자 목표: {user_prefs.investment_goal}\n"

            # Target return (NEW)
            if hasattr(user_prefs, 'target_annual_return_pct') and user_prefs.target_annual_return_pct and user_prefs.target_annual_return_pct > 0:
                context += f"- 목표 수익률: 연 {user_prefs.target_annual_return_pct:.1f}%\n"

            # Loss tolerance (NEW)
            if hasattr(user_prefs, 'max_acceptable_loss_pct') and user_prefs.max_acceptable_loss_pct:
                context += f"- 최대 허용 손실: {user_prefs.max_acceptable_loss_pct:.1f}%\n"

            # Custom instructions
            if user_prefs.custom_instructions:
                context += f"\n### 추가 투자 지침:\n{user_prefs.custom_instructions}\n"

            context += "\n**중요**: 위 사용자 선호도를 최대한 반영하여 추천을 생성하세요.\n"

        context += f"""

## 임무: 전문 트레이더급 포트폴리오 관리
위 계좌 상태와 시장 데이터를 기반으로 **매수와 매도를 모두 고려한** 종합적인 매매 추천을 제공하세요.

### 🎯 핵심 원칙:
1. **현금 잔고 고려**: 매수 추천 시 현재 현금 잔고 ${cash_balance:.2f}로 실제 구매 가능한 종목만 추천
2. **가격대 현실성**: 주가가 $500 이상인 고가 종목(BRK.A, BRK.B, GOOG 등)은 현금이 충분하지 않으면 제외
3. **매도 기회**: 보유 종목 중 손실이 크거나(-10% 이상), 목표가 도달(+20% 이상), 또는 악재 발생 시 매도 추천
4. **포지션 리밸런싱**: 특정 종목 비중이 과도하면(30% 이상) 일부 매도 제안
5. **분산 투자**: 한 종목에 과도한 집중 투자 지양 (현금의 30% 이하로 매수)

### 📋 추천 형식 (반드시 이 형식을 따라주세요):
```
RECOMMENDATION:
ACTION: BUY|SELL|HOLD
TICKER: 종목코드
PERCENTAGE: 0-100
CONFIDENCE: 0-100
RATIONALE: 근거 설명 (한 줄로)
---
```

### 📊 세부 가이드라인:

**매수(BUY) 추천 시:**
- PERCENTAGE: 현금 잔고의 몇 %를 투자할지 (예: 25 = ${cash_balance * 0.25:.2f} 투자)
- 종목 가격과 현금 잔고를 고려하여 **실제 매수 가능한 종목**만 추천
- 예시: 주가 $150인 종목을 현금의 30% 투자 = 약 {int(cash_balance * 0.30 / 150) if cash_balance > 0 else 0}주 매수 가능

**매도(SELL) 추천 시:**
- PERCENTAGE: 보유량의 몇 %를 매도할지 (예: 50 = 보유량의 절반, 100 = 전량)
- 매도 이유를 명확히 제시:
  * 손절: 손실률이 -10% 초과 시
  * 익절: 목표 수익률(+20%) 달성 시
  * 리밸런싱: 포트폴리오 비중 조정
  * 악재: 실적 악화, 산업 전망 악화 등

**보유(HOLD) 추천 시:**
- PERCENTAGE: 0
- 현재 포지션 유지가 최선인 이유 설명

### 📈 추천 개수:
- 최소 3개, 최대 7개의 추천 제공
- **매수와 매도를 균형있게** 제안 (한쪽만 편중되지 않도록)
- 보유 종목이 있다면 최소 1-2개는 매도/보유 검토 필수

### ✅ 출력 예시:
```
RECOMMENDATION:
ACTION: BUY
TICKER: NVDA
PERCENTAGE: 25
CONFIDENCE: 85
RATIONALE: AI 반도체 수요 증가, 강한 상승 모멘텀, 현금의 25%로 매수 가능
---

RECOMMENDATION:
ACTION: SELL
TICKER: AAPL
PERCENTAGE: 50
CONFIDENCE: 70
RATIONALE: 보유 손실률 -12%, 손절 라인 도달, 보유량의 50% 매도하여 손실 제한
---

RECOMMENDATION:
ACTION: HOLD
TICKER: MSFT
PERCENTAGE: 0
CONFIDENCE: 80
RATIONALE: 안정적인 상승 추세 유지 중, 현재 포지션 유지가 최선
---
```

마지막에 **SUMMARY:**로 시작하는 전체 시장 분석 및 포트폴리오 전략 요약을 2-3문장으로 작성해주세요.

**면책 조항**: 이는 참고용 분석이며, 최종 투자 결정은 사용자 본인의 책임입니다.
"""

        return context

    async def _call_gemini_with_retry(self, model, context, max_retries=2):
        """Call Gemini API with retry logic (120s timeout for comprehensive analysis)"""
        import asyncio

        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, context),
                    timeout=120.0  # Increased to 120 seconds for thorough market research
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
