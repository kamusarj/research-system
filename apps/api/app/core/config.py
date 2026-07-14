from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Research System API"
    database_url: str = "sqlite:///./research.db"
    api_cors_origins: str = "http://localhost:3000"
    ai_provider: str = "mock"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6-luna"
    deepseek_api_key: SecretStr | None = None
    deepseek_model: str = "deepseek-v4-pro"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = "openai/gpt-5.6-luna"
    mistral_api_key: SecretStr | None = None
    mistral_model: str = "mistral-large-latest"
    ai_request_timeout: float = 120
    intake_auto_approve_confidence: float = 0.85
    intake_max_content_bytes: int = 2_000_000
    intake_max_attempts: int = 3
    intake_retry_base_seconds: int = 30
    intake_worker_poll_seconds: float = 2
    intake_job_lease_seconds: int = 300
    graph_data_provider: str = "postgres"
    graph_default_node_limit: int = 40
    graph_max_node_limit: int = 100
    graph_max_edge_limit: int = 250
    graph_max_depth: int = 2
    graph_max_neighbors: int = 20
    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: SecretStr | None = None
    github_token: SecretStr | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
