# server/tests/test_employees_api.py
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
def seeded_db(db):
    db.add(Employee(name="Alice", email="alice@test.com", department="Dev", role="employee"))
    db.add(Employee(name="Bob", email="bob@test.com", department="QA", role="employee"))
    db.commit()
    return db


@pytest.mark.asyncio
async def test_list_employees(settings, seeded_db):
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/employees")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_create_employee(settings, db):
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/employees", json={
            "name": "Carol", "email": "carol@test.com", "department": "Dev",
        })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Carol"
    assert "api_key" in data


@pytest.mark.asyncio
async def test_get_employee(settings, seeded_db):
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/employees/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Alice"


@pytest.mark.asyncio
async def test_get_employee_not_found(settings, db):
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/employees/999")
    assert response.status_code == 404
