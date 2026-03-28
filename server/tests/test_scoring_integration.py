import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from server.db.models import (
    Base, Employee, UploadRecord, ParsedMetrics, DimensionScore, MonthlyReport,
)
from server.scoring.orchestrate import score_employee_month


@pytest.fixture
def db_session_with_metrics():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        emp = Employee(name="Test", email="t@t.com", department="eng")
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
        session.refresh(pm)

        yield session, emp.id

    engine.dispose()


class TestScoreEmployeeMonth:
    def test_scores_from_parsed_metrics(self, db_session_with_metrics):
        session, emp_id = db_session_with_metrics
        report = score_employee_month(session, emp_id, "2026-01")

        assert report is not None
        assert report.grade in {"S", "A", "B", "C", "D"}
        assert report.total_score > 0

    def test_creates_dimension_scores(self, db_session_with_metrics):
        session, emp_id = db_session_with_metrics
        score_employee_month(session, emp_id, "2026-01")

        rows = session.query(DimensionScore).filter_by(employee_id=emp_id).all()
        assert len(rows) > 0

    def test_no_metrics_returns_none(self, db_session_with_metrics):
        session, emp_id = db_session_with_metrics
        result = score_employee_month(session, emp_id, "2099-01")
        assert result is None
