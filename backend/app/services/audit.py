"""
audit.py - Standalone AI audit logging service.

Responsibilities:
  - Provide a simple interface for logging AI interactions.
  - Redact sensitive information (PII, secrets) from logs before saving.
  - Write the sanitized log entry to the `ai_audit_logs` database table.
"""

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.ai_audit_log import AIAuditLog, AgentType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redaction Patterns
# ---------------------------------------------------------------------------

# Regex for Indian PAN card numbers (e.g., ABCDE1234F)
PAN_REGEX = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]{1}")

# Regex for common bank account number formats (highly generic)
BANK_ACCOUNT_REGEX = re.compile(r"\b\d{9,18}\b")

# Regex for Indian IFSC codes (e.g., SBIN0001234)
IFSC_REGEX = re.compile(r"[A-Z]{4}0[A-Z0-9]{6}")

# Words that might indicate a secret or key
SECRET_KEYWORDS = ["secret", "password", "token", "key", "apikey", "api_key", "jwt"]

REDACTION_PATTERNS = {
    "pan_number": PAN_REGEX,
    "bank_account_number": BANK_ACCOUNT_REGEX,
    "ifsc_code": IFSC_REGEX,
}

REDACTION_MASK = "[REDACTED]"


def _redact_string(text: str) -> str:
    """Applies all redaction regexes to a single string."""
    if not isinstance(text, str):
        return text

    for pattern in REDACTION_PATTERNS.values():
        text = pattern.sub(REDACTION_MASK, text)

    # Also check for secret keywords in a case-insensitive way
    for keyword in SECRET_KEYWORDS:
        if keyword in text.lower():
            # This is a simple redaction, might need more sophisticated logic
            # for structured data like '{"secret": "value"}'.
            text = f"{REDACTION_MASK}_DETECTED_NEAR_{keyword.upper()}"
            break

    return text


def _redact_recursive(data: Any) -> Any:
    """Recursively traverses a data structure and redacts sensitive strings."""
    if isinstance(data, str):
        return _redact_string(data)
    if isinstance(data, dict):
        return {key: _redact_recursive(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_redact_recursive(item) for item in data]
    return data


# ---------------------------------------------------------------------------
# AuditService
# ---------------------------------------------------------------------------

class AuditService:
    """Provides a method to log AI interactions with PII redaction."""

    def log_interaction(
        self,
        db: Session,
        *,
        employee_id: int | None,
        agent_type: AgentType,
        query: str,
        response: str | None = None,
        action_taken: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Creates and saves an AI audit log entry using the correct schema."""
        try:
            # Redact all relevant fields before logging
            sanitized_query = _redact_string(query)
            sanitized_response = _redact_string(response) if response else None
            sanitized_metadata = _redact_recursive(metadata) if metadata else None

            audit_log = AIAuditLog(
                employee_id=employee_id,
                agent_type=agent_type,
                query=sanitized_query,
                response=sanitized_response,
                action_taken=action_taken,
                metadata_json=json.dumps(sanitized_metadata, default=str) if sanitized_metadata else None,
            )
            db.add(audit_log)
            db.commit()
            logger.info("Successfully created AI audit log entry %d for agent %s", audit_log.id, agent_type.value)

        except Exception as exc:
            logger.error(
                "Failed to create AI audit log for user %d and agent %s: %s",
                employee_id,
                agent_type.value,
                exc,
                exc_info=True,
            )
            db.rollback()


# Module-level singleton
audit_service = AuditService()
