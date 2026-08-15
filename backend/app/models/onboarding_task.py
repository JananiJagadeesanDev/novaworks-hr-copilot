import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OnboardingTaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(100), default="GENERAL", nullable=False
    )  # e.g., "IT_SETUP", "HR_PAPERWORK", "TRAINING", "SECURITY", "BENEFITS"
    status: Mapped[OnboardingTaskStatus] = mapped_column(
        Enum(OnboardingTaskStatus),
        default=OnboardingTaskStatus.PENDING,
        nullable=False,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("employees.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped["Employee"] = relationship(  # type: ignore[name-defined]
        "Employee", foreign_keys=[employee_id], back_populates="onboarding_tasks"
    )
    assigner: Mapped["Employee | None"] = relationship(  # type: ignore[name-defined]
        "Employee", foreign_keys=[assigned_by]
    )
