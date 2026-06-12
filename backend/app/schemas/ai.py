from pydantic import BaseModel, Field


class AiCompletionMessage(BaseModel):
    role: str
    content: str


class AiCompletionRequest(BaseModel):
    messages: list[AiCompletionMessage]


class AiCompletionResponse(BaseModel):
    content: str


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


class AiApiFieldDoc(BaseModel):
    name: str
    type: str
    required: bool = False
    description: str
    enum: list[str] = []
    example: str | int | float | bool | None = None


class AiApiEndpointDoc(BaseModel):
    id: str
    method: str
    path: str
    tag: str
    summary: str
    description: str
    auth_required: bool
    side_effect: bool
    path_params: list[AiApiFieldDoc] = []
    query_params: list[AiApiFieldDoc] = []
    body_schema: dict | None = None
    response_shape: dict | list | str | None = None
    notes: list[str] = []
    ai_usage_examples: list[dict] = []


class AiApiDocsResponse(BaseModel):
    detail_level: str
    total: int
    endpoints: list[AiApiEndpointDoc]
