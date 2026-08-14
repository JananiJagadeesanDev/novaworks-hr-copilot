import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    department_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("departments.id", use_alter=True, name="fk_employee_department"),
        nullable=True,
    )
    manager_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    reports: Mapped[list["Employee"]] = relationship("Employee", back_populates="manager")
    manager: Mapped["Employee | None"] = relationship(
        "Employee", back_populates="reports", remote_side=[id]
    )
    department: Mapped["Department | None"] = relationship(  # type: ignore[name-defined]
        "Department",
        foreign_keys=[department_id],
        back_populates="employees",
    )
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(  # type: ignore[name-defined]
        "LeaveRequest", foreign_keys="LeaveRequest.employee_id", back_populates="employee"
    )
    leave_balances: Mapped[list["LeaveBalance"]] = relationship(  # type: ignore[name-defined]
        "LeaveBalance", back_populates="employee"
    )
    tickets: Mapped[list["Ticket"]] = relationship(  # type: ignore[name-defined]
        "Ticket", foreign_keys="Ticket.employee_id", back_populates="employee"
    )
    projects: Mapped[list["EmployeeProject"]] = relationship(  # type: ignore[name-defined]
        "EmployeeProject", back_populates="employee"
    )
    skills: Mapped[list["EmployeeSkill"]] = relationship(  # type: ignore[name-defined]
        "EmployeeSkill", back_populates="employee"
    )
    announcements: Mapped[list["Announcement"]] = relationship(  # type: ignore[name-defined]
        "Announcement", back_populates="author"
    )
    audit_logs: Mapped[list["AIAuditLog"]] = relationship(  # type: ignore[name-defined]
        "AIAuditLog", back_populates="employee"
    )
