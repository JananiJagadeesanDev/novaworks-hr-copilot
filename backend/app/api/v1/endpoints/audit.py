"""
audit.py — Read-only endpoint for AI audit logs.

Endpoints:
  GET /api/v1/audit-logs         — list recent audit logs (admin/manager: all, employee: own)
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.ai_audit_log import AIAuditLog
from app.models.employee import Employee, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit-logs", tags=["audit"])


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class AuditLogOut(BaseModel):
    id: int
    employee_id: Optional[int]
    agent_type: str
    query: str
    response: Optional[str]
    action_taken: Optional[str]
    metadata_json: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class AuditLogsResponse(BaseModel):
    success: bool = True
    data: list[AuditLogOut]
    total: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("", response_model=AuditLogsResponse)
def get_audit_logs(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return recent AI audit log entries.
    - ADMIN / MANAGER: can see all employees' logs.
    - EMPLOYEE: can only see their own logs.
    """
    query = db.query(AIAuditLog).order_by(AIAuditLog.created_at.desc())

    # Restrict regular employees to their own logs
    if current_user.role == UserRole.EMPLOYEE:
        query = query.filter(AIAuditLog.employee_id == current_user.id)

    total = query.count()
    logs = query.limit(limit).all()

    return AuditLogsResponse(
        success=True,
        total=total,
        data=[
            AuditLogOut(
                id=log.id,
                employee_id=log.employee_id,
                agent_type=log.agent_type.value,
                query=log.query,
                response=log.response,
                action_taken=log.action_taken,
                metadata_json=log.metadata_json,
                created_at=f"{log.created_at.isoformat()}Z" if log.created_at and not log.created_at.isoformat().endswith("Z") else (log.created_at.isoformat() if log.created_at else ""),
            )
            for log in logs
        ],
    )
