"""Scoring engine — converts ParsedMetrics into scores, categories, and grades."""

from dataclasses import dataclass

from server.parsers.types import MonthlyMetrics
from server.scoring.dimensions import DIMENSIONS
from server.scoring.grades import assign_grade


@dataclass(frozen=True)
class DimensionScoreResult:
    name: str
    category: str
    metric_field: str
    raw_value: float
    score: float
    weight: float


@dataclass(frozen=True)
class ScoringResult:
    metric_date: str
    dimension_scores: list[DimensionScoreResult]
    category_scores: dict[str, float]
    category_weights: dict[str, float]
    total_score: float
    grade: str


# Category weights for the total score (sum to 1.0)
CATEGORY_WEIGHTS: dict[str, float] = {
    "activity": 0.25,
    "quality": 0.25,
    "configuration": 0.10,
    "efficiency": 0.25,
    "resource": 0.15,
}


def score_metrics(metrics: MonthlyMetrics) -> ScoringResult:
    """Score a MonthlyMetrics record across all dimensions.

    Returns a ScoringResult with per-dimension scores, category aggregates,
    weighted total, and letter grade.
    """
    dimension_scores: list[DimensionScoreResult] = []

    for dim in DIMENSIONS:
        raw_value = float(getattr(metrics, dim.metric_field, 0))
        score = dim.scorer(raw_value)
        dimension_scores.append(
            DimensionScoreResult(
                name=dim.name,
                category=dim.category,
                metric_field=dim.metric_field,
                raw_value=raw_value,
                score=score,
                weight=dim.weight,
            )
        )

    # Aggregate: weighted average per category
    category_scores: dict[str, float] = {}
    for cat in CATEGORY_WEIGHTS:
        cat_dims = [ds for ds in dimension_scores if ds.category == cat]
        if cat_dims:
            category_scores[cat] = sum(ds.score * ds.weight for ds in cat_dims)
        else:
            category_scores[cat] = 0.0

    # Total: weighted average of categories
    total_score = sum(
        category_scores[cat] * weight for cat, weight in CATEGORY_WEIGHTS.items()
    )

    grade = assign_grade(total_score)

    return ScoringResult(
        metric_date=metrics.metric_date,
        dimension_scores=dimension_scores,
        category_scores=category_scores,
        category_weights=CATEGORY_WEIGHTS,
        total_score=total_score,
        grade=grade,
    )
