import json
import logging
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.agent.reasoning.capability_reasoning.models import CapabilityReasoningResult


class CapabilityReasoningAuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_input: str
    prompt_version: str
    available_capabilities: list[str]
    business_fact_version: str
    llm_output: CapabilityReasoningResult | str | dict[str, object]
    selected_capability: str | None
    confidence: float
    need_clarification: bool
    parse_error: str | None = None


class CapabilityReasoningAuditSink(Protocol):
    def record(self, audit: CapabilityReasoningAuditRecord) -> None: ...


class LoggingCapabilityReasoningAuditSink:
    def __init__(self, logger: logging.Logger | None = None):
        self._logger = logger or logging.getLogger("agent.reasoning.audit")

    def record(self, audit: CapabilityReasoningAuditRecord) -> None:
        self._logger.info(
            "capability_reasoning_audit %s",
            json.dumps(audit.model_dump(mode="json"), ensure_ascii=False),
        )
