import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentType(str, enum.Enum):
    POLICY_RAG = "POLICY_RAG"
    SQL_AGENT = "SQL_AGENT"
    HR_ACTION = "HR_ACTION"
    ROUTER = "ROUTER"


class AIAuditLog(Base):
    __tablename__ = "ai_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_taken: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    employee: Mapped["Employee | None"] = relationship(  # type: ignore[name-defined]
        "Employee", back_populates="audit_logs"
    )
