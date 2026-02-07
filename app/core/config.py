import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PROJECT_NAME: str = "Gony Agentic"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    APP_PORT: int = 8001

    # Infrastructure
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    NATS_URL: str = "nats://localhost:4222"

    # PostgreSQL
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "crud"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3-pro-preview"

    model_config = SettingsConfigDict(
        env_file=os.path.join(str(Path(__file__).resolve().parent.parent.parent), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
