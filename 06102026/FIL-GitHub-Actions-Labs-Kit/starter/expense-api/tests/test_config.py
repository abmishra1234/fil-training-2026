"""Configuration must fail closed (refuse unsafe settings)."""
import pytest

from app.config import ConfigError, load_settings
from tests.conftest import make_env


def test_valid_test_config_loads():
    s = load_settings(make_env())
    assert s.app_env == "test"
    assert s.port == 8000


def test_default_environment_is_prod():
    env = make_env()
    del env["APP_ENV"]
    assert load_settings(env).is_prod


def test_short_jwt_secret_is_rejected():
    with pytest.raises(ConfigError):
        load_settings(make_env(JWT_SECRET="too-short"))


def test_wildcard_cors_is_rejected():
    with pytest.raises(ConfigError):
        load_settings(make_env(CORS_ALLOWED_ORIGINS="*"))


def test_missing_seed_file_is_rejected():
    with pytest.raises(ConfigError):
        load_settings(make_env(SEED_FILE="does/not/exist.json"))
