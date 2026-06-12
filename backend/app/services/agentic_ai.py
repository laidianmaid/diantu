import json

from json_repair import repair_json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shop import Shop
from app.models.user import User
from app.services import ollama as ollama_svc
from app.services.ai_tools import AGENT_TOOLS, ToolExecutionContext, execute_agent_tool

MAX_AGENT_TURNS = 10


def build_system_prompt(user: User | None = None) -> str:
    tools_json = json.dumps(AGENT_TOOLS, ensure_ascii=False, indent=2)
    auth_note = "当前用户已登录，可在必要时获取用户态 API 文档并调用允许的只读 API。" if user else "当前用户未登录，只能使用公开能力；任何需要登录态的 API 都不可用。"
    return f"""你是「来点妹抖吗？」地图助手。

你必须只输出一个 JSON 对象，不要输出 markdown，不要输出解释，不要输出额外文本。

你有两种合法输出：

1. 请求工具：
{{
  "type": "tool_call",
  "tool_name": "search_shops_by_keywords",
  "arguments": {{"keywords": ["安静", "甜品"], "limit": 5}}
}}

2. 返回最终答案：
{{
  "type": "final_answer",
  "reply": "给用户看的自然语言回答",
  "highlighted_shop_ids": [1, 2, 3]
}}

规则：
- 需要店铺数据时，优先调用工具，不要编造店铺信息。
- 最终答案里的 highlighted_shop_ids 必须只包含真实店铺 ID，只要有推荐就填入。
- {auth_note}
- 如果用户提到商圈、区域、地标、大学、景点或地铁站附近/一带/周边的店（例如“五角场”“徐家汇”“静安寺”“长宁路（长宁）”“人民广场（人广）”），优先调用 get_nearby_shops_by_place，不要先把这些地点词直接拿去做 search_shops_by_keywords。
- search_shops_by_keywords 更适合风格、偏好、店名片段、地址片段等字符串召回；它不是地点附近检索的首选工具。
- 优先使用现有专用工具（附近、关键词、详情、top shops）。只有当这些工具不足以回答用户问题时，才调用 get_available_api_docs。
- 如果决定走 API 路线，先调用 get_available_api_docs 缩小到相关接口，再调用 call_available_api；不要在没拿到文档时盲调 API。
- call_available_api 首版只允许只读 API；不要尝试任何写操作。
- 如果某个工具返回空 shops，但用户的问题仍然可能通过别的相关工具回答，不要立刻下结论说没有；先尝试另一种合理工具。
- 如果用户问离自己最近，但工具返回 USER_LOCATION_REQUIRED，你应当直接给出最终答案，提示用户先点击定位；如果定位失败，请提示用户重试，并告诉用户也可以改问区域/地铁站。
- 如果地点搜索返回 PLACE_NOT_FOUND，尝试搜索地点别名。
- 如果工具结果已经足够，请直接返回最终答案，不要无意义循环。

示例：
- 用户说“推荐几家人广的女仆店”时，应优先调用：
  {{"type":"tool_call","tool_name":"get_nearby_shops_by_place","arguments":{{"place_query":"人民广场","limit":5}}}}
- 用户说“我喜欢安静一点、适合聊天的店”时，更适合先调用：
  {{"type":"tool_call","tool_name":"search_shops_by_keywords","arguments":{{"keywords":["安静","聊天"],"limit":8}}}}
- 用户说“我收藏过哪些店”而现有专用工具无法回答时，应先调用：
  {{"type":"tool_call","tool_name":"get_available_api_docs","arguments":{{"keyword":"收藏","tag":"users","detail_level":"compact","limit":5}}}}

可用工具：
{tools_json}
"""


def get_agent_config(user: User | None = None) -> dict:
    return {
        "system_prompt": build_system_prompt(user),
        "tools": AGENT_TOOLS,
        "max_turns": MAX_AGENT_TURNS,
    }


def _repair_and_parse_json(raw_text: str) -> dict:
    repaired = repair_json(raw_text, ensure_ascii=False)
    parsed = json.loads(repaired)
    if not isinstance(parsed, dict):
        raise ValueError("MODEL_OUTPUT_NOT_OBJECT")
    return parsed


def _extract_shop_ids_from_payload(payload, *, limit: int = 10) -> list[int]:
    if limit <= 0:
        return []

    results = []
    seen = set()

    def push(raw_id):
        try:
            shop_id = int(raw_id)
        except (TypeError, ValueError):
            return
        if shop_id <= 0 or shop_id in seen:
            return
        seen.add(shop_id)
        results.append(shop_id)

    def walk(value):
        if len(results) >= limit or value is None:
            return
        if isinstance(value, dict):
            if "id" in value:
                push(value["id"])
            if "shop_id" in value:
                push(value["shop_id"])
            for key in ("shops", "data", "items", "results"):
                if key in value:
                    walk(value[key])
        elif isinstance(value, list):
            for item in value:
                if len(results) >= limit:
                    break
                walk(item)

    walk(payload)
    return results


def _derive_highlighted_ids_from_tool_history(tool_history: list[dict]) -> list[int]:
    for tool_result in reversed(tool_history):
        extracted = _extract_shop_ids_from_payload(tool_result)
        if extracted:
            return extracted
    return []


async def _validate_highlighted_ids(db: AsyncSession, highlighted_ids: list[int]) -> list[int]:
    if not highlighted_ids:
        return []

    result = await db.execute(select(Shop.id).where(Shop.id.in_(highlighted_ids)))
    valid_ids = {shop_id for shop_id in result.scalars().all()}

    ordered_ids = []
    seen = set()
    for shop_id in highlighted_ids:
        if shop_id in valid_ids and shop_id not in seen:
            ordered_ids.append(shop_id)
            seen.add(shop_id)
    return ordered_ids


async def _normalize_final_answer(
    payload: dict,
    db: AsyncSession,
    fallback_highlighted_ids: list[int] | None = None,
) -> dict:
    reply = str(payload.get("reply") or "").strip()
    if not reply:
        raise ValueError("FINAL_REPLY_REQUIRED")

    highlighted_ids = payload.get("highlighted_shop_ids") or []
    if not isinstance(highlighted_ids, list):
        highlighted_ids = []

    normalized_ids = []
    for shop_id in highlighted_ids:
        try:
            normalized_ids.append(int(shop_id))
        except (TypeError, ValueError):
            continue

    if not normalized_ids:
        normalized_ids = [int(shop_id) for shop_id in (fallback_highlighted_ids or [])]

    return {
        "reply": reply,
        "highlighted_shop_ids": await _validate_highlighted_ids(db, normalized_ids),
    }


def _build_initial_user_message(message: str, user_location: tuple[float, float] | None) -> str:
    payload = {
        "type": "user_request",
        "message": message,
        "user_location": (
            {"lat": user_location[0], "lng": user_location[1]} if user_location else None
        ),
    }
    return json.dumps(payload, ensure_ascii=False)


def _build_tool_result_message(tool_name: str, ok: bool, result=None, error: str | None = None) -> str:
    payload = {
        "type": "tool_result",
        "tool_name": tool_name,
        "ok": ok,
        "result": result,
        "error": error,
    }
    return json.dumps(payload, ensure_ascii=False)


async def run_agentic_loop(
    message: str,
    db: AsyncSession,
    user_location: tuple[float, float] | None = None,
    user: User | None = None,
    access_token: str | None = None,
) -> dict:
    messages = [
        {"role": "system", "content": build_system_prompt(user)},
        {"role": "user", "content": _build_initial_user_message(message, user_location)},
    ]
    context = ToolExecutionContext(user_location=user_location, user=user, access_token=access_token)
    successful_tool_history = []

    for _ in range(MAX_AGENT_TURNS):
        raw_text = await ollama_svc.chat(messages)

        try:
            model_output = _repair_and_parse_json(raw_text)
        except Exception:
            messages.append({"role": "assistant", "content": raw_text})
            messages.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "type": "format_error",
                            "message": "请只返回一个合法 JSON 对象，且只能是 tool_call 或 final_answer。",
                        },
                        ensure_ascii=False,
                    ),
                }
            )
            continue

        output_type = model_output.get("type")
        if output_type == "final_answer":
            return await _normalize_final_answer(
                model_output,
                db,
                fallback_highlighted_ids=_derive_highlighted_ids_from_tool_history(successful_tool_history),
            )

        if output_type != "tool_call":
            messages.append({"role": "assistant", "content": raw_text})
            messages.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "type": "format_error",
                            "message": "type 字段必须是 tool_call 或 final_answer。",
                        },
                        ensure_ascii=False,
                    ),
                }
            )
            continue

        tool_name = str(model_output.get("tool_name") or "").strip()
        arguments = model_output.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {}

        try:
            result = await execute_agent_tool(tool_name, arguments, db, context)
            successful_tool_history.append(result)
            tool_feedback = _build_tool_result_message(tool_name, True, result=result)
        except ValueError as exc:
            tool_feedback = _build_tool_result_message(tool_name, False, error=str(exc))

        messages.append({"role": "assistant", "content": raw_text})
        messages.append({"role": "user", "content": tool_feedback})

    return {
        "reply": "我暂时没能稳定完成这次检索，请换一种问法，或缩小范围后再试。",
        "highlighted_shop_ids": [],
    }
