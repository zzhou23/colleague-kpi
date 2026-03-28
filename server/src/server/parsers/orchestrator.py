"""Orchestrator — extract tar.gz, run all parsers, write ParsedMetrics to DB."""

import logging
import os
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from server.db.models import ParsedMetrics, UploadRecord
from server.parsers.config import parse_config
from server.parsers.history import parse_history
from server.parsers.sessions import parse_sessions
from server.parsers.tasks import parse_tasks_and_plans
from server.parsers.types import merge_parser_results

logger = logging.getLogger(__name__)


def process_upload(upload_id: int, database_url: str) -> list[ParsedMetrics]:
    """Process a pending upload: extract, parse, and write metrics to DB.

    Args:
        upload_id: ID of the UploadRecord to process.
        database_url: SQLAlchemy database URL.

    Returns:
        List of ParsedMetrics records created.
    """
    sync_url = database_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    engine = create_engine(sync_url)

    with Session(engine) as session:
        record = session.get(UploadRecord, upload_id)
        if record is None:
            raise ValueError(f"Upload record {upload_id} not found")

        if record.status != "pending":
            raise ValueError(f"Upload {upload_id} is not pending (status={record.status})")

        # Mark as processing
        record.status = "processing"
        session.commit()

        try:
            metrics_list = _extract_and_parse(record.file_path)

            # Write metrics to DB
            created: list[ParsedMetrics] = []
            for m in metrics_list:
                pm = ParsedMetrics(
                    employee_id=record.employee_id,
                    upload_id=upload_id,
                    metric_date=m.metric_date,
                    active_days=m.active_days,
                    session_count=m.session_count,
                    total_turns=m.total_turns,
                    avg_session_duration=m.avg_session_duration,
                    project_count=m.project_count,
                    tool_types_used=m.tool_types_used,
                    complex_session_count=m.complex_session_count,
                    tasks_created=m.tasks_created,
                    tasks_completed=m.tasks_completed,
                    plans_created=m.plans_created,
                    model_switches=m.model_switches,
                    rules_count=m.rules_count,
                    memory_file_count=m.memory_file_count,
                    custom_settings_count=m.custom_settings_count,
                    hooks_count=m.hooks_count,
                    skills_used=m.skills_used,
                    abandoned_sessions=m.abandoned_sessions,
                    git_commits_in_session=m.git_commits_in_session,
                    repeated_queries=m.repeated_queries,
                    error_recovery_avg_turns=m.error_recovery_avg_turns,
                    estimated_tokens=m.estimated_tokens,
                    empty_sessions=m.empty_sessions,
                    large_file_reads=m.large_file_reads,
                    repeated_operations=m.repeated_operations,
                    rejected_commands=m.rejected_commands,
                )
                session.add(pm)
                created.append(pm)

            record.status = "completed"
            record.parsed_at = datetime.now(timezone.utc)
            session.commit()

            for pm in created:
                session.refresh(pm)

            return created

        except Exception:
            record.status = "failed"
            session.commit()
            logger.exception("Failed to process upload %d", upload_id)
            raise


def _extract_and_parse(tar_path: str) -> list:
    """Extract tar.gz and run all parsers.

    Returns list of MonthlyMetrics.
    """
    from server.parsers.types import MonthlyMetrics

    tmp_dir = tempfile.mkdtemp(prefix="claude_parse_")
    try:
        # Extract tar.gz
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(tmp_dir, filter="data")

        # Find the claude directory inside the extraction
        claude_dir = _find_claude_dir(tmp_dir)

        # Run parsers
        history_result = parse_history(claude_dir)
        sessions_result = parse_sessions(claude_dir)

        # Config and tasks are snapshot metrics (not per-month)
        config_globals = parse_config(claude_dir)
        tasks_globals = parse_tasks_and_plans(claude_dir)

        # Merge snapshot metrics
        all_globals = {**config_globals, **tasks_globals}

        # Merge per-month results with globals
        metrics = merge_parser_results(
            [history_result, sessions_result],
            config_globals=all_globals,
        )

        return metrics

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _find_claude_dir(extracted_dir: str) -> str:
    """Find the root of the claude data in the extracted directory.

    The tar.gz might contain files directly or in a subdirectory.
    Look for telltale files like history.jsonl or sessions/.
    """
    # Check if extracted_dir itself has claude data
    if _is_claude_dir(extracted_dir):
        return extracted_dir

    # Check one level of subdirectories
    for name in os.listdir(extracted_dir):
        subdir = os.path.join(extracted_dir, name)
        if os.path.isdir(subdir) and _is_claude_dir(subdir):
            return subdir

    # Fallback: just use extracted_dir
    return extracted_dir


def _is_claude_dir(path: str) -> bool:
    """Check if a directory looks like a .claude data directory."""
    indicators = ["history.jsonl", "sessions", "projects", "settings.json"]
    return any(os.path.exists(os.path.join(path, f)) for f in indicators)
