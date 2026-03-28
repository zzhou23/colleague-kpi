# server/tests/test_scores_api.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from server.config import Settings
from server.db.models import Base, Employee, ParsedMetrics, DimensionScore, MonthlyReport
from server.main import create_app


@pytest.fixture
def client_with_data(tmp_path):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    settings = Settings(
        database_url=db_url,
        secret_key="test-secret",
        upload_dir=str(tmp_path / "uploads"),
    )
    app = create_app(settings)

    # Seed test data
    engine = create_engine(db_url)
    with Session(engine) as session:
        emp = Employee(name="Test User", email="test@example.com", department="eng")
        session.add(emp)
        session.commit()
        session.refresh(emp)

        pm = ParsedMetrics(
            employee_id=emp.id,
            upload_id=1,
            metric_date="2026-01",
            active_days=20,
            session_count=80,
            total_turns=600,
            avg_session_duration=20.0,
            project_count=5,
            tool_types_used=8,
            complex_session_count=15,
            tasks_created=10,
            tasks_completed=8,
            plans_created=5,
            model_switches=3,
            rules_count=5,
            memory_file_count=4,
            custom_settings_count=6,
            hooks_count=3,
            skills_used=4,
            abandoned_sessions=2,
            git_commits_in_session=25,
            repeated_queries=1,
            error_recovery_avg_turns=2.0,
            estimated_tokens=500_000,
            empty_sessions=1,
            large_file_reads=2,
            repeated_operations=1,
            rejected_commands=0,
        )
        session.add(pm)
        session.commit()

        yield TestClient(app), emp.id

    engine.dispose()


class TestTriggerScoring:
    def test_trigger_scoring_creates_report(self, client_with_data):
        client, emp_id = client_with_data
        resp = client.post(f"/api/employees/{emp_id}/score", json={"year_month": "2026-01"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["grade"] in ["S", "A", "B", "C", "D"]
        assert data["total_score"] > 0
        assert data["year_month"] == "2026-01"

    def test_trigger_scoring_employee_not_found(self, client_with_data):
        client, _ = client_with_data
        resp = client.post("/api/employees/999/score", json={"year_month": "2026-01"})
        assert resp.status_code == 404

    def test_trigger_scoring_no_metrics(self, client_with_data):
        client, emp_id = client_with_data
        resp = client.post(f"/api/employees/{emp_id}/score", json={"year_month": "2099-01"})
        assert resp.status_code == 404


class TestGetDimensionScores:
    def test_get_scores_after_trigger(self, client_with_data):
        client, emp_id = client_with_data
        # First trigger scoring
        client.post(f"/api/employees/{emp_id}/score", json={"year_month": "2026-01"})
        # Then query scores
        resp = client.get(f"/api/employees/{emp_id}/scores?year_month=2026-01")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert all("dimension_name" in d for d in data)
        assert all("score" in d for d in data)

    def test_get_scores_empty(self, client_with_data):
        client, emp_id = client_with_data
        resp = client.get(f"/api/employees/{emp_id}/scores")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_scores_employee_not_found(self, client_with_data):
        client, _ = client_with_data
        resp = client.get("/api/employees/999/scores")
        assert resp.status_code == 404


class TestGetMonthlyReports:
    def test_get_reports_after_trigger(self, client_with_data):
        client, emp_id = client_with_data
        client.post(f"/api/employees/{emp_id}/score", json={"year_month": "2026-01"})
        resp = client.get(f"/api/employees/{emp_id}/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["grade"] in ["S", "A", "B", "C", "D"]

    def test_get_reports_with_month_filter(self, client_with_data):
        client, emp_id = client_with_data
        client.post(f"/api/employees/{emp_id}/score", json={"year_month": "2026-01"})
        resp = client.get(f"/api/employees/{emp_id}/reports?year_month=2026-01")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_reports_empty(self, client_with_data):
        client, emp_id = client_with_data
        resp = client.get(f"/api/employees/{emp_id}/reports")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_reports_employee_not_found(self, client_with_data):
        client, _ = client_with_data
        resp = client.get("/api/employees/999/reports")
        assert resp.status_code == 404
