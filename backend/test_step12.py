"""
test_step12.py — Automated verification for Step 12: HR Action Agent + api_tools + permissions.

Tests:
1. Permission Matrix Unit Tests
2. Employee Tool Call: Apply Sick Leave
3. Employee Tool Call: Create Support Ticket
4. Permission Interception: Employee trying to approve leave
5. Manager Tool Call: Approve Leave Request
6. Manager Tool Call: Assign Employee to Project

Usage:
    cd backend
    .\\.venv\\Scripts\\python test_step12.py
"""

import asyncio
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
import app.db.base_import  # noqa: F401
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.employee import Employee, UserRole
from app.services.ai.action_agent import action_agent_service
from app.services.ai.permissions import check_action_permission


def print_step(title: str):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


async def run_tests():
    print_step("Step 12 Verification: HR Action Agent, Tools & Permissions")
    db = SessionLocal()

    try:
        # 1. Permission Matrix Tests
        print_step("[1/6] Testing Role Permissions Matrix")
        allowed_emp, _ = check_action_permission("apply_leave", UserRole.EMPLOYEE)
        assert allowed_emp is True
        print("  [+] Employee allowed to apply_leave: True")

        denied_emp, reason = check_action_permission("approve_leave", UserRole.EMPLOYEE)
        assert denied_emp is False
        print(f"  [+] Employee blocked from approve_leave: {reason}")

        denied_ann, _ = check_action_permission("create_announcement", UserRole.EMPLOYEE)
        assert denied_ann is False
        print("  [+] Employee blocked from create_announcement: True")

        allowed_mgr, _ = check_action_permission("approve_leave", UserRole.MANAGER)
        assert allowed_mgr is True
        print("  [+] Manager allowed to approve_leave: True")

        allowed_proj, _ = check_action_permission("assign_project", UserRole.MANAGER)
        assert allowed_proj is True
        print("  [+] Manager allowed to assign_project: True")

        # Fetch test users
        emp_raj = db.query(Employee).filter(Employee.email == "raj.kumar@novaworks.com").first()
        mgr_priya = db.query(Employee).filter(Employee.email == "priya.sharma@novaworks.com").first()
        emp_sara = db.query(Employee).filter(Employee.email == "sara.thomas@novaworks.com").first()

        assert emp_raj is not None and mgr_priya is not None and emp_sara is not None

        raj_token = create_access_token(subject=emp_raj.id, role=emp_raj.role.value)
        priya_token = create_access_token(subject=mgr_priya.id, role=mgr_priya.role.value)

        # 2. Employee Action: Apply Sick Leave
        print_step("[2/6] Testing Employee Action: Apply Sick Leave")
        msg_leave = "Apply sick leave from 2025-09-10 to 2025-09-11 because of dental surgery."
        print(f"User Request (Raj Kumar): '{msg_leave}'")
        res_leave = await action_agent_service.run(msg_leave, emp_raj, raj_token)
        print(f"Action Taken: {res_leave['action_taken']}")
        print(f"Tool Result:  {res_leave['tool_result']}")
        print(f"Synthesized Answer:\n{res_leave['answer']}\n")

        assert res_leave["tool_called"] == "apply_leave"
        assert res_leave["tool_result"].get("success") is True, f"Failed: {res_leave['tool_result']}"
        leave_id = res_leave["tool_result"]["data"]["id"]
        print(f"[+] Leave request #{leave_id} created successfully with status PENDING.")

        # 3. Employee Action: Create Ticket
        print_step("[3/6] Testing Employee Action: Create Support Ticket")
        msg_ticket = "Create an urgent IT ticket: Cannot connect to production database server."
        print(f"User Request (Raj Kumar): '{msg_ticket}'")
        res_ticket = await action_agent_service.run(msg_ticket, emp_raj, raj_token)
        print(f"Action Taken: {res_ticket['action_taken']}")
        print(f"Tool Result:  {res_ticket['tool_result']}")
        print(f"Synthesized Answer:\n{res_ticket['answer']}\n")

        assert res_ticket["tool_called"] == "create_ticket"
        assert res_ticket["tool_result"].get("success") is True
        print("[+] Support ticket created successfully.")

        # 4. Unauthorized Action Interception
        print_step("[4/6] Testing Permission Defense (Employee trying to approve leave)")
        msg_hack = f"Approve leave request {leave_id}."
        print(f"User Request (Raj Kumar): '{msg_hack}'")
        res_hack = await action_agent_service.run(msg_hack, emp_raj, raj_token)
        print(f"Action Taken: {res_hack['action_taken']}")
        print(f"Synthesized Answer:\n{res_hack['answer']}\n")

        assert res_hack["action_taken"] == "DENIED"
        assert "do not have permission" in res_hack["answer"].lower()
        print("[+] Unauthorized action successfully intercepted before API dispatch.")

        # 5. Manager Action: Approve Leave Request
        print_step("[5/6] Testing Manager Action: Approve Leave Request")
        msg_approve = f"Approve leave request {leave_id} with note: Dental leave approved. Take care."
        print(f"User Request (Priya Sharma, Manager): '{msg_approve}'")
        res_approve = await action_agent_service.run(msg_approve, mgr_priya, priya_token)
        print(f"Action Taken: {res_approve['action_taken']}")
        print(f"Tool Result:  {res_approve['tool_result']}")
        print(f"Synthesized Answer:\n{res_approve['answer']}\n")

        assert res_approve["tool_called"] == "update_leave"
        assert res_approve["tool_result"].get("success") is True
        assert res_approve["tool_result"]["data"]["status"] == "APPROVED"
        print(f"[+] Leave request #{leave_id} successfully approved by Manager.")

        # 6. Manager Action: Assign Employee to Project
        print_step("[6/6] Testing Manager Action: Assign Employee to Project")
        msg_proj = f"Assign employee {emp_sara.id} to project 2 as Senior Frontend Lead."
        print(f"User Request (Priya Sharma, Manager): '{msg_proj}'")
        res_proj = await action_agent_service.run(msg_proj, mgr_priya, priya_token)
        print(f"Action Taken: {res_proj['action_taken']}")
        print(f"Tool Result:  {res_proj['tool_result']}")
        print(f"Synthesized Answer:\n{res_proj['answer']}\n")

        assert res_proj["tool_called"] == "assign_project"
        assert res_proj["tool_result"].get("success") is True
        print("[+] Project assignment successfully executed by Manager.")

        print("\n" + "=" * 60)
        print("🎉 STEP 12 PASSED ALL VERIFICATIONS!")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_tests())
