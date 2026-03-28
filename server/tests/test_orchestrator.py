"""Tests for the orchestrator — extract, parse, write to DB."""

import json
import os
import tarfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from server.db.models import Base, Employee, ParsedMetrics, UploadRecord
from server.parsers.orchestrator import process_upload, _extract_and_parse


@pytest.fixture
def test_db(tmp_path):
    """Create file-based SQLite DB and return engine + URL."""
    db_path = os.path.join(str(tmp_path), "test.db")
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return engine, url


def _make_tar_gz(tmp_path: str, claude_data: dict[str, str | dict]) -> str:
    """Create a tar.gz with simulated .claude directory contents.

    claude_data: mapping of relative paths to content.
        str content → write as text file
        dict content → write as JSON
    """
    claude_dir = os.path.join(str(tmp_path), "claude_root")
    os.makedirs(claude_dir, exist_ok=True)

    for rel_path, content in claude_data.items():
        full_path = os.path.join(claude_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            if isinstance(content, dict) or isinstance(content, list):
                json.dump(content, f)
            else:
                f.write(content)

    tar_path = os.path.join(str(tmp_path), "upload.tar.gz")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(claude_dir, arcname="claude_data")

    return tar_path


def _history_line(display: str, timestamp: int, project: str = "p1", session_id: str = "s1") -> str:
    return json.dumps({
        "display": display,
        "timestamp": timestamp,
        "project": project,
        "sessionId": session_id,
    })


class TestExtractAndParse:
    def test_basic_extraction(self, tmp_path):
        """Extract tar.gz and parse basic history data."""
        history = "\n".join([
            _history_line("hello", 1772438400000),  # 2026-03-01
            _history_line("/model opus", 1772438460000),
            _history_line("/commit", 1772438520000),
        ])
        tar_path = _make_tar_gz(tmp_path, {
            "history.jsonl": history,
        })
        metrics = _extract_and_parse(tar_path)
        assert len(metrics) == 1
        m = metrics[0]
        assert m.metric_date == "2026-03"
        assert m.active_days == 1
        assert m.model_switches == 1
        assert m.skills_used == 1

    def test_config_globals_applied(self, tmp_path):
        """Config and task metrics are applied to all months."""
        history = "\n".join([
            _history_line("q1", 1772438400000),  # March
            _history_line("q2", 1775116800000),  # April
        ])
        tar_path = _make_tar_gz(tmp_path, {
            "history.jsonl": history,
            "CLAUDE.md": "# Rules",
            "rules/style.md": "# Style",
            "settings.json": json.dumps({"model": "opus", "hooks": {"Notification": []}}),
            "plans/plan-a.md": "# Plan A",
        })
        metrics = _extract_and_parse(tar_path)
        assert len(metrics) == 2
        for m in metrics:
            assert m.rules_count == 2  # CLAUDE.md + style.md
            assert m.custom_settings_count == 2  # model + hooks
            assert m.hooks_count == 1  # Notification
            assert m.plans_created == 1

    def test_empty_archive(self, tmp_path):
        """Empty archive produces no metrics."""
        tar_path = _make_tar_gz(tmp_path, {})
        metrics = _extract_and_parse(tar_path)
        assert metrics == []


class TestProcessUpload:
    def test_full_pipeline(self, tmp_path, test_db):
        """End-to-end: upload record → parse → metrics in DB."""
        engine, url = test_db

        # Seed employee + upload record
        history = _history_line("hello", 1772438400000)
        tar_path = _make_tar_gz(tmp_path, {"history.jsonl": history})

        with Session(engine) as session:
            emp = Employee(name="Test User", email="test@example.com", department="Dev")
            session.add(emp)
            session.commit()

            record = UploadRecord(
                employee_id=emp.id,
                file_path=tar_path,
                file_size=os.path.getsize(tar_path),
                status="pending",
            )
            session.add(record)
            session.commit()
            upload_id = record.id

        # Process
        created = process_upload(upload_id, url)
        assert len(created) == 1
        assert created[0].metric_date == "2026-03"
        assert created[0].active_days == 1

        # Verify DB state
        with Session(engine) as session:
            record = session.get(UploadRecord, upload_id)
            assert record.status == "completed"
            assert record.parsed_at is not None

            metrics = session.query(ParsedMetrics).filter_by(upload_id=upload_id).all()
            assert len(metrics) == 1

    def test_not_pending_raises(self, test_db):
        """Processing a non-pending upload raises ValueError."""
        engine, url = test_db

        with Session(engine) as session:
            emp = Employee(name="Test", email="t@e.com", department="Dev")
            session.add(emp)
            session.commit()
            record = UploadRecord(
                employee_id=emp.id,
                file_path="nonexistent.tar.gz",
                file_size=0,
                status="completed",
            )
            session.add(record)
            session.commit()
            upload_id = record.id

        with pytest.raises(ValueError, match="not pending"):
            process_upload(upload_id, url)

    def test_missing_upload_raises(self, test_db):
        """Processing a nonexistent upload raises ValueError."""
        _, url = test_db
        with pytest.raises(ValueError, match="not found"):
            process_upload(999, url)

    def test_failed_parse_marks_failed(self, test_db):
        """If parsing fails, upload record is marked as failed."""
        engine, url = test_db

        with Session(engine) as session:
            emp = Employee(name="Test", email="t@e.com", department="Dev")
            session.add(emp)
            session.commit()
            record = UploadRecord(
                employee_id=emp.id,
                file_path="nonexistent.tar.gz",
                file_size=0,
                status="pending",
            )
            session.add(record)
            session.commit()
            upload_id = record.id

        with pytest.raises(Exception):
            process_upload(upload_id, url)

        with Session(engine) as session:
            record = session.get(UploadRecord, upload_id)
            assert record.status == "failed"
