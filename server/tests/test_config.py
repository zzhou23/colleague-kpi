from server.config import Settings


def test_default_settings():
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        secret_key="test-secret-key-min-32-chars-long!",
    )
    assert settings.database_url == "postgresql+asyncpg://user:pass@localhost/test"
    assert settings.upload_dir == "uploads"
    assert settings.max_upload_size_mb == 200
    assert settings.archive_retention_days == 30


def test_settings_custom_values():
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        secret_key="test-secret-key-min-32-chars-long!",
        upload_dir="/data/uploads",
        max_upload_size_mb=500,
        archive_retention_days=60,
    )
    assert settings.upload_dir == "/data/uploads"
    assert settings.max_upload_size_mb == 500
    assert settings.archive_retention_days == 60
