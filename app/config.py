from pathlib import Path
from typing import Annotated
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    BOT_TOKEN: str = "000000000:TEST_TOKEN_FOR_CI"
    ADMIN_IDS: Annotated[list[int], NoDecode] = Field(default_factory=list)

    DATABASE_URL: str = "postgresql+asyncpg://pdfuser:StrongPassword123!@postgres:5432/pdfbot"
    REDIS_URL: str = "redis://redis:6379/0"

    TEMP_DIR: Path = Path("/tmp/pdf_converter")
    FONTS_DIR: Path = Path("/usr/share/fonts/truetype/dejavu")

    MAX_FILE_SIZE_MB: int = 40
    MAX_IMAGE_COUNT: int = 50
    MAX_PDF_MERGE_COUNT: int = 15
    MAX_PDF_PAGES: int = 500
    MAX_IMAGE_DIMENSION: int = 8000
    MAX_CONCURRENT_JOBS_PER_USER: int = 2
    MAX_QUEUE_SIZE: int = 200
    CONVERSION_TIMEOUT_SECONDS: int = 90
    RATE_LIMIT_CALLS_PER_MINUTE: int = 20

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            v = v.strip().strip("[]")
            if not v:
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)