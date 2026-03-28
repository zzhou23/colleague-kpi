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
