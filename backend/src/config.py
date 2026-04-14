# backend/src/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://stream:stream@localhost:5432/stream"
    redis_url: str = "redis://localhost:6379/0"
    newsapi_key: str = ""
    gnews_api_key: str = ""

    test_mode: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
