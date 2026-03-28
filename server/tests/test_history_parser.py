"""Tests for history.jsonl parser."""

import json
import os
import tempfile

import pytest

from server.parsers.history import parse_history


def _write_history(entries: list[dict], path: str) -> str:
    """Write history.jsonl to a temp directory."""
    filepath = os.path.join(path, "history.jsonl")
    with open(filepath, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return filepath


class TestParseHistory:
    def test_empty_file(self, tmp_path: str):
        """Empty history.jsonl returns empty result."""
        _write_history([], str(tmp_path))
        result = parse_history(str(tmp_path))
        assert result.metrics_by_month == {}

    def test_active_days_count(self, tmp_path: str):
        """Count unique days with activity per month."""
        entries = [
            # 2026-03-01 (day 1)
            {"display": "hello", "timestamp": 1772438400000, "project": "proj1", "sessionId": "s1"},
            # 2026-03-01 (same day, different command)
            {"display": "world", "timestamp": 1772438460000, "project": "proj1", "sessionId": "s1"},
            # 2026-03-02 (day 2)
            {"display": "foo", "timestamp": 1772524800000, "project": "proj1", "sessionId": "s2"},
        ]
        _write_history(entries, str(tmp_path))
        result = parse_history(str(tmp_path))
        assert "2026-03" in result.metrics_by_month
        assert result.metrics_by_month["2026-03"]["active_days"] == 2

    def test_model_switches(self, tmp_path: str):
        """Count /model commands."""
        entries = [
            {"display": "/model ", "timestamp": 1772438400000, "project": "p", "sessionId": "s1"},
            {"display": "/model sonnet", "timestamp": 1772438460000, "project": "p", "sessionId": "s1"},
            {"display": "normal query", "timestamp": 1772438520000, "project": "p", "sessionId": "s1"},
        ]
        _write_history(entries, str(tmp_path))
        result = parse_history(str(tmp_path))
        assert result.metrics_by_month["2026-03"]["model_switches"] == 2

    def test_skills_used(self, tmp_path: str):
        """Count slash commands (skills)."""
        entries = [
            {"display": "/init ", "timestamp": 1772438400000, "project": "p", "sessionId": "s1"},
            {"display": "/commit ", "timestamp": 1772438460000, "project": "p", "sessionId": "s1"},
            {"display": "/model ", "timestamp": 1772438520000, "project": "p", "sessionId": "s1"},
            {"display": "normal query", "timestamp": 1772438580000, "project": "p", "sessionId": "s1"},
        ]
        _write_history(entries, str(tmp_path))
        result = parse_history(str(tmp_path))
        # /model is counted separately, /init and /commit are skills
        assert result.metrics_by_month["2026-03"]["skills_used"] == 2

    def test_project_count(self, tmp_path: str):
        """Count unique projects used per month."""
        entries = [
            {"display": "q1", "timestamp": 1772438400000, "project": "projA", "sessionId": "s1"},
            {"display": "q2", "timestamp": 1772438460000, "project": "projB", "sessionId": "s1"},
            {"display": "q3", "timestamp": 1772438520000, "project": "projA", "sessionId": "s2"},
        ]
        _write_history(entries, str(tmp_path))
        result = parse_history(str(tmp_path))
        assert result.metrics_by_month["2026-03"]["project_count"] == 2

    def test_multiple_months(self, tmp_path: str):
        """Metrics are grouped by month."""
        entries = [
            # March 2026
            {"display": "q1", "timestamp": 1772438400000, "project": "p1", "sessionId": "s1"},
            # April 2026 (1 month later)
            {"display": "q2", "timestamp": 1775116800000, "project": "p2", "sessionId": "s2"},
        ]
        _write_history(entries, str(tmp_path))
        result = parse_history(str(tmp_path))
        assert "2026-03" in result.metrics_by_month
        assert "2026-04" in result.metrics_by_month
        assert result.metrics_by_month["2026-03"]["project_count"] == 1
        assert result.metrics_by_month["2026-04"]["project_count"] == 1

    def test_missing_file(self, tmp_path: str):
        """Missing history.jsonl returns empty result."""
        result = parse_history(str(tmp_path))
        assert result.metrics_by_month == {}

    def test_malformed_lines_skipped(self, tmp_path: str):
        """Malformed JSON lines are skipped gracefully."""
        filepath = os.path.join(str(tmp_path), "history.jsonl")
        with open(filepath, "w") as f:
            f.write('{"display":"ok","timestamp":1772438400000,"project":"p","sessionId":"s"}\n')
            f.write("not json\n")
            f.write('{"display":"ok2","timestamp":1772438460000,"project":"p","sessionId":"s"}\n')
        result = parse_history(str(tmp_path))
        assert result.metrics_by_month["2026-03"]["active_days"] == 1
