from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Tên dịch vụ trong mạng Compose và địa chỉ loopback: trình duyệt của kẻ tấn công không thể khiến
# nạn nhân gửi các Host này qua một tên miền do chúng kiểm soát.
INTERNAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "api", "frontend"})


class Settings(BaseSettings):
    app_name: str = "API Hệ thống nghiên cứu"
    deployment_environment: Literal["local", "staging", "production"] = "local"
    secret_files_dir: str = "/run/secrets"
    database_url: str = "sqlite:///./research.db"
    database_pool_size: int = Field(default=5, ge=1, le=100)
    database_max_overflow: int = Field(default=5, ge=0, le=100)
    database_pool_timeout_seconds: float = Field(default=30, gt=0, le=300)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86_400)
    api_cors_origins: str = "http://localhost:3000"
    # Tên máy được chấp nhận ở header Host/X-Forwarded-Host, ngoài tên nội bộ và host của
    # API_CORS_ORIGINS. Danh sách phân cách bằng dấu phẩy; "*" tắt kiểm tra (không khuyến nghị).
    api_trusted_hosts: str = ""
    ai_provider: str = "mistral"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6-luna"
    graph_chat_default_provider: Literal[
        "openai", "deepseek", "claude_code", "codex", "antigravity"
    ] = "deepseek"
    chat_max_history_messages: int = 20
    # Ngân sách ký tự cho lịch sử gửi lại mỗi lượt; tin mới nhất luôn được giữ.
    chat_max_history_chars: int = Field(default=8_000, ge=1_000, le=200_000)
    chat_max_context_chars: int = 16_000
    chat_max_tool_loops: int = 4
    chat_max_proposals: int = 20
    chat_max_message_chars: int = 12_000
    chat_max_output_tokens: int = 1_500
    chat_redaction_enabled: bool = True
    chat_import_max_html_bytes: int = 2_000_000
    chat_import_max_messages: int = 400
    chat_import_max_images: int = 50
    chat_import_max_image_bytes: int = 10_000_000
    chat_import_max_total_image_bytes: int = 50_000_000
    chat_import_max_total_chars: int = 400_000
    chat_import_timeout_seconds: float = 20
    chat_import_max_redirects: int = 2
    chat_import_image_retries: int = 2
    chat_import_image_retry_backoff_seconds: float = 0.25
    graph_v2_enabled: bool = True
    graph_v2_documents_enabled: bool = True
    graph_v2_chat_enabled: bool = True
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_uploads_per_window: int = 10
    rate_limit_analysis_per_window: int = 10
    rate_limit_chat_per_window: int = 30
    rate_limit_apply_per_window: int = 10
    api_slow_request_ms: int = 2_000
    http_gzip_minimum_size: int = Field(default=1024, ge=256, le=1_000_000)
    http_gzip_compresslevel: int = Field(default=5, ge=1, le=9)
    log_format: str = "json"
    metrics_enabled: bool = False
    metrics_bearer_token: SecretStr | None = None
    auth_mode: Literal["disabled", "local"] = "disabled"
    auth_session_hours: int = 12
    auth_cookie_name: str = "research_session"
    auth_csrf_cookie_name: str = "research_csrf"
    auth_cookie_secure: bool = True
    auth_cookie_samesite: Literal["lax", "strict"] = "lax"
    auth_login_attempts_per_window: int = 5
    deepseek_api_key: SecretStr | None = None
    deepseek_model: str = "deepseek-v4-pro"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = "openai/gpt-5.6-luna"
    mistral_api_key: SecretStr | None = None
    mistral_model: str = "mistral-large-latest"
    ai_request_timeout: float = 120
    # Trần token đầu ra cho tác vụ JSON có cấu trúc (chống tiêu thụ không giới hạn).
    ai_max_output_tokens: int = Field(default=8192, ge=256, le=65536)
    # Cầu nối trên máy chủ chạy Claude Code/Codex/Antigravity bằng gói đăng nhập của chủ máy
    # (`app/ai_cli_bridge.py`). Để trống URL là tắt ba nhà cung cấp này.
    ai_cli_bridge_url: str = ""
    ai_cli_bridge_token: SecretStr | None = None
    ai_cli_timeout_seconds: float = Field(default=300, ge=10, le=900)
    claude_code_model: str = "sonnet"
    claude_code_effort: Literal["low", "medium", "high", "xhigh", "max"] | None = "low"
    codex_model: str = "gpt-6-luna"
    codex_effort: Literal["low", "medium", "high", "xhigh", "max"] | None = "low"
    antigravity_model: str = "gemini-3.8-flash-medium"
    intake_auto_approve_confidence: float = 0.85
    # Tự duyệt chỉ khi nguồn thuộc các tên miền này (và tên miền con); rỗng = không giới hạn.
    # Nội dung có dấu hiệu prompt injection không bao giờ được tự duyệt.
    intake_auto_approve_domains: str = ""
    intake_max_content_bytes: int = 2_000_000
    intake_max_pdf_bytes: int = 25_000_000
    intake_request_timeout_seconds: float = 20
    intake_request_retries: int = 2
    intake_request_backoff_seconds: float = 0.25
    intake_max_redirects: int = 5
    intake_user_agent: str = ""
    # Politeness toward the sites being collected. Off by default for robots.txt so an
    # existing deployment's behaviour does not change silently on upgrade.
    intake_host_min_interval_seconds: float = 1.0
    intake_respect_robots: bool = False
    # Reuse an unchanged page instead of downloading it again on retry.
    intake_conditional_get: bool = True
    intake_accept_language: str = "vi,en-US;q=0.9,en;q=0.8"
    # Per-host request header overrides, keyed by hostname without a leading "www.".
    intake_host_headers: dict[str, dict[str, str]] = {}
    intake_pdf_max_pages: int = 80
    intake_max_attempts: int = 3
    intake_retry_base_seconds: int = 30
    intake_worker_poll_seconds: float = 2
    intake_worker_max_backoff_seconds: float = 60
    intake_job_lease_seconds: int = 300
    browser_render_enabled: bool = False
    browserless_ws_url: str = "ws://browserless:3000"
    browserless_token: SecretStr | None = None
    browser_render_timeout_seconds: float = 20
    browser_render_wait_ms: int = 500
    browser_render_max_bytes: int = 2_000_000
    ocr_enabled: bool = False
    ocr_command: str = "tesseract"
    ocr_languages: str = "eng+vie"
    ocr_dpi: int = 200
    ocr_max_pixels: int = 20_000_000
    ocr_max_pages: int = 20
    ocr_timeout_seconds: float = 30
    ocr_min_chars: int = 40
    ocr_max_output_chars: int = 120_000
    document_storage_backend: str = "local"
    document_storage_dir: str = "/var/tmp/research-system/objects"
    document_max_upload_bytes: int = 20_000_000
    minio_endpoint: str = "minio:9000"
    minio_access_key: SecretStr | None = None
    minio_secret_key: SecretStr | None = None
    minio_secure: bool = True
    minio_bucket: str = "research-documents"
    minio_region: str | None = None
    minio_auto_create_bucket: bool = False
    minio_spool_memory_bytes: int = 8_388_608
    document_worker_max_attempts: int = 3
    document_worker_retry_base_seconds: int = 30
    document_worker_lease_seconds: int = 600
    document_extract_max_chars: int = 120_000
    document_graph_max_nodes: int = 80
    document_graph_max_edges: int = 120
    latex_compiler_command: str = "xelatex"
    latex_compile_timeout_seconds: float = 20
    latex_compile_max_source_chars: int = 200_000
    latex_compile_max_pdf_bytes: int = 10_000_000
    graph_data_provider: str = "postgres"
    graph_default_node_limit: int = 40
    # The browser may render the complete current local corpus, while the explicit ceiling keeps
    # accidental/untrusted requests bounded. Cursor/tile loading is required before this is raised.
    graph_max_node_limit: int = 1000
    graph_max_edge_limit: int = 4000
    graph_max_depth: int = 2
    graph_max_neighbors: int = 20
    graph_max_path_hops: int = 12
    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: SecretStr | None = None
    neo4j_database: str = "neo4j"
    neo4j_batch_size: int = 500
    neo4j_connection_timeout_seconds: float = 5
    neo4j_retry_timeout_seconds: float = 15
    search_data_provider: Literal["postgres", "meilisearch"] = "postgres"
    vector_data_provider: Literal["postgres", "pgvector"] = "postgres"
    meilisearch_url: str | None = None
    meilisearch_api_key: SecretStr | None = None
    meilisearch_index: str = "research_items"
    meilisearch_batch_size: int = 500
    meilisearch_request_timeout_seconds: float = 10
    meilisearch_task_timeout_seconds: float = 60
    search_embedding_provider: Literal["mistral", "gemini"] = "mistral"
    search_embedding_model: str = "mistral-embed"
    search_embedding_dimensions: int = 1024
    search_embedding_chunk_chars: int = 4_000
    search_embedding_chunk_overlap_chars: int = 200
    search_embedding_chunk_min_chars: int = 100
    search_embedding_max_chunks_per_item: int = 32
    search_embedding_batch_size: int = 32
    search_embedding_request_retries: int = 2
    search_embedding_retry_backoff_seconds: float = 0.5
    search_document_max_chars: int = 120_000
    search_max_results: int = 100
    search_hybrid_enabled: bool = False
    search_mmr_lambda: float = 0.5
    search_semantic_max_distance: float = 0.7
    chat_document_scope_top_k_passages: int = 6
    chat_document_scope_passage_chars: int = 1_500
    github_token: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def load_secret_files_and_validate_deployment(self) -> "Settings":
        secret_fields = (
            "database_url",
            "openai_api_key",
            "deepseek_api_key",
            "gemini_api_key",
            "openrouter_api_key",
            "mistral_api_key",
            "ai_cli_bridge_token",
            "minio_access_key",
            "minio_secret_key",
            "neo4j_password",
            "meilisearch_api_key",
            "github_token",
            "metrics_bearer_token",
            "browserless_token",
        )
        secret_root = Path(self.secret_files_dir)
        for field_name in secret_fields:
            path = secret_root / field_name
            if not path.is_file():
                continue
            value = path.read_text(encoding="utf-8")
            if len(value) > 16_384:
                raise ValueError(f"Secret file {field_name} exceeds 16 KiB")
            value = value.rstrip("\r\n")
            if not value:
                continue
            if field_name == "database_url":
                self.database_url = value
            else:
                setattr(self, field_name, SecretStr(value))

        if self.deployment_environment != "local":
            if self.auth_mode != "local":
                raise ValueError("Staging/production requires AUTH_MODE=local")
            if not self.auth_cookie_secure:
                raise ValueError("Staging/production requires AUTH_COOKIE_SECURE=true")
            if not self.auth_cookie_name.startswith("__Host-"):
                raise ValueError("Staging/production requires an __Host- session cookie")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]

    @property
    def auto_approve_domains(self) -> set[str]:
        return {
            domain.strip().lower().lstrip(".")
            for domain in self.intake_auto_approve_domains.split(",")
            if domain.strip()
        }

    @property
    def trusted_hosts(self) -> set[str] | None:
        """None nghĩa là tắt kiểm tra host."""
        extra = {host.strip().lower() for host in self.api_trusted_hosts.split(",") if host.strip()}
        if "*" in extra:
            return None
        origin_hosts = {urlsplit(origin).hostname or "" for origin in self.cors_origins}
        return (INTERNAL_HOSTS | extra | origin_hosts) - {""}

    @property
    def metrics_secret(self) -> str | None:
        if self.metrics_bearer_token is None:
            return None
        value = self.metrics_bearer_token.get_secret_value().strip()
        return value or None

    @property
    def auth_enabled(self) -> bool:
        return self.auth_mode == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
