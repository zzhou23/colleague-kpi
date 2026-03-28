"""Parser for history.jsonl — command history from Claude Code."""

import json
import logging
import os
from datetime import datetime, timezone

from server.parsers.types import ParserResult

logger = logging.getLogger(__name__)

# Built-in commands that are NOT counted as "skills"
_BUILTIN_COMMANDS = frozenset({
    "/model", "/login", "/logout", "/help", "/clear", "/compact",
    "/cost", "/doctor", "/config", "/status", "/memory",
})


def parse_history(claude_dir: str) -> ParserResult:
    """Parse history.jsonl to extract activity and command metrics.

    Extracts per month:
        - active_days: unique days with at least one command
        - model_switches: /model commands
        - skills_used: slash commands (excluding builtins)
        - project_count: unique projects used
    """
    filepath = os.path.join(claude_dir, "history.jsonl")
    if not os.path.isfile(filepath):
        return ParserResult()

    # Per-month accumulators
    month_days: dict[str, set[str]] = {}       # month -> set of date strings
    month_projects: dict[str, set[str]] = {}   # month -> set of project paths
    month_model_switches: dict[str, int] = {}
    month_skills: dict[str, int] = {}

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                logger.debug("Skipping malformed history line: %s", line[:80])
                continue

            timestamp_ms = entry.get("timestamp")
            if not isinstance(timestamp_ms, (int, float)):
                continue

            dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            month = dt.strftime("%Y-%m")
            day = dt.strftime("%Y-%m-%d")

            # Active days
            month_days.setdefault(month, set()).add(day)

            # Project count
            project = entry.get("project", "")
            if project:
                month_projects.setdefault(month, set()).add(project)

            # Command analysis
            display = entry.get("display", "").strip()
            if display.startswith("/model"):
                month_model_switches[month] = month_model_switches.get(month, 0) + 1
            elif display.startswith("/") and not any(
                display.startswith(cmd) for cmd in _BUILTIN_COMMANDS
            ):
                month_skills[month] = month_skills.get(month, 0) + 1

    # Build result
    all_months = set(month_days) | set(month_projects)
    metrics_by_month: dict[str, dict[str, int | float]] = {}
    for month in all_months:
        metrics_by_month[month] = {
            "active_days": len(month_days.get(month, set())),
            "project_count": len(month_projects.get(month, set())),
            "model_switches": month_model_switches.get(month, 0),
            "skills_used": month_skills.get(month, 0),
        }

    return ParserResult(metrics_by_month=metrics_by_month)
