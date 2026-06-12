from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.shop import Shop, ShopPhoto, ShopStatus
from app.models.user import User, UserRole
from app.models.social import Favorite, Checkin
from app.routers.deps import get_current_user, get_optional_user, require_admin
from app.schemas.shop import ShopCreate, ShopUpdate, ShopOut, ShopListOut
from app.services.markdown_import import parse_markdown_table
from app.services.geocoding import geocode_address

router = APIRouter(prefix="/shops", tags=["shops"])


def _shop_query(where=None):
    q = select(Shop).options(
        selectinload(Shop.photos),
        selectinload(Shop.checkins),
        selectinload(Shop.favorites),
    )
    if where is not None:
        q = q.where(where)
    return q


def _build_shop_out(shop: Shop, user: User | None = None) -> ShopOut:
    uid = user.id if user else None
    return ShopOut(
        id=shop.id,
        name=shop.name,
        color=shop.color,
        address=shop.address,
        lat=shop.lat,
        lng=shop.lng,
        description=shop.description,
        style=shop.style,
        type=shop.type,
        status=shop.status,
        hours=shop.hours,
        score=shop.score,
        owner_id=shop.owner_id,
        created_at=shop.created_at,
        photo_urls=[p.url for p in shop.photos],
        checkin_count=len(shop.checkins),
        favorite_count=len(shop.favorites),
        is_checked_in=any(c.user_id == uid for c in shop.checkins) if uid else False,
        is_favorited=any(f.user_id == uid for f in shop.favorites) if uid else False,
    )


@router.post("/admin/import/markdown", tags=["admin"])
async def import_markdown(
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    content = (await file.read()).decode("utf-8")
    parse = parse_markdown_table(content)

    # 串行地理编码：稳定优先，每条 200ms 间隔，QPS 超限自动退避重试
    # 220 条约 44 秒，导入一次性操作可以接受
    created, updated = 0, 0
    geocode_failed = []
    for row in parse.rows:
        result = await db.execute(select(Shop).where(Shop.name == row["name"]))
        shop = result.scalar_one_or_none()
        coords = await geocode_address(row["address"]) if row["address"] else None
        if coords is None and row["address"]:
            geocode_failed.append(row["name"])
        if shop:
            shop.color = row["color"]
            shop.address = row["address"]
            if coords:
                shop.lat, shop.lng = coords
            updated += 1
        else:
            shop = Shop(name=row["name"], color=row["color"], address=row["address"])
            if coords:
                shop.lat, shop.lng = coords
            db.add(shop)
            created += 1
    await db.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": len(parse.warnings),
        "total_parsed": len(parse.rows),
        "warnings": [str(w) for w in parse.warnings],
        "geocode_failed": geocode_failed,
    }


@router.get("", response_model=list[ShopListOut])
async def list_shops(
    color: str | None = Query(None),
    status: ShopStatus | None = Query(None),
    style: str | None = Query(None),
    limit: int | None = Query(None, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = select(Shop)
    if color:
        q = q.where(Shop.color == color)
    if status:
        q = q.where(Shop.status == status)
    if style:
        q = q.where(Shop.style == style)
    if limit is not None:
        q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=ShopOut, status_code=201)
async def create_shop(
    body: ShopCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    coords = await geocode_address(body.address)
    shop = Shop(**body.model_dump(), owner_id=user.id)
    if coords:
        shop.lat, shop.lng = coords
    db.add(shop)
    await db.commit()
    await db.refresh(shop)
    result = await db.execute(_shop_query(Shop.id == shop.id))
    return _build_shop_out(result.scalar_one())


@router.post("/{shop_id}/geocode", tags=["admin"])
async def retry_geocode(
    shop_id: int,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = result.scalar_one_or_none()
    if not shop:
        raise HTTPException(404, "Shop not found")
    if not shop.address:
        raise HTTPException(400, "Shop has no address")
    coords = await geocode_address(shop.address)
    if not coords:
        raise HTTPException(422, f"高德无法解析地址：{shop.address}")
    shop.lat, shop.lng = coords
    await db.commit()
    return {"lat": shop.lat, "lng": shop.lng}


@router.get("/{shop_id}", response_model=ShopOut)
async def get_shop(
    shop_id: int,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    result = await db.execute(_shop_query(Shop.id == shop_id))
    shop = result.scalar_one_or_none()
    if not shop:
        raise HTTPException(404, "Shop not found")
    return _build_shop_out(shop, user)


@router.patch("/{shop_id}", response_model=ShopOut)
async def update_shop(
    shop_id: int,
    body: ShopUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(_shop_query(Shop.id == shop_id))
    shop = result.scalar_one_or_none()
    if not shop:
        raise HTTPException(404, "Shop not found")
    if user.role not in (UserRole.superadmin, UserRole.admin) and shop.owner_id != user.id:
        raise HTTPException(403, "Forbidden")
    data = body.model_dump(exclude_none=True)
    if "address" in data:
        coords = await geocode_address(data["address"])
        if coords:
            shop.lat, shop.lng = coords
    for k, v in data.items():
        setattr(shop, k, v)
    await db.commit()
    result = await db.execute(_shop_query(Shop.id == shop_id))
    return _build_shop_out(result.scalar_one())


@router.delete("/{shop_id}", status_code=204)
async def delete_shop(
    shop_id: int,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = result.scalar_one_or_none()
    if not shop:
        raise HTTPException(404, "Shop not found")
    await db.delete(shop)
    await db.commit()


@router.post("/{shop_id}/favorite", status_code=200)
async def toggle_favorite(
    shop_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Favorite).where(Favorite.user_id == user.id, Favorite.shop_id == shop_id))
    fav = result.scalar_one_or_none()
    if fav:
        await db.delete(fav)
        await db.commit()
        return {"favorited": False}
    db.add(Favorite(user_id=user.id, shop_id=shop_id))
    await db.commit()
    return {"favorited": True}


@router.post("/{shop_id}/checkin", status_code=200)
async def toggle_checkin(
    shop_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Checkin).where(Checkin.user_id == user.id, Checkin.shop_id == shop_id))
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
        return {"checked_in": False}
    db.add(Checkin(user_id=user.id, shop_id=shop_id))
    await db.commit()
    return {"checked_in": True}
