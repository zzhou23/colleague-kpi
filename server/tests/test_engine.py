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
