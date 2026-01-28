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
from ..config import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


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

    return {
        'settings': settings,
        'broker': broker,
        'portfolio': portfolio,
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

        # Gemini 설정
        logger.info("[CHAT] 🤖 Configuring Gemini API...")
        genai.configure(api_key=settings.gemini_api_key)

        # Use gemini-3-flash-preview (latest flash model)
        logger.info("[CHAT] 🎯 Initializing Gemini model: gemini-3-flash-preview")
        model = genai.GenerativeModel('gemini-3-flash-preview')

        # 컨텍스트 구성
        logger.info("[CHAT] 📝 Building context with portfolio data...")
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

        context += f"""

사용자 질문: {request.message}

위 포트폴리오 정보를 참고하여 사용자의 질문에 답변해주세요.
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
