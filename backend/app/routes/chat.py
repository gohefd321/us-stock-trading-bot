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

        # Extract risk appetite
        if any(word in user_lower for word in ['안전', '보수적', '위험 회피', 'conservative', 'safe']):
            prefs.risk_appetite = 'conservative'
            changed = True
        elif any(word in user_lower for word in ['공격적', '고위험', 'aggressive', 'high risk']):
            prefs.risk_appetite = 'aggressive'
            changed = True
        elif any(word in user_lower for word in ['중립', '보통', 'moderate', 'balanced']):
            prefs.risk_appetite = 'moderate'
            changed = True

        # Extract investment style
        if any(word in user_lower for word in ['성장주', 'growth', '그로스']):
            prefs.investment_style = 'growth'
            changed = True
        elif any(word in user_lower for word in ['가치주', 'value', '밸류']):
            prefs.investment_style = 'value'
            changed = True
        elif any(word in user_lower for word in ['배당주', 'dividend']):
            prefs.investment_style = 'dividend'
            changed = True

        # Extract sector preferences
        sector_map = {
            '기술주': 'technology', '테크': 'technology', 'tech': 'technology',
            '헬스케어': 'healthcare', '의료': 'healthcare', '제약': 'healthcare',
            '금융': 'finance', 'bank': 'finance',
            '에너지': 'energy',
            '소비재': 'consumer', '리테일': 'consumer'
        }

        for keyword, sector in sector_map.items():
            if keyword in user_lower:
                if '싫어' in user_lower or '피하' in user_lower or 'avoid' in user_lower:
                    # Add to avoided sectors
                    avoided = set(prefs.avoided_sectors.split(',')) if prefs.avoided_sectors else set()
                    avoided.add(sector)
                    prefs.avoided_sectors = ','.join(filter(None, avoided))
                    changed = True
                elif '좋아' in user_lower or '관심' in user_lower or 'prefer' in user_lower or 'like' in user_lower:
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
                if '싫어' in user_lower or '피하' in user_lower or 'avoid' in user_lower:
                    avoided_tickers = set(prefs.avoided_tickers.split(',')) if prefs.avoided_tickers else set()
                    avoided_tickers.add(ticker)
                    prefs.avoided_tickers = ','.join(filter(None, avoided_tickers))
                    changed = True
                elif '좋아' in user_lower or '추천' in user_lower or 'buy' in user_lower or 'prefer' in user_lower:
                    preferred_tickers = set(prefs.preferred_tickers.split(',')) if prefs.preferred_tickers else set()
                    preferred_tickers.add(ticker)
                    prefs.preferred_tickers = ','.join(filter(None, preferred_tickers))
                    changed = True

        # Extract trading strategy preferences
        if '분산' in user_lower or 'diversif' in user_lower:
            prefs.prefer_diversification = True
            changed = True

        if '하락' in user_lower and ('매수' in user_lower or 'buy' in user_lower):
            prefs.prefer_dip_buying = True
            changed = True

        if '모멘텀' in user_lower or 'momentum' in user_lower:
            prefs.prefer_momentum = True
            changed = True

        # Save custom instructions
        if '조건' in user_lower or '전략' in user_lower or 'strategy' in user_lower:
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

        # Gemini 설정
        logger.info("[CHAT] 🤖 Configuring Gemini API...")
        genai.configure(api_key=settings.gemini_api_key)

        # Use gemini-3-flash-preview (latest flash model)
        logger.info("[CHAT] 🎯 Initializing Gemini model: gemini-3-flash-preview")
        model = genai.GenerativeModel('gemini-3-flash-preview')

        # 컨텍스트 구성
        logger.info("[CHAT] 📝 Building context with portfolio and market data...")
        context = f"""
당신은 미국 주식 투자 분석 전문가입니다. 사용자의 포트폴리오를 분석하고 투자 조언을 제공합니다.

현재 포트폴리오 상태:
- 총 자산: ${portfolio_state.get('total_value', 0):.2f}
- 현금 잔고: ${portfolio_state.get('cash_balance', 0):.2f}
- 일일 손익: {portfolio_state.get('daily_pnl_pct', 0):.2f}%
- 총 손익: {portfolio_state.get('total_pnl_pct', 0):.2f}%
- 보유 포지션 수: {portfolio_state.get('position_count', 0)}개

보유 종목:
"""

        # 보유 종목 정보 추가
        positions = portfolio_state.get('positions', [])
        if positions:
            logger.info(f"[CHAT] 📈 Adding {len(positions)} positions to context")
            for pos in positions:
                context += f"""
- {pos.get('ticker')}: {pos.get('quantity')}주
  평단가: ${pos.get('avg_cost', 0):.2f}
  현재가: ${pos.get('current_price', 0):.2f}
  손익률: {pos.get('unrealized_pnl_pct', 0):.2f}%
"""
        else:
            logger.info("[CHAT] 📭 No positions to add")
            context += "- 보유 중인 종목이 없습니다.\n"

        # 시장 데이터 추가
        context += f"\n\n{market_summary.get('summary_text', '')}\n"

        context += f"""

사용자 질문: {request.message}

위 포트폴리오 정보와 시장 동향을 참고하여 사용자의 질문에 답변해주세요.
- Reddit WSB에서 트렌딩 중인 종목 정보를 활용하세요
- Yahoo Finance의 실시간 가격 및 뉴스 정보를 참고하세요
- 사용자가 특정 종목에 대해 물어보면 해당 종목의 현재 상황을 설명해주세요

답변은 친절하고 이해하기 쉽게, 한국어로 작성해주세요.
투자 조언을 할 때는 반드시 "이는 참고용이며 투자 결정은 본인의 책임입니다"라는 경고를 포함해주세요.
"""
        logger.info(f"[CHAT] ✅ Context built ({len(context)} chars)")

        # Gemini API 호출 with timeout and retry
        import asyncio

        logger.info("[CHAT] 🚀 Calling Gemini API (timeout: 30s)...")
        try:
            # Run with 30 second timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, context),
                timeout=30.0
            )
            logger.info("[CHAT] ✅ Gemini API responded successfully")
        except asyncio.TimeoutError:
            logger.error("[CHAT] ⏱️ Gemini API timeout after 30 seconds")
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
