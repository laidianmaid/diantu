from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import generate_api_key
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.user import UserOut, ApiKeyOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.post("/me/apikey", response_model=ApiKeyOut)
async def generate_key(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user.api_key = generate_api_key()
    await db.commit()
    await db.refresh(user)
    return ApiKeyOut(api_key=user.api_key)
