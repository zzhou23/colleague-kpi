import logging
import os
import shutil

from apscheduler.schedulers.blocking import BlockingScheduler

from agent.collector import collect_claude_data
from agent.config import AgentConfig
from agent.uploader import UploadResult, upload_to_server

logger = logging.getLogger(__name__)


def run_job(
    claude_dir: str,
    server_url: str,
    api_key: str,
) -> UploadResult:
    """Collect claude data and upload to server. Cleans up temp files."""
    tar_path = collect_claude_data(claude_dir)
    try:
        result = upload_to_server(
            file_path=tar_path,
            server_url=server_url,
            api_key=api_key,
        )
        if result.success:
            logger.info("Upload succeeded, upload_id=%s", result.upload_id)
        else:
            logger.error("Upload failed: %s", result.error)
        return result
    finally:
        # Clean up tar.gz and its temp directory
        tar_dir = os.path.dirname(tar_path)
        shutil.rmtree(tar_dir, ignore_errors=True)


def main() -> None:
    """Entry point: run the collection job on a schedule."""
    logging.basicConfig(level=logging.INFO)
    config = AgentConfig()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_job,
        "cron",
        hour=config.schedule_hour,
        minute=config.schedule_minute,
        kwargs={
            "claude_dir": config.claude_dir,
            "server_url": config.server_url,
            "api_key": config.api_key,
        },
    )

    logger.info(
        "Scheduler started, will run daily at %02d:%02d",
        config.schedule_hour,
        config.schedule_minute,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
