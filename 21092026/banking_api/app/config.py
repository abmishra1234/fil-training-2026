from pydantic_settings import BaseSettings, SettingsConfigDict # type: ignore

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./bank.db"
    APP_NAME: str = "Personal Banking API"
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()
print(f"Starting {settings.APP_NAME}")


