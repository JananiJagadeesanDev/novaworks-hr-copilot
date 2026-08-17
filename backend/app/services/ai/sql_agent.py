"""
sql_agent.py — Natural Language to SQL Agent for NovaWorks HR Intelligence.

Workflow:
  1. Translate natural language HR questions into safe, read-only SQLite queries.
  2. Validate generated SQL through `sql_guardrails` (blocking DML, multi-statement, sensitive fields).
  3. Execute query against database and fetch rows.
  4. Synthesize query results into a clear natural-language summary.
"""

import asyncio
import logging
import re
from typing import Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.employee import Employee, UserRole
from app.services.ai.sql_guardrails import enforce_row_limit, validate_row_level_security, validate_sql

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed DB Schema Context for Prompt
# ---------------------------------------------------------------------------
SCHEMA_DESCRIPTION = """
Available SQLite Tables & Columns:

1. employees:
   - id (INTEGER PRIMARY KEY)
   - employee_id (TEXT UNIQUE, e.g. 'EMP004')
   - first_name (TEXT)
   - last_name (TEXT)
   - email (TEXT UNIQUE)
   - role (TEXT: 'ADMIN', 'MANAGER', 'EMPLOYEE')
   - job_title (TEXT)
   - department_id (INTEGER FK -> departments.id)
   - manager_id (INTEGER FK -> employees.id)
   - hire_date (DATE)
   - is_active (BOOLEAN)

2. departments:
   - id (INTEGER PRIMARY KEY)
   - name (TEXT, e.g. 'Engineering', 'Human Resources', 'Finance')
   - description (TEXT)
   - manager_id (INTEGER FK -> employees.id)

3. projects:
   - id (INTEGER PRIMARY KEY)
   - name (TEXT)
   - description (TEXT)
   - start_date (DATE)
   - end_date (DATE)
   - status (TEXT: 'PLANNED', 'ACTIVE', 'COMPLETED', 'ON_HOLD')

4. employee_projects:
   - id (INTEGER PRIMARY KEY)
   - employee_id (INTEGER FK -> employees.id)
   - project_id (INTEGER FK -> projects.id)
   - role (TEXT, e.g. 'Backend Developer', 'Frontend Developer')
   - joined_at (DATE)

5. skills:
   - id (INTEGER PRIMARY KEY)
   - name (TEXT, e.g. 'Python', 'React', 'SQL', 'FastAPI')
   - category (TEXT)

6. employee_skills:
   - id (INTEGER PRIMARY KEY)
   - employee_id (INTEGER FK -> employees.id)
   - skill_id (INTEGER FK -> skills.id)
   - proficiency_level (TEXT: 'BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT')

7. job_history:
   - id (INTEGER PRIMARY KEY)
   - employee_id (INTEGER FK -> employees.id)
   - department_id (INTEGER FK -> departments.id)
   - job_title (TEXT)
   - start_date (DATE)
   - end_date (DATE)
   - location (TEXT)
   - change_reason (TEXT: 'NEW_HIRE', 'PROMOTION', 'LATERAL_MOVE')

8. leave_balances:
   - id (INTEGER PRIMARY KEY)
   - employee_id (INTEGER FK -> employees.id)
   - leave_type (TEXT: 'ANNUAL', 'SICK', 'CASUAL', 'MATERNITY', 'PATERNITY', 'UNPAID')
   - total_days (FLOAT)
   - used_days (FLOAT)
   - year (INTEGER)

9. leave_requests:
   - id (INTEGER PRIMARY KEY)
   - employee_id (INTEGER FK -> employees.id)
   - leave_type (TEXT: 'ANNUAL', 'SICK', 'CASUAL', 'MATERNITY', 'PATERNITY', 'UNPAID')
   - start_date (DATE)
   - end_date (DATE)
   - days_requested (FLOAT)
   - reason (TEXT)
   - status (TEXT: 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')
   - approved_by (INTEGER FK -> employees.id)
   - approver_note (TEXT)

10. tickets:
    - id (INTEGER PRIMARY KEY)
    - ticket_number (TEXT UNIQUE, e.g. 'TKT-001')
    - employee_id (INTEGER FK -> employees.id)
    - title (TEXT)
    - description (TEXT)
    - category (TEXT: 'payroll', 'benefits', 'it', 'facilities', 'documents', 'general')
    - priority (TEXT: 'LOW', 'MEDIUM', 'HIGH', 'URGENT')
    - status (TEXT: 'OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED')
    - assigned_to (INTEGER FK -> employees.id)
    - resolution (TEXT)

11. announcements:
    - id (INTEGER PRIMARY KEY)
    - title (TEXT)
    - content (TEXT)
    - author_id (INTEGER FK -> employees.id)
    - target_role (TEXT: 'EMPLOYEE', 'MANAGER', 'ADMIN', or NULL for all)
    - is_active (BOOLEAN)

12. onboarding_tasks:
    - id (INTEGER PRIMARY KEY)
    - employee_id (INTEGER FK -> employees.id)
    - title (TEXT)
    - description (TEXT)
    - category (TEXT: 'HR_PAPERWORK', 'IT_SETUP', 'TRAINING', 'SECURITY')
    - status (TEXT: 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED')
    - due_date (DATE)
    - assigned_by (INTEGER FK -> employees.id)
"""

SQL_SYSTEM_PROMPT = f"""You are the NovaWorks SQL Generator.
Your job is to translate natural language questions into safe, valid SQLite SQL queries.

Database Schema:
{SCHEMA_DESCRIPTION}

Strict SQL Generation Rules:
1. Generate ONLY ONE valid SQLite SELECT or WITH query.
2. Output ONLY the raw SQL query inside a markdown code block (```sql ... ```).
3. Do NOT include explanations, comments, or preamble outside the code block.
4. STRICTLY FORBIDDEN to access: hashed_password, salary, bank account details, PAN details, date of birth.
5. If the user refers to "my", "me", "I", use the current user ID provided in the prompt context.
6. Use clear column aliases (e.g. e.first_name || ' ' || e.last_name AS employee_name).
7. Case-insensitive string matching: use LOWER(column) LIKE '%value%' or standard SQLite LIKE.
8. YEAR FILTERING: The `year` column in leave_balances is an INTEGER. When filtering for the
   current year, always use: CAST(strftime('%Y', 'now') AS INTEGER)
   NEVER use strftime('%Y', 'now') directly — it returns TEXT and will not match the INTEGER column.
9. EMPLOYEE ID DISTINCTION — this is critical:
   - `employees.id` is the INTEGER primary key (1, 2, 3 ...) used as a foreign key in ALL other tables
     (leave_balances.employee_id, leave_requests.employee_id, tickets.employee_id, etc.)
   - `employees.employee_id` is a human-readable TEXT string like 'EMP001', 'EMP002' — it is NOT
     used as a foreign key anywhere else.
   - When the user says "my leave balance", filter using: leave_balances.employee_id = <current_user_id>
     where <current_user_id> is the INTEGER `id` value provided in the User Context, NOT the 'EMP00X' string.
10. LEAVE TYPE ALIASES — map common HR/Indian terminology to the correct enum value:
    - "earned leave", "EL", "PL" (privilege leave), "annual leave" → leave_type = 'ANNUAL'
    - "sick leave", "SL", "medical leave"                          → leave_type = 'SICK'
    - "casual leave", "CL"                                          → leave_type = 'ANNUAL' (no CASUAL type exists)
    - "maternity leave"                                             → leave_type = 'MATERNITY'
    - "paternity leave"                                             → leave_type = 'PATERNITY'
    - "unpaid leave", "LWP" (leave without pay)                     → leave_type = 'UNPAID'
    Always use the exact uppercase enum value from the schema.
11. ROLE-BASED ACCESS CONTROL (RBAC) & EMPLOYEE PRIVACY:
    - If User Role = 'EMPLOYEE':
      * An employee is ONLY authorized to view their OWN private records: `leave_balances`, `leave_requests`, `tickets`.
      * If the question asks for another employee's leave balance or leave history (e.g. "What is Priya's leave balance?", "Show me John's leaves"), you MUST NOT query or return the logged-in user's balance, and you MUST NOT return another employee's records. Output ONLY:
        DENIED: Employees are only permitted to view their own leave balances and records.
    - If User Role = 'MANAGER':
      * Managers can query leave balances and requests for direct reports or employees in their department.
    - If User Role = 'ADMIN':
      * Admins can query all employee records.
"""

SYNTHESIS_SYSTEM_PROMPT = """You are the NovaWorks HR Intelligence Assistant.
Given the user's question, the SQL query executed, and the resulting database rows, provide a concise, factual, and professional summary answering the user's question.

Rules:
1. Base your answer strictly on the provided SQL results.
2. If zero rows are returned, clearly state that no matching records were found.
3. Present lists or key metrics clearly and politely.
4. Do not mention internal database column names or raw SQL unless asked.
5. When mentioning a year, use the CURRENT YEAR provided in the context. Never guess or assume a year from your training data.
6. The `leave_balances` table tracks APPROVED leave usage only. PENDING leave requests are stored
   separately in `leave_requests` and do NOT automatically reduce the balance until approved.
   If asked about effective remaining leave, note any pending requests separately.
"""


class SQLAgentService:
    """Service for Natural Language to SQL generation, validation, and execution."""

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.0,  # Zero temperature for deterministic SQL generation
        )

    def _extract_sql(self, text_content: str) -> str:
        """Extract clean SQL from markdown code blocks or plain text."""
        match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text_content.strip()


    async def generate_sql(self, question: str, current_user: Employee) -> str:
        """Generate a SQLite query for the given question and user context."""
        user_context = (
            f"User Context:\n"
            f"- Current User ID: {current_user.id}\n"
            f"- Employee ID: {current_user.employee_id}\n"
            f"- Full Name: {current_user.first_name} {current_user.last_name}\n"
            f"- Role: {current_user.role.value}\n"
            f"- Department ID: {current_user.department_id}\n"
        )
        user_prompt = f"{user_context}\nQuestion: {question}"

        llm = self._get_llm()
        messages = [
            SystemMessage(content=SQL_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = await asyncio.to_thread(llm.invoke, messages)
        raw_sql = self._extract_sql(response.content)
        return raw_sql

    async def synthesize_answer(self, question: str, sql: str, rows: list[dict]) -> str:
        """Generate a natural language summary of query results."""
        import datetime
        current_year = datetime.datetime.now().year
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")

        prompt = (
            f"Current Date: {current_date} (Year: {current_year})\n\n"
            f"User Question: {question}\n\n"
            f"Executed SQL: {sql}\n\n"
            f"Query Results ({len(rows)} rows):\n{rows}\n"
        )

        llm = self._get_llm()
        messages = [
            SystemMessage(content=SYNTHESIS_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = await asyncio.to_thread(llm.invoke, messages)
        return response.content.strip()

    def format_sql_results_fast(self, rows: list[dict], question: str) -> str:
        """Format database rows directly without needing an extra synthesis LLM round-trip."""
        if not rows:
            return "No matching records were found in the database."

        # Single aggregate or single metric (e.g. COUNT(*), remaining_sick_leave, avg_salary)
        if len(rows) == 1 and len(rows[0]) == 1:
            key, val = list(rows[0].items())[0]
            formatted_key = key.replace("_", " ").title()
            return f"**{formatted_key}**: {val}"

        # Leave balances query
        if any("leave_type" in r for r in rows):
            lines = ["Here is your current leave balance summary:"]
            for r in rows:
                l_type = str(r.get("leave_type", "")).title()
                total = r.get("total_days", 0)
                used = r.get("used_days", 0)
                remaining = r.get("remaining_days", total - used if (total is not None and used is not None) else None)
                if remaining is not None:
                    lines.append(f"* **{l_type} Leave**: **{remaining}** days remaining ({total} total, {used} used)")
                else:
                    details = ", ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in r.items())
                    lines.append(f"* **{l_type} Leave**: {details}")
            lines.append("\n*Note: Pending leave requests do not reduce your balance until approved by your manager.*")
            return "\n".join(lines)

        # Tabular formatting for <= 15 rows
        if len(rows) <= 15:
            keys = list(rows[0].keys())
            if len(keys) <= 3 and len(rows) <= 10:
                lines = [f"Found {len(rows)} matching record(s):"]
                for r in rows:
                    item_desc = " | ".join(f"**{k.replace('_', ' ').title()}**: {v}" for k, v in r.items() if v is not None)
                    lines.append(f"* {item_desc}")
                return "\n".join(lines)
            else:
                header = "| " + " | ".join(k.replace('_', ' ').title() for k in keys) + " |"
                divider = "| " + " | ".join("---" for _ in keys) + " |"
                table_rows = [header, divider]
                for r in rows:
                    row_str = "| " + " | ".join(str(r.get(k, "")) for k in keys) + " |"
                    table_rows.append(row_str)
                return f"Found {len(rows)} record(s):\n\n" + "\n".join(table_rows)

        return f"Found {len(rows)} matching records."

    async def ask(self, question: str, current_user: Employee, db: Session) -> dict:
        """Process user question through full NL-to-SQL pipeline.

        Returns:
            dict with 'answer' (str), 'sql' (str), 'rows' (list[dict])
        """
        # 1. Generate SQL
        try:
            generated_sql = await self.generate_sql(question, current_user)
        except Exception as exc:
            logger.error("SQL generation failed: %s", exc, exc_info=True)
            return {
                "answer": "I'm sorry, I was unable to generate a query for your question. Please try rephrasing.",
                "sql": "",
                "rows": [],
            }

        # Check if LLM emitted an explicit RBAC denial
        if "DENIED" in generated_sql.upper():
            return {
                "answer": "I cannot provide this information. As an employee, you only have permission to view your own leave balances and personal records.",
                "sql": "",
                "rows": [],
            }

        # 2. Validate SQL Syntax, Injection, and Sensitive Columns
        is_valid, error_msg = validate_sql(generated_sql)
        if not is_valid:
            logger.warning("Generated SQL failed guardrails: %r | Reason: %s", generated_sql, error_msg)
            return {
                "answer": f"I cannot fulfill this request because it violates security policies: {error_msg}.",
                "sql": generated_sql,
                "rows": [],
            }

        # 3. Enforce Scalable Row-Level Security (RLS)
        rls_valid, rls_error = validate_row_level_security(generated_sql, current_user.id, current_user.role.value)
        if not rls_valid:
            logger.warning("Generated SQL failed RLS check: %r | Reason: %s", generated_sql, rls_error)
            return {
                "answer": "I cannot provide this information. As an employee, you are only permitted to query your own personal records.",
                "sql": generated_sql,
                "rows": [],
            }

        # 4. Enforce maximum row limit
        safe_sql = enforce_row_limit(generated_sql, max_limit=50)

        # 4. Execute SQL
        rows: list[dict] = []
        try:
            result = db.execute(text(safe_sql))
            if result.returns_rows:
                keys = list(result.keys())
                for r in result.fetchall():
                    row_dict = {}
                    for idx, key in enumerate(keys):
                        val = r[idx]
                        # Format dates/enums to serializable strings
                        if hasattr(val, "isoformat"):
                            val = val.isoformat()
                        elif hasattr(val, "value"):
                            val = val.value
                        row_dict[key] = val
                    rows.append(row_dict)
        except Exception as db_exc:
            logger.error("SQL execution failed for query %r: %s", safe_sql, db_exc)
            return {
                "answer": "An error occurred while executing the database query. Please refine your question.",
                "sql": safe_sql,
                "rows": [],
            }

        # 5. Format answer directly (fast-path, avoids 2nd LLM round-trip)
        answer = self.format_sql_results_fast(rows, question)

        return {
            "answer": answer,
            "sql": safe_sql,
            "rows": rows,
        }


# Module singleton
sql_agent_service = SQLAgentService()
