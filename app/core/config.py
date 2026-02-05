import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Gony Agentic"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    NATS_URL: str = "nats://localhost:4222"

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
