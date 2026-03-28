# server/src/server/api/schemas.py
from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    name: str
    email: str
    department: str
    role: str = "employee"


class EmployeeResponse(BaseModel):
    id: int
    name: str
    email: str
    department: str
    role: str
    model_config = {"from_attributes": True}


class EmployeeCreateResponse(EmployeeResponse):
    api_key: str


class DimensionScoreResponse(BaseModel):
    id: int
    category: str
    dimension_name: str
    raw_value: float
    score: float
    year_month: str
    model_config = {"from_attributes": True}


class MonthlyReportResponse(BaseModel):
    id: int
    employee_id: int
    year_month: str
    activity_score: float
    quality_score: float
    cognition_score: float
    efficiency_score: float
    resource_score: float
    total_score: float
    grade: str
    model_config = {"from_attributes": True}


class ScoreRequest(BaseModel):
    year_month: str
