import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from server.db.models import Base, Employee, UploadRecord, ParsedMetrics, DimensionScore, MonthlyReport


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_employee_creation(db):
    emp = Employee(name="Alice", email="alice@test.com", department="Engineering", role="admin")
    db.add(emp)
    db.commit()
    db.refresh(emp)
    assert emp.id is not None
    assert emp.name == "Alice"
    assert emp.role == "admin"


def test_upload_record_fk(db):
    emp = Employee(name="Bob", email="bob@test.com", department="QA", role="employee")
    db.add(emp)
    db.commit()
    upload = UploadRecord(employee_id=emp.id, file_path="/uploads/bob.tar.gz", file_size=1024, status="pending")
    db.add(upload)
    db.commit()
    db.refresh(upload)
    assert upload.employee_id == emp.id
    assert upload.status == "pending"


def test_parsed_metrics_fields(db):
    emp = Employee(name="Carol", email="carol@test.com", department="Dev", role="employee")
    db.add(emp)
    db.commit()
    metrics = ParsedMetrics(
        employee_id=emp.id, upload_id=1, metric_date="2026-03",
        active_days=20, session_count=50, total_turns=300,
        project_count=3, tool_types_used=5, tasks_created=10, tasks_completed=8,
    )
    db.add(metrics)
    db.commit()
    assert metrics.active_days == 20
    assert metrics.tasks_completed == 8


def test_dimension_score(db):
    emp = Employee(name="Dan", email="dan@test.com", department="Dev", role="employee")
    db.add(emp)
    db.commit()
    score = DimensionScore(
        employee_id=emp.id, year_month="2026-03",
        category="activity", dimension_name="monthly_active_days",
        raw_value=20.0, score=85.0,
    )
    db.add(score)
    db.commit()
    assert score.score == 85.0


def test_monthly_report(db):
    emp = Employee(name="Eve", email="eve@test.com", department="Dev", role="employee")
    db.add(emp)
    db.commit()
    report = MonthlyReport(
        employee_id=emp.id, year_month="2026-03",
        activity_score=80.0, quality_score=75.0, cognition_score=70.0,
        efficiency_score=85.0, resource_score=90.0,
        total_score=80.0, grade="A",
    )
    db.add(report)
    db.commit()
    assert report.grade == "A"


def test_all_tables_exist(db):
    engine = db.get_bind()
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    assert "employees" in table_names
    assert "upload_records" in table_names
    assert "parsed_metrics" in table_names
    assert "dimension_scores" in table_names
    assert "monthly_reports" in table_names
