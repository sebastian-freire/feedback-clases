from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# El .env vive en la raíz del monorepo; las variables de entorno reales tienen prioridad.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    database_url: str
    test_database_url: str | None = None
    jwt_secret: str = Field(min_length=32)
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173"
    app_timezone: str = "America/Montevideo"
    feedback_window_days: int = Field(default=7, ge=0)
    seed_user_password: str = "demo1234"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
