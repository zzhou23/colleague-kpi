# server/src/server/api/employees.py
import secrets
import bcrypt

from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.api.deps import get_settings
from server.api.schemas import EmployeeCreate, EmployeeResponse, EmployeeCreateResponse
from server.db.models import Employee

router = APIRouter()


def _get_sync_session() -> Session:
    settings = get_settings()
    url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(url)
    return Session(engine)


@router.get("/employees", response_model=list[EmployeeResponse])
async def list_employees() -> list[Employee]:
    session = _get_sync_session()
    employees = session.execute(select(Employee).order_by(Employee.id)).scalars().all()
    return employees


@router.post("/employees", response_model=EmployeeCreateResponse, status_code=201)
async def create_employee(data: EmployeeCreate) -> EmployeeCreateResponse:
    session = _get_sync_session()
    api_key = secrets.token_urlsafe(32)
    hashed = bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()
    employee = Employee(
        name=data.name,
        email=data.email,
        department=data.department,
        role=data.role,
        api_key_hash=hashed,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return EmployeeCreateResponse(
        id=employee.id,
        name=employee.name,
        email=employee.email,
        department=employee.department,
        role=employee.role,
        api_key=api_key,
    )


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: int) -> Employee:
    session = _get_sync_session()
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee
