from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.review import Review, ReviewReaction, ReactionType
from app.models.user import User


async def recalculate_shop_score(shop_id: int, db: AsyncSession) -> float:
    result = await db.execute(
        select(Review.score, User.weight)
        .join(User, Review.user_id == User.id)
        .where(Review.shop_id == shop_id, Review.score.isnot(None), Review.parent_id.is_(None))
    )
    rows = result.all()
    if not rows:
        return 0.0
    total_weight = sum(w for _, w in rows)
    if total_weight == 0:
        return 0.0
    return sum(s * w for s, w in rows) / total_weight


async def recalculate_user_weight(user_id: int, db: AsyncSession) -> float:
    result = await db.execute(
        select(
            ReviewReaction.type,
            User.weight,
        )
        .join(Review, ReviewReaction.review_id == Review.id)
        .join(User, ReviewReaction.user_id == User.id)
        .where(Review.user_id == user_id)
    )
    rows = result.all()
    net = sum(w if t == ReactionType.like else -w for t, w in rows)
    # Clamp between 0.1 and 10.0
    return max(0.1, min(10.0, 1.0 + net / 10.0))
