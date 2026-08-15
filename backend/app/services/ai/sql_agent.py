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
from app.models.employee import Employee
from app.services.ai.sql_guardrails import enforce_row_limit, validate_sql

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
"""

SYNTHESIS_SYSTEM_PROMPT = """You are the NovaWorks HR Intelligence Assistant.
Given the user's question, the SQL query executed, and the resulting database rows, provide a concise, factual, and professional summary answering the user's question.

Rules:
1. Base your answer strictly on the provided SQL results.
2. If zero rows are returned, clearly state that no matching records were found.
3. Present lists or key metrics clearly and politely.
4. Do not mention internal database column names or raw SQL unless asked.
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
        prompt = (
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

        # 2. Validate SQL against Guardrails
        is_valid, error_msg = validate_sql(generated_sql)
        if not is_valid:
            logger.warning("Generated SQL failed guardrails: %r | Reason: %s", generated_sql, error_msg)
            return {
                "answer": f"I cannot fulfill this request because it violates security policies: {error_msg}.",
                "sql": generated_sql,
                "rows": [],
            }

        # 3. Enforce maximum row limit
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

        # 5. Synthesize natural language answer
        try:
            answer = await self.synthesize_answer(question, safe_sql, rows)
        except Exception as synth_exc:
            logger.error("Answer synthesis failed: %s", synth_exc)
            answer = f"Found {len(rows)} matching record(s)."

        return {
            "answer": answer,
            "sql": safe_sql,
            "rows": rows,
        }


# Module singleton
sql_agent_service = SQLAgentService()
