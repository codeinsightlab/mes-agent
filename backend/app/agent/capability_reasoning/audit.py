import json
from datetime import UTC, datetime

from sqlalchemy import Engine, text

from app.agent.capability_reasoning.models import (
    CapabilityReasoningResult,
    CapabilityValidationResult,
)
from app.core.type_defs import JsonObject


class CapabilityReasoningAuditRepository:
    def __init__(self, engine: Engine):
        self._engine = engine
        self.create_schema()

    def create_schema(self) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS capability_reasoning_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id VARCHAR(64) NOT NULL,
                        user_input TEXT NOT NULL,
                        context_level VARCHAR(64) NOT NULL,
                        candidate_capabilities TEXT NOT NULL,
                        selected_capability VARCHAR(128),
                        confidence FLOAT NOT NULL,
                        reasoning_result TEXT NOT NULL,
                        validation_result TEXT NOT NULL,
                        execution_result TEXT,
                        created_at VARCHAR(64) NOT NULL
                    )
                    """
                )
            )

    def record(
        self,
        *,
        request_id: str,
        user_input: str,
        reasoning_result: CapabilityReasoningResult,
        validation_result: CapabilityValidationResult,
        execution_result: JsonObject | None = None,
    ) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO capability_reasoning_audit (
                        request_id,
                        user_input,
                        context_level,
                        candidate_capabilities,
                        selected_capability,
                        confidence,
                        reasoning_result,
                        validation_result,
                        execution_result,
                        created_at
                    )
                    VALUES (
                        :request_id,
                        :user_input,
                        :context_level,
                        :candidate_capabilities,
                        :selected_capability,
                        :confidence,
                        :reasoning_result,
                        :validation_result,
                        :execution_result,
                        :created_at
                    )
                    """
                ),
                {
                    "request_id": request_id,
                    "user_input": user_input,
                    "context_level": reasoning_result.context_level,
                    "candidate_capabilities": json.dumps(
                        [
                            item.model_dump(mode="json")
                            for item in reasoning_result.candidate_capabilities
                        ],
                        ensure_ascii=False,
                    ),
                    "selected_capability": reasoning_result.selected_capability,
                    "confidence": reasoning_result.confidence,
                    "reasoning_result": reasoning_result.model_dump_json(),
                    "validation_result": validation_result.model_dump_json(),
                    "execution_result": (
                        json.dumps(execution_result, ensure_ascii=False)
                        if execution_result is not None
                        else None
                    ),
                    "created_at": datetime.now(UTC).isoformat(),
                },
            )
