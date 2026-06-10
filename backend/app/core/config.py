from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://diantu:diantu123@db:5432/diantu"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    amap_key: str = ""
    amap_js_key: str = ""

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "gemma3"

    telegram_bot_token: str = ""
    app_name: str = "来点妹抖吗？"
    frontend_url: str = "http://localhost:5173"


settings = Settings()
