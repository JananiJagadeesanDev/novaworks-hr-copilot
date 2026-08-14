from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("employees.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    manager: Mapped["Employee | None"] = relationship(  # type: ignore[name-defined]
        "Employee",
        foreign_keys=[manager_id],
        primaryjoin="Department.manager_id == Employee.id",
    )
    employees: Mapped[list["Employee"]] = relationship(  # type: ignore[name-defined]
        "Employee",
        foreign_keys="Employee.department_id",
        back_populates="department",
    )
