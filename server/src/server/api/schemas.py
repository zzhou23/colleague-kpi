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
