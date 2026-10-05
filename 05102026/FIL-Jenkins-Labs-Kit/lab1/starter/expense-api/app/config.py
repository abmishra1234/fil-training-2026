"""A02 Security Misconfiguration: all configuration comes from the environment,
defaults are secure, and the app refuses to start with unsafe values."""
import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    app_env: str
    port: int
    jwt_secret: str
    jwt_issuer: str
    token_ttl_seconds: int
    cors_allowed_origins: tuple
    login_rate_limit_per_minute: int
    seed_file: Path
    max_body_bytes: int = 16 * 1024
    lockout_threshold: int = 5
    lockout_seconds: int = 15 * 60

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


def _int(env, name, default, lo, hi):
    raw = env.get(name, str(default))
    if not raw.isdigit() or not lo <= int(raw) <= hi:
        raise ConfigError(f"{name} must be an integer in [{lo}, {hi}]")
    return int(raw)


def load_settings(env=os.environ) -> Settings:
    app_env = env.get("APP_ENV", "prod")          # secure default: prod
    if app_env not in ("test", "prod"):
        raise ConfigError("APP_ENV must be 'test' or 'prod'")

    secret = env.get("JWT_SECRET", "")
    if len(secret.encode()) < 32:                 # A04: >= 256-bit key, no fallback
        raise ConfigError("JWT_SECRET is required and must be at least 32 bytes")

    origins = tuple(o.strip() for o in env.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip())
    if "*" in origins:
        raise ConfigError("Wildcard CORS origin is not allowed")

    seed = Path(env.get("SEED_FILE", "seed/seed_data.json"))
    if not seed.is_file():
        raise ConfigError("SEED_FILE not found")

    return Settings(
        app_env=app_env,
        port=_int(env, "APP_PORT", 8000, 1, 65535),
        jwt_secret=secret,
        jwt_issuer=env.get("JWT_ISSUER", "expense-api"),
        token_ttl_seconds=_int(env, "ACCESS_TOKEN_TTL_SECONDS", 900, 60, 900),
        cors_allowed_origins=origins,
        login_rate_limit_per_minute=_int(env, "LOGIN_RATE_LIMIT_PER_MINUTE", 10, 1, 100000),
        seed_file=seed,
    )
