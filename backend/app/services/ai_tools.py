from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shop import Shop
from app.models.user import User
from app.services.ai_api_catalog import call_available_api, get_available_api_docs
from app.services.geocoding import geocode_address

MAX_TOOL_LIMIT = 20

AGENT_TOOLS = [
    {
        "name": "get_top_shops",
        "description": "按评分返回前 N 家店，可按状态、颜色、风格过滤。",
        "arguments_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_TOOL_LIMIT},
                "status": {"type": "string"},
                "color": {"type": "string"},
                "style": {"type": "string"},
            },
        },
    },
    {
        "name": "get_nearest_to_self",
        "description": "根据用户当前位置返回最近的 N 家店。只有在用户明确问离自己最近时才调用。",
        "arguments_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_TOOL_LIMIT},
                "radius_m": {"type": "integer", "minimum": 1},
            },
        },
    },
    {
        "name": "get_nearby_shops_by_place",
        "description": "根据地点名称先解析地点，再返回附近的 N 家店。用户提到商圈、区域、地标、大学、景点或地铁站（如五角场、徐家汇、静安寺、人民广场）时，优先调用这个工具。",
        "arguments_schema": {
            "type": "object",
            "required": ["place_query"],
            "properties": {
                "place_query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_TOOL_LIMIT},
                "radius_m": {"type": "integer", "minimum": 1},
            },
        },
    },
    {
        "name": "search_shops_by_keywords",
        "description": "按名称、地址、风格、描述、类型做字符串搜索，适合根据用户喜好、店名片段、风格标签先粗召回候选店铺。不要把商圈、区域、地标、大学或地铁站名称优先当作这个工具的关键词；这类地点词优先用 get_nearby_shops_by_place。",
        "arguments_schema": {
            "type": "object",
            "required": ["keywords"],
            "properties": {
                "keywords": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ]
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_TOOL_LIMIT},
                "status": {"type": "string"},
                "color": {"type": "string"},
                "style": {"type": "string"},
            },
        },
    },
    {
        "name": "get_shop_details",
        "description": "按店铺 ID 拉取更完整详情，用于解释推荐理由或二次比较。",
        "arguments_schema": {
            "type": "object",
            "required": ["shop_ids"],
            "properties": {
                "shop_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 1,
                    "maxItems": MAX_TOOL_LIMIT,
                }
            },
        },
    },
    {
        "name": "get_available_api_docs",
        "description": "当现有专用工具不足时，按关键词、标签、方法或路径前缀获取当前用户可访问的 AI 专用 API 文档。优先先用 compact 文档缩小范围。",
        "arguments_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "tag": {"type": "string"},
                "method": {"type": "string"},
                "path_prefix": {"type": "string"},
                "detail_level": {"type": "string", "enum": ["compact", "full"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_TOOL_LIMIT},
            },
        },
    },
    {
        "name": "call_available_api",
        "description": "在当前用户登录态下调用 AI 专用文档中允许的只读 API。首版只允许 GET，并且 path 必须来自 get_available_api_docs 返回的文档。",
        "arguments_schema": {
            "type": "object",
            "required": ["method", "path"],
            "properties": {
                "method": {"type": "string", "enum": ["GET"]},
                "path": {"type": "string"},
                "query": {"type": "object"},
            },
        },
    },
]


@dataclass
class ToolExecutionContext:
    user_location: tuple[float, float] | None = None
    user: User | None = None
    access_token: str | None = None


def _clamp_limit(raw_limit, default: int = 5) -> int:
    try:
        limit = int(raw_limit or default)
    except (TypeError, ValueError):
        limit = default
    return max(1, min(MAX_TOOL_LIMIT, limit))


def _apply_common_filters(query, arguments: dict):
    if arguments.get("status"):
        query = query.where(Shop.status == arguments["status"])
    if arguments.get("color"):
        query = query.where(Shop.color == arguments["color"])
    if arguments.get("style"):
        query = query.where(Shop.style == arguments["style"])
    return query


def _shop_summary(shop: Shop, distance_m: float | None = None) -> dict:
    result = {
        "id": shop.id,
        "name": shop.name,
        "color": shop.color,
        "status": shop.status.value,
        "score": round(shop.score, 2),
        "address": shop.address,
        "style": shop.style,
        "type": shop.type,
    }
    if distance_m is not None:
        result["distance_m"] = round(distance_m, 1)
    return result


def _shop_detail(shop: Shop) -> dict:
    return {
        "id": shop.id,
        "name": shop.name,
        "color": shop.color,
        "status": shop.status.value,
        "score": round(shop.score, 2),
        "address": shop.address,
        "style": shop.style,
        "type": shop.type,
        "description": (shop.description or "")[:400],
        "hours": shop.hours,
        "lat": shop.lat,
        "lng": shop.lng,
    }


def _normalize_keywords(raw_keywords) -> list[str]:
    if isinstance(raw_keywords, list):
        keywords = [str(item).strip() for item in raw_keywords]
    else:
        keywords = [part.strip() for part in str(raw_keywords or "").replace("，", " ").split()]
    return [keyword for keyword in keywords if keyword]


def _distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_m = 6371000
    lat1_rad, lng1_rad = radians(lat1), radians(lng1)
    lat2_rad, lng2_rad = radians(lat2), radians(lng2)
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    hav = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng / 2) ** 2
    return 2 * radius_m * asin(sqrt(hav))


async def _get_nearby_shops(
    db: AsyncSession,
    lat: float,
    lng: float,
    limit: int,
    radius_m: float | None = None,
) -> list[dict]:
    result = await db.execute(
        select(Shop)
        .where(Shop.lat.is_not(None), Shop.lng.is_not(None))
        .order_by(Shop.score.desc(), Shop.id.asc())
    )
    shops = result.scalars().all()

    ranked = []
    for shop in shops:
        distance_m = _distance_meters(lat, lng, shop.lat, shop.lng)
        if radius_m and distance_m > radius_m:
            continue
        ranked.append((distance_m, shop))

    ranked.sort(key=lambda item: (item[0], -item[1].score, item[1].id))
    return [_shop_summary(shop, distance_m=distance) for distance, shop in ranked[:limit]]


async def _tool_get_top_shops(db: AsyncSession, arguments: dict) -> dict:
    limit = _clamp_limit(arguments.get("limit"), default=10)
    query = _apply_common_filters(select(Shop), arguments).order_by(Shop.score.desc(), Shop.id.asc()).limit(limit)
    result = await db.execute(query)
    shops = result.scalars().all()
    return {"shops": [_shop_summary(shop) for shop in shops]}


async def _tool_get_nearest_to_self(db: AsyncSession, arguments: dict, context: ToolExecutionContext) -> dict:
    if not context.user_location:
        raise ValueError("USER_LOCATION_REQUIRED")

    limit = _clamp_limit(arguments.get("limit"), default=5)
    radius_m = arguments.get("radius_m")
    lat, lng = context.user_location
    shops = await _get_nearby_shops(db, lat, lng, limit, radius_m)
    return {"shops": shops, "origin": {"lat": lat, "lng": lng}}


async def _tool_get_nearby_shops_by_place(db: AsyncSession, arguments: dict) -> dict:
    place_query = str(arguments.get("place_query") or "").strip()
    if not place_query:
        raise ValueError("PLACE_QUERY_REQUIRED")

    coords = await geocode_address(place_query)
    if not coords:
        raise ValueError("PLACE_NOT_FOUND")

    limit = _clamp_limit(arguments.get("limit"), default=5)
    radius_m = arguments.get("radius_m")
    lat, lng = coords
    shops = await _get_nearby_shops(db, lat, lng, limit, radius_m)
    return {
        "shops": shops,
        "origin": {"place_query": place_query, "lat": lat, "lng": lng},
    }


async def _tool_search_shops_by_keywords(db: AsyncSession, arguments: dict) -> dict:
    keywords = _normalize_keywords(arguments.get("keywords"))
    if not keywords:
        raise ValueError("KEYWORDS_REQUIRED")

    limit = _clamp_limit(arguments.get("limit"), default=8)
    query = _apply_common_filters(select(Shop), arguments)

    clauses = []
    for keyword in keywords:
        pattern = f"%{keyword}%"
        clauses.append(
            or_(
                Shop.name.ilike(pattern),
                Shop.address.ilike(pattern),
                Shop.style.ilike(pattern),
                Shop.description.ilike(pattern),
                Shop.type.ilike(pattern),
            )
        )

    for clause in clauses:
        query = query.where(clause)

    query = query.order_by(Shop.score.desc(), Shop.id.asc()).limit(limit)
    result = await db.execute(query)
    shops = result.scalars().all()
    return {"keywords": keywords, "shops": [_shop_summary(shop) for shop in shops]}


async def _tool_get_shop_details(db: AsyncSession, arguments: dict) -> dict:
    shop_ids = [int(shop_id) for shop_id in arguments.get("shop_ids", [])][:MAX_TOOL_LIMIT]
    if not shop_ids:
        raise ValueError("SHOP_IDS_REQUIRED")

    result = await db.execute(select(Shop).where(Shop.id.in_(shop_ids)))
    shops = {shop.id: shop for shop in result.scalars().all()}
    ordered = [shops[shop_id] for shop_id in shop_ids if shop_id in shops]
    return {"shops": [_shop_detail(shop) for shop in ordered]}


async def _tool_get_available_api_docs(arguments: dict, context: ToolExecutionContext) -> dict:
    return get_available_api_docs(
        context.user,
        keyword=str(arguments.get("keyword") or "").strip() or None,
        tag=str(arguments.get("tag") or "").strip() or None,
        method=str(arguments.get("method") or "").strip() or None,
        path_prefix=str(arguments.get("path_prefix") or "").strip() or None,
        detail_level=str(arguments.get("detail_level") or "compact").strip() or "compact",
        limit=arguments.get("limit"),
    )


async def _tool_call_available_api(arguments: dict, context: ToolExecutionContext) -> dict:
    return await call_available_api(
        user=context.user,
        access_token=context.access_token,
        method=str(arguments.get("method") or "").strip(),
        path=str(arguments.get("path") or "").strip(),
        query=arguments.get("query"),
        body=arguments.get("body"),
    )


async def execute_agent_tool(
    tool_name: str,
    arguments: dict,
    db: AsyncSession,
    context: ToolExecutionContext,
) -> dict:
    if tool_name == "get_top_shops":
        return await _tool_get_top_shops(db, arguments)
    if tool_name == "get_nearest_to_self":
        return await _tool_get_nearest_to_self(db, arguments, context)
    if tool_name == "get_nearby_shops_by_place":
        return await _tool_get_nearby_shops_by_place(db, arguments)
    if tool_name == "search_shops_by_keywords":
        return await _tool_search_shops_by_keywords(db, arguments)
    if tool_name == "get_shop_details":
        return await _tool_get_shop_details(db, arguments)
    if tool_name == "get_available_api_docs":
        return await _tool_get_available_api_docs(arguments, context)
    if tool_name == "call_available_api":
        return await _tool_call_available_api(arguments, context)

    raise ValueError("UNKNOWN_TOOL")
