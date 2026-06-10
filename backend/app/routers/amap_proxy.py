"""
高德地图安全代理。
前端配置 serviceHost 后，JS SDK 会将需要 jscode 的请求发到这里，
后端在转发时自动附加 jscode，jscode 不暴露给浏览器。
"""
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response
from app.core.config import settings

router = APIRouter(prefix="/_AMapService", tags=["amap-proxy"])

AMAP_API_BASE = "https://restapi.amap.com"


@router.api_route("/{path:path}", methods=["GET", "POST"])
async def amap_proxy(path: str, request: Request):
    params = dict(request.query_params)
    params["jscode"] = settings.amap_jscode

    url = f"{AMAP_API_BASE}/{path}"
    async with httpx.AsyncClient(timeout=10) as client:
        if request.method == "GET":
            resp = await client.get(url, params=params)
        else:
            body = await request.body()
            resp = await client.post(url, params=params, content=body,
                                     headers={"Content-Type": request.headers.get("content-type", "application/json")})

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )
