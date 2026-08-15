"""
api_tools.py — Authenticated REST API Dispatcher for HR Action Agent.

Executes HR operations by calling backend REST endpoints in-process using
httpx.ASGITransport with the current user's JWT bearer token.
All database mutations, validations, and permission checks are enforced
by the FastAPI endpoint handlers.
"""

import logging
from typing import Any, Optional
import httpx
from app.main import app

logger = logging.getLogger(__name__)


def _get_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def apply_leave(
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: Optional[str] = None,
    is_half_day: bool = False,
    half_day_period: Optional[str] = None,
    *,
    access_token: str,
) -> dict[str, Any]:
    """Call POST /api/v1/leaves/requests to apply for leave."""
    payload = {
        "leave_type": leave_type.upper(),
        "start_date": start_date,
        "end_date": end_date,
        "reason": reason,
        "is_half_day": is_half_day,
        "half_day_period": half_day_period,
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/leaves/requests", json=payload, headers=_get_headers(access_token))
        if response.is_success:
            return {"success": True, "status_code": response.status_code, "data": response.json()}
        return {"success": False, "status_code": response.status_code, "error": response.json().get("detail", response.text)}


async def update_leave(
    request_id: int,
    status: str,
    approver_notes: Optional[str] = None,
    *,
    access_token: str,
) -> dict[str, Any]:
    """Call PATCH /api/v1/leaves/requests/{request_id} to approve/reject/cancel leave."""
    payload = {
        "status": status.upper(),
        "approver_notes": approver_notes,
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(f"/api/v1/leaves/requests/{request_id}", json=payload, headers=_get_headers(access_token))
        if response.is_success:
            return {"success": True, "status_code": response.status_code, "data": response.json()}
        return {"success": False, "status_code": response.status_code, "error": response.json().get("detail", response.text)}


async def get_leave_balance(*, access_token: str) -> dict[str, Any]:
    """Call GET /api/v1/leaves/balance to fetch user's current leave balance."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/leaves/balance", headers=_get_headers(access_token))
        if response.is_success:
            return {"success": True, "status_code": response.status_code, "data": response.json()}
        return {"success": False, "status_code": response.status_code, "error": response.json().get("detail", response.text)}


async def create_ticket(
    title: str,
    description: str,
    category: str,
    priority: str = "MEDIUM",
    *,
    access_token: str,
) -> dict[str, Any]:
    """Call POST /api/v1/tickets to create an HR/IT ticket."""
    clean_priority = priority.upper()
    if clean_priority == "URGENT":
        clean_priority = "HIGH"
    if clean_priority not in ("LOW", "MEDIUM", "HIGH"):
        clean_priority = "MEDIUM"

    payload = {
        "title": title,
        "description": description,
        "category": category.lower(),
        "priority": clean_priority,
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/tickets", json=payload, headers=_get_headers(access_token))
        if response.is_success:
            return {"success": True, "status_code": response.status_code, "data": response.json()}
        return {"success": False, "status_code": response.status_code, "error": response.json().get("detail", response.text)}


async def update_ticket(
    ticket_id: int,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[int] = None,
    resolution: Optional[str] = None,
    *,
    access_token: str,
) -> dict[str, Any]:
    """Call PATCH /api/v1/tickets/{ticket_id} to update or resolve a ticket."""
    payload: dict[str, Any] = {}
    if status:
        payload["status"] = status.upper()
    if priority:
        payload["priority"] = priority.upper()
    if assigned_to is not None:
        payload["assigned_to"] = assigned_to
    if resolution:
        payload["resolution"] = resolution

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(f"/api/v1/tickets/{ticket_id}", json=payload, headers=_get_headers(access_token))
        if response.is_success:
            return {"success": True, "status_code": response.status_code, "data": response.json()}
        return {"success": False, "status_code": response.status_code, "error": response.json().get("detail", response.text)}


async def create_announcement(
    title: str,
    content: str,
    target_role: Optional[str] = None,
    *,
    access_token: str,
) -> dict[str, Any]:
    """Call POST /api/v1/announcements to publish a company announcement."""
    payload = {
        "title": title,
        "content": content,
        "target_role": target_role.upper() if target_role else None,
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/announcements", json=payload, headers=_get_headers(access_token))
        if response.is_success:
            return {"success": True, "status_code": response.status_code, "data": response.json()}
        return {"success": False, "status_code": response.status_code, "error": response.json().get("detail", response.text)}


async def assign_project(
    employee_id: int,
    project_id: int,
    role: Optional[str] = None,
    joined_at: Optional[str] = None,
    *,
    access_token: str,
) -> dict[str, Any]:
    """Call POST /api/v1/employees/{employee_id}/projects to assign an employee to a project."""
    payload = {
        "project_id": project_id,
        "role": role,
        "joined_at": joined_at,
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/employees/{employee_id}/projects",
            json=payload,
            headers=_get_headers(access_token),
        )
        if response.is_success:
            return {"success": True, "status_code": response.status_code, "data": response.json()}
        return {"success": False, "status_code": response.status_code, "error": response.json().get("detail", response.text)}
