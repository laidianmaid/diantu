import json
import re
import httpx
from app.core.config import settings


SYSTEM_PROMPT = """你是「来点妹抖吗？」地图助手，帮助用户发现上海妹抖店。
你可以根据用户需求推荐女仆店，或帮助筛选。
如果你要高亮地图上的女仆店，请在回复末尾添加 JSON 块：
```highlight
{"shop_ids": [1, 2, 3]}
```
否则不要输出 highlight 块。"""


async def chat(message: str, shop_context: str = "") -> tuple[str, list[int]]:
    prompt = message
    if shop_context:
        prompt = f"当前地图上的女仆店信息：\n{shop_context}\n\n用户问题：{message}"

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        data = resp.json()

    reply_full = data.get("message", {}).get("content", "")

    highlighted_ids = []
    highlight_match = re.search(r"```highlight\s*(\{.*?\})\s*```", reply_full, re.DOTALL)
    if highlight_match:
        try:
            highlighted_ids = json.loads(highlight_match.group(1)).get("shop_ids", [])
        except Exception:
            pass
        reply_full = reply_full[:highlight_match.start()].strip()

    return reply_full, highlighted_ids
