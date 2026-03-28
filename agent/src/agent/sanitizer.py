import os
import shutil
import tempfile

EXCLUDED_FILES = {
    ".credentials.json",
    "mcp-needs-auth-cache.json",
    "notify.ps1",
}

EXCLUDED_DIRS = {
    "session-env",
    "cache",
    "downloads",
    "shell-snapshots",
    "debug",
    "backups",
    "plugins",
}


def sanitize_claude_dir(claude_dir: str) -> str:
    """Copy claude_dir to a temp directory, removing sensitive files.
    Returns the path to the sanitized temporary directory.
    """
    temp_dir = tempfile.mkdtemp(prefix="claude_sanitized_")

    for root, dirs, files in os.walk(claude_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        rel_root = os.path.relpath(root, claude_dir)
        dest_root = os.path.join(temp_dir, rel_root) if rel_root != "." else temp_dir

        os.makedirs(dest_root, exist_ok=True)

        for filename in files:
            if filename in EXCLUDED_FILES:
                continue
            src = os.path.join(root, filename)
            dst = os.path.join(dest_root, filename)
            shutil.copy2(src, dst)

    return temp_dir
