"""
sql_guardrails.py — Security & validation guardrails for the SQL Agent.

Responsibilities:
  - Ensure SQL queries are strictly read-only (SELECT / WITH).
  - Block DML and DDL commands (INSERT, UPDATE, DELETE, DROP, ALTER, etc.).
  - Block attempts to query forbidden sensitive columns (passwords, salaries, PAN, bank info).
  - Block multi-statement execution / SQL injection chaining.
  - Enforce maximum row limits (default: 50).
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Forbidden Keywords & Commands (Case-Insensitive)
# ---------------------------------------------------------------------------
FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "PRAGMA",
    "ATTACH",
    "DETACH",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
    "UPSERT",
    "MERGE",
    "CALL",
    "INTO",
}

# ---------------------------------------------------------------------------
# Forbidden Sensitive Columns (Privacy & Security Reference)
# ---------------------------------------------------------------------------
FORBIDDEN_COLUMNS = {
    "hashed_password",
    "bank_account_number",
    "bank_account_name",
    "bank_branch",
    "bank_ifsc",
    "pan_number",
    "pan_name",
    "pan_dob",
    "date_of_birth",
    "current_salary_usd",
    "profile_photo_path",
    "profile_photo_mime",
}

# Regex to strip single-line and multi-line SQL comments
COMMENT_REGEX = re.compile(r"(--[^\n]*)|(/\*[\s\S]*?\*/)")


def clean_sql(sql: str) -> str:
    """Strip comments and normalize whitespace."""
    no_comments = COMMENT_REGEX.sub(" ", sql)
    return " ".join(no_comments.split()).strip()


def validate_sql(sql: str) -> tuple[bool, Optional[str]]:
    """Validate a generated SQL query against all safety rules.

    Returns:
        (is_valid, error_message): (True, None) if safe, or (False, reason) if unsafe.
    """
    cleaned = clean_sql(sql)
    if not cleaned:
        return False, "Query is empty"

    # 1. Block multi-statement chaining (; separated queries)
    # Allow a trailing semicolon if it's the very last character
    statements = [s.strip() for s in cleaned.rstrip(";").split(";") if s.strip()]
    if len(statements) > 1:
        return False, "Multiple SQL statements are not permitted"

    statement = statements[0]
    upper_sql = statement.upper()

    # 2. Must start with SELECT or WITH
    if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
        return False, "Only read-only SELECT or WITH statements are permitted"

    # 3. Tokenize words to inspect forbidden keywords
    tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", statement))
    upper_tokens = {t.upper() for t in tokens}
    lower_tokens = {t.lower() for t in tokens}

    # Check forbidden keywords
    blocked_keywords = upper_tokens.intersection(FORBIDDEN_KEYWORDS)
    # Exception: INTO is forbidden unless part of valid read-only structure (which SQLite doesn't use for SELECT)
    if blocked_keywords:
        return False, f"Forbidden SQL operation detected: {', '.join(sorted(blocked_keywords))}"

    # 4. Check forbidden sensitive columns
    blocked_cols = lower_tokens.intersection(FORBIDDEN_COLUMNS)
    if blocked_cols:
        return False, f"Access to sensitive column(s) is prohibited: {', '.join(sorted(blocked_cols))}"

    # Also check direct substring occurrences (e.g. table.column or column alias)
    lower_sql = statement.lower()
    for col in FORBIDDEN_COLUMNS:
        if re.search(rf"\b{re.escape(col)}\b", lower_sql):
            return False, f"Access to sensitive column(s) is prohibited: {col}"

    return True, None


def enforce_row_limit(sql: str, max_limit: int = 50) -> str:
    """Ensure the SQL query has a LIMIT clause <= max_limit."""
    cleaned = clean_sql(sql).rstrip(";")
    limit_match = re.search(r"\bLIMIT\s+(\d+)", cleaned, re.IGNORECASE)

    if limit_match:
        current_limit = int(limit_match.group(1))
        if current_limit > max_limit:
            cleaned = re.sub(
                r"\bLIMIT\s+\d+",
                f"LIMIT {max_limit}",
                cleaned,
                flags=re.IGNORECASE,
            )
        return cleaned
    else:
        return f"{cleaned} LIMIT {max_limit}"
