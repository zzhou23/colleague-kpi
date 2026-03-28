"""Parser for configuration data — settings.json, CLAUDE.md, rules/, memory/."""

import json
import logging
import os

logger = logging.getLogger(__name__)


def parse_config(claude_dir: str) -> dict[str, int | float]:
    """Parse configuration files to extract config-level metrics.

    These are "snapshot" metrics — not per-month but reflect current state.
    The orchestrator applies them to all months in the upload.

    Returns dict with:
        - rules_count: CLAUDE.md + rules/*.md files
        - memory_file_count: files across projects/*/memory/
        - custom_settings_count: top-level keys in settings.json
        - hooks_count: hook event types in settings.json
    """
    return {
        "rules_count": _count_rules(claude_dir),
        "memory_file_count": _count_memory_files(claude_dir),
        "custom_settings_count": _count_settings(claude_dir),
        "hooks_count": _count_hooks(claude_dir),
    }


def _count_rules(claude_dir: str) -> int:
    """Count CLAUDE.md + all files in rules/ directory."""
    count = 0

    claude_md = os.path.join(claude_dir, "CLAUDE.md")
    if os.path.isfile(claude_md):
        count += 1

    rules_dir = os.path.join(claude_dir, "rules")
    if os.path.isdir(rules_dir):
        for fname in os.listdir(rules_dir):
            if os.path.isfile(os.path.join(rules_dir, fname)):
                count += 1

    return count


def _count_memory_files(claude_dir: str) -> int:
    """Count memory files across all projects."""
    count = 0
    projects_dir = os.path.join(claude_dir, "projects")
    if not os.path.isdir(projects_dir):
        return 0

    for project_name in os.listdir(projects_dir):
        memory_dir = os.path.join(projects_dir, project_name, "memory")
        if os.path.isdir(memory_dir):
            for fname in os.listdir(memory_dir):
                if os.path.isfile(os.path.join(memory_dir, fname)):
                    count += 1

    return count


def _count_settings(claude_dir: str) -> int:
    """Count top-level keys in settings.json."""
    settings_path = os.path.join(claude_dir, "settings.json")
    if not os.path.isfile(settings_path):
        return 0

    try:
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return len(data)
    except (json.JSONDecodeError, OSError):
        logger.debug("Could not parse settings.json")

    return 0


def _count_hooks(claude_dir: str) -> int:
    """Count hook event types in settings.json."""
    settings_path = os.path.join(claude_dir, "settings.json")
    if not os.path.isfile(settings_path):
        return 0

    try:
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
        hooks = data.get("hooks", {})
        if isinstance(hooks, dict):
            return len(hooks)
    except (json.JSONDecodeError, OSError):
        logger.debug("Could not parse settings.json for hooks")

    return 0
