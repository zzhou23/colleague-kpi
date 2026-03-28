import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from server.db.models import Base, Employee, ParsedMetrics, DimensionScore, MonthlyReport
from server.parsers.types import MonthlyMetrics
from server.scoring.engine import score_metrics
from server.scoring.persist import persist_scoring_result


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        emp = Employee(name="Test User", email="test@example.com", department="eng")
        session.add(emp)
        session.commit()
        session.refresh(emp)
        yield session, emp.id
    engine.dispose()


def _sample_metrics() -> MonthlyMetrics:
    return MonthlyMetrics(
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


class TestPersistScoringResult:
    def test_creates_dimension_scores(self, db_session):
        session, emp_id = db_session
        scoring_result = score_metrics(_sample_metrics())
        persist_scoring_result(session, emp_id, scoring_result)

        rows = session.query(DimensionScore).filter_by(employee_id=emp_id).all()
        assert len(rows) == len(scoring_result.dimension_scores)

    def test_creates_monthly_report(self, db_session):
        session, emp_id = db_session
        scoring_result = score_metrics(_sample_metrics())
        persist_scoring_result(session, emp_id, scoring_result)

        report = session.query(MonthlyReport).filter_by(
            employee_id=emp_id, year_month="2026-01"
        ).one()
        assert report.grade == scoring_result.grade
        assert report.total_score == pytest.approx(scoring_result.total_score, abs=0.01)

    def test_dimension_score_fields(self, db_session):
        session, emp_id = db_session
        scoring_result = score_metrics(_sample_metrics())
        persist_scoring_result(session, emp_id, scoring_result)

        row = session.query(DimensionScore).filter_by(
            employee_id=emp_id, dimension_name="active_days"
        ).one()
        assert row.category == "activity"
        assert row.raw_value == 20.0
        assert 0.0 <= row.score <= 100.0

    def test_monthly_report_category_scores(self, db_session):
        session, emp_id = db_session
        scoring_result = score_metrics(_sample_metrics())
        persist_scoring_result(session, emp_id, scoring_result)

        report = session.query(MonthlyReport).filter_by(
            employee_id=emp_id, year_month="2026-01"
        ).one()
        assert report.activity_score == pytest.approx(
            scoring_result.category_scores["activity"], abs=0.01
        )
        assert report.efficiency_score == pytest.approx(
            scoring_result.category_scores["efficiency"], abs=0.01
        )

    def test_replaces_existing_scores_on_rerun(self, db_session):
        session, emp_id = db_session
        scoring_result = score_metrics(_sample_metrics())
        persist_scoring_result(session, emp_id, scoring_result)
        persist_scoring_result(session, emp_id, scoring_result)

        reports = session.query(MonthlyReport).filter_by(
            employee_id=emp_id, year_month="2026-01"
        ).all()
        assert len(reports) == 1
