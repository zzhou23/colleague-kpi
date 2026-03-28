import os
import tarfile

from agent.collector import collect_claude_data


def test_returns_tar_gz_file(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text('{"theme": "dark"}')

    result = collect_claude_data(str(claude_dir))

    assert result.endswith(".tar.gz")
    assert os.path.isfile(result)


def test_tar_contains_sanitized_files(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text('{"theme": "dark"}')
    (claude_dir / ".credentials.json").write_text('{"token": "secret"}')

    result = collect_claude_data(str(claude_dir))

    with tarfile.open(result, "r:gz") as tar:
        names = tar.getnames()
    assert any("settings.json" in n for n in names)
    assert not any(".credentials.json" in n for n in names)


def test_preserves_nested_structure(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    projects = claude_dir / "projects" / "myproject"
    projects.mkdir(parents=True)
    (projects / "CLAUDE.md").write_text("# Rules")

    result = collect_claude_data(str(claude_dir))

    with tarfile.open(result, "r:gz") as tar:
        names = tar.getnames()
    assert any("projects/myproject/CLAUDE.md" in n for n in names)


def test_cleanup_removes_temp_dir(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text("{}")

    result = collect_claude_data(str(claude_dir))

    # The sanitized temp dir should be cleaned up, only tar.gz remains
    tar_dir = os.path.dirname(result)
    items = os.listdir(tar_dir)
    assert len(items) == 1
    assert items[0].endswith(".tar.gz")
