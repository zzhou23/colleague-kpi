"""Top-level scoring orchestration — bridge between ParsedMetrics and scoring engine."""

from sqlalchemy.orm import Session

from server.db.models import MonthlyReport, ParsedMetrics
from server.parsers.types import MonthlyMetrics
from server.scoring.engine import score_metrics
from server.scoring.persist import persist_scoring_result


def score_employee_month(
    session: Session, employee_id: int, year_month: str
) -> MonthlyReport | None:
    """Score a single employee for a single month.

    Reads the latest ParsedMetrics for the employee+month, runs the scoring
    engine, and persists results.

    Returns the MonthlyReport, or None if no ParsedMetrics found.
    """
    pm = (
        session.query(ParsedMetrics)
        .filter_by(employee_id=employee_id, metric_date=year_month)
        .order_by(ParsedMetrics.id.desc())
        .first()
    )

    if pm is None:
        return None

    metrics = MonthlyMetrics(
        metric_date=pm.metric_date,
        active_days=pm.active_days,
        session_count=pm.session_count,
        total_turns=pm.total_turns,
        avg_session_duration=pm.avg_session_duration,
        project_count=pm.project_count,
        tool_types_used=pm.tool_types_used,
        complex_session_count=pm.complex_session_count,
        tasks_created=pm.tasks_created,
        tasks_completed=pm.tasks_completed,
        plans_created=pm.plans_created,
        model_switches=pm.model_switches,
        rules_count=pm.rules_count,
        memory_file_count=pm.memory_file_count,
        custom_settings_count=pm.custom_settings_count,
        hooks_count=pm.hooks_count,
        skills_used=pm.skills_used,
        abandoned_sessions=pm.abandoned_sessions,
        git_commits_in_session=pm.git_commits_in_session,
        repeated_queries=pm.repeated_queries,
        error_recovery_avg_turns=pm.error_recovery_avg_turns,
        estimated_tokens=pm.estimated_tokens,
        empty_sessions=pm.empty_sessions,
        large_file_reads=pm.large_file_reads,
        repeated_operations=pm.repeated_operations,
        rejected_commands=pm.rejected_commands,
    )

    scoring_result = score_metrics(metrics)
    return persist_scoring_result(session, employee_id, scoring_result)
