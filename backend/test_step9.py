"""
test_step9.py — Automated verification for Step 9: POST /api/v1/chat/policy endpoint.

Tests:
1. Authentication verification (401/403 when unauthenticated)
2. In-scope policy question via HTTP POST /api/v1/chat/policy
3. Grounding & Source attribution in response structure
4. Out-of-scope question guardrail behavior
5. Input validation on empty payload

Usage:
    cd backend
    .\\.venv\\Scripts\\python test_step9.py
"""

import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from app.main import app


def print_step(title: str):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main():
    print_step("Step 9 Verification: POST /api/v1/chat/policy")
    client = TestClient(app)

    # 1. Login to obtain JWT token
    print("[1/5] Authenticating as employee (raj.kumar@novaworks.com)...")
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "raj.kumar@novaworks.com", "password": "Employee@123"},
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token_data = login_res.json()
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[+] Authenticated successfully. User: {token_data['full_name']} ({token_data['role']})")

    # 2. Unauthenticated request protection
    print_step("[2/5] Testing Auth Guard (Unauthenticated Request)")
    unauth_res = client.post("/api/v1/chat/policy", json={"message": "What is the leave policy?"})
    print(f"Status without token: {unauth_res.status_code}")
    assert unauth_res.status_code in (401, 403), f"Expected 401/403, got {unauth_res.status_code}"
    print("[+] Auth protection verified: Unauthenticated request rejected.")

    # 3. In-scope policy chat query
    print_step("[3/5] Testing In-Scope Policy Chat Request")
    question = "How many days of sick leave are employees entitled to per year?"
    print(f"Sending POST /api/v1/chat/policy with message: '{question}'")
    chat_res = client.post(
        "/api/v1/chat/policy",
        headers=headers,
        json={"message": question},
    )
    assert chat_res.status_code == 200, f"Chat request failed: {chat_res.text}"
    body = chat_res.json()
    print("Response payload:")
    print(f"  success: {body['success']}")
    print(f"  answer:  {body['data']['answer']}")
    print(f"  sources: {body['data']['sources']}")

    assert body["success"] is True, "Expected success to be True"
    assert "10" in body["data"]["answer"] or "sick" in body["data"]["answer"].lower(), "Expected answer to mention sick leave details"
    assert len(body["data"]["sources"]) > 0, "Expected at least one source document attribution"
    print("[+] In-scope policy question answered accurately with sources.")

    # 4. Out-of-scope query guardrail test
    print_step("[4/5] Testing Out-of-Scope / Hallucination Guardrail")
    out_scope_q = "What is the secret recipe for the cafeteria soup and what is the stock price?"
    print(f"Sending POST /api/v1/chat/policy with message: '{out_scope_q}'")
    out_res = client.post(
        "/api/v1/chat/policy",
        headers=headers,
        json={"message": out_scope_q},
    )
    assert out_res.status_code == 200, f"Request failed: {out_res.text}"
    out_body = out_res.json()
    print("Response payload:")
    print(f"  success: {out_body['success']}")
    print(f"  answer:  {out_body['data']['answer']}")
    assert out_body["success"] is True
    assert (
        "don't have enough information" in out_body["data"]["answer"].lower()
        or "contact the hr team" in out_body["data"]["answer"].lower()
    ), "Expected guardrail refusal response for out-of-scope question"
    print("[+] Out-of-scope question cleanly refused by Policy RAG guardrail.")

    # 5. Empty payload validation
    print_step("[5/5] Testing Request Validation (Empty Question)")
    val_res = client.post(
        "/api/v1/chat/policy",
        headers=headers,
        json={"message": "   "},
    )
    print(f"Status for empty message: {val_res.status_code}")
    assert val_res.status_code == 422, f"Expected 422 for blank message, got {val_res.status_code}"
    print("[+] Validation verified: Empty message rejected with 422.")

    print("\n" + "=" * 60)
    print("🎉 STEP 9 PASSED ALL VERIFICATIONS!")
    print("=" * 60)


if __name__ == "__main__":
    main()
