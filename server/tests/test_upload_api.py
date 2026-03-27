# server/tests/test_upload_api.py
import io
import tarfile
import json

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from server.db.models import Base, Employee
from server.main import create_app
from server.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(
        database_url=f"sqlite:///{tmp_path}/test.db",
        secret_key="test-secret-key-min-32-chars-long!",
        upload_dir=str(tmp_path / "uploads"),
    )


@pytest.fixture
def db(settings):
    engine = create_engine(settings.database_url.replace("+asyncpg", ""))
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def employee_with_key(db):
    import bcrypt
    emp = Employee(
        name="Test User", email="test@test.com",
        department="Dev", role="employee",
        api_key_hash=bcrypt.hashpw(b"test-api-key-123", bcrypt.gensalt()).decode(),
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def make_test_tarball() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        history = json.dumps({"display": "/init", "timestamp": 1772266811658}).encode()
        info = tarfile.TarInfo(name=".claude/history.jsonl")
        info.size = len(history)
        tar.addfile(info, io.BytesIO(history))
    buf.seek(0)
    return buf.read()


@pytest.mark.asyncio
async def test_upload_success(settings, db, employee_with_key):
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tarball = make_test_tarball()
        response = await client.post(
            "/api/upload",
            headers={"X-API-Key": "test-api-key-123"},
            files={"file": ("claude.tar.gz", tarball, "application/gzip")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert "upload_id" in data


@pytest.mark.asyncio
async def test_upload_invalid_api_key(settings, db, employee_with_key):
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tarball = make_test_tarball()
        response = await client.post(
            "/api/upload",
            headers={"X-API-Key": "wrong-key"},
            files={"file": ("claude.tar.gz", tarball, "application/gzip")},
        )
    assert response.status_code == 401
