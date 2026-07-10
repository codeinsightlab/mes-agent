from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.type_defs import JsonObject


class SemanticRouterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    semantic_router_version: str = "v1"
    domain: str
    intent: str
    entities: JsonObject = Field(default_factory=dict)
    confidence: float = Field(..., ge=0, le=1)
    need_clarification: bool
    clarification_reason: str | None = None

    @field_validator("domain", "intent")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field must not be empty")
        return stripped

    @field_validator("clarification_reason")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
