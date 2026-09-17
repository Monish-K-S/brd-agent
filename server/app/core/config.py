from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BRD Agent API"
    app_version: str = "0.1.0"

    environment: str = "development"

    frontend_url: str

    supabase_url: str
    supabase_publishable_key: str
    supabase_service_role_key: str | None = None

    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    database_url: str

    max_upload_files: int = 10
    max_upload_bytes: int = 10 * 1024 * 1024
    max_extracted_chars: int = 500_000
    max_pdf_pages: int = 200

    rate_limit_enabled: bool = True
    rate_limit_brd_generate: str = "5/hour"
    rate_limit_consolidate: str = "10/hour"
    rate_limit_extract: str = "10/hour"
    rate_limit_brd_ask: str = "30/minute"
    rate_limit_brd_export: str = "20/hour"
    rate_limit_upload: str = "30/hour"
    rate_limit_gmail_search: str = "30/minute"
    rate_limit_gmail_recent: str = "30/minute"
    rate_limit_gmail_import: str = "20/hour"
    rate_limit_gmail_connect: str = "10/hour"
    rate_limit_gmail_callback: str = "20/minute"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
