import pytest
from pydantic import ValidationError

from elden_lore_api.config import Settings


def test_production_rejects_default_secrets() -> None:
    with pytest.raises(ValidationError, match="strong NEO4J_PASSWORD"):
        Settings(app_env="production", _env_file=None)


def test_production_accepts_explicit_long_secrets() -> None:
    settings = Settings(
        app_env="production",
        neo4j_password="n" * 32,
        editorial_token="e" * 48,
        _env_file=None,
    )

    assert settings.app_env == "production"
