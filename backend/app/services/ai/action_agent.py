"""
action_agent.py — HR Task Automation Agent for NovaWorks.

Responsibilities:
  1. Extract action intent & parameters from user messages using LLM.
  2. Perform pre-flight permission validation via permissions.py.
  3. Execute action via authenticated backend REST API tools (api_tools.py).
  4. Synthesize clear, user-friendly confirmation responses.
"""

import asyncio
import json
import logging
import re
from datetime import date
from typing import Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.models.employee import Employee
from app.services.ai import api_tools, hitl
from app.services.ai.permissions import check_action_permission

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool Schema Definitions
# ---------------------------------------------------------------------------

AVAILABLE_TOOLS_DOC = """
Available Actions & Required Parameters:

1. apply_leave:
   - leave_type: "ANNUAL", "SICK", "CASUAL", "MATERNITY", "PATERNITY", "UNPAID"
   - start_date: "YYYY-MM-DD"
   - end_date: "YYYY-MM-DD"
   - reason: string (optional)
   - is_half_day: boolean (default false)
   - half_day_period: "FIRST_HALF" or "SECOND_HALF" or null

2. update_leave:
   - request_id: integer (ID of the leave request)
   - status: "APPROVED", "REJECTED", or "CANCELLED"
   - approver_notes: string (optional)

3. get_leave_balance:
   - (no parameters required)

4. create_ticket:
   - title: string (short title)
   - description: string (details)
   - category: "payroll", "benefits", "it", "facilities", "documents", or "general"
   - priority: "LOW", "MEDIUM", or "HIGH" (default "MEDIUM")

5. update_ticket:
   - ticket_id: integer
   - status: "OPEN", "IN_PROGRESS", "RESOLVED", or "CLOSED" (optional)
   - priority: "LOW", "MEDIUM", or "HIGH" (optional)
   - assigned_to: integer (employee ID to assign to, optional)
   - resolution: string (optional)

6. create_announcement:
   - title: string
   - content: string
   - target_role: "EMPLOYEE", "MANAGER", "ADMIN", or null (for everyone)

7. assign_project:
   - employee_id: integer
   - project_id: integer
   - role: string (e.g. "Frontend Developer", "Backend Lead")
   - joined_at: "YYYY-MM-DD" (optional)

8. none:
   - message: explanation of why no tool can be called or request more details.
"""

INTENT_EXTRACTION_PROMPT = """You are the NovaWorks HR Action Intent Extractor.
Analyze the user's message and determine the intended HR action and structured arguments.

Today's Date: {today_date}

{available_tools_doc}

Output Format:
You MUST output ONLY a JSON object with this exact structure:
```json
{{
  "action": "<tool_name_or_none>",
  "parameters": {{ ... }}
}}
```

Rules:
1. Always parse dates relative to today's date ({today_date}).
2. Infer sensible defaults if not specified (e.g., leave_type="ANNUAL" or "SICK" based on context, priority="MEDIUM").
3. If essential information is missing, output action="none" and explain what is missing.
4. Output ONLY the JSON block, no conversational text.
"""

SYNTHESIS_PROMPT = """You are the NovaWorks HR Action Assistant.
Given the user's initial request, the action executed, and the API response result, produce a friendly, professional, and clear confirmation message.

Rules:
1. If the API call succeeded, clearly confirm the action, its ID/number, and current status.
2. If the API call returned an error, explain the issue politely without jargon (e.g., insufficient leave balance).
3. Keep the response concise and reassuring.
"""


class ActionAgentService:
    """Service for intent extraction, permission checking, and tool dispatch."""

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0,
        )

    async def extract_intent(self, message: str, current_user: Employee) -> dict[str, Any]:
        """Uses LLM to classify user intent and extract tool parameters."""
        today_str = date.today().isoformat()
        prompt_content = INTENT_EXTRACTION_PROMPT.format(today_date=today_str, available_tools_doc=AVAILABLE_TOOLS_DOC)
        user_context = f"Current User ID: {current_user.id}, Role: {current_user.role.value}, Email: {current_user.email}\nUser Message: {message}"

        llm = self._get_llm()
        messages = [
            SystemMessage(content=prompt_content),
            HumanMessage(content=user_context),
        ]

        try:
            response = await llm.ainvoke(messages)
            text = response.content.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            raw_json = match.group(1) if match else text
            parsed = json.loads(raw_json.strip())
            logger.info("Action intent extracted: %r", parsed)
            return parsed
        except Exception as exc:
            logger.error("Failed to extract action intent: %s", exc, exc_info=True)
            return {"action": "none", "parameters": {"message": "I could not parse your request as a valid HR action."}}

    async def execute_tool(self, action: str, params: dict[str, Any], access_token: str) -> dict[str, Any]:
        """Dispatches action execution to backend REST API via api_tools."""
        logger.info("Executing API tool '%s' with parameters: %r", action, params)

        if action == "apply_leave":
            return await api_tools.apply_leave(
                leave_type=params.get("leave_type", "ANNUAL"),
                start_date=params.get("start_date", date.today().isoformat()),
                end_date=params.get("end_date", date.today().isoformat()),
                reason=params.get("reason"),
                is_half_day=params.get("is_half_day", False),
                half_day_period=params.get("half_day_period"),
                access_token=access_token,
            )
        elif action == "update_leave":
            return await api_tools.update_leave(
                request_id=int(params.get("request_id", 0)),
                status=params.get("status", "APPROVED"),
                approver_notes=params.get("approver_notes"),
                access_token=access_token,
            )
        elif action == "get_leave_balance":
            return await api_tools.get_leave_balance(access_token=access_token)
        elif action == "create_ticket":
            return await api_tools.create_ticket(
                title=params.get("title", "HR/IT Request"),
                description=params.get("description", "Created via NovaWorks Copilot"),
                category=params.get("category", "general"),
                priority=params.get("priority", "MEDIUM"),
                access_token=access_token,
            )
        elif action == "update_ticket":
            return await api_tools.update_ticket(
                ticket_id=int(params.get("ticket_id", 0)),
                status=params.get("status"),
                priority=params.get("priority"),
                assigned_to=params.get("assigned_to"),
                resolution=params.get("resolution"),
                access_token=access_token,
            )
        elif action == "create_announcement":
            return await api_tools.create_announcement(
                title=params.get("title", ""),
                content=params.get("content", ""),
                target_role=params.get("target_role"),
                access_token=access_token,
            )
        elif action == "assign_project":
            return await api_tools.assign_project(
                employee_id=int(params.get("employee_id", 0)),
                project_id=int(params.get("project_id", 0)),
                role=params.get("role"),
                joined_at=params.get("joined_at"),
                access_token=access_token,
            )
        else:
            return {"success": False, "error": f"Unsupported action '{action}'"}

    async def synthesize_response(self, user_message: str, action: str, tool_result: dict[str, Any]) -> str:
        """Synthesize a natural language confirmation of the tool execution."""
        prompt = (
            f"User Request: {user_message}\n"
            f"Action Executed: {action}\n"
            f"Tool Result: {json.dumps(tool_result, default=str)}\n"
        )
        llm = self._get_llm()
        messages = [
            SystemMessage(content=SYNTHESIS_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = await llm.ainvoke(messages)
        return response.content.strip()

    async def run(
        self,
        message: str,
        current_user: Employee,
        access_token: str,
        confirm: bool = False,
        confirmation_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Full pipeline: Intent -> HITL Check -> Permission Check -> Tool Call -> Synthesis."""
        # Check if confirming a previously registered HITL action
        if confirm and confirmation_id:
            pending = hitl.validate_and_consume_confirmation(confirmation_id, current_user.id)
            if not pending:
                return {
                    "answer": "The confirmation token is invalid or has expired. Please re-issue your action request.",
                    "action_taken": "FAILED",
                    "tool_called": "none",
                    "tool_result": {"error": "Invalid or expired confirmation_id"},
                }
            action = pending["tool_name"]
            params = pending["parameters"]
            logger.info("Proceeding with confirmed HITL action '%s' for user %s", action, current_user.employee_id)
        else:
            # 1. Intent Extraction
            intent = await self.extract_intent(message, current_user)
            action = intent.get("action", "none").lower()
            params = intent.get("parameters", {})

        if action == "none" or not action:
            return {
                "answer": params.get("message", "I could not identify a specific HR action to perform. Please provide more details."),
                "action_taken": "NONE",
                "tool_called": "none",
                "tool_result": {},
            }

        # 2. Permission Check
        is_allowed, denial_reason = check_action_permission(action, current_user.role, params)
        if not is_allowed:
            logger.warning(
                "Permission denied for user %s (role %s) on action %s: %s",
                current_user.employee_id,
                current_user.role.value,
                action,
                denial_reason,
            )
            return {
                "answer": denial_reason or "You do not have permission to perform this action.",
                "action_taken": "DENIED",
                "tool_called": action,
                "tool_result": {"error": "Permission denied", "detail": denial_reason},
            }

        # 3. HITL High-Impact Action Check (if unconfirmed)
        if not confirm and hitl.is_high_impact_action(action, params):
            pending_info = hitl.register_pending_confirmation(current_user.id, action, params)
            return {
                "answer": pending_info["prompt"],
                "action_taken": "CONFIRMATION_REQUIRED",
                "tool_called": action,
                "tool_result": {
                    "requires_confirmation": True,
                    "confirmation_id": pending_info["confirmation_id"],
                    "parameters": params,
                },
            }

        # 4. Tool Execution via API
        tool_result = await self.execute_tool(action, params, access_token)

        # 5. Response Synthesis
        answer = await self.synthesize_response(message, action, tool_result)

        return {
            "answer": answer,
            "action_taken": action if tool_result.get("success") else f"{action}_FAILED",
            "tool_called": action,
            "tool_result": tool_result,
        }


# Module singleton
action_agent_service = ActionAgentService()
