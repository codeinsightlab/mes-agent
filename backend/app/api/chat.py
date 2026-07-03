from fastapi import APIRouter, Depends, HTTPException

from app.application.chat_persistence_service import ChatPersistenceService
from app.application.chat_result import ChatUseCaseResult
from app.application.chat_service import ChatApplicationService
from app.core.config import get_settings
from app.domain.llm.exceptions import (
    LlmAuthenticationError,
    LlmCallError,
    LlmConfigurationError,
    LlmResponseFormatError,
    LlmTimeoutError,
    LlmUnavailableError,
)
from app.domain.persistence.exceptions import (
    ConversationInitializationError,
    DatabaseConfigurationError,
    DatabaseConnectionError,
    ModelResultPersistenceError,
)
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.llm.client_factory import create_llm_client
from app.schemas.chat import ChatApiRequest, ChatApiResponse, TokenUsageApiResponse


router = APIRouter(prefix="/api", tags=["chat"])
_chat_service: ChatApplicationService | None = None
_database_engine = None


def get_chat_service() -> ChatApplicationService:
    global _chat_service, _database_engine
    if _chat_service is not None:
        return _chat_service

    try:
        settings = get_settings()
        _database_engine = create_database_engine(settings)
        session_factory = create_session_factory(_database_engine)
        _chat_service = ChatApplicationService(
            llm_client=create_llm_client(settings),
            persistence_service=ChatPersistenceService(session_factory),
            provider=settings.llm_provider,
            model=settings.llm_model,
            agent_version=settings.agent_version,
            prompt_version=settings.prompt_version,
            tool_version=settings.tool_version,
        )
        return _chat_service
    except LlmConfigurationError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "llm_configuration_error", "message": str(exc)},
        ) from exc
    except DatabaseConfigurationError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "database_configuration_error", "message": str(exc)},
        ) from exc


def close_chat_service():
    global _chat_service, _database_engine
    if _chat_service is not None:
        _chat_service.close()
        _chat_service = None
    if _database_engine is not None:
        _database_engine.dispose()
        _database_engine = None


def to_api_response(result: ChatUseCaseResult) -> ChatApiResponse:
    response = result.response
    usage = None
    if response.usage is not None:
        usage = TokenUsageApiResponse(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

    return ChatApiResponse(
        content=response.content,
        model=response.model,
        provider=response.provider,
        conversation_key=result.conversation_key,
        response_message_key=result.response_message_key,
        call_key=result.call_key,
        finish_reason=response.finish_reason,
        usage=usage,
    )


@router.post("/chat", response_model=ChatApiResponse)
def chat(
    request: ChatApiRequest,
    service: ChatApplicationService = Depends(get_chat_service),
):
    message = request.message.strip()
    if not message:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_request", "message": "message cannot be empty."},
        )

    try:
        return to_api_response(service.chat(message))
    except LlmConfigurationError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "llm_configuration_error", "message": str(exc)},
        ) from exc
    except LlmAuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "llm_authentication_error",
                "message": "LLM provider authentication failed.",
            },
        ) from exc
    except LlmTimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={"error": "llm_timeout", "message": "LLM provider request timed out."},
        ) from exc
    except LlmUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "llm_unavailable",
                "message": "LLM provider is temporarily unavailable.",
            },
        ) from exc
    except LlmResponseFormatError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "llm_response_format_error",
                "message": "LLM provider returned an unexpected response.",
            },
        ) from exc
    except LlmCallError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "llm_call_error", "message": "LLM provider call failed."},
        ) from exc
    except DatabaseConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "database_connection_error",
                "message": "Database connection failed.",
            },
        ) from exc
    except ConversationInitializationError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "conversation_initialization_error",
                "message": "Failed to initialize chat records.",
            },
        ) from exc
    except ModelResultPersistenceError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "model_result_persistence_error",
                "message": "Failed to save model result.",
            },
        ) from exc
