from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Read backend/.env regardless of the command's working directory."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )
    tmdb_read_access_token: SecretStr = SecretStr("")
    environment: Literal["development", "test"] = "development"
    db_host: str = Field(default="127.0.0.1", min_length=1)
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = Field(min_length=1)
    db_user: str = Field(min_length=1)
    db_password: SecretStr = Field(min_length=1)
    cors_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://127.0.0.1:4173",
    ])

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, values: list[str]) -> list[str]:
        cleaned = []
        for value in values:
            try:
                url = urlsplit(value)
                valid = (
                    url.scheme in {"http", "https"} and url.hostname
                    and url.username is None and url.password is None
                    and url.path in {"", "/"} and not url.query and not url.fragment
                    and "*" not in value
                )
                _ = url.port  # Invalid port syntax must fail validation too.
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("CORS origins must be explicit http(s) origins without paths or wildcards")
            cleaned.append(value.rstrip("/"))
        return list(dict.fromkeys(cleaned))

    def database_url(self) -> URL:
        # URL.create correctly escapes passwords; callers never concatenate a DSN.
        return URL.create(
            "postgresql+psycopg", username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host, port=self.db_port, database=self.db_name,
        )
