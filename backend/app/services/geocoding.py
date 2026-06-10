import httpx
from app.core.config import settings


async def geocode_address(address: str) -> tuple[float, float] | None:
    if not settings.amap_key:
        return None
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {"address": address, "key": settings.amap_key, "city": "上海"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    if data.get("status") == "1" and data.get("geocodes"):
        loc = data["geocodes"][0]["location"]
        lng_str, lat_str = loc.split(",")
        return float(lat_str), float(lng_str)
    return None
