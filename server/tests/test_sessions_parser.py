"""Tests for sessions parser."""

import json
import os

import pytest

from server.parsers.sessions import parse_sessions


def _make_session_meta(tmp_path: str, pid: int, session_id: str, started_at: int, cwd: str = "/work"):
    """Create sessions/<pid>.json metadata file."""
    sessions_dir = os.path.join(tmp_path, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    with open(os.path.join(sessions_dir, f"{pid}.json"), "w") as f:
        json.dump({
            "pid": pid,
            "sessionId": session_id,
            "cwd": cwd,
            "startedAt": started_at,
            "kind": "interactive",
            "entrypoint": "cli",
        }, f)


def _make_session_jsonl(tmp_path: str, project: str, session_id: str, messages: list[dict]):
    """Create projects/<project>/<session_id>.jsonl with messages."""
    proj_dir = os.path.join(tmp_path, "projects", project)
    os.makedirs(proj_dir, exist_ok=True)
    filepath = os.path.join(proj_dir, f"{session_id}.jsonl")
    with open(filepath, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")


def _user_msg(timestamp: str, session_id: str = "s1") -> dict:
    return {
        "type": "user",
        "timestamp": timestamp,
        "sessionId": session_id,
        "uuid": "u1",
        "parentUuid": None,
        "isSidechain": False,
        "message": {"role": "user", "content": "hello"},
        "userType": "external",
        "cwd": "/work",
        "version": "1.0.0",
    }


def _assistant_msg(
    timestamp: str,
    session_id: str = "s1",
    tool_uses: list[dict] | None = None,
    usage: dict | None = None,
) -> dict:
    content: list[dict] = []
    if tool_uses:
        content.extend(tool_uses)
    else:
        content.append({"type": "text", "text": "response"})
    return {
        "type": "assistant",
        "timestamp": timestamp,
        "sessionId": session_id,
        "uuid": "a1",
        "parentUuid": "u1",
        "isSidechain": False,
        "message": {
            "role": "assistant",
            "content": content,
            "model": "claude-opus-4-6",
            "type": "message",
            "id": "msg1",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": usage or {"input_tokens": 500, "output_tokens": 200},
        },
        "userType": "external",
        "cwd": "/work",
        "version": "1.0.0",
    }


def _tool_use(name: str, input_data: dict | None = None) -> dict:
    return {
        "type": "tool_use",
        "id": "tu1",
        "name": name,
        "input": input_data or {},
    }


class TestParseSessions:
    def test_empty_directory(self, tmp_path):
        """No sessions returns empty result."""
        result = parse_sessions(str(tmp_path))
        assert result.metrics_by_month == {}

    def test_session_count_and_turns(self, tmp_path):
        """Count sessions and user turns."""
        # Session meta: started 2026-03-01
        _make_session_meta(str(tmp_path), 100, "s1", 1772438400000)
        _make_session_jsonl(str(tmp_path), "proj1", "s1", [
            _user_msg("2026-03-01T00:00:00Z"),
            _assistant_msg("2026-03-01T00:01:00Z"),
            _user_msg("2026-03-01T00:02:00Z"),
            _assistant_msg("2026-03-01T00:03:00Z"),
            _user_msg("2026-03-01T00:04:00Z"),
            _assistant_msg("2026-03-01T00:05:00Z"),
        ])
        result = parse_sessions(str(tmp_path))
        m = result.metrics_by_month["2026-03"]
        assert m["session_count"] == 1
        assert m["total_turns"] == 3  # 3 user messages = 3 turns

    def test_tool_types_used(self, tmp_path):
        """Count unique tool types across all sessions in a month."""
        _make_session_meta(str(tmp_path), 100, "s1", 1772438400000)
        _make_session_jsonl(str(tmp_path), "proj1", "s1", [
            _user_msg("2026-03-01T00:00:00Z"),
            _assistant_msg("2026-03-01T00:01:00Z", tool_uses=[
                _tool_use("Read"),
                _tool_use("Edit"),
            ]),
            _user_msg("2026-03-01T00:02:00Z"),
            _assistant_msg("2026-03-01T00:03:00Z", tool_uses=[
                _tool_use("Bash"),
                _tool_use("Read"),  # duplicate
            ]),
        ])
        result = parse_sessions(str(tmp_path))
        assert result.metrics_by_month["2026-03"]["tool_types_used"] == 3  # Read, Edit, Bash

    def test_complex_session(self, tmp_path):
        """Session with 3+ turns and 2+ tool types is complex."""
        _make_session_meta(str(tmp_path), 100, "s1", 1772438400000)
        _make_session_jsonl(str(tmp_path), "proj1", "s1", [
            _user_msg("2026-03-01T00:00:00Z"),
            _assistant_msg("2026-03-01T00:01:00Z", tool_uses=[_tool_use("Read")]),
            _user_msg("2026-03-01T00:02:00Z"),
            _assistant_msg("2026-03-01T00:03:00Z", tool_uses=[_tool_use("Edit")]),
            _user_msg("2026-03-01T00:04:00Z"),
            _assistant_msg("2026-03-01T00:05:00Z", tool_uses=[_tool_use("Bash")]),
        ])
        result = parse_sessions(str(tmp_path))
        assert result.metrics_by_month["2026-03"]["complex_session_count"] == 1

    def test_non_complex_session(self, tmp_path):
        """Session with < 3 turns is not complex."""
        _make_session_meta(str(tmp_path), 100, "s1", 1772438400000)
        _make_session_jsonl(str(tmp_path), "proj1", "s1", [
            _user_msg("2026-03-01T00:00:00Z"),
            _assistant_msg("2026-03-01T00:01:00Z", tool_uses=[_tool_use("Read")]),
        ])
        result = parse_sessions(str(tmp_path))
        assert result.metrics_by_month["2026-03"]["complex_session_count"] == 0

    def test_abandoned_session(self, tmp_path):
        """Session with user message but no assistant response is abandoned."""
        _make_session_meta(str(tmp_path), 100, "s1", 1772438400000)
        _make_session_jsonl(str(tmp_path), "proj1", "s1", [
            _user_msg("2026-03-01T00:00:00Z"),
        ])
        result = parse_sessions(str(tmp_path))
        assert result.metrics_by_month["2026-03"]["abandoned_sessions"] == 1

    def test_empty_session(self, tmp_path):
        """Session with no user messages is empty."""
        _make_session_meta(str(tmp_path), 100, "s1", 1772438400000)
        _make_session_jsonl(str(tmp_path), "proj1", "s1", [])
        result = parse_sessions(str(tmp_path))
        m = result.metrics_by_month.get("2026-03", {})
        assert m.get("empty_sessions", 0) == 1

    def test_git_commits_counted(self, tmp_path):
        """Bash tool calls with git commit are counted."""
        _make_session_meta(str(tmp_path), 100, "s1", 1772438400000)
        _make_session_jsonl(str(tmp_path), "proj1", "s1", [
            _user_msg("2026-03-01T00:00:00Z"),
            _assistant_msg("2026-03-01T00:01:00Z", tool_uses=[
                _tool_use("Bash", {"command": "git commit -m 'fix'"}),
            ]),
            _user_msg("2026-03-01T00:02:00Z"),
            _assistant_msg("2026-03-01T00:03:00Z", tool_uses=[
                _tool_use("Bash", {"command": "git commit -m 'feat'"}),
            ]),
        ])
        result = parse_sessions(str(tmp_path))
        assert result.metrics_by_month["2026-03"]["git_commits_in_session"] == 2

    def test_large_file_reads(self, tmp_path):
        """Read tool calls with large offset/limit are counted."""
        _make_session_meta(str(tmp_path), 100, "s1", 1772438400000)
        _make_session_jsonl(str(tmp_path), "proj1", "s1", [
            _user_msg("2026-03-01T00:00:00Z"),
            _assistant_msg("2026-03-01T00:01:00Z", tool_uses=[
                _tool_use("Read", {"file_path": "/big.js"}),
                _tool_use("Read", {"file_path": "/big.js"}),  # repeated read = large
            ]),
        ])
        result = parse_sessions(str(tmp_path))
        # At least counting repeated reads of same file
        assert result.metrics_by_month["2026-03"]["repeated_operations"] >= 1

    def test_estimated_tokens(self, tmp_path):
        """Sum up token usage from assistant messages."""
        _make_session_meta(str(tmp_path), 100, "s1", 1772438400000)
        _make_session_jsonl(str(tmp_path), "proj1", "s1", [
            _user_msg("2026-03-01T00:00:00Z"),
            _assistant_msg("2026-03-01T00:01:00Z",
                           usage={"input_tokens": 1000, "output_tokens": 500}),
            _user_msg("2026-03-01T00:02:00Z"),
            _assistant_msg("2026-03-01T00:03:00Z",
                           usage={"input_tokens": 800, "output_tokens": 300}),
        ])
        result = parse_sessions(str(tmp_path))
        assert result.metrics_by_month["2026-03"]["estimated_tokens"] == 2600

    def test_session_duration(self, tmp_path):
        """Calculate average session duration from first to last message timestamp."""
        _make_session_meta(str(tmp_path), 100, "s1", 1772438400000)
        # Session lasts 5 minutes (300 seconds)
        _make_session_jsonl(str(tmp_path), "proj1", "s1", [
            _user_msg("2026-03-01T00:00:00Z"),
            _assistant_msg("2026-03-01T00:05:00Z"),
        ])
        result = parse_sessions(str(tmp_path))
        assert result.metrics_by_month["2026-03"]["avg_session_duration"] == 300.0
