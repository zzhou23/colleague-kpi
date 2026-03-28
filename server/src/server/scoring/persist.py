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
