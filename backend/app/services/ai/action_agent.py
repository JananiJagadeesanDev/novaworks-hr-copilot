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
from app.services.ai import api_tools
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

INTENT_EXTRACTION_PROMPT = f"""You are the NovaWorks HR Action Intent Extractor.
Analyze the user's message and determine the intended HR action and structured arguments.

Today's Date: {{today_date}}

{AVAILABLE_TOOLS_DOC}

Output Format:
You MUST output ONLY a JSON object with this exact structure:
```json
{{
  "action": "<tool_name_or_none>",
  "parameters": {{ ... }}
}}
```

Rules:
1. Always parse dates relative to today's date ({{today_date}}).
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

    def _extract_json(self, text_content: str) -> dict[str, Any]:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text_content)
        raw = match.group(1) if match else text_content
        try:
            return json.loads(raw.strip())
        except Exception:
            return {"action": "none", "parameters": {}}

    async def extract_intent(self, user_message: str, current_user: Employee) -> dict[str, Any]:
        """Extract tool name and arguments from user message."""
        today_str = date.today().isoformat()
        sys_prompt = INTENT_EXTRACTION_PROMPT.replace("{today_date}", today_str)
        user_prompt = (
            f"User Context:\n"
            f"- User ID: {current_user.id}\n"
            f"- Name: {current_user.first_name} {current_user.last_name}\n"
            f"- Role: {current_user.role.value}\n\n"
            f"User Request: {user_message}"
        )

        llm = self._get_llm()
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = await asyncio.to_thread(llm.invoke, messages)
        return self._extract_json(response.content)

    async def execute_tool(self, action: str, params: dict[str, Any], access_token: str) -> dict[str, Any]:
        """Dispatch tool call to api_tools."""
        if action == "apply_leave":
            return await api_tools.apply_leave(
                leave_type=params.get("leave_type", "ANNUAL"),
                start_date=params.get("start_date", ""),
                end_date=params.get("end_date", ""),
                reason=params.get("reason"),
                is_half_day=params.get("is_half_day", False),
                half_day_period=params.get("half_day_period"),
                access_token=access_token,
            )
        elif action == "update_leave":
            return await api_tools.update_leave(
                request_id=int(params.get("request_id", 0)),
                status=params.get("status", ""),
                approver_notes=params.get("approver_notes"),
                access_token=access_token,
            )
        elif action == "get_leave_balance":
            return await api_tools.get_leave_balance(access_token=access_token)
        elif action == "create_ticket":
            return await api_tools.create_ticket(
                title=params.get("title", "Support Request"),
                description=params.get("description", ""),
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
        response = await asyncio.to_thread(llm.invoke, messages)
        return response.content.strip()

    async def run(
        self,
        message: str,
        current_user: Employee,
        access_token: str,
    ) -> dict[str, Any]:
        """Full pipeline: Intent -> Permission Check -> Tool Call -> Synthesis."""
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

        # 3. Tool Execution via API
        tool_result = await self.execute_tool(action, params, access_token)

        # 4. Response Synthesis
        answer = await self.synthesize_response(message, action, tool_result)

        return {
            "answer": answer,
            "action_taken": action if tool_result.get("success") else f"{action}_FAILED",
            "tool_called": action,
            "tool_result": tool_result,
        }


# Module singleton
action_agent_service = ActionAgentService()
