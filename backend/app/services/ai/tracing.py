"""
tracing.py — AI Workflow Observability & Tracing Service for NovaWorks Copilot.

Provides OpenTelemetry/LangSmith compatible structured tracing for AI workflows.
Tracks prompt inputs, model outputs, tool parameters, execution latency (ms),
token usage estimates, and permission/guardrail intercept statuses.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger("ai_tracer")


class AITraceSpan:
    """Represents a single trace span for an AI agent interaction."""

    def __init__(
        self,
        span_id: str,
        agent_name: str,
        employee_id: int,
        role: str,
        input_prompt: str,
    ):
        self.span_id = span_id
        self.agent_name = agent_name
        self.employee_id = employee_id
        self.role = role
        self.input_prompt = input_prompt
        self.start_time = time.perf_counter()
        self.end_time: Optional[float] = None
        self.latency_ms: float = 0.0
        self.status = "SUCCESS"
        self.output_response: Optional[str] = None
        self.tool_called: Optional[str] = None
        self.tool_params: dict[str, Any] = {}
        self.tokens_estimated: int = 0
        self.error: Optional[str] = None

    def finish(
        self,
        output_response: Optional[str] = None,
        tool_called: Optional[str] = None,
        tool_params: Optional[dict[str, Any]] = None,
        status: str = "SUCCESS",
        error: Optional[str] = None,
    ):
        """Finalize trace span and compute latency and token statistics."""
        self.end_time = time.perf_counter()
        self.latency_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.output_response = output_response
        self.tool_called = tool_called
        self.tool_params = tool_params or {}
        self.status = status
        self.error = error
        
        # Simple token estimation heuristic (1 token ~= 4 chars)
        in_tokens = len(self.input_prompt or "") // 4
        out_tokens = len(output_response or "") // 4
        self.tokens_estimated = in_tokens + out_tokens

        self._log_trace()

    def _log_trace(self):
        """Output trace log event formatted for OpenTelemetry/LangSmith ingested logs."""
        trace_data = {
            "trace_event": "ai_span_completion",
            "span_id": self.span_id,
            "agent_name": self.agent_name,
            "employee_id": self.employee_id,
            "role": self.role,
            "latency_ms": self.latency_ms,
            "estimated_tokens": self.tokens_estimated,
            "status": self.status,
            "tool_called": self.tool_called,
            "error": self.error,
        }
        logger.info("[TRACE] %s", trace_data)


class AITracer:
    """Manager for creating and recording AI execution trace spans."""

    @asynccontextmanager
    async def trace_span(
        self,
        agent_name: str,
        employee_id: int,
        role: str,
        input_prompt: str,
    ) -> AsyncGenerator[AITraceSpan, None]:
        span_id = f"span_{uuid.uuid4().hex[:12]}"
        span = AITraceSpan(
            span_id=span_id,
            agent_name=agent_name,
            employee_id=employee_id,
            role=role,
            input_prompt=input_prompt,
        )
        try:
            yield span
        except Exception as exc:
            span.finish(status="ERROR", error=str(exc))
            raise


ai_tracer = AITracer()
