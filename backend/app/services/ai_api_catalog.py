import re
from copy import deepcopy

import httpx

from app.models.user import User

MAX_API_DOC_LIMIT = 20


def _param(
    name: str,
    type_: str,
    description: str,
    *,
    required: bool = False,
    enum: list[str] | None = None,
    example=None,
):
    return {
        "name": name,
        "type": type_,
        "required": required,
        "description": description,
        "enum": enum or [],
        "example": example,
    }


AI_API_CATALOG = [
    {
        "id": "users.me",
        "method": "GET",
        "path": "/api/v1/users/me",
        "tag": "users",
        "summary": "获取当前登录用户资料",
        "description": "返回当前登录用户自己的基础账号信息，包括角色、权重、头像和创建时间。",
        "auth_required": True,
        "ai_callable": True,
        "side_effect": False,
        "visibility": "authenticated",
        "path_params": [],
        "query_params": [],
        "body_schema": None,
        "response_shape": {
            "id": "integer",
            "username": "string",
            "email": "string",
            "role": "string",
            "weight": "number",
            "avatar_url": "string|null",
            "created_at": "datetime",
        },
        "notes": [
            "适合确认当前用户身份、角色和基础画像。",
            "不返回密码、token 或其他敏感认证信息。",
        ],
        "ai_usage_examples": [
            {"question": "我是谁", "request": {"method": "GET", "path": "/api/v1/users/me"}},
        ],
    },
    {
        "id": "users.me.favorites",
        "method": "GET",
        "path": "/api/v1/users/me/favorites",
        "tag": "users",
        "summary": "列出当前用户收藏的店铺",
        "description": "分页返回当前登录用户收藏过的店铺摘要，适合回答“我收藏过哪些店”或为偏好分析提供候选样本。",
        "auth_required": True,
        "ai_callable": True,
        "side_effect": False,
        "visibility": "authenticated",
        "path_params": [],
        "query_params": [
            _param("limit", "integer", "返回条数，1-50，默认 20。", example=20),
            _param("offset", "integer", "分页偏移量，默认 0。", example=0),
        ],
        "body_schema": None,
        "response_shape": [
            {
                "shop_id": "integer",
                "shop_name": "string",
                "address": "string",
                "color": "string",
                "style": "string|null",
                "type": "string|null",
                "status": "string",
                "score": "number",
                "lat": "number|null",
                "lng": "number|null",
                "favorited_at": "datetime",
            }
        ],
        "notes": [
            "结果按收藏时间倒序返回，最近收藏优先。",
            "如果需要更完整店铺信息，再结合 /api/v1/shops/{shop_id} 使用。",
        ],
        "ai_usage_examples": [
            {
                "question": "我收藏过哪些店",
                "request": {"method": "GET", "path": "/api/v1/users/me/favorites", "query": {"limit": 10}},
            },
        ],
    },
    {
        "id": "users.me.checkins",
        "method": "GET",
        "path": "/api/v1/users/me/checkins",
        "tag": "users",
        "summary": "列出当前用户打卡过的店铺",
        "description": "分页返回当前登录用户打卡过的店铺摘要，适合回答“我去过哪些店”或分析活动区域偏好。",
        "auth_required": True,
        "ai_callable": True,
        "side_effect": False,
        "visibility": "authenticated",
        "path_params": [],
        "query_params": [
            _param("limit", "integer", "返回条数，1-50，默认 20。", example=20),
            _param("offset", "integer", "分页偏移量，默认 0。", example=0),
        ],
        "body_schema": None,
        "response_shape": [
            {
                "shop_id": "integer",
                "shop_name": "string",
                "address": "string",
                "color": "string",
                "style": "string|null",
                "type": "string|null",
                "status": "string",
                "score": "number",
                "lat": "number|null",
                "lng": "number|null",
                "checked_in_at": "datetime",
            }
        ],
        "notes": [
            "结果按打卡时间倒序返回，最近打卡优先。",
            "适合判断用户常去区域、消费轨迹和复访偏好。",
        ],
        "ai_usage_examples": [
            {
                "question": "我最近打卡过哪些店",
                "request": {"method": "GET", "path": "/api/v1/users/me/checkins", "query": {"limit": 10}},
            },
        ],
    },
    {
        "id": "users.me.reviews",
        "method": "GET",
        "path": "/api/v1/users/me/reviews",
        "tag": "users",
        "summary": "列出当前用户写过的评论",
        "description": "分页返回当前登录用户写过的评论及对应店铺摘要，适合分析口味、偏好和常见评价维度。",
        "auth_required": True,
        "ai_callable": True,
        "side_effect": False,
        "visibility": "authenticated",
        "path_params": [],
        "query_params": [
            _param("limit", "integer", "返回条数，1-50，默认 20。", example=20),
            _param("offset", "integer", "分页偏移量，默认 0。", example=0),
        ],
        "body_schema": None,
        "response_shape": [
            {
                "review_id": "integer",
                "shop_id": "integer",
                "shop_name": "string",
                "shop_color": "string",
                "shop_style": "string|null",
                "shop_type": "string|null",
                "shop_status": "string",
                "shop_score": "number",
                "content": "string",
                "score": "number|null",
                "created_at": "datetime",
            }
        ],
        "notes": [
            "结果按评论时间倒序返回，优先看最新评论。",
            "评论内容适合做偏好总结，但不要把单条评论过度泛化成绝对结论。",
        ],
        "ai_usage_examples": [
            {
                "question": "根据我以前的评论分析我喜欢什么店",
                "request": {"method": "GET", "path": "/api/v1/users/me/reviews", "query": {"limit": 20}},
            },
        ],
    },
    {
        "id": "shops.list",
        "method": "GET",
        "path": "/api/v1/shops",
        "tag": "shops",
        "summary": "列出店铺地图摘要",
        "description": "返回店铺列表摘要，适合地图展示和轻量筛选。若需要单店更多字段，再调用详情接口。",
        "auth_required": False,
        "ai_callable": True,
        "side_effect": False,
        "visibility": "public",
        "path_params": [],
        "query_params": [
            _param("color", "string", "按 canonical color 过滤。", enum=["sagegreen", "olivedrab", "seagreen", "salmon", "hotpink"]),
            _param("status", "string", "按 canonical status 过滤。", enum=["open", "closed", "preparing", "shutdown"]),
            _param("style", "string", "按风格字符串过滤。"),
            _param("limit", "integer", "返回条数，1-100；为空时返回所有匹配结果。", example=20),
            _param("offset", "integer", "分页偏移量，默认 0。", example=0),
        ],
        "body_schema": None,
        "response_shape": [
            {
                "id": "integer",
                "name": "string",
                "color": "string",
                "lat": "number|null",
                "lng": "number|null",
                "status": "string",
                "score": "number",
            }
        ],
        "notes": [
            "这是轻量列表接口，不包含地址、描述、收藏/打卡标记等详情字段。",
            "如果问题只需要地图层摘要，可优先用它；否则更推荐现有专用 AI 工具。",
        ],
        "ai_usage_examples": [
            {
                "question": "给我看营业中的纯荤店",
                "request": {"method": "GET", "path": "/api/v1/shops", "query": {"status": "open", "color": "hotpink", "limit": 20}},
            },
        ],
    },
    {
        "id": "shops.detail",
        "method": "GET",
        "path": "/api/v1/shops/{shop_id}",
        "tag": "shops",
        "summary": "获取单个店铺详情",
        "description": "返回单个店铺的完整详情，包括地址、描述、照片、收藏/打卡统计，以及当前用户是否已收藏/打卡。",
        "auth_required": False,
        "ai_callable": True,
        "side_effect": False,
        "visibility": "public",
        "path_params": [
            _param("shop_id", "integer", "店铺 ID。", required=True, example=1),
        ],
        "query_params": [],
        "body_schema": None,
        "response_shape": {
            "id": "integer",
            "name": "string",
            "address": "string",
            "description": "string|null",
            "style": "string|null",
            "type": "string|null",
            "status": "string",
            "hours": "object|null",
            "score": "number",
            "photo_urls": ["string"],
            "favorite_count": "integer",
            "checkin_count": "integer",
            "is_favorited": "boolean",
            "is_checked_in": "boolean",
        },
        "notes": [
            "如果用户已登录，结果会带当前用户维度的 is_favorited / is_checked_in。",
            "适合在已知 shop_id 后补充推荐理由。",
        ],
        "ai_usage_examples": [
            {
                "question": "我想看这家店的详情",
                "request": {"method": "GET", "path": "/api/v1/shops/12"},
            },
        ],
    },
    {
        "id": "reviews.list",
        "method": "GET",
        "path": "/api/v1/shops/{shop_id}/reviews",
        "tag": "reviews",
        "summary": "列出某店的评论",
        "description": "分页返回某家店的顶层评论及其回复，适合分析口碑和用户评价维度。",
        "auth_required": False,
        "ai_callable": True,
        "side_effect": False,
        "visibility": "public",
        "path_params": [
            _param("shop_id", "integer", "店铺 ID。", required=True, example=1),
        ],
        "query_params": [
            _param("limit", "integer", "返回条数，1-100；为空时返回全部。", example=20),
            _param("offset", "integer", "分页偏移量，默认 0。", example=0),
        ],
        "body_schema": None,
        "response_shape": [
            {
                "id": "integer",
                "shop_id": "integer",
                "user_id": "integer",
                "username": "string",
                "content": "string",
                "score": "number|null",
                "parent_id": "integer|null",
                "created_at": "datetime",
                "likes": "integer",
                "dislikes": "integer",
                "replies": ["ReviewOut"],
            }
        ],
        "notes": [
            "只返回顶层评论，replies 字段中会嵌套对应回复。",
            "适合解释店铺口碑，但文本可能较长，调用时建议配合 limit。",
        ],
        "ai_usage_examples": [
            {
                "question": "这家店的评论怎么样",
                "request": {"method": "GET", "path": "/api/v1/shops/12/reviews", "query": {"limit": 10}},
            },
        ],
    },
]


def _can_view(entry: dict, user: User | None) -> bool:
    if entry["visibility"] == "public":
        return True
    return user is not None


def _limit(value, default=10):
    try:
        size = int(value or default)
    except (TypeError, ValueError):
        size = default
    return max(1, min(MAX_API_DOC_LIMIT, size))


def _string_matches(entry: dict, keyword: str) -> bool:
    haystacks = [
        entry["id"],
        entry["method"],
        entry["path"],
        entry["tag"],
        entry["summary"],
        entry["description"],
        *entry.get("notes", []),
    ]
    return any(keyword in str(item).lower() for item in haystacks)


def _serialize_entry(entry: dict, detail_level: str) -> dict:
    data = deepcopy(entry)
    data.pop("visibility", None)
    data.pop("ai_callable", None)

    if detail_level == "compact":
        data["notes"] = data.get("notes", [])[:2]
        data["ai_usage_examples"] = data.get("ai_usage_examples", [])[:1]
    return data


def get_available_api_docs(
    user: User | None,
    *,
    keyword: str | None = None,
    tag: str | None = None,
    method: str | None = None,
    path_prefix: str | None = None,
    detail_level: str = "compact",
    limit: int | None = None,
) -> dict:
    filtered = [entry for entry in AI_API_CATALOG if _can_view(entry, user)]

    if keyword:
        keyword_lower = keyword.strip().lower()
        filtered = [entry for entry in filtered if _string_matches(entry, keyword_lower)]
    if tag:
        filtered = [entry for entry in filtered if entry["tag"] == tag]
    if method:
        filtered = [entry for entry in filtered if entry["method"] == method.upper()]
    if path_prefix:
        filtered = [entry for entry in filtered if entry["path"].startswith(path_prefix)]

    limited = filtered[: _limit(limit, default=10)]
    return {
        "detail_level": detail_level,
        "total": len(filtered),
        "endpoints": [_serialize_entry(entry, detail_level) for entry in limited],
    }


def _compile_path_pattern(path_template: str) -> re.Pattern:
    pattern = re.sub(r"\{([^}]+)\}", r"(?P<\1>[^/]+)", path_template)
    return re.compile(f"^{pattern}$")


def _coerce_value(param: dict, raw_value):
    param_type = param["type"]
    value = raw_value
    if param_type == "integer":
        value = int(raw_value)
    elif param_type == "number":
        value = float(raw_value)
    elif param_type == "boolean":
        if isinstance(raw_value, bool):
            value = raw_value
        elif str(raw_value).lower() in ("true", "1", "yes"):
            value = True
        elif str(raw_value).lower() in ("false", "0", "no"):
            value = False
        else:
            raise ValueError(f"INVALID_BOOLEAN:{param['name']}")
    else:
        value = str(raw_value)

    enum_values = param.get("enum") or []
    if enum_values and str(value) not in enum_values:
        raise ValueError(f"INVALID_ENUM:{param['name']}")
    return value


def _validate_query(entry: dict, query: dict | None) -> dict:
    query = query or {}
    if not isinstance(query, dict):
        raise ValueError("API_QUERY_MUST_BE_OBJECT")

    allowed = {param["name"]: param for param in entry.get("query_params", [])}
    unknown = [key for key in query if key not in allowed]
    if unknown:
        raise ValueError("API_QUERY_PARAM_NOT_ALLOWED")

    validated = {}
    for name, param in allowed.items():
        if name not in query:
            if param.get("required"):
                raise ValueError(f"MISSING_QUERY_PARAM:{name}")
            continue
        validated[name] = _coerce_value(param, query[name])
    return validated


def _match_api_entry(method: str, path: str, user: User | None) -> tuple[dict, dict]:
    for entry in AI_API_CATALOG:
        if not entry["ai_callable"] or not _can_view(entry, user):
            continue
        if entry["method"] != method:
            continue
        match = _compile_path_pattern(entry["path"]).match(path)
        if not match:
            continue
        path_params = {}
        for param in entry.get("path_params", []):
            raw_value = match.group(param["name"])
            path_params[param["name"]] = _coerce_value(param, raw_value)
        return entry, path_params
    raise ValueError("API_NOT_ALLOWED")


def _trim_response_payload(payload, *, max_items: int = 20, max_str_len: int = 500):
    if isinstance(payload, str):
        return payload[:max_str_len]
    if isinstance(payload, list):
        return [_trim_response_payload(item, max_items=max_items, max_str_len=max_str_len) for item in payload[:max_items]]
    if isinstance(payload, dict):
        return {key: _trim_response_payload(value, max_items=max_items, max_str_len=max_str_len) for key, value in payload.items()}
    return payload


async def call_available_api(
    *,
    user: User | None,
    access_token: str | None,
    method: str,
    path: str,
    query: dict | None = None,
    body: dict | None = None,
) -> dict:
    normalized_method = str(method or "").upper()
    if normalized_method != "GET":
        raise ValueError("READ_ONLY_API_ONLY")

    entry, _ = _match_api_entry(normalized_method, path, user)
    if entry["auth_required"] and not access_token:
        raise ValueError("AUTH_REQUIRED")
    if body:
        raise ValueError("READ_ONLY_API_BODY_NOT_ALLOWED")

    validated_query = _validate_query(entry, query)

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    async with httpx.AsyncClient(transport=transport, base_url="http://app") as client:
        response = await client.request(normalized_method, path, params=validated_query, headers=headers)

    if response.status_code >= 400:
        detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        return {
            "ok": False,
            "status_code": response.status_code,
            "method": normalized_method,
            "path": path,
            "error": detail,
        }

    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
    return {
        "ok": True,
        "status_code": response.status_code,
        "method": normalized_method,
        "path": path,
        "data": _trim_response_payload(data),
    }
