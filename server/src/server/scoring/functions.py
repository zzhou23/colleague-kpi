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
