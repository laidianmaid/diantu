from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.shop import Shop
from app.schemas.ai import AiChatRequest, AiChatResponse
from app.services import ollama as ollama_svc

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=AiChatResponse)
async def ai_chat(body: AiChatRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shop))
    shops = result.scalars().all()
    context = "\n".join(
        f"ID:{s.id} 名称:{s.name} 颜色:{s.color} 地址:{s.address} 状态:{s.status.value} 风格:{s.style or '未知'} 分数:{s.score:.1f}"
        for s in shops
    )
    reply, ids = await ollama_svc.chat(body.message, context)
    return AiChatResponse(reply=reply, highlighted_shop_ids=ids)
