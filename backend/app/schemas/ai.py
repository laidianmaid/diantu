from pydantic import BaseModel, Field


class AiLocation(BaseModel):
    lat: float
    lng: float


class AiChatRequest(BaseModel):
    message: str
    user_location: AiLocation | None = None


class AiChatResponse(BaseModel):
    reply: str
    highlighted_shop_ids: list[int] = []


class AiAgentConfigResponse(BaseModel):
    system_prompt: str
    tools: list[dict]
    max_turns: int


class AiToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    user_location: AiLocation | None = None


class AiToolExecuteResponse(BaseModel):
    tool_name: str
    ok: bool
    result: dict | list | None = None
    error: str | None = None
