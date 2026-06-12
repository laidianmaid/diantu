from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.shop import Shop
from app.schemas.ai import AiChatRequest, AiChatResponse, AiContextResponse
from app.services.ai_context import build_shop_context
from app.services import ollama as ollama_svc

router = APIRouter(prefix="/ai", tags=["ai"])


async def _get_shop_context(db: AsyncSession) -> str:
    result = await db.execute(select(Shop))
    shops = result.scalars().all()
    return build_shop_context(shops)


@router.get("/context", response_model=AiContextResponse)
async def ai_context(db: AsyncSession = Depends(get_db)):
    return AiContextResponse(shop_context=await _get_shop_context(db))


@router.post("/chat", response_model=AiChatResponse)
async def ai_chat(body: AiChatRequest, db: AsyncSession = Depends(get_db)):
    context = await _get_shop_context(db)
    reply, ids = await ollama_svc.chat(body.message, context)
    return AiChatResponse(reply=reply, highlighted_shop_ids=ids)
