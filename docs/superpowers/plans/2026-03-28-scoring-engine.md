# Scoring Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scoring engine that converts raw `ParsedMetrics` into per-dimension scores, category aggregates, grades (S/A/B/C/D), and `MonthlyReport` records.

**Architecture:** The scoring engine is a pure-function pipeline: `ParsedMetrics` → dimension definitions (with scoring functions) → `DimensionScore` records → weighted category aggregation → grade assignment → `MonthlyReport`. All scoring logic is stateless and testable without a database. A thin DB layer calls the pure functions and persists results.

**Tech Stack:** Python 3.12, SQLAlchemy (sync Session), pytest, frozen dataclasses

---

## File Structure

| File | Responsibility |
|------|---------------|
| `server/src/server/scoring/__init__.py` | Package init (empty) |
| `server/src/server/scoring/dimensions.py` | Dimension definitions: name, category, metric field, scoring function, weight |
| `server/src/server/scoring/functions.py` | Pure scoring functions (linear, threshold, ratio, inverse) |
| `server/src/server/scoring/engine.py` | `score_metrics()` — takes ParsedMetrics, returns scored dimensions + category scores + grade |
| `server/src/server/scoring/grades.py` | Grade boundaries and assignment function |
| `server/src/server/scoring/persist.py` | DB persistence: write DimensionScore + MonthlyReport rows |
| `server/tests/test_scoring_functions.py` | Unit tests for pure scoring functions |
| `server/tests/test_dimensions.py` | Tests for dimension registry completeness |
| `server/tests/test_engine.py` | Tests for the scoring pipeline end-to-end (no DB) |
| `server/tests/test_grades.py` | Tests for grade assignment |
| `server/tests/test_scoring_persist.py` | Integration tests for DB persistence |

---

### Task 1: Pure Scoring Functions

**Files:**
- Create: `server/src/server/scoring/__init__.py`
- Create: `server/src/server/scoring/functions.py`
- Create: `server/tests/test_scoring_functions.py`

- [ ] **Step 1: Write failing tests for scoring functions**

```python
# server/tests/test_scoring_functions.py
import pytest

from server.scoring.functions import (
    linear_score,
    threshold_score,
    ratio_score,
    inverse_score,
    capped_linear_score,
)


class TestLinearScore:
    """Maps a raw value linearly to 0-100 between min_val and max_val."""

    def test_at_minimum(self):
        assert linear_score(0, min_val=0, max_val=30) == 0.0

    def test_at_maximum(self):
        assert linear_score(30, min_val=0, max_val=30) == 100.0

    def test_midpoint(self):
        assert linear_score(15, min_val=0, max_val=30) == 50.0

    def test_below_minimum_clamps_to_zero(self):
        assert linear_score(-5, min_val=0, max_val=30) == 0.0

    def test_above_maximum_clamps_to_100(self):
        assert linear_score(50, min_val=0, max_val=30) == 100.0


class TestThresholdScore:
    """Returns 100 if value >= threshold, else proportional score."""

    def test_above_threshold(self):
        assert threshold_score(10, threshold=5) == 100.0

    def test_at_threshold(self):
        assert threshold_score(5, threshold=5) == 100.0

    def test_below_threshold(self):
        assert threshold_score(2, threshold=5) == pytest.approx(40.0)

    def test_zero_value(self):
        assert threshold_score(0, threshold=5) == 0.0


class TestRatioScore:
    """Scores a ratio (numerator/denominator) on a 0-100 scale."""

    def test_perfect_ratio(self):
        assert ratio_score(10, 10, target=1.0) == 100.0

    def test_half_ratio(self):
        assert ratio_score(5, 10, target=1.0) == 50.0

    def test_zero_denominator_returns_zero(self):
        assert ratio_score(5, 0, target=1.0) == 0.0

    def test_exceeds_target_clamps(self):
        assert ratio_score(10, 5, target=1.0) == 100.0


class TestInverseScore:
    """Higher raw value = lower score (for negative metrics like abandoned sessions)."""

    def test_zero_is_perfect(self):
        assert inverse_score(0, max_bad=10) == 100.0

    def test_at_max_bad(self):
        assert inverse_score(10, max_bad=10) == 0.0

    def test_midpoint(self):
        assert inverse_score(5, max_bad=10) == 50.0

    def test_exceeds_max_bad_clamps(self):
        assert inverse_score(15, max_bad=10) == 0.0


class TestCappedLinearScore:
    """Like linear but with a soft cap — beyond cap, diminishing returns."""

    def test_below_cap(self):
        assert capped_linear_score(5, cap=10, max_val=20) == pytest.approx(50.0)

    def test_at_cap(self):
        assert capped_linear_score(10, cap=10, max_val=20) == pytest.approx(80.0)

    def test_at_max(self):
        assert capped_linear_score(20, cap=10, max_val=20) == 100.0

    def test_zero(self):
        assert capped_linear_score(0, cap=10, max_val=20) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_scoring_functions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server.scoring'`

- [ ] **Step 3: Implement scoring functions**

```python
# server/src/server/scoring/__init__.py
# (empty)
```

```python
# server/src/server/scoring/functions.py
"""Pure scoring functions that map raw metric values to 0-100 scores."""


def linear_score(value: float, *, min_val: float, max_val: float) -> float:
    """Linearly map value from [min_val, max_val] to [0, 100], clamped."""
    if max_val == min_val:
        return 100.0 if value >= max_val else 0.0
    ratio = (value - min_val) / (max_val - min_val)
    return max(0.0, min(100.0, ratio * 100.0))


def threshold_score(value: float, *, threshold: float) -> float:
    """Return 100 if value >= threshold, else proportional score."""
    if threshold == 0:
        return 100.0
    if value >= threshold:
        return 100.0
    return max(0.0, (value / threshold) * 100.0)


def ratio_score(
    numerator: float, denominator: float, *, target: float
) -> float:
    """Score based on numerator/denominator ratio vs target. 0-100, clamped."""
    if denominator == 0:
        return 0.0
    ratio = numerator / denominator
    return max(0.0, min(100.0, (ratio / target) * 100.0))


def inverse_score(value: float, *, max_bad: float) -> float:
    """Higher value = lower score. 0 is perfect (100), max_bad is worst (0)."""
    if max_bad == 0:
        return 0.0 if value > 0 else 100.0
    return max(0.0, min(100.0, (1.0 - value / max_bad) * 100.0))


def capped_linear_score(value: float, *, cap: float, max_val: float) -> float:
    """Linear up to cap (worth 80%), then diminishing returns to max_val (100%).

    Below cap:  score = (value / cap) * 80
    Above cap:  score = 80 + ((value - cap) / (max_val - cap)) * 20
    """
    if value <= 0:
        return 0.0
    if cap == 0 or max_val == 0:
        return 100.0
    if value <= cap:
        return (value / cap) * 80.0
    beyond = min(value, max_val) - cap
    return 80.0 + (beyond / (max_val - cap)) * 20.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_scoring_functions.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add server/src/server/scoring/__init__.py server/src/server/scoring/functions.py server/tests/test_scoring_functions.py
git commit -m "feat: add pure scoring functions (linear, threshold, ratio, inverse, capped)"
```

---

### Task 2: Grade Assignment

**Files:**
- Create: `server/src/server/scoring/grades.py`
- Create: `server/tests/test_grades.py`

- [ ] **Step 1: Write failing tests for grade assignment**

```python
# server/tests/test_grades.py
import pytest

from server.scoring.grades import assign_grade, GRADE_BOUNDARIES


class TestAssignGrade:
    def test_s_grade(self):
        assert assign_grade(95.0) == "S"

    def test_a_grade(self):
        assert assign_grade(82.0) == "A"

    def test_b_grade(self):
        assert assign_grade(65.0) == "B"

    def test_c_grade(self):
        assert assign_grade(50.0) == "C"

    def test_d_grade(self):
        assert assign_grade(30.0) == "D"

    def test_boundary_s(self):
        assert assign_grade(90.0) == "S"

    def test_boundary_a(self):
        assert assign_grade(75.0) == "A"

    def test_boundary_b(self):
        assert assign_grade(60.0) == "B"

    def test_boundary_c(self):
        assert assign_grade(40.0) == "C"

    def test_zero(self):
        assert assign_grade(0.0) == "D"

    def test_perfect(self):
        assert assign_grade(100.0) == "S"


class TestGradeBoundaries:
    def test_boundaries_are_descending(self):
        scores = [b[0] for b in GRADE_BOUNDARIES]
        assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_grades.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement grade assignment**

```python
# server/src/server/scoring/grades.py
"""Grade assignment from total score."""

# (min_score, grade) — checked top-down, first match wins
GRADE_BOUNDARIES: list[tuple[float, str]] = [
    (90.0, "S"),
    (75.0, "A"),
    (60.0, "B"),
    (40.0, "C"),
    (0.0, "D"),
]


def assign_grade(total_score: float) -> str:
    """Assign S/A/B/C/D grade based on total score (0-100)."""
    for min_score, grade in GRADE_BOUNDARIES:
        if total_score >= min_score:
            return grade
    return "D"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_grades.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add server/src/server/scoring/grades.py server/tests/test_grades.py
git commit -m "feat: add grade assignment (S/A/B/C/D) with boundaries"
```

---

### Task 3: Dimension Definitions

**Files:**
- Create: `server/src/server/scoring/dimensions.py`
- Create: `server/tests/test_dimensions.py`

- [ ] **Step 1: Write failing tests for dimension registry**

```python
# server/tests/test_dimensions.py
import pytest

from server.scoring.dimensions import DIMENSIONS, Dimension
from server.parsers.types import MonthlyMetrics


EXPECTED_CATEGORIES = {"activity", "quality", "configuration", "efficiency", "resource"}

# All numeric fields on MonthlyMetrics (excluding metric_date)
METRICS_FIELDS = {
    f.name for f in MonthlyMetrics.__dataclass_fields__.values() if f.name != "metric_date"
}


class TestDimensionRegistry:
    def test_has_at_least_20_dimensions(self):
        assert len(DIMENSIONS) >= 20

    def test_all_categories_covered(self):
        categories = {d.category for d in DIMENSIONS}
        assert categories == EXPECTED_CATEGORIES

    def test_dimension_is_frozen_dataclass(self):
        d = DIMENSIONS[0]
        assert isinstance(d, Dimension)
        with pytest.raises(AttributeError):
            d.name = "changed"  # type: ignore[misc]

    def test_all_metric_fields_reference_valid_metrics(self):
        for d in DIMENSIONS:
            assert d.metric_field in METRICS_FIELDS, (
                f"Dimension '{d.name}' references unknown metric '{d.metric_field}'"
            )

    def test_weights_per_category_sum_to_1(self):
        from collections import defaultdict
        weights: dict[str, float] = defaultdict(float)
        for d in DIMENSIONS:
            weights[d.category] += d.weight
        for cat, total in weights.items():
            assert total == pytest.approx(1.0), (
                f"Category '{cat}' weights sum to {total}, expected 1.0"
            )

    def test_each_dimension_has_a_scorer(self):
        for d in DIMENSIONS:
            assert callable(d.scorer), f"Dimension '{d.name}' has no scorer"

    def test_scorer_returns_float_for_sample_input(self):
        for d in DIMENSIONS:
            result = d.scorer(10)
            assert isinstance(result, (int, float)), (
                f"Dimension '{d.name}' scorer returned {type(result)}"
            )
            assert 0.0 <= result <= 100.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_dimensions.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement dimension definitions**

```python
# server/src/server/scoring/dimensions.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_dimensions.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add server/src/server/scoring/dimensions.py server/tests/test_dimensions.py
git commit -m "feat: add 25 scoring dimensions across 5 categories"
```

---

### Task 4: Scoring Engine (Core Pipeline)

**Files:**
- Create: `server/src/server/scoring/engine.py`
- Create: `server/tests/test_engine.py`

- [ ] **Step 1: Write failing tests for the scoring engine**

```python
# server/tests/test_engine.py
import pytest

from server.parsers.types import MonthlyMetrics
from server.scoring.engine import score_metrics, ScoringResult


class TestScoreMetrics:
    """score_metrics takes a MonthlyMetrics and returns a ScoringResult."""

    def _make_metrics(self, **overrides) -> MonthlyMetrics:
        defaults = {
            "metric_date": "2026-01",
            "active_days": 20,
            "session_count": 80,
            "total_turns": 600,
            "avg_session_duration": 20.0,
            "project_count": 5,
            "tool_types_used": 8,
            "complex_session_count": 15,
            "tasks_created": 10,
            "tasks_completed": 8,
            "plans_created": 5,
            "model_switches": 3,
            "rules_count": 5,
            "memory_file_count": 4,
            "custom_settings_count": 6,
            "hooks_count": 3,
            "skills_used": 4,
            "abandoned_sessions": 2,
            "git_commits_in_session": 25,
            "repeated_queries": 1,
            "error_recovery_avg_turns": 2.0,
            "estimated_tokens": 500_000,
            "empty_sessions": 1,
            "large_file_reads": 2,
            "repeated_operations": 1,
            "rejected_commands": 0,
        }
        defaults.update(overrides)
        return MonthlyMetrics(**defaults)

    def test_returns_scoring_result(self):
        result = score_metrics(self._make_metrics())
        assert isinstance(result, ScoringResult)

    def test_has_dimension_scores(self):
        result = score_metrics(self._make_metrics())
        assert len(result.dimension_scores) > 0

    def test_dimension_score_structure(self):
        result = score_metrics(self._make_metrics())
        ds = result.dimension_scores[0]
        assert hasattr(ds, "name")
        assert hasattr(ds, "category")
        assert hasattr(ds, "raw_value")
        assert hasattr(ds, "score")
        assert 0.0 <= ds.score <= 100.0

    def test_has_all_category_scores(self):
        result = score_metrics(self._make_metrics())
        expected = {"activity", "quality", "configuration", "efficiency", "resource"}
        assert set(result.category_scores.keys()) == expected

    def test_category_scores_in_range(self):
        result = score_metrics(self._make_metrics())
        for cat, score in result.category_scores.items():
            assert 0.0 <= score <= 100.0, f"{cat} score {score} out of range"

    def test_total_score_in_range(self):
        result = score_metrics(self._make_metrics())
        assert 0.0 <= result.total_score <= 100.0

    def test_has_grade(self):
        result = score_metrics(self._make_metrics())
        assert result.grade in {"S", "A", "B", "C", "D"}

    def test_good_user_gets_high_score(self):
        result = score_metrics(self._make_metrics())
        assert result.total_score >= 60.0
        assert result.grade in {"S", "A", "B"}

    def test_inactive_user_gets_low_score(self):
        result = score_metrics(self._make_metrics(
            active_days=1, session_count=2, total_turns=10,
            avg_session_duration=1.0, project_count=0, tool_types_used=1,
            complex_session_count=0, tasks_created=0, tasks_completed=0,
            plans_created=0, git_commits_in_session=0,
        ))
        assert result.total_score < 60.0

    def test_zero_metrics_does_not_crash(self):
        result = score_metrics(MonthlyMetrics(metric_date="2026-01"))
        assert isinstance(result, ScoringResult)
        assert result.grade == "D"

    def test_category_weights_applied(self):
        result = score_metrics(self._make_metrics())
        # total_score should be weighted average of category scores
        weighted = sum(
            result.category_scores[cat] * w
            for cat, w in result.category_weights.items()
        )
        assert result.total_score == pytest.approx(weighted, abs=0.01)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_engine.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the scoring engine**

```python
# server/src/server/scoring/engine.py
"""Scoring engine — converts ParsedMetrics into scores, categories, and grades."""

from dataclasses import dataclass, field

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_engine.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add server/src/server/scoring/engine.py server/tests/test_engine.py
git commit -m "feat: add scoring engine with category aggregation and grading"
```

---

### Task 5: DB Persistence Layer

**Files:**
- Create: `server/src/server/scoring/persist.py`
- Create: `server/tests/test_scoring_persist.py`

- [ ] **Step 1: Write failing tests for persistence**

```python
# server/tests/test_scoring_persist.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from server.db.models import Base, Employee, ParsedMetrics, DimensionScore, MonthlyReport
from server.parsers.types import MonthlyMetrics
from server.scoring.engine import score_metrics
from server.scoring.persist import persist_scoring_result


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        emp = Employee(name="Test User", email="test@example.com", department="eng")
        session.add(emp)
        session.commit()
        session.refresh(emp)
        yield session, emp.id
    engine.dispose()


def _sample_metrics() -> MonthlyMetrics:
    return MonthlyMetrics(
        metric_date="2026-01",
        active_days=20,
        session_count=80,
        total_turns=600,
        avg_session_duration=20.0,
        project_count=5,
        tool_types_used=8,
        complex_session_count=15,
        tasks_created=10,
        tasks_completed=8,
        plans_created=5,
        model_switches=3,
        rules_count=5,
        memory_file_count=4,
        custom_settings_count=6,
        hooks_count=3,
        skills_used=4,
        abandoned_sessions=2,
        git_commits_in_session=25,
        repeated_queries=1,
        error_recovery_avg_turns=2.0,
        estimated_tokens=500_000,
        empty_sessions=1,
        large_file_reads=2,
        repeated_operations=1,
        rejected_commands=0,
    )


class TestPersistScoringResult:
    def test_creates_dimension_scores(self, db_session):
        session, emp_id = db_session
        scoring_result = score_metrics(_sample_metrics())
        persist_scoring_result(session, emp_id, scoring_result)

        rows = session.query(DimensionScore).filter_by(employee_id=emp_id).all()
        assert len(rows) == len(scoring_result.dimension_scores)

    def test_creates_monthly_report(self, db_session):
        session, emp_id = db_session
        scoring_result = score_metrics(_sample_metrics())
        persist_scoring_result(session, emp_id, scoring_result)

        report = session.query(MonthlyReport).filter_by(
            employee_id=emp_id, year_month="2026-01"
        ).one()
        assert report.grade == scoring_result.grade
        assert report.total_score == pytest.approx(scoring_result.total_score, abs=0.01)

    def test_dimension_score_fields(self, db_session):
        session, emp_id = db_session
        scoring_result = score_metrics(_sample_metrics())
        persist_scoring_result(session, emp_id, scoring_result)

        row = session.query(DimensionScore).filter_by(
            employee_id=emp_id, dimension_name="active_days"
        ).one()
        assert row.category == "activity"
        assert row.raw_value == 20.0
        assert 0.0 <= row.score <= 100.0

    def test_monthly_report_category_scores(self, db_session):
        session, emp_id = db_session
        scoring_result = score_metrics(_sample_metrics())
        persist_scoring_result(session, emp_id, scoring_result)

        report = session.query(MonthlyReport).filter_by(
            employee_id=emp_id, year_month="2026-01"
        ).one()
        assert report.activity_score == pytest.approx(
            scoring_result.category_scores["activity"], abs=0.01
        )
        assert report.efficiency_score == pytest.approx(
            scoring_result.category_scores["efficiency"], abs=0.01
        )

    def test_replaces_existing_scores_on_rerun(self, db_session):
        session, emp_id = db_session
        scoring_result = score_metrics(_sample_metrics())
        persist_scoring_result(session, emp_id, scoring_result)
        persist_scoring_result(session, emp_id, scoring_result)

        reports = session.query(MonthlyReport).filter_by(
            employee_id=emp_id, year_month="2026-01"
        ).all()
        assert len(reports) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_scoring_persist.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement persistence**

```python
# server/src/server/scoring/persist.py
"""Persist scoring results to database."""

from sqlalchemy.orm import Session

from server.db.models import DimensionScore, MonthlyReport
from server.scoring.engine import ScoringResult


def persist_scoring_result(
    session: Session, employee_id: int, result: ScoringResult
) -> MonthlyReport:
    """Write DimensionScore rows and a MonthlyReport for one employee+month.

    If scores already exist for this employee+month, they are replaced.

    Returns the created/updated MonthlyReport.
    """
    year_month = result.metric_date

    # Delete existing scores for this employee+month
    session.query(DimensionScore).filter_by(
        employee_id=employee_id, year_month=year_month
    ).delete()
    session.query(MonthlyReport).filter_by(
        employee_id=employee_id, year_month=year_month
    ).delete()

    # Write dimension scores
    for ds in result.dimension_scores:
        session.add(
            DimensionScore(
                employee_id=employee_id,
                year_month=year_month,
                category=ds.category,
                dimension_name=ds.name,
                raw_value=ds.raw_value,
                score=ds.score,
            )
        )

    # Write monthly report
    report = MonthlyReport(
        employee_id=employee_id,
        year_month=year_month,
        activity_score=result.category_scores.get("activity", 0.0),
        quality_score=result.category_scores.get("quality", 0.0),
        cognition_score=result.category_scores.get("configuration", 0.0),
        efficiency_score=result.category_scores.get("efficiency", 0.0),
        resource_score=result.category_scores.get("resource", 0.0),
        total_score=result.total_score,
        grade=result.grade,
    )
    session.add(report)
    session.commit()

    return report
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_scoring_persist.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add server/src/server/scoring/persist.py server/tests/test_scoring_persist.py
git commit -m "feat: add scoring persistence layer with upsert semantics"
```

---

### Task 6: Integrate Scoring into Orchestrator

**Files:**
- Modify: `server/src/server/parsers/orchestrator.py`
- Create: `server/tests/test_scoring_integration.py`

- [ ] **Step 1: Write failing integration test**

```python
# server/tests/test_scoring_integration.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from server.db.models import (
    Base, Employee, UploadRecord, ParsedMetrics, DimensionScore, MonthlyReport,
)
from server.scoring.orchestrate import score_employee_month


@pytest.fixture
def db_session_with_metrics():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        emp = Employee(name="Test", email="t@t.com", department="eng")
        session.add(emp)
        session.commit()
        session.refresh(emp)

        pm = ParsedMetrics(
            employee_id=emp.id,
            upload_id=1,
            metric_date="2026-01",
            active_days=20,
            session_count=80,
            total_turns=600,
            avg_session_duration=20.0,
            project_count=5,
            tool_types_used=8,
            complex_session_count=15,
            tasks_created=10,
            tasks_completed=8,
            plans_created=5,
            model_switches=3,
            rules_count=5,
            memory_file_count=4,
            custom_settings_count=6,
            hooks_count=3,
            skills_used=4,
            abandoned_sessions=2,
            git_commits_in_session=25,
            repeated_queries=1,
            error_recovery_avg_turns=2.0,
            estimated_tokens=500_000,
            empty_sessions=1,
            large_file_reads=2,
            repeated_operations=1,
            rejected_commands=0,
        )
        session.add(pm)
        session.commit()
        session.refresh(pm)

        yield session, emp.id

    engine.dispose()


class TestScoreEmployeeMonth:
    def test_scores_from_parsed_metrics(self, db_session_with_metrics):
        session, emp_id = db_session_with_metrics
        report = score_employee_month(session, emp_id, "2026-01")

        assert report is not None
        assert report.grade in {"S", "A", "B", "C", "D"}
        assert report.total_score > 0

    def test_creates_dimension_scores(self, db_session_with_metrics):
        session, emp_id = db_session_with_metrics
        score_employee_month(session, emp_id, "2026-01")

        rows = session.query(DimensionScore).filter_by(employee_id=emp_id).all()
        assert len(rows) > 0

    def test_no_metrics_returns_none(self, db_session_with_metrics):
        session, emp_id = db_session_with_metrics
        result = score_employee_month(session, emp_id, "2099-01")
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_scoring_integration.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create the orchestration function**

```python
# server/src/server/scoring/orchestrate.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_scoring_integration.py -v`
Expected: All PASS

- [ ] **Step 5: Run all scoring tests together**

Run: `cd server && python -m pytest tests/test_scoring_functions.py tests/test_grades.py tests/test_dimensions.py tests/test_engine.py tests/test_scoring_persist.py tests/test_scoring_integration.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add server/src/server/scoring/orchestrate.py server/tests/test_scoring_integration.py
git commit -m "feat: add scoring orchestration — bridge ParsedMetrics to scoring engine"
```

---

### Task 7: Full Test Suite & Final Commit

**Files:**
- No new files — validation only

- [ ] **Step 1: Run entire server test suite**

Run: `cd server && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS (existing + new)

- [ ] **Step 2: Verify test count**

Run: `cd server && python -m pytest tests/ --co -q | tail -1`
Expected: Should show 40+ tests collected

- [ ] **Step 3: Final commit with progress update**

Update `docs/progress.md` to reflect Phase 4 completion, then commit:

```bash
git add docs/progress.md
git commit -m "docs: update progress — Phase 4 (scoring engine) complete"
```
