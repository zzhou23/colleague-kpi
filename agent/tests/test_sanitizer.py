import os
import json

from agent.sanitizer import sanitize_claude_dir


def test_removes_credentials(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / ".credentials.json").write_text('{"token": "secret"}')
    (claude_dir / "history.jsonl").write_text('{"display": "/init"}')

    result = sanitize_claude_dir(str(claude_dir))
    assert not os.path.exists(os.path.join(result, ".credentials.json"))
    assert os.path.exists(os.path.join(result, "history.jsonl"))


def test_removes_env_files(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    session_env = claude_dir / "session-env"
    session_env.mkdir()
    (session_env / "env.json").write_text('{"SECRET_KEY": "abc"}')
    (claude_dir / "settings.json").write_text('{}')

    result = sanitize_claude_dir(str(claude_dir))
    assert not os.path.exists(os.path.join(result, "session-env"))
    assert os.path.exists(os.path.join(result, "settings.json"))


def test_preserves_directory_structure(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    sessions = claude_dir / "sessions"
    sessions.mkdir()
    (sessions / "123.json").write_text('{"id": "123"}')
    projects = claude_dir / "projects" / "myproject" / "memory"
    projects.mkdir(parents=True)
    (projects / "MEMORY.md").write_text("# Memory")

    result = sanitize_claude_dir(str(claude_dir))
    assert os.path.exists(os.path.join(result, "sessions", "123.json"))
    assert os.path.exists(os.path.join(result, "projects", "myproject", "memory", "MEMORY.md"))
