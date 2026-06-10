import asyncio
import httpx
from app.core.config import settings

# 串行导入模式：每次请求后固定 sleep，QPS ≤ 5，彻底避免限速
_SLEEP_BETWEEN = 0.2  # 200ms，QPS=5，远低于高德免费版上限
_MAX_RETRIES = 5


async def geocode_address(address: str) -> tuple[float, float] | None:
    if not settings.amap_key or not address:
        return None
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {"address": address, "key": settings.amap_key, "city": "上海"}

    for attempt in range(_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                data = resp.json()

            if data.get("status") == "1" and data.get("geocodes"):
                loc = data["geocodes"][0]["location"]
                lng_str, lat_str = loc.split(",")
                await asyncio.sleep(_SLEEP_BETWEEN)
                return float(lat_str), float(lng_str)

            # QPS 超限，指数退避
            if data.get("infocode") in ("10003", "10044"):
                wait = 2.0 ** attempt
                await asyncio.sleep(wait)
                continue

            # 地址真的查不到
            await asyncio.sleep(_SLEEP_BETWEEN)
            return None

        except Exception:
            await asyncio.sleep(1.0 * (attempt + 1))

    return None
