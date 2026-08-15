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
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.employee import Employee
from app.services.ai.policy_rag import policy_rag_service
from app.services.ai.sql_agent import sql_agent_service
from app.services.ai.action_agent import action_agent_service
from app.services.ai.router_agent import router_agent_service, AgentName
from app.services.ai.tracing import ai_tracer
from app.services.audit import audit_service
from app.models.ai_audit_log import AgentType
from app.api.v1.deps import bearer_scheme

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
# Action Agent Schemas
# ---------------------------------------------------------------------------

class ActionChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Natural language command for Action Agent")
    access_token: Optional[str] = Field(None, description="Raw access token, if available")
    confirm: bool = Field(False, description="Confirm high-impact action execution")
    confirmation_id: Optional[str] = Field(None, description="Pending HITL confirmation ID")


class ActionChatData(BaseModel):
    answer: str
    action_taken: str
    tool_called: str
    tool_result: dict[str, Any]


class ActionChatResponse(BaseModel):
    success: bool = True
    data: ActionChatData
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Main Router Schemas
# ---------------------------------------------------------------------------

class MainChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's message for the main router")


class MainChatResponse(BaseModel):
    agent: str
    response: dict[str, Any]


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
        async with ai_tracer.trace_span("policy_rag", current_user.id, current_user.role.value, question) as span:
            rag_result = await policy_rag_service.ask(question=question, db=db)
            span.finish(output_response=rag_result["answer"])

        response = PolicyChatResponse(
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
        audit_service.log_interaction(
            db=db,
            employee_id=current_user.id,
            agent_type=AgentType.POLICY_RAG,
            query=question,
            response=rag_result["answer"],
            metadata={"sources": rag_result.get("sources", [])},
        )
        return response
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
        async with ai_tracer.trace_span("sql_agent", current_user.id, current_user.role.value, question) as span:
            sql_result = await sql_agent_service.ask(
                question=question,
                current_user=current_user,
                db=db,
            )
            span.finish(output_response=sql_result["answer"], tool_called="sql_query", tool_params={"sql": sql_result.get("sql")})

        response = SQLChatResponse(
            success=True,
            data=SQLChatData(
                answer=sql_result["answer"],
                sql=sql_result.get("sql", ""),
                rows=sql_result.get("rows", []),
            ),
            error=None,
        )
        audit_service.log_interaction(
            db=db,
            employee_id=current_user.id,
            agent_type=AgentType.SQL_AGENT,
            query=question,
            response=sql_result["answer"],
            metadata={"sql": sql_result.get("sql", ""), "rows": sql_result.get("rows", [])},
        )
        return response
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


@router.post("/actions", response_model=ActionChatResponse)
async def chat_actions(
    payload: ActionChatRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
    credentials: str = Depends(bearer_scheme),
):
    """Perform HR tasks using natural language via guarded, tool-calling LLM."""
    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be blank",
        )

    logger.info(
        "Action chat request from employee %s (%s): %r",
        current_user.employee_id,
        current_user.role.value,
        message,
    )

    try:
        # The service needs the raw token to make authenticated API calls on the user's behalf
        access_token = credentials.credentials
        async with ai_tracer.trace_span("action_agent", current_user.id, current_user.role.value, message) as span:
            action_result = await action_agent_service.run(
                message=message,
                current_user=current_user,
                access_token=access_token,
                confirm=payload.confirm,
                confirmation_id=payload.confirmation_id,
            )
            span.finish(
                output_response=action_result["answer"],
                tool_called=action_result.get("tool_called"),
                status="SUCCESS" if "FAILED" not in action_result.get("action_taken", "") else "FAILED",
            )

        success = "FAILED" not in action_result.get("action_taken", "") and action_result.get("action_taken") != "DENIED"

        response = ActionChatResponse(
            success=success,
            data=ActionChatData(**action_result),
            error=action_result.get("tool_result", {}).get("error") if not success else None,
        )
        audit_service.log_interaction(
            db=db,
            employee_id=current_user.id,
            agent_type=AgentType.HR_ACTION,
            query=message,
            response=action_result["answer"],
            action_taken=action_result.get("action_taken"),
            metadata={
                "tool_called": action_result.get("tool_called"),
                "tool_params": action_result.get("parameters"),
            },
        )
        return response
    except Exception as exc:
        logger.error("Action chat failed for user %s: %s", current_user.employee_id, exc, exc_info=True)
        return ActionChatResponse(
            success=False,
            data=ActionChatData(
                answer="An error occurred while performing the action. Please try again later.",
                action_taken="ERROR",
                tool_called="none",
                tool_result={"error": str(exc)},
            ),
            error=str(exc),
        )


@router.post("/router", response_model=MainChatResponse)
async def chat_router(
    payload: MainChatRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
    credentials: str = Depends(bearer_scheme),
):
    """Main entry point for the AI copilot. Classifies intent and routes to the correct agent."""
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be blank")

    # 1. Classify intent
    agent_name = await router_agent_service.classify(message)

    # 2. Delegate to the appropriate agent
    response_data: dict[str, Any]

    if agent_name == "policy_rag":
        response_data = await policy_rag_service.ask(question=message, db=db)
    elif agent_name == "sql_agent":
        response_data = await sql_agent_service.ask(question=message, current_user=current_user, db=db)
    elif agent_name == "action_agent":
        access_token = credentials.credentials
        response_data = await action_agent_service.run(message=message, current_user=current_user, access_token=access_token)
    else:  # "none"
        response_data = {"answer": "I'm sorry, I'm not sure how to handle that request. Please try rephrasing or ask me about HR policies, data, or actions."}

    # 3. Log the interaction
    # The agent name from the router needs to be cast to the AgentType enum
    agent_type_map: dict[AgentName, AgentType] = {
        "policy_rag": AgentType.POLICY_RAG,
        "sql_agent": AgentType.SQL_AGENT,
        "action_agent": AgentType.HR_ACTION,
        "none": AgentType.ROUTER, # Log 'none' classifications under the router itself
    }
    agent_type = agent_type_map.get(agent_name, AgentType.ROUTER)

    audit_service.log_interaction(
        db=db,
        employee_id=current_user.id,
        agent_type=agent_type,
        query=message,
        response=response_data.get("answer"),
        action_taken=response_data.get("action_taken"),
        metadata=response_data,
    )

    return MainChatResponse(agent=agent_name, response=response_data)


@router.post("/stream")
async def chat_stream(
    payload: MainChatRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
    credentials: str = Depends(bearer_scheme),
):
    """Stream AI interaction stages and response tokens using Server-Sent Events (SSE)."""
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be blank")

    async def event_generator():
        import json
        import asyncio

        # Event 1: Intent Classification Stage
        yield f"event: status\ndata: {json.dumps({'stage': 'intent_classification', 'message': 'Classifying query intent...'})}\n\n"
        await asyncio.sleep(0.2)

        agent_name = await router_agent_service.classify(message)
        yield f"event: status\ndata: {json.dumps({'stage': 'routing', 'agent': agent_name, 'message': f'Routed to {agent_name}'})}\n\n"
        await asyncio.sleep(0.2)

        # Event 2: Execution Stage
        yield f"event: status\ndata: {json.dumps({'stage': 'execution', 'message': 'Processing agent logic & guardrails...'})}\n\n"

        access_token = credentials.credentials
        if agent_name == "policy_rag":
            response_data = await policy_rag_service.ask(question=message, db=db)
        elif agent_name == "sql_agent":
            response_data = await sql_agent_service.ask(question=message, current_user=current_user, db=db)
        elif agent_name == "action_agent":
            response_data = await action_agent_service.run(message=message, current_user=current_user, access_token=access_token)
        else:
            response_data = {"answer": "I'm sorry, I'm not sure how to handle that request."}

        # Event 3: Token Streaming / Text Delta
        answer = response_data.get("answer", "")
        chunk_size = 30
        for i in range(0, len(answer), chunk_size):
            chunk = answer[i:i + chunk_size]
            yield f"event: delta\ndata: {json.dumps({'content': chunk})}\n\n"
            await asyncio.sleep(0.05)

        # Event 4: Completion Event
        yield f"event: done\ndata: {json.dumps({'agent': agent_name, 'success': True, 'data': response_data})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
