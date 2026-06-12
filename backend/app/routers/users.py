from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import generate_api_key
from app.models.user import User
from app.models.shop import Shop
from app.models.social import Favorite, Checkin
from app.models.review import Review
from app.routers.deps import get_current_user
from app.schemas.user import (
    UserOut,
    ApiKeyOut,
    UserFavoriteShopOut,
    UserCheckinShopOut,
    UserReviewHistoryOut,
)

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


@router.get("/me/favorites", response_model=list[UserFavoriteShopOut], summary="列出当前用户收藏店铺")
async def my_favorites(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Favorite, Shop)
        .join(Shop, Shop.id == Favorite.shop_id)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc(), Favorite.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()
    return [
        UserFavoriteShopOut(
            shop_id=shop.id,
            shop_name=shop.name,
            address=shop.address,
            color=shop.color,
            style=shop.style,
            type=shop.type,
            status=shop.status,
            score=shop.score,
            lat=shop.lat,
            lng=shop.lng,
            favorited_at=favorite.created_at,
        )
        for favorite, shop in rows
    ]


@router.get("/me/checkins", response_model=list[UserCheckinShopOut], summary="列出当前用户打卡店铺")
async def my_checkins(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Checkin, Shop)
        .join(Shop, Shop.id == Checkin.shop_id)
        .where(Checkin.user_id == user.id)
        .order_by(Checkin.created_at.desc(), Checkin.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()
    return [
        UserCheckinShopOut(
            shop_id=shop.id,
            shop_name=shop.name,
            address=shop.address,
            color=shop.color,
            style=shop.style,
            type=shop.type,
            status=shop.status,
            score=shop.score,
            lat=shop.lat,
            lng=shop.lng,
            checked_in_at=checkin.created_at,
        )
        for checkin, shop in rows
    ]


@router.get("/me/reviews", response_model=list[UserReviewHistoryOut], summary="列出当前用户历史评论")
async def my_reviews(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Review, Shop)
        .join(Shop, Shop.id == Review.shop_id)
        .where(Review.user_id == user.id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()
    return [
        UserReviewHistoryOut(
            review_id=review.id,
            shop_id=shop.id,
            shop_name=shop.name,
            shop_color=shop.color,
            shop_style=shop.style,
            shop_type=shop.type,
            shop_status=shop.status,
            shop_score=shop.score,
            content=review.content,
            score=review.score,
            created_at=review.created_at,
        )
        for review, shop in rows
    ]
