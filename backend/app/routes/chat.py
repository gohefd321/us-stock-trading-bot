"""
Chat API Routes for AI Investment Analysis
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import google.generativeai as genai
from typing import Optional

from ..database import get_db
from ..services.portfolio_manager import PortfolioManager
from ..services.broker_service import BrokerService
from ..services.market_data_service import MarketDataService
from ..config import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


async def _extract_and_save_preferences(user_message: str, ai_response: str, db: AsyncSession):
    """
    Extract investment preferences from chat conversation and save to database
    """
    try:
        from ..models import InvestmentPreference
        from sqlalchemy import select
        from datetime import datetime

        # Keywords to detect preference changes
        user_lower = user_message.lower()

        # Get or create preference record
        stmt = select(InvestmentPreference).limit(1)
        result = await db.execute(stmt)
        prefs = result.scalar_one_or_none()

        if not prefs:
            prefs = InvestmentPreference()
            db.add(prefs)

        changed = False

        # Extract risk appetite (more aggressive detection)
        if any(word in user_lower for word in ['안전', '보수적', '위험 회피', 'conservative', 'safe', '안정', '리스크 낮', '손실 최소']):
            prefs.risk_appetite = 'conservative'
            changed = True
        elif any(word in user_lower for word in ['공격적', '고위험', 'aggressive', 'high risk', '리스크 높', '고수익', '적극']):
            prefs.risk_appetite = 'aggressive'
            changed = True
        elif any(word in user_lower for word in ['중립', '보통', 'moderate', 'balanced', '균형', '중간']):
            prefs.risk_appetite = 'moderate'
            changed = True

        # Extract investment style (more aggressive detection)
        if any(word in user_lower for word in ['성장주', 'growth', '그로스', '성장', '미래', '혁신', '신기술']):
            prefs.investment_style = 'growth'
            changed = True
        elif any(word in user_lower for word in ['가치주', 'value', '밸류', '저평가', '가치', '저가']):
            prefs.investment_style = 'value'
            changed = True
        elif any(word in user_lower for word in ['배당주', 'dividend', '배당', '배당금', '안정수익', '배당수익']):
            prefs.investment_style = 'dividend'
            changed = True

        # Extract sector preferences (expanded keywords)
        sector_map = {
            '기술주': 'technology', '테크': 'technology', 'tech': 'technology', 'it': 'technology',
            '소프트웨어': 'technology', '반도체': 'technology', '클라우드': 'technology',
            '헬스케어': 'healthcare', '의료': 'healthcare', '제약': 'healthcare', '바이오': 'healthcare',
            '금융': 'finance', 'bank': 'finance', '은행': 'finance', '증권': 'finance',
            '에너지': 'energy', '석유': 'energy', '가스': 'energy',
            '소비재': 'consumer', '리테일': 'consumer', '유통': 'consumer', '쇼핑': 'consumer'
        }

        for keyword, sector in sector_map.items():
            if keyword in user_lower:
                if any(neg in user_lower for neg in ['싫어', '피하', 'avoid', '제외', '안좋', '투자안']):
                    # Add to avoided sectors
                    avoided = set(prefs.avoided_sectors.split(',')) if prefs.avoided_sectors else set()
                    avoided.add(sector)
                    prefs.avoided_sectors = ','.join(filter(None, avoided))
                    changed = True
                elif any(pos in user_lower for pos in ['좋아', '관심', 'prefer', 'like', '투자', '매수', '추천', '원해', '원함']):
                    # Add to preferred sectors
                    preferred = set(prefs.preferred_sectors.split(',')) if prefs.preferred_sectors else set()
                    preferred.add(sector)
                    prefs.preferred_sectors = ','.join(filter(None, preferred))
                    changed = True

        # Extract ticker preferences (simple pattern matching)
        import re
        ticker_pattern = r'\b([A-Z]{1,5})\b'
        tickers = re.findall(ticker_pattern, user_message)

        for ticker in tickers:
            if len(ticker) >= 2 and len(ticker) <= 5:  # Valid ticker length
                if any(neg in user_lower for neg in ['싫어', '피하', 'avoid', '제외', '안좋', '투자안', '손실', '매도']):
                    avoided_tickers = set(prefs.avoided_tickers.split(',')) if prefs.avoided_tickers else set()
                    avoided_tickers.add(ticker)
                    prefs.avoided_tickers = ','.join(filter(None, avoided_tickers))
                    changed = True
                elif any(pos in user_lower for pos in ['좋아', '추천', 'buy', 'prefer', '매수', '투자', '사고싶', '관심', '원해', '원함']):
                    preferred_tickers = set(prefs.preferred_tickers.split(',')) if prefs.preferred_tickers else set()
                    preferred_tickers.add(ticker)
                    prefs.preferred_tickers = ','.join(filter(None, preferred_tickers))
                    changed = True

        # Extract trading strategy preferences (more aggressive)
        if any(word in user_lower for word in ['분산', 'diversif', '여러', '다양', '골고루']):
            prefs.prefer_diversification = True
            changed = True

        if any(word in user_lower for word in ['하락', '떨어지', '하락장', '저점', 'dip']) and \
           any(word in user_lower for word in ['매수', 'buy', '사', '기회']):
            prefs.prefer_dip_buying = True
            changed = True

        if any(word in user_lower for word in ['모멘텀', 'momentum', '추세', '상승', '급등', '강세']):
            prefs.prefer_momentum = True
            changed = True

        # Save custom instructions (more inclusive)
        if any(word in user_lower for word in ['조건', '전략', 'strategy', '방식', '원칙', '기준', '선호', '스타일']):
            if prefs.custom_instructions:
                prefs.custom_instructions += f"\n[{datetime.now().strftime('%Y-%m-%d')}] {user_message}"
            else:
                prefs.custom_instructions = f"[{datetime.now().strftime('%Y-%m-%d')}] {user_message}"
            changed = True

        # Extract trading behavior preferences (NEW)
        if any(word in user_lower for word in ['단타', '데이', 'day trading', '당일', '하루']):
            prefs.prefer_day_trading = True
            changed = True

        if any(word in user_lower for word in ['스윙', 'swing', '며칠', '단기']):
            prefs.prefer_swing_trading = True
            changed = True

        if any(word in user_lower for word in ['장기', 'long term', '장투', '오래', '보유', '몇년', '몇 년']):
            prefs.prefer_long_term = True
            changed = True

        # Extract price range preferences (NEW)
        price_mentions = re.findall(r'\$?\s*(\d+(?:\.\d+)?)\s*(?:달러|불|dollar|usd)', user_lower)
        if price_mentions and any(word in user_lower for word in ['이하', '이내', '까지', '범위', '가격대']):
            try:
                max_price = float(price_mentions[0])
                if max_price > 0 and max_price < 10000:  # Reasonable range
                    prefs.max_stock_price = max_price
                    changed = True
            except:
                pass

        # Extract investment goals (NEW)
        goal_map = {
            '은퇴': '은퇴 자금',
            'retirement': '은퇴 자금',
            '단기 수익': '단기 수익',
            'short term': '단기 수익',
            '자산 증식': '자산 증식',
            'wealth': '자산 증식',
            '소득': '소득 창출',
            'income': '소득 창출'
        }
        for keyword, goal in goal_map.items():
            if keyword in user_lower:
                prefs.investment_goal = goal
                changed = True
                break

        # Extract target return expectations (NEW)
        return_mentions = re.findall(r'(\d+)\s*%', user_message)
        if return_mentions and any(word in user_lower for word in ['수익', 'return', '목표', 'target', '기대', '원해']):
            try:
                target = float(return_mentions[0])
                if 1 <= target <= 200:  # Reasonable range
                    prefs.target_annual_return_pct = target
                    changed = True
            except:
                pass

        # Extract loss tolerance (NEW)
        if any(word in user_lower for word in ['손실', 'loss', '손해', '잃', '마이너스']):
            loss_mentions = re.findall(r'(\d+)\s*%', user_message)
            if loss_mentions:
                try:
                    max_loss = float(loss_mentions[0])
                    if 1 <= max_loss <= 50:  # Reasonable range
                        prefs.max_acceptable_loss_pct = max_loss
                        changed = True
                except:
                    pass

        # Save any investment-related conversation to custom instructions
        if any(word in user_lower for word in ['투자', 'invest', '포트폴리오', '매수', '매도', 'buy', 'sell', '종목', 'stock']):
            if not prefs.custom_instructions or user_message not in prefs.custom_instructions:
                if prefs.custom_instructions:
                    prefs.custom_instructions += f"\n[{datetime.now().strftime('%Y-%m-%d')}] {user_message}"
                else:
                    prefs.custom_instructions = f"[{datetime.now().strftime('%Y-%m-%d')}] {user_message}"
                changed = True

        if changed:
            prefs.last_updated_by_chat = datetime.now()
            await db.commit()
            logger.info(f"[CHAT] 💾 Investment preferences updated from conversation")

    except Exception as e:
        logger.error(f"[CHAT] Failed to extract preferences: {e}")
        # Don't fail the chat if preference extraction fails
        pass


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    error: Optional[str] = None


# Dependency: Get services
async def get_services(db: AsyncSession = Depends(get_db)):
    """Get initialized services"""
    settings = Settings()
    broker = BrokerService(settings)
    portfolio = PortfolioManager(broker, settings, db)
    market_data = MarketDataService(settings)

    return {
        'settings': settings,
        'broker': broker,
        'portfolio': portfolio,
        'market_data': market_data,
        'db': db
    }


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    services: dict = Depends(get_services)
):
    """
    AI 투자 분석 챗봇 엔드포인트

    사용자의 질문을 받아 포트폴리오 정보와 함께 Gemini AI에 전달하여
    투자 분석 및 조언을 제공합니다.
    """
    try:
        logger.info(f"[CHAT] 📨 Chat request received: '{request.message[:100]}...'")

        settings = services['settings']
        portfolio = services['portfolio']
        market_data = services['market_data']

        # Gemini API 키 확인
        logger.info("[CHAT] 🔑 Checking Gemini API key...")
        if not settings.gemini_api_key:
            logger.warning("[CHAT] ❌ Gemini API key not configured")
            return ChatResponse(
                response="",
                error="Gemini API 키가 설정되지 않았습니다. 설정 페이지에서 API 키를 입력해주세요."
            )
        logger.info(f"[CHAT] ✅ Gemini API key found: {settings.gemini_api_key[:8]}...")

        # 포트폴리오 현재 상태 가져오기
        logger.info("[CHAT] 📊 Fetching portfolio state...")
        portfolio_state = await portfolio.get_current_state()
        logger.info(f"[CHAT] ✅ Portfolio state retrieved: ${portfolio_state.get('total_value', 0):.2f} total, {portfolio_state.get('position_count', 0)} positions")

        # 시장 데이터 가져오기
        logger.info("[CHAT] 🌐 Fetching market data...")
        market_summary = await market_data.get_market_summary()
        logger.info(f"[CHAT] ✅ Market data retrieved: {len(market_summary.get('wsb_trending', []))} WSB stocks")

        # 사용자 투자 선호도 가져오기
        logger.info("[CHAT] 🎯 Loading user investment preferences...")
        from ..models import InvestmentPreference
        from sqlalchemy import select
        stmt = select(InvestmentPreference).limit(1)
        result = await services['db'].execute(stmt)
        user_prefs = result.scalar_one_or_none()
        logger.info(f"[CHAT] ✅ User preferences loaded: {user_prefs is not None}")

        # Gemini 설정
        logger.info("[CHAT] 🤖 Configuring Gemini API...")
        genai.configure(api_key=settings.gemini_api_key)

        # Use gemini-3-flash-preview (latest flash model) with Google Search enabled
        logger.info("[CHAT] 🎯 Initializing Gemini model: gemini-3-flash-preview with Google Search")
        model = genai.GenerativeModel(
            'gemini-3-flash-preview',
            tools='google_search_retrieval'  # Enable Google Search
        )

        # 컨텍스트 구성
        logger.info("[CHAT] 📝 Building context with portfolio and market data...")
        cash_balance = portfolio_state.get('cash_balance', 0)
        total_value = portfolio_state.get('total_value', 0)

        context = f"""
당신은 20년 경력의 전문 주식 트레이더이자 포트폴리오 매니저입니다.
사용자의 계좌를 관리하며, 매수/매도 결정, 리스크 관리, 자산 배분에 대한 전문적인 조언을 제공합니다.

## 현재 계좌 상태:
- **총 자산**: ${total_value:.2f}
- **현금 잔고 (매수 가능 자금)**: ${cash_balance:.2f}
- **일일 손익**: {portfolio_state.get('daily_pnl_pct', 0):.2f}%
- **총 손익**: {portfolio_state.get('total_pnl_pct', 0):.2f}%
- **보유 포지션 수**: {portfolio_state.get('position_count', 0)}개

## 보유 종목:
"""

        # 사용자 투자 선호도 추가
        if user_prefs:
            context += "\n\n## 사용자 투자 선호도 (전문 트레이더로서 반드시 고려):\n"

            # Risk and style
            risk_map = {'conservative': '보수적 (안전 중시)', 'moderate': '중립적 (균형)', 'aggressive': '공격적 (고위험 고수익)'}
            style_map = {'growth': '성장주', 'value': '가치주', 'dividend': '배당주', 'balanced': '균형'}
            context += f"- **위험 성향**: {risk_map.get(user_prefs.risk_appetite, user_prefs.risk_appetite)}\n"
            context += f"- **투자 스타일**: {style_map.get(user_prefs.investment_style, user_prefs.investment_style)}\n"

            # Sectors
            if user_prefs.preferred_sectors:
                context += f"- **선호 섹터**: {user_prefs.preferred_sectors}\n"
            if user_prefs.avoided_sectors:
                context += f"- **회피 섹터**: {user_prefs.avoided_sectors}\n"

            # Tickers
            if user_prefs.preferred_tickers:
                context += f"- **관심 종목**: {user_prefs.preferred_tickers}\n"
            if user_prefs.avoided_tickers:
                context += f"- **투자 제외 종목**: {user_prefs.avoided_tickers}\n"

            # Strategy preferences
            if user_prefs.prefer_diversification:
                context += "- **전략**: 분산투자 선호\n"
            if user_prefs.prefer_dip_buying:
                context += "- **전략**: 하락장 매수 선호 (저점 매수)\n"
            if user_prefs.prefer_momentum:
                context += "- **전략**: 모멘텀 투자 선호 (상승 추세)\n"

            # Trading behavior (NEW)
            if hasattr(user_prefs, 'prefer_day_trading') and user_prefs.prefer_day_trading:
                context += "- **매매 스타일**: 단타 (당일 매매)\n"
            if hasattr(user_prefs, 'prefer_swing_trading') and user_prefs.prefer_swing_trading:
                context += "- **매매 스타일**: 스윙 트레이딩 (수일~수주)\n"
            if hasattr(user_prefs, 'prefer_long_term') and user_prefs.prefer_long_term:
                context += "- **매매 스타일**: 장기 투자\n"

            # Price range (NEW)
            if hasattr(user_prefs, 'max_stock_price') and user_prefs.max_stock_price and user_prefs.max_stock_price > 0:
                context += f"- **가격대 선호**: ${user_prefs.max_stock_price:.2f} 이하\n"

            # Investment goal (NEW)
            if hasattr(user_prefs, 'investment_goal') and user_prefs.investment_goal:
                context += f"- **투자 목표**: {user_prefs.investment_goal}\n"

            # Target return (NEW)
            if hasattr(user_prefs, 'target_annual_return_pct') and user_prefs.target_annual_return_pct and user_prefs.target_annual_return_pct > 0:
                context += f"- **목표 수익률**: 연 {user_prefs.target_annual_return_pct:.1f}%\n"

            # Loss tolerance (NEW)
            if hasattr(user_prefs, 'max_acceptable_loss_pct') and user_prefs.max_acceptable_loss_pct:
                context += f"- **최대 허용 손실**: {user_prefs.max_acceptable_loss_pct:.1f}%\n"

            # Custom instructions
            if user_prefs.custom_instructions:
                context += f"\n**추가 투자 지침**:\n{user_prefs.custom_instructions}\n"

            context += "\n"

        context += """
"""

        # 보유 종목 정보 추가
        positions = portfolio_state.get('positions', [])
        if positions:
            logger.info(f"[CHAT] 📈 Adding {len(positions)} positions to context")
            for pos in positions:
                ticker = pos.get('ticker')
                quantity = pos.get('quantity', 0)
                avg_cost = pos.get('avg_cost', 0)
                current_price = pos.get('current_price', 0)
                pnl_pct = pos.get('unrealized_pnl_pct', 0)
                position_value = quantity * current_price

                context += f"""
- **{ticker}**: {quantity}주
  평단가: ${avg_cost:.2f} | 현재가: ${current_price:.2f}
  포지션 가치: ${position_value:.2f} | 손익률: {pnl_pct:+.2f}%
"""
        else:
            logger.info("[CHAT] 📭 No positions to add")
            context += "- 현재 보유 종목이 없습니다. 신규 투자 기회를 찾아주세요.\n"

        # 시장 데이터 추가
        context += f"\n\n{market_summary.get('summary_text', '')}\n"

        context += f"""

## 사용자 질문: {request.message}

## 전문 트레이더로서의 대응 방침:

### 🎯 핵심 원칙:
1. **현금 잔고 고려**: 매수 추천 시 현재 현금 ${cash_balance:.2f}로 실제 구매 가능한 종목만 제안
2. **현실적인 가격대**: 고가 종목(주가 $500 이상)은 현금이 충분하지 않으면 제외
3. **매수와 매도 균형**: 보유 종목이 있으면 매도/보유 검토도 함께 제안
4. **손절/익절 판단**: 보유 종목 중 -10% 이상 손실이나 +20% 이상 수익 달성 시 매도 고려
5. **리스크 관리**: 한 종목에 과도한 집중 투자 지양, 분산투자 강조

### 📊 정보 활용:
- **Reddit WSB 트렌딩**: 단기 모멘텀 파악
- **Yahoo Finance**: 실시간 가격 및 뉴스
- **Google 검색**: 최신 뉴스, 실적 발표, 산업 동향, 주가 전망 등을 적극 조사
- **사용자 선호도**: 위에 명시된 투자 선호도를 최우선으로 고려

### 💬 답변 스타일:
- 전문 트레이더답게 구체적이고 실전적인 조언 제공
- 매수/매도 추천 시 명확한 근거와 함께 제시
- 가격, 수량, 비중 등 구체적인 숫자 포함
- 리스크와 기회를 균형있게 설명
- 한국어로 친절하면서도 전문적으로 답변

### ⚠️ 면책:
답변 마지막에 반드시 "이는 참고용 분석이며, 최종 투자 결정은 본인의 책임입니다"를 포함하세요.

### 📝 학습 기능:
사용자의 메시지에서 투자 선호도, 관심 종목, 투자 스타일 등의 힌트를 파악하여 답변에 반영하고, 이러한 정보는 자동으로 저장됩니다.
"""
        logger.info(f"[CHAT] ✅ Context built ({len(context)} chars)")

        # Gemini API 호출 with timeout and retry
        import asyncio

        logger.info("[CHAT] 🚀 Calling Gemini API (timeout: 120s)...")
        try:
            # Run with 120 second timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, context),
                timeout=120.0
            )
            logger.info("[CHAT] ✅ Gemini API responded successfully")
        except asyncio.TimeoutError:
            logger.error("[CHAT] ⏱️ Gemini API timeout after 120 seconds")
            return ChatResponse(
                response="",
                error="AI 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
            )

        if not response or not response.text:
            logger.error("[CHAT] ❌ Empty response from Gemini API")
            return ChatResponse(
                response="",
                error="AI 응답을 생성하지 못했습니다. 다시 시도해주세요."
            )

        response_length = len(response.text)
        logger.info(f"[CHAT] 📤 Response generated ({response_length} chars)")

        # Extract and save investment preferences from conversation
        db = services['db']
        await _extract_and_save_preferences(request.message, response.text, db)

        logger.info(f"[CHAT] ✅ Chat request completed successfully")

        return ChatResponse(response=response.text)

    except Exception as e:
        error_msg = f"오류가 발생했습니다: {str(e)}"
        logger.error(f"[CHAT] 💥 Exception caught: {type(e).__name__}")
        logger.error(f"[CHAT] 💥 Error message: {str(e)}", exc_info=True)

        # Return proper JSON even on error
        try:
            logger.info("[CHAT] 🔄 Returning error response as ChatResponse")
            return ChatResponse(
                response="",
                error=error_msg
            )
        except Exception as json_error:
            logger.error(f"[CHAT] 💥 Failed to create ChatResponse: {json_error}")
            # Fallback to manual JSON
            from fastapi.responses import JSONResponse
            logger.info("[CHAT] 🔄 Falling back to manual JSONResponse")
            return JSONResponse(
                status_code=500,
                content={"response": "", "error": error_msg}
            )
