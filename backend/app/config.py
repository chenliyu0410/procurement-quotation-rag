from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:55432/procurement_rag"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: float = 20.0
    llm_reasoning_effort: Literal["", "none", "minimal", "low", "medium", "high", "xhigh", "max"] = ""
    embedding_dimension: int = 1536
    embedding_provider: str = "openai"
    embedding_model: str = ""
    index_schema_version: str = "v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
