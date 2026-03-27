from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    department: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="employee")
    api_key_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    uploads: Mapped[list["UploadRecord"]] = relationship(back_populates="employee")
    scores: Mapped[list["DimensionScore"]] = relationship(back_populates="employee")
    reports: Mapped[list["MonthlyReport"]] = relationship(back_populates="employee")


class UploadRecord(Base):
    __tablename__ = "upload_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    upload_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="uploads")


class ParsedMetrics(Base):
    __tablename__ = "parsed_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    upload_id: Mapped[int] = mapped_column(Integer)
    metric_date: Mapped[str] = mapped_column(String(7))

    # Activity
    active_days: Mapped[int] = mapped_column(Integer, default=0)
    session_count: Mapped[int] = mapped_column(Integer, default=0)
    total_turns: Mapped[int] = mapped_column(Integer, default=0)
    avg_session_duration: Mapped[float] = mapped_column(Float, default=0.0)

    # Quality
    project_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_types_used: Mapped[int] = mapped_column(Integer, default=0)
    complex_session_count: Mapped[int] = mapped_column(Integer, default=0)
    tasks_created: Mapped[int] = mapped_column(Integer, default=0)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    plans_created: Mapped[int] = mapped_column(Integer, default=0)

    # Configuration
    model_switches: Mapped[int] = mapped_column(Integer, default=0)
    rules_count: Mapped[int] = mapped_column(Integer, default=0)
    memory_file_count: Mapped[int] = mapped_column(Integer, default=0)
    custom_settings_count: Mapped[int] = mapped_column(Integer, default=0)
    hooks_count: Mapped[int] = mapped_column(Integer, default=0)
    skills_used: Mapped[int] = mapped_column(Integer, default=0)

    # Efficiency
    abandoned_sessions: Mapped[int] = mapped_column(Integer, default=0)
    git_commits_in_session: Mapped[int] = mapped_column(Integer, default=0)
    repeated_queries: Mapped[int] = mapped_column(Integer, default=0)
    error_recovery_avg_turns: Mapped[float] = mapped_column(Float, default=0.0)

    # Resource
    estimated_tokens: Mapped[int] = mapped_column(Integer, default=0)
    empty_sessions: Mapped[int] = mapped_column(Integer, default=0)
    large_file_reads: Mapped[int] = mapped_column(Integer, default=0)
    repeated_operations: Mapped[int] = mapped_column(Integer, default=0)
    rejected_commands: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DimensionScore(Base):
    __tablename__ = "dimension_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    year_month: Mapped[str] = mapped_column(String(7))
    category: Mapped[str] = mapped_column(String(50))
    dimension_name: Mapped[str] = mapped_column(String(100))
    raw_value: Mapped[float] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employee: Mapped["Employee"] = relationship(back_populates="scores")


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    year_month: Mapped[str] = mapped_column(String(7))
    activity_score: Mapped[float] = mapped_column(Float)
    quality_score: Mapped[float] = mapped_column(Float)
    cognition_score: Mapped[float] = mapped_column(Float)
    efficiency_score: Mapped[float] = mapped_column(Float)
    resource_score: Mapped[float] = mapped_column(Float)
    total_score: Mapped[float] = mapped_column(Float)
    grade: Mapped[str] = mapped_column(String(2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employee: Mapped["Employee"] = relationship(back_populates="reports")
