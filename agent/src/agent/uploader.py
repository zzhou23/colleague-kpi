from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class UploadResult:
    success: bool
    upload_id: int | None = None
    error: str | None = None


def upload_to_server(
    file_path: str,
    server_url: str,
    api_key: str,
    timeout: float = 30.0,
) -> UploadResult:
    """Upload a tar.gz file to the server's /upload endpoint."""
    try:
        with open(file_path, "rb") as f:
            response = httpx.post(
                f"{server_url}/upload",
                files={"file": ("claude_data.tar.gz", f, "application/gzip")},
                headers={"x-api-key": api_key},
                timeout=timeout,
            )

        if response.status_code == 200:
            data = response.json()
            return UploadResult(success=True, upload_id=data["upload_id"])

        return UploadResult(
            success=False,
            error=f"Server returned {response.status_code}: {response.text}",
        )
    except httpx.HTTPError as exc:
        return UploadResult(success=False, error=str(exc))
