import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeaveType(str, enum.Enum):
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    MATERNITY = "MATERNITY"
    PATERNITY = "PATERNITY"
    UNPAID = "UNPAID"


class LeaveStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[LeaveStatus] = mapped_column(
        Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    approver_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped["Employee"] = relationship(  # type: ignore[name-defined]
        "Employee", foreign_keys=[employee_id], back_populates="leave_requests"
    )
    approver: Mapped["Employee | None"] = relationship(  # type: ignore[name-defined]
        "Employee", foreign_keys=[approved_by]
    )


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), nullable=False)
    total_days: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    used_days: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    employee: Mapped["Employee"] = relationship(  # type: ignore[name-defined]
        "Employee", back_populates="leave_balances"
    )
