"""Dimension definitions: what to measure, how to score, and relative weight."""

from dataclasses import dataclass
from functools import partial
from typing import Callable

from server.scoring.functions import (
    capped_linear_score,
    inverse_score,
    linear_score,
    ratio_score,
    threshold_score,
)


@dataclass(frozen=True)
class Dimension:
    name: str
    category: str  # activity | quality | configuration | efficiency | resource
    metric_field: str  # field name on MonthlyMetrics / ParsedMetrics
    scorer: Callable[[float], float]  # raw_value -> 0-100 score
    weight: float  # weight within category, category weights sum to 1.0


# --- Activity (4 dimensions, weights sum to 1.0) ---

_activity_dims = [
    Dimension(
        name="active_days",
        category="activity",
        metric_field="active_days",
        scorer=partial(linear_score, min_val=0, max_val=25),
        weight=0.30,
    ),
    Dimension(
        name="session_count",
        category="activity",
        metric_field="session_count",
        scorer=partial(capped_linear_score, cap=60, max_val=150),
        weight=0.25,
    ),
    Dimension(
        name="total_turns",
        category="activity",
        metric_field="total_turns",
        scorer=partial(capped_linear_score, cap=500, max_val=2000),
        weight=0.25,
    ),
    Dimension(
        name="avg_session_duration",
        category="activity",
        metric_field="avg_session_duration",
        scorer=partial(capped_linear_score, cap=15.0, max_val=60.0),
        weight=0.20,
    ),
]

# --- Quality (6 dimensions, weights sum to 1.0) ---

_quality_dims = [
    Dimension(
        name="project_count",
        category="quality",
        metric_field="project_count",
        scorer=partial(capped_linear_score, cap=3, max_val=10),
        weight=0.15,
    ),
    Dimension(
        name="tool_diversity",
        category="quality",
        metric_field="tool_types_used",
        scorer=partial(capped_linear_score, cap=5, max_val=12),
        weight=0.20,
    ),
    Dimension(
        name="complex_sessions",
        category="quality",
        metric_field="complex_session_count",
        scorer=partial(capped_linear_score, cap=10, max_val=30),
        weight=0.20,
    ),
    Dimension(
        name="tasks_created",
        category="quality",
        metric_field="tasks_created",
        scorer=partial(threshold_score, threshold=5),
        weight=0.15,
    ),
    Dimension(
        name="tasks_completed",
        category="quality",
        metric_field="tasks_completed",
        scorer=partial(threshold_score, threshold=5),
        weight=0.15,
    ),
    Dimension(
        name="plans_created",
        category="quality",
        metric_field="plans_created",
        scorer=partial(threshold_score, threshold=3),
        weight=0.15,
    ),
]

# --- Configuration (6 dimensions, weights sum to 1.0) ---

_configuration_dims = [
    Dimension(
        name="model_switches",
        category="configuration",
        metric_field="model_switches",
        scorer=partial(threshold_score, threshold=2),
        weight=0.10,
    ),
    Dimension(
        name="rules_count",
        category="configuration",
        metric_field="rules_count",
        scorer=partial(capped_linear_score, cap=3, max_val=10),
        weight=0.25,
    ),
    Dimension(
        name="memory_files",
        category="configuration",
        metric_field="memory_file_count",
        scorer=partial(threshold_score, threshold=3),
        weight=0.20,
    ),
    Dimension(
        name="custom_settings",
        category="configuration",
        metric_field="custom_settings_count",
        scorer=partial(threshold_score, threshold=5),
        weight=0.15,
    ),
    Dimension(
        name="hooks_usage",
        category="configuration",
        metric_field="hooks_count",
        scorer=partial(threshold_score, threshold=2),
        weight=0.15,
    ),
    Dimension(
        name="skills_used",
        category="configuration",
        metric_field="skills_used",
        scorer=partial(threshold_score, threshold=3),
        weight=0.15,
    ),
]

# --- Efficiency (4 dimensions, weights sum to 1.0) ---

_efficiency_dims = [
    Dimension(
        name="low_abandonment",
        category="efficiency",
        metric_field="abandoned_sessions",
        scorer=partial(inverse_score, max_bad=20),
        weight=0.30,
    ),
    Dimension(
        name="git_commits",
        category="efficiency",
        metric_field="git_commits_in_session",
        scorer=partial(capped_linear_score, cap=20, max_val=60),
        weight=0.30,
    ),
    Dimension(
        name="low_repeated_queries",
        category="efficiency",
        metric_field="repeated_queries",
        scorer=partial(inverse_score, max_bad=15),
        weight=0.20,
    ),
    Dimension(
        name="error_recovery",
        category="efficiency",
        metric_field="error_recovery_avg_turns",
        scorer=partial(inverse_score, max_bad=10.0),
        weight=0.20,
    ),
]

# --- Resource (5 dimensions, weights sum to 1.0) ---

_resource_dims = [
    Dimension(
        name="token_efficiency",
        category="resource",
        metric_field="estimated_tokens",
        scorer=partial(inverse_score, max_bad=5_000_000),
        weight=0.25,
    ),
    Dimension(
        name="low_empty_sessions",
        category="resource",
        metric_field="empty_sessions",
        scorer=partial(inverse_score, max_bad=20),
        weight=0.20,
    ),
    Dimension(
        name="low_large_file_reads",
        category="resource",
        metric_field="large_file_reads",
        scorer=partial(inverse_score, max_bad=30),
        weight=0.20,
    ),
    Dimension(
        name="low_repeated_ops",
        category="resource",
        metric_field="repeated_operations",
        scorer=partial(inverse_score, max_bad=20),
        weight=0.20,
    ),
    Dimension(
        name="low_rejected_commands",
        category="resource",
        metric_field="rejected_commands",
        scorer=partial(inverse_score, max_bad=15),
        weight=0.15,
    ),
]

DIMENSIONS: list[Dimension] = (
    _activity_dims
    + _quality_dims
    + _configuration_dims
    + _efficiency_dims
    + _resource_dims
)
