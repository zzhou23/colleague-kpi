# server/src/server/api/upload.py
import os
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Header, HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import bcrypt as _bcrypt

from server.api.deps import get_settings
from server.db.models import Employee, UploadRecord

router = APIRouter()


def _get_sync_session() -> Session:
    settings = get_settings()
    url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(url)
    return Session(engine)


def _authenticate(api_key: str) -> Employee:
    session = _get_sync_session()
    employees = session.execute(
        select(Employee).where(Employee.api_key_hash.isnot(None))
    ).scalars().all()
    for emp in employees:
        if _bcrypt.checkpw(api_key.encode(), emp.api_key_hash.encode()):
            return emp
    raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/upload")
async def upload_claude_data(
    file: UploadFile = File(...),
    x_api_key: str = Header(...),
) -> dict:
    employee = _authenticate(x_api_key)
    settings = get_settings()

    os.makedirs(settings.upload_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{employee.id}_{timestamp}.tar.gz"
    file_path = os.path.join(settings.upload_dir, filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    session = _get_sync_session()
    record = UploadRecord(
        employee_id=employee.id,
        file_path=file_path,
        file_size=len(content),
        status="pending",
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    return {"status": "received", "upload_id": record.id}
