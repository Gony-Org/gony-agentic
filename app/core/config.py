import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PROJECT_NAME: str = "Gony Agentic"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    APP_PORT: int = 8001
    CRUD_API_URL: str

    # Infrastructure
    QDRANT_HOST: str
    QDRANT_PORT: int
    NATS_URL: str

    # PostgreSQL
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Gemini
    GEMINI_API_KEY: str
    GEMINI_MODEL: str

    # Anthropic
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str

    model_config = SettingsConfigDict(
        env_file=os.path.join(str(Path(__file__).resolve().parent.parent.parent), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
