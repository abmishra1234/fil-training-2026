from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./bank.db"
    APP_NAME: str = "Personal Banking API"

    # ---- Extension 6: JWT settings ----
    # No default on purpose: the app must refuse to start without a real secret.
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "bank_api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    # Bootstrap admin (optional). Created once at startup if it does not exist.
    ADMIN_USERNAME: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()
print(f"Starting {settings.APP_NAME}")
