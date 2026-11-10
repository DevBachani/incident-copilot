"""Smoke tests — keep CI green from day one."""

from incident_copilot import __version__
from incident_copilot.config import get_settings


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_settings_load() -> None:
    settings = get_settings()
    # Defaults always present even without a .env file.
    assert settings.groq_model
    assert settings.database_url.startswith("postgresql://")
