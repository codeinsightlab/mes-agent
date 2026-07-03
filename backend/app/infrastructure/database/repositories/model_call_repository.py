from datetime import datetime

from sqlalchemy.orm import Session

from app.infrastructure.database.models.model_call import AgentModelCall


CALL_STATUS_CALLING = 1
CALL_STATUS_SUCCESS = 2
CALL_STATUS_FAILED = 3
CALL_STATUS_TIMEOUT = 4


class ModelCallRepository:
    def __init__(self, session: Session):
        self._session = session

    def create_calling(
        self,
        call_key: str,
        conversation_id: int,
        request_message_id: int,
        provider: str,
        model: str,
        agent_version: str,
        prompt_version: str,
        tool_version: str | None,
        system_prompt_snapshot: str | None,
        request_snapshot: str,
        now: datetime,
    ) -> AgentModelCall:
        model_call = AgentModelCall(
            call_key=call_key,
            conversation_id=conversation_id,
            request_message_id=request_message_id,
            response_message_id=None,
            provider=provider,
            model=model,
            agent_version=agent_version,
            prompt_version=prompt_version,
            tool_version=tool_version,
            system_prompt_snapshot=system_prompt_snapshot,
            request_snapshot=request_snapshot,
            response_snapshot=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            duration_ms=None,
            call_status=CALL_STATUS_CALLING,
            finish_reason=None,
            error_code=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model_call)
        self._session.flush()
        return model_call

    def update_success(
        self,
        model_call: AgentModelCall,
        response_message_id: int,
        response_snapshot: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        total_tokens: int | None,
        duration_ms: int,
        finish_reason: str | None,
        model: str,
        provider: str,
        now: datetime,
    ):
        model_call.response_message_id = response_message_id
        model_call.response_snapshot = response_snapshot
        model_call.prompt_tokens = prompt_tokens
        model_call.completion_tokens = completion_tokens
        model_call.total_tokens = total_tokens
        model_call.duration_ms = duration_ms
        model_call.call_status = CALL_STATUS_SUCCESS
        model_call.finish_reason = finish_reason
        model_call.error_code = None
        model_call.error_message = None
        model_call.model = model
        model_call.provider = provider
        model_call.updated_at = now
        self._session.flush()

    def update_failure(
        self,
        model_call: AgentModelCall,
        call_status: int,
        duration_ms: int,
        error_code: str,
        error_message: str,
        now: datetime,
    ):
        model_call.response_message_id = None
        model_call.duration_ms = duration_ms
        model_call.call_status = call_status
        model_call.error_code = error_code
        model_call.error_message = error_message
        model_call.updated_at = now
        self._session.flush()

    def get_by_id(self, model_call_id: int) -> AgentModelCall:
        return self._session.get_one(AgentModelCall, model_call_id)
