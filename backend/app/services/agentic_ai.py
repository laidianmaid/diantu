import json

from json_repair import repair_json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shop import Shop
from app.services import ollama as ollama_svc
from app.services.ai_tools import AGENT_TOOLS, ToolExecutionContext, execute_agent_tool

MAX_AGENT_TURNS = 10


def build_system_prompt() -> str:
    tools_json = json.dumps(AGENT_TOOLS, ensure_ascii=False, indent=2)
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
- 最终答案里的 highlighted_shop_ids 必须只包含真实店铺 ID。
- 如果用户问离自己最近，但工具返回 USER_LOCATION_REQUIRED，你应当直接给出最终答案，提示用户先点击定位；如果定位失败，请提示用户重试，并告诉用户也可以改问区域/地铁站。
- 如果地点搜索返回 PLACE_NOT_FOUND，也应直接给出最终答案，引导用户换更具体的地标、商圈或地铁站名称。
- 如果工具结果已经足够，请直接结束，不要无意义循环。
- 最多允许 {MAX_AGENT_TURNS} 轮模型决策。

可用工具：
{tools_json}
"""


def get_agent_config() -> dict:
    return {
        "system_prompt": build_system_prompt(),
        "tools": AGENT_TOOLS,
        "max_turns": MAX_AGENT_TURNS,
    }


def _repair_and_parse_json(raw_text: str) -> dict:
    repaired = repair_json(raw_text, ensure_ascii=False)
    parsed = json.loads(repaired)
    if not isinstance(parsed, dict):
        raise ValueError("MODEL_OUTPUT_NOT_OBJECT")
    return parsed


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


async def _normalize_final_answer(payload: dict, db: AsyncSession) -> dict:
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
) -> dict:
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": _build_initial_user_message(message, user_location)},
    ]
    context = ToolExecutionContext(user_location=user_location)

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
            return await _normalize_final_answer(model_output, db)

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
            tool_feedback = _build_tool_result_message(tool_name, True, result=result)
        except ValueError as exc:
            tool_feedback = _build_tool_result_message(tool_name, False, error=str(exc))

        messages.append({"role": "assistant", "content": raw_text})
        messages.append({"role": "user", "content": tool_feedback})

    return {
        "reply": "我暂时没能稳定完成这次检索，请换一种问法，或缩小范围后再试。",
        "highlighted_shop_ids": [],
    }
