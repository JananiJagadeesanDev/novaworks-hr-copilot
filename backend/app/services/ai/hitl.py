"""
hitl.py — Human-in-the-Loop (HITL) Confirmation Manager for High-Impact HR Actions.

Enforces explicit human approval for actions that have significant impact
(e.g., approving/rejecting leave, assigning projects, creating announcements).
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Tools and status combinations that require explicit human confirmation
HIGH_IMPACT_ACTIONS: set[str] = {
    "update_leave",
    "assign_project",
    "create_announcement",
    "deactivate_employee",
}

# In-memory pending confirmation cache: confirmation_id -> PendingConfirmation
_PENDING_CONFIRMATIONS: dict[str, dict[str, Any]] = {}
CONFIRMATION_TTL_MINUTES = 10


def is_high_impact_action(tool_name: str, parameters: dict[str, Any]) -> bool:
    """Check if an action tool invocation requires human confirmation."""
    if tool_name not in HIGH_IMPACT_ACTIONS:
        return False
    
    # For update_leave, only status changes (APPROVED/REJECTED) are high impact
    if tool_name == "update_leave":
        status = str(parameters.get("status", "")).upper()
        if status not in ("APPROVED", "REJECTED", "CANCELLED"):
            return False

    return True


def create_confirmation_prompt(tool_name: str, parameters: dict[str, Any]) -> str:
    """Generate a clear, human-readable confirmation prompt."""
    if tool_name == "update_leave":
        req_id = parameters.get("request_id")
        status = parameters.get("status")
        notes = parameters.get("approver_notes", "No notes provided")
        return f"⚠️ **Confirmation Required**: Are you sure you want to update leave request #{req_id} status to **{status}**? (Notes: {notes})"
    
    elif tool_name == "assign_project":
        emp_id = parameters.get("employee_id")
        proj_id = parameters.get("project_id")
        role = parameters.get("role", "Team Member")
        return f"⚠️ **Confirmation Required**: Are you sure you want to assign Employee #{emp_id} to Project #{proj_id} as **{role}**?"

    elif tool_name == "create_announcement":
        title = parameters.get("title")
        role = parameters.get("target_role") or "All Employees"
        return f"⚠️ **Confirmation Required**: Are you sure you want to publish company announcement **'{title}'** to target audience **{role}**?"

    elif tool_name == "deactivate_employee":
        emp_id = parameters.get("employee_id")
        return f"⚠️ **CRITICAL Confirmation Required**: Are you sure you want to DEACTIVATE employee account #{emp_id}? This will revoke system access."

    return f"⚠️ **Confirmation Required**: Please confirm execution of action **{tool_name}** with parameters: {parameters}"


def register_pending_confirmation(
    user_id: int,
    tool_name: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Register a pending confirmation and return token payload."""
    confirmation_id = f"conf_{uuid.uuid4().hex[:12]}"
    expiry = datetime.now(timezone.utc) + timedelta(minutes=CONFIRMATION_TTL_MINUTES)
    
    payload = {
        "confirmation_id": confirmation_id,
        "user_id": user_id,
        "tool_name": tool_name,
        "parameters": parameters,
        "expires_at": expiry.isoformat(),
        "prompt": create_confirmation_prompt(tool_name, parameters),
    }

    _PENDING_CONFIRMATIONS[confirmation_id] = payload
    logger.info("Registered HITL pending confirmation %s for user %d (tool: %s)", confirmation_id, user_id, tool_name)
    return payload


def validate_and_consume_confirmation(
    confirmation_id: str,
    user_id: int,
) -> Optional[dict[str, Any]]:
    """Validate a confirmation ID and consume it if valid."""
    pending = _PENDING_CONFIRMATIONS.get(confirmation_id)
    if not pending:
        logger.warning("HITL confirmation %s not found or expired", confirmation_id)
        return None

    if pending["user_id"] != user_id:
        logger.warning("HITL confirmation user mismatch: expected %d, got %d", pending["user_id"], user_id)
        return None

    expiry = datetime.fromisoformat(pending["expires_at"])
    if datetime.now(timezone.utc) > expiry:
        logger.warning("HITL confirmation %s expired at %s", confirmation_id, expiry)
        _PENDING_CONFIRMATIONS.pop(confirmation_id, None)
        return None

    # Consume token so it cannot be re-used
    _PENDING_CONFIRMATIONS.pop(confirmation_id, None)
    logger.info("Successfully validated and consumed HITL confirmation %s", confirmation_id)
    return pending
