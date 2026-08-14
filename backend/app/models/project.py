import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.PLANNED, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["EmployeeProject"]] = relationship(
        "EmployeeProject", back_populates="project"
    )


class EmployeeProject(Base):
    __tablename__ = "employee_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    role: Mapped[str | None] = mapped_column(String(150), nullable=True)
    joined_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    employee: Mapped["Employee"] = relationship(  # type: ignore[name-defined]
        "Employee", back_populates="projects"
    )
    project: Mapped["Project"] = relationship("Project", back_populates="members")
