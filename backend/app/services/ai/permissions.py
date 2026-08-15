"""
permissions.py — AI Action Permissions Matrix & Access Control.

Defines role permissions for HR Action Agent tools:
- EMPLOYEE: Can apply for leave, check leave balances, create tickets, view own records.
- MANAGER:  Employee permissions + approve/reject leave, assign/resolve tickets, create announcements, assign projects.
- ADMIN:    Full permissions across all actions.
"""

from typing import Optional
from app.models.employee import UserRole

# ---------------------------------------------------------------------------
# Action Permissions Mapping
# ---------------------------------------------------------------------------

ACTION_PERMISSIONS: dict[str, set[UserRole]] = {
    # Leave actions
    "apply_leave": {UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.ADMIN},
    "get_leave_balance": {UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.ADMIN},
    "cancel_leave": {UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.ADMIN},
    "approve_leave": {UserRole.MANAGER, UserRole.ADMIN},
    "reject_leave": {UserRole.MANAGER, UserRole.ADMIN},
    "update_leave": {UserRole.MANAGER, UserRole.ADMIN},

    # Ticket actions
    "create_ticket": {UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.ADMIN},
    "update_ticket": {UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.ADMIN},
    "assign_ticket": {UserRole.MANAGER, UserRole.ADMIN},
    "resolve_ticket": {UserRole.MANAGER, UserRole.ADMIN},

    # Announcement actions
    "create_announcement": {UserRole.MANAGER, UserRole.ADMIN},

    # Project actions
    "assign_project": {UserRole.MANAGER, UserRole.ADMIN},
}


def check_action_permission(
    action: str,
    role: UserRole,
    params: Optional[dict] = None,
) -> tuple[bool, Optional[str]]:
    """Check whether a user with `role` is permitted to execute `action`.

    Returns:
        (is_allowed, error_message): (True, None) if permitted, or (False, reason) if denied.
    """
    # Fine-grained check for update_leave
    if action == "update_leave":
        status = ((params or {}).get("status") or "").upper()
        if status == "CANCELLED":
            return True, None
        if role not in (UserRole.MANAGER, UserRole.ADMIN):
            action_desc = "approve or reject leave requests" if status in ("APPROVED", "REJECTED") else "update leave requests"
            return False, f"You do not have permission to {action_desc}."
        return True, None

    allowed_roles = ACTION_PERMISSIONS.get(action)
    if allowed_roles is None:
        return False, f"Unknown action: '{action}'"

    if role in allowed_roles:
        return True, None

    action_readable = action.replace("_", " ")
    return (
        False,
        f"You do not have permission to {action_readable}. "
        f"This action requires one of the following roles: {', '.join([r.value for r in sorted(allowed_roles, key=lambda x: x.value)])}.",
    )
