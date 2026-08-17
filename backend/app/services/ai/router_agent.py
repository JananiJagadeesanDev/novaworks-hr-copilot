"""
router_agent.py — Intent classification router for the NovaWorks HR Copilot.

Reads a user's message and decides which specialized agent should handle it:
  - policy_rag: For questions about company policies.
  - sql_agent: For analytical questions about HR data.
  - action_agent: For performing tasks like booking leave or creating tickets.
"""

import asyncio
import json
import logging
import re
from typing import Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# The exact names of the agents the router can delegate to.
AgentName = Literal["policy_rag", "sql_agent", "action_agent", "none"]


ROUTER_SYSTEM_PROMPT = """You are the master routing agent for the NovaWorks PeopleOps Copilot.
Your job is to analyze the user's message and classify it into one of the following categories based on which specialized agent is best equipped to handle it.

Available Agents:

1.  **policy_rag**: Use for questions about company policies, rules, procedures, and benefits.
    - Example: "How much vacation time do I get?"
    - Example: "What is the company's work-from-home policy?"
    - Example: "Are there any rules about dress code?"

2.  **sql_agent**: Use for analytical questions that require querying data about employees, projects, or departments.
    - Example: "How many new employees joined last month?"
    - Example: "Which engineers are not assigned to any project?"
    - Example: "List all active projects in the marketing department."

3.  **action_agent**: Use for commands that perform an action, such as creating, updating, or requesting something.
    - Example: "Book my leave from next Monday to Wednesday."
    - Example: "Approve leave request #123."
    - Example: "Create an IT ticket because my laptop is slow."
    - Example: "Draft an announcement about the upcoming company picnic."

4.  **none**: Use if the message is a greeting, a thank you, or does not clearly fit into any of the above categories.
    - Example: "hello"
    - Example: "thanks for your help"
    - Example: "what can you do?"

Output Format:
You MUST output ONLY a JSON object with this exact structure:
```json
{
  "agent": "<agent_name>"
}
```

Choose the best agent from the literal values: "policy_rag", "sql_agent", "action_agent", or "none".
"""


class RouterAgentService:
    """Stateless service for classifying user intent.

    This service uses a zero-temperature LLM call to ensure the classification
    is as deterministic as possible.
    """

    def _fast_path_classify(self, message: str) -> Optional[AgentName]:
        """High-precision regex/keyword fast path to bypass LLM classification."""
        msg = message.strip().lower()

        # 1. Greetings & meta inquiries -> none (handled instantly)
        if re.match(r"^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening)|thanks|thank\s+you|bye|goodbye|what can you do|help)$", msg):
            return "none"

        # 2. Direct Actions (apply, book, request leave, approve/reject, create ticket)
        if re.search(r"\b(apply|book|submit|request)\b.*\b(leave|time off|vacation|half[- ]day|wfh)\b", msg) or \
           re.search(r"\b(approve|reject|cancel)\b.*\b(leave|request|ticket)\b", msg) or \
           re.search(r"\b(create|raise|open|file)\b.*\b(ticket|issue|bug|announcement)\b", msg):
            return "action_agent"

        # 3. SQL data queries (assignments, projects, employees, skills, headcount, leave balances)
        if re.search(r"\b(assigned to|assigned on|who is assigned|who works on|which projects|project assignments|my project|my projects)\b", msg) or \
           re.search(r"\b(leave balance|remaining leave|leaves do i have|leaves left|my sick leave balance|my annual leave balance)\b", msg) or \
           re.search(r"\b(which employees|who knows|list (all )?(employees|projects|departments|tickets)|headcount|count of employees)\b", msg):
            return "sql_agent"

        # 4. Policy questions (rules, policies, benefits, guidelines, entitlements)
        if re.search(r"\b(policy|policies|handbook|guideline|guidelines|rules|maternity|paternity|bereavement|wfh|work from home|remote work|dress code|probation|notice period|reimbursement|insurance|perks|learning and dev|budget)\b", msg):
            return "policy_rag"

        return None

    def _heuristic_classify(self, message: str) -> AgentName:
        """Keyword-based fallback when the LLM router is unavailable."""
        fast = self._fast_path_classify(message)
        if fast is not None:
            return fast
        msg_lower = message.lower()
        if any(k in msg_lower for k in ["policy", "sick leave", "work from home", "wfh", "late to work", "half-day", "rules", "guidelines"]):
            return "policy_rag"
        elif any(k in msg_lower for k in ["apply", "create a", "approve", "assign employee", "announcement", "ticket for"]):
            return "action_agent"
        elif any(k in msg_lower for k in ["projects", "employees", "assigned to", "show my", "find", "salary", "bank", "pan", "drop table", "delete from"]):
            return "sql_agent"
        return "none"

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0,  # Deterministic output for classification
            timeout=10,
        )

    def _extract_json(self, text_content: str) -> dict[str, str]:
        """Extracts a JSON object from a markdown code block or raw text."""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text_content)
        raw = match.group(1) if match else text_content
        try:
            return json.loads(raw.strip())
        except (json.JSONDecodeError, AttributeError):
            logger.warning("Router LLM did not return valid JSON: %r", text_content)
            return {"agent": "none"}

    async def classify(self, message: str) -> AgentName:
        """Classifies the user message and returns the name of the appropriate agent."""
        # 1. Check zero-latency fast-path first
        fast_classified = self._fast_path_classify(message)
        if fast_classified is not None:
            logger.info("Fast-path classified message %r -> %s (0 LLM calls)", message, fast_classified)
            return fast_classified

        # 2. If ambiguous, fall back to LLM
        if not settings.GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY is not configured; using heuristic routing fallback.")
            return self._heuristic_classify(message)

        llm = self._get_llm()
        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(llm.invoke, messages),
                timeout=15,
            )
            result_json = self._extract_json(response.content)
            agent_name = result_json.get("agent", "none")

            # Ensure the returned agent name is one of the allowed literals
            if agent_name not in ("policy_rag", "sql_agent", "action_agent", "none"):
                logger.warning("Router returned an invalid agent name: %s", agent_name)
                return "none"

            logger.info("Router classified message %r to agent: %s", message, agent_name)
            return agent_name  # type: ignore

        except asyncio.TimeoutError:
            logger.error("Router LLM classification timed out; using heuristic fallback.")
            return self._heuristic_classify(message)
        except Exception as exc:
            logger.error("Router LLM classification failed (%s), using heuristic fallback", exc)
            return self._heuristic_classify(message)


# Module-level singleton
router_agent_service = RouterAgentService()
