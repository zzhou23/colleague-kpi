import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from server.db.models import Base, Employee, MonthlyReport
from server.main import create_app
from server.config import Settings


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / f"test_dashboard_{uuid.uuid4().hex[:8]}.db"
    db_url = f"sqlite:///{db_path}"
    settings = Settings(
        database_url=db_url,
        secret_key="test-secret",
    )
    app = create_app(settings)
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    session = Session(engine)
    for i, (name, dept, score, grade) in enumerate([
        ("Alice", "Engineering", 92.0, "S"),
        ("Bob", "Engineering", 78.0, "A"),
        ("Carol", "Design", 55.0, "C"),
    ], start=1):
        emp = Employee(id=i, name=name, email=f"{name.lower()}@test.com", department=dept)
        session.add(emp)
        session.flush()
        report = MonthlyReport(
            employee_id=i,
            year_month="2026-03",
            activity_score=score,
            quality_score=score,
            cognition_score=score,
            efficiency_score=score,
            resource_score=score,
            total_score=score,
            grade=grade,
        )
        session.add(report)
    session.commit()
    session.close()
    yield TestClient(app)
    engine.dispose()


def test_dashboard_summary(client):
    resp = client.get("/api/dashboard/summary", params={"year_month": "2026-03"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_employees"] == 3
    assert data["grade_distribution"]["S"] == 1
    assert data["grade_distribution"]["A"] == 1
    assert data["grade_distribution"]["C"] == 1
    assert data["avg_score"] == pytest.approx(75.0, abs=0.1)
    assert data["max_score"] == pytest.approx(92.0)
    assert data["min_score"] == pytest.approx(55.0)


def test_dashboard_rankings_top(client):
    resp = client.get("/api/dashboard/rankings", params={
        "year_month": "2026-03", "order": "top", "limit": 2
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "Alice"
    assert data[0]["total_score"] == pytest.approx(92.0)


def test_dashboard_rankings_bottom(client):
    resp = client.get("/api/dashboard/rankings", params={
        "year_month": "2026-03", "order": "bottom", "limit": 1
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Carol"


def test_dashboard_summary_no_data(client):
    resp = client.get("/api/dashboard/summary", params={"year_month": "2099-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_employees"] == 3
    assert data["avg_score"] == 0.0
    assert data["grade_distribution"] == {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
