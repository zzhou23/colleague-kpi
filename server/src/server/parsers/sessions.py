"""Parser for session data — JSONL transcripts and session metadata."""

import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from server.parsers.types import ParserResult

logger = logging.getLogger(__name__)


@dataclass
class _SessionStats:
    """Accumulator for a single session's statistics."""

    session_id: str
    month: str
    user_turns: int = 0
    assistant_turns: int = 0
    tool_types: set[str] = field(default_factory=set)
    git_commits: int = 0
    estimated_tokens: int = 0
    file_reads: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    file_edits: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None


def _parse_timestamp(ts: str) -> datetime | None:
    """Parse ISO-format timestamp string."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _month_from_ms(timestamp_ms: int) -> str:
    """Convert millisecond timestamp to YYYY-MM."""
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m")


def _collect_session_ids(claude_dir: str) -> dict[str, str]:
    """Map session_id -> month from sessions/*.json metadata files."""
    sessions_dir = os.path.join(claude_dir, "sessions")
    session_months: dict[str, str] = {}
    if not os.path.isdir(sessions_dir):
        return session_months

    for fname in os.listdir(sessions_dir):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(sessions_dir, fname), encoding="utf-8") as f:
                meta = json.load(f)
            sid = meta.get("sessionId", "")
            started = meta.get("startedAt")
            if sid and isinstance(started, (int, float)):
                session_months[sid] = _month_from_ms(started)
        except (json.JSONDecodeError, OSError):
            logger.debug("Skipping malformed session meta: %s", fname)

    return session_months


def _analyze_session_jsonl(filepath: str, session_id: str, month: str) -> _SessionStats:
    """Parse a single session JSONL file and extract stats."""
    stats = _SessionStats(session_id=session_id, month=month)

    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = entry.get("type", "")
                timestamp = _parse_timestamp(entry.get("timestamp", ""))

                if timestamp:
                    if stats.first_timestamp is None or timestamp < stats.first_timestamp:
                        stats.first_timestamp = timestamp
                    if stats.last_timestamp is None or timestamp > stats.last_timestamp:
                        stats.last_timestamp = timestamp

                if msg_type == "user":
                    stats.user_turns += 1

                elif msg_type == "assistant":
                    stats.assistant_turns += 1
                    message = entry.get("message", {})

                    # Token usage
                    usage = message.get("usage", {})
                    stats.estimated_tokens += usage.get("input_tokens", 0)
                    stats.estimated_tokens += usage.get("output_tokens", 0)

                    # Tool analysis
                    content = message.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            if block.get("type") != "tool_use":
                                continue

                            tool_name = block.get("name", "")
                            stats.tool_types.add(tool_name)
                            tool_input = block.get("input", {})

                            # Git commits
                            if tool_name == "Bash":
                                cmd = tool_input.get("command", "")
                                if "git commit" in cmd:
                                    stats.git_commits += 1

                            # File reads tracking
                            if tool_name == "Read":
                                fp = tool_input.get("file_path", "")
                                if fp:
                                    stats.file_reads[fp] += 1

                            # File edits tracking
                            if tool_name == "Edit":
                                fp = tool_input.get("file_path", "")
                                if fp:
                                    stats.file_edits[fp] += 1

    except OSError:
        logger.debug("Could not read session file: %s", filepath)

    return stats


def parse_sessions(claude_dir: str) -> ParserResult:
    """Parse all session data to extract session-level metrics.

    Scans:
        - sessions/*.json for session metadata (start time, session ID)
        - projects/*/<session_id>.jsonl for session transcripts

    Extracts per month:
        - session_count, total_turns, avg_session_duration
        - tool_types_used, complex_session_count
        - abandoned_sessions, empty_sessions
        - git_commits_in_session
        - estimated_tokens
        - repeated_operations (same file read/edit multiple times)
    """
    session_months = _collect_session_ids(claude_dir)
    if not session_months:
        return ParserResult()

    # Find all session JSONL files in projects/
    session_files: dict[str, str] = {}  # session_id -> filepath
    projects_dir = os.path.join(claude_dir, "projects")
    if os.path.isdir(projects_dir):
        for project_name in os.listdir(projects_dir):
            proj_path = os.path.join(projects_dir, project_name)
            if not os.path.isdir(proj_path):
                continue
            for fname in os.listdir(proj_path):
                if fname.endswith(".jsonl"):
                    sid = fname[:-6]  # Remove .jsonl
                    if sid in session_months:
                        session_files[sid] = os.path.join(proj_path, fname)

    # Analyze each session
    all_stats: list[_SessionStats] = []
    for sid, month in session_months.items():
        filepath = session_files.get(sid)
        if filepath:
            stats = _analyze_session_jsonl(filepath, sid, month)
        else:
            # Session exists in metadata but no JSONL found — empty session
            stats = _SessionStats(session_id=sid, month=month)
        all_stats.append(stats)

    # Aggregate by month
    month_sessions: dict[str, list[_SessionStats]] = defaultdict(list)
    for s in all_stats:
        month_sessions[s.month].append(s)

    metrics_by_month: dict[str, dict[str, int | float]] = {}
    for month, sessions in month_sessions.items():
        session_count = len(sessions)
        total_turns = sum(s.user_turns for s in sessions)
        all_tool_types: set[str] = set()
        total_tokens = 0
        total_git_commits = 0
        complex_count = 0
        abandoned_count = 0
        empty_count = 0
        repeated_ops = 0
        durations: list[float] = []

        for s in sessions:
            all_tool_types.update(s.tool_types)
            total_tokens += s.estimated_tokens
            total_git_commits += s.git_commits

            # Complex: 3+ turns AND 2+ tool types
            if s.user_turns >= 3 and len(s.tool_types) >= 2:
                complex_count += 1

            # Abandoned: has user input but no assistant response
            if s.user_turns > 0 and s.assistant_turns == 0:
                abandoned_count += 1

            # Empty: no user messages at all
            if s.user_turns == 0 and s.assistant_turns == 0:
                empty_count += 1

            # Session duration
            if s.first_timestamp and s.last_timestamp and s.first_timestamp != s.last_timestamp:
                duration = (s.last_timestamp - s.first_timestamp).total_seconds()
                durations.append(duration)

            # Repeated operations (same file read/edited 2+ times)
            for count in s.file_reads.values():
                if count >= 2:
                    repeated_ops += count - 1
            for count in s.file_edits.values():
                if count >= 2:
                    repeated_ops += count - 1

        avg_duration = sum(durations) / len(durations) if durations else 0.0

        metrics_by_month[month] = {
            "session_count": session_count,
            "total_turns": total_turns,
            "avg_session_duration": avg_duration,
            "tool_types_used": len(all_tool_types),
            "complex_session_count": complex_count,
            "abandoned_sessions": abandoned_count,
            "empty_sessions": empty_count,
            "git_commits_in_session": total_git_commits,
            "estimated_tokens": total_tokens,
            "repeated_operations": repeated_ops,
            "large_file_reads": 0,  # TODO: need tool_result data to determine size
            "repeated_queries": 0,  # TODO: need NLP similarity analysis
            "error_recovery_avg_turns": 0.0,  # TODO: need error pattern detection
        }

    return ParserResult(metrics_by_month=metrics_by_month)
