import os
import shutil
import tarfile
import tempfile

from agent.sanitizer import sanitize_claude_dir


def collect_claude_data(claude_dir: str) -> str:
    """Sanitize claude_dir and pack into a .tar.gz archive.

    Returns the path to the created tar.gz file.
    The caller is responsible for cleaning up the returned file.
    """
    sanitized_dir = sanitize_claude_dir(claude_dir)

    try:
        output_dir = tempfile.mkdtemp(prefix="claude_archive_")
        tar_path = os.path.join(output_dir, "claude_data.tar.gz")

        with tarfile.open(tar_path, "w:gz") as tar:
            for entry in os.listdir(sanitized_dir):
                full_path = os.path.join(sanitized_dir, entry)
                tar.add(full_path, arcname=entry)

        return tar_path
    finally:
        shutil.rmtree(sanitized_dir, ignore_errors=True)
