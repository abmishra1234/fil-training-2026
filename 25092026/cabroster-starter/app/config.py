from datetime import time

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./cabroster.db"

    # JWT (Test Contract: these two names are fixed, algorithm must be HS256)
    JWT_SECRET_KEY: str = "dev-only-secret-change-me-in-dotenv-0123456789"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BCRYPT_ROUNDS: int = 12

    # Slot configuration (all times are IST)
    PICKUP_TIME: time = time(6, 30)
    DROP_TIME: time = time(16, 30)
    PICKUP_BOOKING_CUTOFF: time = time(21, 0)   # on the PREVIOUS day
    DROP_BOOKING_CUTOFF: time = time(14, 0)     # on the SAME day
    CANCEL_CUTOFF_MINUTES: int = 60             # before departure
    START_WINDOW_MINUTES: int = 30              # driver may start this long before departure
    BOOKING_HORIZON_DAYS: int = 7


settings = Settings()
