# server/src/server/api/deps.py
from server.config import Settings

_settings: Settings | None = None


def set_settings(settings: Settings) -> None:
    global _settings
    _settings = settings


def get_settings() -> Settings:
    if _settings is None:
        raise RuntimeError("Settings not initialized")
    return _settings
