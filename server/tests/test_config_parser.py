"""Tests for config parser (settings, rules, memory)."""

import json
import os

import pytest

from server.parsers.config import parse_config


def _write_settings(tmp_path: str, settings: dict):
    with open(os.path.join(tmp_path, "settings.json"), "w") as f:
        json.dump(settings, f)


def _write_claude_md(tmp_path: str, content: str = "# Rules"):
    with open(os.path.join(tmp_path, "CLAUDE.md"), "w") as f:
        f.write(content)


def _write_rules(tmp_path: str, rules: list[str]):
    rules_dir = os.path.join(tmp_path, "rules")
    os.makedirs(rules_dir, exist_ok=True)
    for name in rules:
        with open(os.path.join(rules_dir, name), "w") as f:
            f.write(f"# {name}")


def _write_memory(tmp_path: str, projects: dict[str, list[str]]):
    """Create projects/<name>/memory/<files> structure."""
    for proj, files in projects.items():
        mem_dir = os.path.join(tmp_path, "projects", proj, "memory")
        os.makedirs(mem_dir, exist_ok=True)
        for fname in files:
            with open(os.path.join(mem_dir, fname), "w") as f:
                f.write("memory content")


class TestParseConfig:
    def test_empty_directory(self, tmp_path):
        result = parse_config(str(tmp_path))
        assert result["rules_count"] == 0
        assert result["memory_file_count"] == 0
        assert result["custom_settings_count"] == 0
        assert result["hooks_count"] == 0

    def test_settings_custom_count(self, tmp_path):
        """Count non-default settings entries."""
        _write_settings(str(tmp_path), {
            "permissions": {"allow": ["Bash(git*)"]},
            "hooks": {},
            "model": "opus",
            "voiceEnabled": True,
            "autoUpdatesChannel": "latest",
        })
        result = parse_config(str(tmp_path))
        # permissions, hooks, model, voiceEnabled, autoUpdatesChannel = 5 top-level keys
        assert result["custom_settings_count"] == 5

    def test_hooks_count(self, tmp_path):
        """Count hook event types."""
        _write_settings(str(tmp_path), {
            "hooks": {
                "Notification": [{"matcher": "", "hooks": [{"type": "command", "command": "notify.ps1"}]}],
                "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": "startup.sh"}]}],
            },
        })
        result = parse_config(str(tmp_path))
        assert result["hooks_count"] == 2

    def test_rules_count_with_claude_md(self, tmp_path):
        """CLAUDE.md + rules/*.md are all counted."""
        _write_claude_md(str(tmp_path))
        _write_rules(str(tmp_path), ["coding.md", "testing.md"])
        result = parse_config(str(tmp_path))
        assert result["rules_count"] == 3  # CLAUDE.md + 2 rules

    def test_rules_count_no_claude_md(self, tmp_path):
        """Only rules/ files when no CLAUDE.md."""
        _write_rules(str(tmp_path), ["style.md"])
        result = parse_config(str(tmp_path))
        assert result["rules_count"] == 1

    def test_memory_file_count(self, tmp_path):
        """Count memory files across all projects."""
        _write_memory(str(tmp_path), {
            "proj1": ["MEMORY.md", "user_prefs.md"],
            "proj2": ["MEMORY.md"],
        })
        result = parse_config(str(tmp_path))
        assert result["memory_file_count"] == 3

    def test_no_memory_dirs(self, tmp_path):
        """No memory directory returns 0."""
        result = parse_config(str(tmp_path))
        assert result["memory_file_count"] == 0
