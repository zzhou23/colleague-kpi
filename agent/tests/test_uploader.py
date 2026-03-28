import json

import httpx
import pytest

from agent.uploader import upload_to_server, UploadResult


@pytest.fixture
def tar_file(tmp_path):
    """Create a dummy tar.gz file for testing."""
    import tarfile
    tar_path = tmp_path / "test.tar.gz"
    with tarfile.open(str(tar_path), "w:gz") as tar:
        info = tarfile.TarInfo(name="settings.json")
        data = b'{"theme": "dark"}'
        info.size = len(data)
        import io
        tar.addfile(info, io.BytesIO(data))
    return str(tar_path)


def test_upload_success(tar_file, httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:8000/upload",
        method="POST",
        json={"status": "received", "upload_id": 42},
        status_code=200,
    )

    result = upload_to_server(
        file_path=tar_file,
        server_url="http://localhost:8000",
        api_key="test-key-123",
    )

    assert result.success is True
    assert result.upload_id == 42

    request = httpx_mock.get_request()
    assert request.headers["x-api-key"] == "test-key-123"


def test_upload_auth_failure(tar_file, httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:8000/upload",
        method="POST",
        json={"detail": "Invalid API key"},
        status_code=401,
    )

    result = upload_to_server(
        file_path=tar_file,
        server_url="http://localhost:8000",
        api_key="bad-key",
    )

    assert result.success is False
    assert "401" in result.error


def test_upload_network_error(tar_file, httpx_mock):
    httpx_mock.add_exception(
        httpx.ConnectError("Connection refused"),
        url="http://localhost:8000/upload",
    )

    result = upload_to_server(
        file_path=tar_file,
        server_url="http://localhost:8000",
        api_key="test-key",
    )

    assert result.success is False
    assert result.error is not None
