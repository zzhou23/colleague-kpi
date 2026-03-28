from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from server.api.deps import get_settings
from server.api.schemas import DashboardSummaryResponse, RankingEntry
from server.db.models import Employee, MonthlyReport

router = APIRouter()


def _get_sync_session() -> Session:
    settings = get_settings()
    url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(url)
    return Session(engine)


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    year_month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="Format: YYYY-MM"),
) -> DashboardSummaryResponse:
    session = _get_sync_session()
    total_employees = session.scalar(select(func.count(Employee.id)))

    reports = (
        session.execute(
            select(MonthlyReport).where(MonthlyReport.year_month == year_month)
        )
        .scalars()
        .all()
    )

    if not reports:
        return DashboardSummaryResponse(
            total_employees=total_employees or 0,
            avg_score=0.0,
            max_score=0.0,
            min_score=0.0,
            grade_distribution={"S": 0, "A": 0, "B": 0, "C": 0, "D": 0},
        )

    scores = [r.total_score for r in reports]
    grade_dist = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    for r in reports:
        if r.grade in grade_dist:
            grade_dist[r.grade] += 1

    return DashboardSummaryResponse(
        total_employees=total_employees or 0,
        avg_score=round(sum(scores) / len(scores), 1),
        max_score=max(scores),
        min_score=min(scores),
        grade_distribution=grade_dist,
    )


@router.get("/dashboard/rankings", response_model=list[RankingEntry])
async def dashboard_rankings(
    year_month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="Format: YYYY-MM"),
    order: Literal["top", "bottom"] = Query("top", description="top or bottom"),
    limit: int = Query(10, ge=1, le=100),
) -> list[RankingEntry]:
    session = _get_sync_session()

    query = (
        select(MonthlyReport, Employee)
        .join(Employee, MonthlyReport.employee_id == Employee.id)
        .where(MonthlyReport.year_month == year_month)
    )

    if order == "bottom":
        query = query.order_by(MonthlyReport.total_score.asc())
    else:
        query = query.order_by(MonthlyReport.total_score.desc())

    query = query.limit(limit)
    rows = session.execute(query).all()

    return [
        RankingEntry(
            employee_id=emp.id,
            name=emp.name,
            department=emp.department,
            total_score=report.total_score,
            grade=report.grade,
        )
        for report, emp in rows
    ]
