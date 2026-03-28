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
