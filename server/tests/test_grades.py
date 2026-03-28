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
