import os
from unittest.mock import patch, MagicMock

from agent.scheduler import run_job
from agent.uploader import UploadResult


def test_run_job_collects_and_uploads(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text("{}")

    fake_result = UploadResult(success=True, upload_id=99)

    with patch("agent.scheduler.upload_to_server", return_value=fake_result) as mock_upload:
        result = run_job(
            claude_dir=str(claude_dir),
            server_url="http://localhost:8000",
            api_key="test-key",
        )

    assert result.success is True
    assert result.upload_id == 99
    mock_upload.assert_called_once()
    # The tar.gz file passed to uploader should exist at call time
    call_args = mock_upload.call_args
    assert call_args.kwargs["server_url"] == "http://localhost:8000"
    assert call_args.kwargs["api_key"] == "test-key"


def test_run_job_cleans_up_tar_after_upload(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text("{}")

    fake_result = UploadResult(success=True, upload_id=1)
    tar_paths = []

    def capture_upload(file_path, **kwargs):
        tar_paths.append(file_path)
        return fake_result

    with patch("agent.scheduler.upload_to_server", side_effect=capture_upload):
        run_job(
            claude_dir=str(claude_dir),
            server_url="http://localhost:8000",
            api_key="test-key",
        )

    # tar.gz and its parent temp dir should be cleaned up
    assert len(tar_paths) == 1
    assert not os.path.exists(tar_paths[0])


def test_run_job_cleans_up_on_upload_failure(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text("{}")

    fake_result = UploadResult(success=False, error="Server returned 500")
    tar_paths = []

    def capture_upload(file_path, **kwargs):
        tar_paths.append(file_path)
        return fake_result

    with patch("agent.scheduler.upload_to_server", side_effect=capture_upload):
        result = run_job(
            claude_dir=str(claude_dir),
            server_url="http://localhost:8000",
            api_key="test-key",
        )

    assert result.success is False
    # Still cleans up even on failure
    assert not os.path.exists(tar_paths[0])
