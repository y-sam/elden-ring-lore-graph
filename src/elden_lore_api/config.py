from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)

    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "change-me-for-local-development"
    neo4j_database: str = "neo4j"
    editorial_token: str = Field(default="local-development-only", min_length=16)
    editorial_enabled: bool = True
    answer_generator: Literal["deterministic", "openai"] = "deterministic"
    openai_api_key: str | None = None
    openai_model: str = "gpt-6-astra"
    openai_timeout_seconds: float = Field(default=12.0, ge=1.0, le=60.0)
    openai_max_output_tokens: int = Field(default=600, ge=100, le=2000)
    answer_cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    answer_cache_max_entries: int = Field(default=500, ge=10, le=10000)
    answer_rate_limit_per_minute: int = Field(default=60, ge=1, le=10000)
    feedback_rate_limit_per_minute: int = Field(default=10, ge=1, le=1000)
    max_request_bytes: int = Field(default=16_384, ge=1024, le=1_048_576)

    @model_validator(mode="after")
    def production_secrets_must_be_explicit(self) -> "Settings":
        if self.app_env != "production":
            return self
        if self.neo4j_password == "change-me-for-local-development" or len(
            self.neo4j_password
        ) < 16:
            raise ValueError("production requires a strong NEO4J_PASSWORD")
        if self.editorial_token == "local-development-only" or len(
            self.editorial_token
        ) < 32:
            raise ValueError("production requires a random EDITORIAL_TOKEN")
        if self.answer_generator == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when ANSWER_GENERATOR=openai")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
