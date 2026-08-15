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
from typing import Literal

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

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0,  # Deterministic output for classification
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
        llm = self._get_llm()
        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]

        try:
            response = await asyncio.to_thread(llm.invoke, messages)
            result_json = self._extract_json(response.content)
            agent_name = result_json.get("agent", "none")

            # Ensure the returned agent name is one of the allowed literals
            if agent_name not in ("policy_rag", "sql_agent", "action_agent", "none"):
                logger.warning("Router returned an invalid agent name: %s", agent_name)
                return "none"

            logger.info("Router classified message %r to agent: %s", message, agent_name)
            return agent_name  # type: ignore

        except Exception as exc:
            logger.error("Router LLM classification failed (%s), using heuristic fallback", exc)
            msg_lower = message.lower()
            if any(k in msg_lower for k in ["policy", "sick leave", "work from home", "wfh", "late to work", "half-day", "rules", "guidelines"]):
                return "policy_rag"
            elif any(k in msg_lower for k in ["apply", "create a", "approve", "assign employee", "announcement", "ticket for"]):
                return "action_agent"
            elif any(k in msg_lower for k in ["projects", "employees", "assigned to", "show my", "find", "salary", "bank", "pan", "drop table", "delete from"]):
                return "sql_agent"
            return "none"


# Module-level singleton
router_agent_service = RouterAgentService()
