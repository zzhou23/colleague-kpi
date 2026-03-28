"""Shared types for parser modules."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MonthlyMetrics:
    """Raw metrics extracted from ~/.claude data, grouped by YYYY-MM."""

    metric_date: str  # "YYYY-MM"

    # Activity
    active_days: int = 0
    session_count: int = 0
    total_turns: int = 0
    avg_session_duration: float = 0.0

    # Quality
    project_count: int = 0
    tool_types_used: int = 0
    complex_session_count: int = 0
    tasks_created: int = 0
    tasks_completed: int = 0
    plans_created: int = 0

    # Configuration
    model_switches: int = 0
    rules_count: int = 0
    memory_file_count: int = 0
    custom_settings_count: int = 0
    hooks_count: int = 0
    skills_used: int = 0

    # Efficiency
    abandoned_sessions: int = 0
    git_commits_in_session: int = 0
    repeated_queries: int = 0
    error_recovery_avg_turns: float = 0.0

    # Resource
    estimated_tokens: int = 0
    empty_sessions: int = 0
    large_file_reads: int = 0
    repeated_operations: int = 0
    rejected_commands: int = 0


@dataclass(frozen=True)
class ParserResult:
    """Result from a single parser, containing partial metrics keyed by month."""

    metrics_by_month: dict[str, dict[str, int | float]] = field(
        default_factory=dict
    )


def merge_parser_results(
    results: list[ParserResult], config_globals: dict[str, int | float] | None = None
) -> list[MonthlyMetrics]:
    """Merge multiple ParserResults into MonthlyMetrics per month.

    Args:
        results: List of ParserResult from individual parsers.
        config_globals: Config metrics (rules_count, etc.) that apply to all months.

    Returns:
        List of MonthlyMetrics, one per month found in the data.
    """
    all_months: set[str] = set()
    for r in results:
        all_months.update(r.metrics_by_month.keys())

    merged: list[MonthlyMetrics] = []
    for month in sorted(all_months):
        combined: dict[str, int | float] = {}
        for r in results:
            if month in r.metrics_by_month:
                combined.update(r.metrics_by_month[month])
        if config_globals:
            combined.update(config_globals)
        merged.append(MonthlyMetrics(metric_date=month, **combined))

    return merged
