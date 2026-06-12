from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.review import Review, ReviewReaction, ReactionType
from app.models.shop import Shop
from app.models.user import User, UserRole
from app.routers.deps import get_current_user
from app.schemas.review import ReviewCreate, ReviewOut, ReactionCreate
from app.services.scoring import recalculate_shop_score, recalculate_user_weight

router = APIRouter(tags=["reviews"])


def _review_out(r: Review) -> ReviewOut:
    likes = sum(1 for rx in r.reactions if rx.type == ReactionType.like)
    dislikes = sum(1 for rx in r.reactions if rx.type == ReactionType.dislike)
    return ReviewOut(
        id=r.id,
        shop_id=r.shop_id,
        user_id=r.user_id,
        username=r.user.username if r.user else "",
        content=r.content,
        score=r.score,
        platform=r.platform,
        parent_id=r.parent_id,
        created_at=r.created_at,
        likes=likes,
        dislikes=dislikes,
        replies=[_review_out(rep) for rep in (r.replies or []) if rep.parent_id == r.id],
    )


@router.get("/shops/{shop_id}/reviews", response_model=list[ReviewOut])
async def list_reviews(
    shop_id: int,
    limit: int | None = Query(None, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Review)
        .where(Review.shop_id == shop_id, Review.parent_id.is_(None))
        .order_by(Review.created_at.desc())
    )
    if limit is not None:
        query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    reviews = result.scalars().all()
    # Eagerly load relations
    for r in reviews:
        await db.refresh(r, ["user", "reactions", "replies"])
    return [_review_out(r) for r in reviews]


@router.post("/shops/{shop_id}/reviews", response_model=ReviewOut, status_code=201)
async def create_review(
    shop_id: int,
    body: ReviewCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shop_result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = shop_result.scalar_one_or_none()
    if not shop:
        raise HTTPException(404, "Shop not found")
    review = Review(
        shop_id=shop_id,
        user_id=user.id,
        content=body.content,
        score=body.score,
        parent_id=body.parent_id,
    )
    db.add(review)
    await db.flush()
    if body.score is not None and body.parent_id is None:
        shop.score = await recalculate_shop_score(shop_id, db)
    await db.commit()
    await db.refresh(review, ["user", "reactions", "replies"])
    return _review_out(review)


@router.delete("/reviews/{review_id}", status_code=204)
async def delete_review(
    review_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")
    if user.role not in (UserRole.superadmin, UserRole.admin) and review.user_id != user.id:
        raise HTTPException(403, "Forbidden")
    await db.delete(review)
    await db.commit()


@router.post("/reviews/{review_id}/reactions", status_code=200)
async def react_to_review(
    review_id: int,
    body: ReactionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")

    existing = await db.execute(
        select(ReviewReaction).where(
            ReviewReaction.review_id == review_id,
            ReviewReaction.user_id == user.id,
        )
    )
    rx = existing.scalar_one_or_none()
    if rx:
        if rx.type == body.type:
            await db.delete(rx)
            await db.commit()
            return {"action": "removed"}
        rx.type = body.type
    else:
        db.add(ReviewReaction(review_id=review_id, user_id=user.id, type=body.type))

    await db.flush()
    new_weight = await recalculate_user_weight(review.user_id, db)
    author_result = await db.execute(select(User).where(User.id == review.user_id))
    author = author_result.scalar_one_or_none()
    if author:
        author.weight = new_weight
    await db.commit()
    return {"action": "set", "type": body.type}
