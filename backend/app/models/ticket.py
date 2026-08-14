import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False
    )
    assigned_to: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped["Employee"] = relationship(  # type: ignore[name-defined]
        "Employee", foreign_keys=[employee_id], back_populates="tickets"
    )
    assignee: Mapped["Employee | None"] = relationship(  # type: ignore[name-defined]
        "Employee", foreign_keys=[assigned_to]
    )
