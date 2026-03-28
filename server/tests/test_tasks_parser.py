"""Tests for tasks & plans parser."""

import json
import os

import pytest

from server.parsers.tasks import parse_tasks_and_plans


def _write_tasks(tmp_path: str, session_tasks: dict[str, list[dict]]):
    """Create tasks/<session_id>/<n>.json files."""
    for session_id, tasks in session_tasks.items():
        task_dir = os.path.join(tmp_path, "tasks", session_id)
        os.makedirs(task_dir, exist_ok=True)
        for task in tasks:
            with open(os.path.join(task_dir, f"{task['id']}.json"), "w") as f:
                json.dump(task, f)


def _write_plans(tmp_path: str, plan_names: list[str]):
    """Create plans/<name>.md files."""
    plans_dir = os.path.join(tmp_path, "plans")
    os.makedirs(plans_dir, exist_ok=True)
    for name in plan_names:
        with open(os.path.join(plans_dir, name), "w") as f:
            f.write(f"# Plan {name}")


class TestParseTasksAndPlans:
    def test_empty_directory(self, tmp_path):
        result = parse_tasks_and_plans(str(tmp_path))
        assert result["tasks_created"] == 0
        assert result["tasks_completed"] == 0
        assert result["plans_created"] == 0

    def test_tasks_created_and_completed(self, tmp_path):
        _write_tasks(str(tmp_path), {
            "session1": [
                {"id": "1", "subject": "Task 1", "status": "completed"},
                {"id": "2", "subject": "Task 2", "status": "completed"},
                {"id": "3", "subject": "Task 3", "status": "pending"},
            ],
            "session2": [
                {"id": "1", "subject": "Task A", "status": "completed"},
                {"id": "2", "subject": "Task B", "status": "in_progress"},
            ],
        })
        result = parse_tasks_and_plans(str(tmp_path))
        assert result["tasks_created"] == 5
        assert result["tasks_completed"] == 3

    def test_plans_created(self, tmp_path):
        _write_plans(str(tmp_path), ["plan-a.md", "plan-b.md", "plan-c.md"])
        result = parse_tasks_and_plans(str(tmp_path))
        assert result["plans_created"] == 3

    def test_combined(self, tmp_path):
        _write_tasks(str(tmp_path), {
            "s1": [{"id": "1", "subject": "T", "status": "completed"}],
        })
        _write_plans(str(tmp_path), ["plan.md"])
        result = parse_tasks_and_plans(str(tmp_path))
        assert result["tasks_created"] == 1
        assert result["tasks_completed"] == 1
        assert result["plans_created"] == 1

    def test_malformed_task_skipped(self, tmp_path):
        task_dir = os.path.join(str(tmp_path), "tasks", "s1")
        os.makedirs(task_dir)
        with open(os.path.join(task_dir, "1.json"), "w") as f:
            f.write("not json")
        result = parse_tasks_and_plans(str(tmp_path))
        assert result["tasks_created"] == 0
