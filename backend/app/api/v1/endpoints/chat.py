"""
chat.py — AI Chat Router for NovaWorks HR Copilot.

Endpoints:
  - POST /api/v1/chat/policy   (Step 9: Policy RAG)
  - POST /api/v1/chat/sql      (Step 11: SQL Agent)
  - POST /api/v1/chat/actions  (Step 13: Action Agent - deferred)
  - POST /api/v1/chat/router   (Step 14: Agent Router - deferred)
"""

import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.employee import Employee
from app.services.ai.policy_rag import policy_rag_service
from app.services.ai.sql_agent import sql_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["ai-chat"])


# ---------------------------------------------------------------------------
# Policy RAG Schemas
# ---------------------------------------------------------------------------

class PolicyChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Policy question asked by employee")


class PolicySourceOut(BaseModel):
    title: str
    category: str


class PolicyChatData(BaseModel):
    answer: str
    sources: list[PolicySourceOut] = Field(default_factory=list)


class PolicyChatResponse(BaseModel):
    success: bool = True
    data: PolicyChatData
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# SQL Agent Schemas
# ---------------------------------------------------------------------------

class SQLChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Natural language question for SQL Agent")


class SQLChatData(BaseModel):
    answer: str
    sql: str
    rows: list[dict[str, Any]] = Field(default_factory=list)


class SQLChatResponse(BaseModel):
    success: bool = True
    data: SQLChatData
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/policy", response_model=PolicyChatResponse)
async def chat_policy(
    payload: PolicyChatRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Answer employee HR policy questions via Grounded Policy RAG."""
    question = payload.message.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question message cannot be blank",
        )

    logger.info(
        "Policy chat request from employee %s (%s): %r",
        current_user.employee_id,
        current_user.role.value,
        question,
    )

    try:
        rag_result = await policy_rag_service.ask(question=question, db=db)
        return PolicyChatResponse(
            success=True,
            data=PolicyChatData(
                answer=rag_result["answer"],
                sources=[
                    PolicySourceOut(title=s.get("title", ""), category=s.get("category", ""))
                    for s in rag_result.get("sources", [])
                ],
            ),
            error=None,
        )
    except Exception as exc:
        logger.error("Policy chat failed for user %s: %s", current_user.employee_id, exc, exc_info=True)
        return PolicyChatResponse(
            success=False,
            data=PolicyChatData(
                answer="An error occurred while answering your policy question. Please try again later.",
                sources=[],
            ),
            error=str(exc),
        )


@router.post("/sql", response_model=SQLChatResponse)
async def chat_sql(
    payload: SQLChatRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Query HR databases using natural language with strict read-only SQL guardrails."""
    question = payload.message.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question message cannot be blank",
        )

    logger.info(
        "SQL chat request from employee %s (%s): %r",
        current_user.employee_id,
        current_user.role.value,
        question,
    )

    try:
        sql_result = await sql_agent_service.ask(
            question=question,
            current_user=current_user,
            db=db,
        )
        return SQLChatResponse(
            success=True,
            data=SQLChatData(
                answer=sql_result["answer"],
                sql=sql_result.get("sql", ""),
                rows=sql_result.get("rows", []),
            ),
            error=None,
        )
    except Exception as exc:
        logger.error("SQL chat failed for user %s: %s", current_user.employee_id, exc, exc_info=True)
        return SQLChatResponse(
            success=False,
            data=SQLChatData(
                answer="An error occurred while processing your database query. Please try again later.",
                sql="",
                rows=[],
            ),
            error=str(exc),
        )
