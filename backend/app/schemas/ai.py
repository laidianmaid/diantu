from pydantic import BaseModel


class AiChatRequest(BaseModel):
    message: str


class AiChatResponse(BaseModel):
    reply: str
    highlighted_shop_ids: list[int] = []
