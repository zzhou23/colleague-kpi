# server/src/server/api/scores.py
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.api.deps import get_settings
from server.api.schemas import DimensionScoreResponse, MonthlyReportResponse, ScoreRequest
from server.db.models import DimensionScore, Employee, MonthlyReport, ParsedMetrics
from server.scoring.orchestrate import score_employee_month

router = APIRouter()


def _get_sync_session() -> Session:
    settings = get_settings()
    url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(url)
    return Session(engine)


def _get_employee_or_404(session: Session, employee_id: int) -> Employee:
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.get(
    "/employees/{employee_id}/scores",
    response_model=list[DimensionScoreResponse],
)
async def get_dimension_scores(
    employee_id: int,
    year_month: str | None = Query(None),
) -> list[DimensionScore]:
    session = _get_sync_session()
    _get_employee_or_404(session, employee_id)
    query = select(DimensionScore).where(DimensionScore.employee_id == employee_id)
    if year_month:
        query = query.where(DimensionScore.year_month == year_month)
    query = query.order_by(DimensionScore.year_month, DimensionScore.category)
    return session.execute(query).scalars().all()


@router.get(
    "/employees/{employee_id}/reports",
    response_model=list[MonthlyReportResponse],
)
async def get_monthly_reports(
    employee_id: int,
    year_month: str | None = Query(None),
) -> list[MonthlyReport]:
    session = _get_sync_session()
    _get_employee_or_404(session, employee_id)
    query = select(MonthlyReport).where(MonthlyReport.employee_id == employee_id)
    if year_month:
        query = query.where(MonthlyReport.year_month == year_month)
    query = query.order_by(MonthlyReport.year_month.desc())
    return session.execute(query).scalars().all()


@router.post(
    "/employees/{employee_id}/score",
    response_model=MonthlyReportResponse,
    status_code=201,
)
async def trigger_scoring(employee_id: int, body: ScoreRequest) -> MonthlyReport:
    session = _get_sync_session()
    _get_employee_or_404(session, employee_id)
    report = score_employee_month(session, employee_id, body.year_month)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"No parsed metrics found for {body.year_month}",
        )
    session.refresh(report)
    return report
