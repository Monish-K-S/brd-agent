import json
from functools import lru_cache
from typing import Annotated

from pydantic import ValidationInfo, field_validator
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    SettingsConfigDict,
)


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
    google_drive_redirect_uri: str

    token_encryption_key: str

    oauth_state_secret: str

    database_url: str

    max_upload_files: int = 10
    max_upload_bytes: int = 10 * 1024 * 1024
    max_extracted_chars: int = 500_000
    max_pdf_pages: int = 200

    # Total character budget across every source in a workspace when they
    # are concatenated into the single project PDF handed to Sarvam.
    # Per-document caps alone leave this aggregate unbounded (N docs x
    # 500k chars), so the extraction service truncates the tail to fit.
    max_aggregate_chars: int = 1_000_000

    generation_job_timeout_minutes: int = 15

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
    rate_limit_drive_connect: str = "10/hour"
    rate_limit_drive_callback: str = "20/minute"
    rate_limit_drive_picker_token: str = "30/minute"
    rate_limit_drive_import: str = "20/hour"

    allowed_hosts: Annotated[list[str], NoDecode] = ["*"]
    expose_db_health: bool = False

    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173"
    ]

    @field_validator("allowed_hosts", "cors_origins", mode="before")
    @classmethod
    def _parse_host_list(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        defaults = {
            "allowed_hosts": ["*"],
            "cors_origins": ["http://localhost:5173"],
        }

        if value is None or (
            isinstance(value, str) and not value.strip()
        ):
            return defaults[info.field_name]

        if isinstance(value, str):
            stripped = value.strip()

            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)

                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass

            items = [
                item.strip()
                for item in stripped.split(",")
                if item.strip()
            ]

            return items or defaults[info.field_name]

        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
