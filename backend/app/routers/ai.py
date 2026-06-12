from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.routers.deps import (
    AuthContext,
    get_optional_auth_context,
    rate_limit_ai_chat,
    rate_limit_ai_config,
    rate_limit_ai_tools,
)
from app.schemas.ai import (
    AiApiDocsResponse,
    AiAgentConfigResponse,
    AiChatRequest,
    AiChatResponse,
    AiToolExecuteRequest,
    AiToolExecuteResponse,
)
from app.services.agentic_ai import get_agent_config, run_agentic_loop
from app.services.ai_api_catalog import get_available_api_docs
from app.services.ai_tools import ToolExecutionContext, execute_agent_tool

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/agent/config", response_model=AiAgentConfigResponse)
async def ai_agent_config(
    _: None = Depends(rate_limit_ai_config),
    auth: AuthContext = Depends(get_optional_auth_context),
):
    return AiAgentConfigResponse(**get_agent_config(auth.user))


@router.get("/api-docs", response_model=AiApiDocsResponse)
async def ai_api_docs(
    keyword: str | None = Query(None),
    tag: str | None = Query(None),
    method: str | None = Query(None),
    path_prefix: str | None = Query(None),
    detail_level: str = Query("compact", pattern="^(compact|full)$"),
    limit: int = Query(10, ge=1, le=20),
    _: None = Depends(rate_limit_ai_config),
    auth: AuthContext = Depends(get_optional_auth_context),
):
    return AiApiDocsResponse(
        **get_available_api_docs(
            auth.user,
            keyword=keyword,
            tag=tag,
            method=method,
            path_prefix=path_prefix,
            detail_level=detail_level,
            limit=limit,
        )
    )


@router.post("/tools/execute", response_model=AiToolExecuteResponse)
async def ai_tools_execute(
    body: AiToolExecuteRequest,
    _: None = Depends(rate_limit_ai_tools),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_optional_auth_context),
):
    user_location = None
    if body.user_location:
        user_location = (body.user_location.lat, body.user_location.lng)

    try:
        result = await execute_agent_tool(
            body.tool_name,
            body.arguments,
            db,
            ToolExecutionContext(user_location=user_location, user=auth.user, access_token=auth.access_token),
        )
        return AiToolExecuteResponse(tool_name=body.tool_name, ok=True, result=result)
    except ValueError as exc:
        return AiToolExecuteResponse(tool_name=body.tool_name, ok=False, error=str(exc))


@router.post("/chat", response_model=AiChatResponse)
async def ai_chat(
    body: AiChatRequest,
    _: None = Depends(rate_limit_ai_chat),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_optional_auth_context),
):
    user_location = None
    if body.user_location:
        user_location = (body.user_location.lat, body.user_location.lng)

    result = await run_agentic_loop(body.message, db, user_location=user_location, user=auth.user, access_token=auth.access_token)
    return AiChatResponse(**result)
