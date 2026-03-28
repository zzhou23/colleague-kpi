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
        assert capped_linear_score(5, cap=10, max_val=20) == pytest.approx(40.0)

    def test_at_cap(self):
        assert capped_linear_score(10, cap=10, max_val=20) == pytest.approx(80.0)

    def test_at_max(self):
        assert capped_linear_score(20, cap=10, max_val=20) == 100.0

    def test_zero(self):
        assert capped_linear_score(0, cap=10, max_val=20) == 0.0
