"""Parser for tasks and plans data."""

import json
import logging
import os

logger = logging.getLogger(__name__)


def parse_tasks_and_plans(claude_dir: str) -> dict[str, int]:
    """Parse tasks/*/*.json and plans/*.md to extract task/plan metrics.

    These are snapshot metrics (not per-month).

    Returns dict with:
        - tasks_created: total task JSON files found
        - tasks_completed: tasks with status "completed"
        - plans_created: total plan files found
    """
    return {
        "tasks_created": _count_tasks(claude_dir, count_completed=False),
        "tasks_completed": _count_tasks(claude_dir, count_completed=True),
        "plans_created": _count_plans(claude_dir),
    }


def _count_tasks(claude_dir: str, *, count_completed: bool) -> int:
    """Count task files, optionally filtering to completed only."""
    tasks_dir = os.path.join(claude_dir, "tasks")
    if not os.path.isdir(tasks_dir):
        return 0

    count = 0
    for session_id in os.listdir(tasks_dir):
        session_path = os.path.join(tasks_dir, session_id)
        if not os.path.isdir(session_path):
            continue
        for fname in os.listdir(session_path):
            if not fname.endswith(".json"):
                continue
            filepath = os.path.join(session_path, fname)
            try:
                with open(filepath, encoding="utf-8") as f:
                    task = json.load(f)
                if count_completed:
                    if task.get("status") == "completed":
                        count += 1
                else:
                    count += 1
            except (json.JSONDecodeError, OSError):
                logger.debug("Skipping malformed task file: %s", filepath)

    return count


def _count_plans(claude_dir: str) -> int:
    """Count plan files in plans/ directory."""
    plans_dir = os.path.join(claude_dir, "plans")
    if not os.path.isdir(plans_dir):
        return 0

    count = 0
    for fname in os.listdir(plans_dir):
        if os.path.isfile(os.path.join(plans_dir, fname)):
            count += 1

    return count
