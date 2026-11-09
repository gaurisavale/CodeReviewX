"""Application settings, read from environment variables (prefix CODEREVIEWX_) or a .env file."""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CODEREVIEWX_", env_file=".env", extra="ignore")

    app_name: str = "CodeReviewX API"
    version: str = "3.0.0"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./codereviewx.db"
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:3100", "http://127.0.0.1:3000"])

    # ingestion limits
    max_code_kb: int = 512            # one pasted file
    max_zip_mb: int = 20              # uploaded archive
    max_unzipped_mb: int = 60         # zip-bomb guard
    max_files: int = 150              # files analysed per project run
    max_file_kb: int = 300            # larger files are skipped, not failed
    git_timeout_s: int = 60           # shallow clone time limit
    include_tests: bool = False       # analyse test files in project scans

    # scoring
    use_learned_weights: bool = False  # swap hand-set factor weights for the data-calibrated ones


@lru_cache
def get_settings() -> Settings:
    return Settings()
