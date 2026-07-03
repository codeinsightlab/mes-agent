from fastapi import APIRouter, Depends, HTTPException

from app.agent.catalog.heat_treatment import TOOL_VERSION
from app.agent.graph import build_agent_graph
from app.agent.nodes.tool_matcher import LangChainToolMatcher
from app.application.agent_query_service import AgentQueryService
from app.core.config import get_settings
from app.domain.llm.exceptions import LlmConfigurationError
from app.infrastructure.agent.langchain_factory import create_agent_chat_model
from app.schemas.agent import AgentQueryRequest, AgentQueryResponse


router = APIRouter(prefix="/api/agent", tags=["agent"])
_agent_service: AgentQueryService | None = None


def get_agent_query_service() -> AgentQueryService:
    global _agent_service
    if _agent_service is not None:
        return _agent_service
    try:
        settings = get_settings()
        matcher = LangChainToolMatcher(create_agent_chat_model(settings))
        compiled_graph = build_agent_graph(
            matcher=matcher,
            match_threshold=settings.agent_tool_match_threshold,
        )
        _agent_service = AgentQueryService(
            compiled_graph=compiled_graph,
            agent_version=settings.agent_version,
            prompt_version=settings.prompt_version,
            tool_version=settings.tool_version or TOOL_VERSION,
        )
        return _agent_service
    except LlmConfigurationError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "llm_configuration_error", "message": str(exc)},
        ) from exc


def close_agent_query_service():
    global _agent_service
    _agent_service = None


@router.post("/query", response_model=AgentQueryResponse)
def agent_query(
    request: AgentQueryRequest,
    service: AgentQueryService = Depends(get_agent_query_service),
):
    return service.query(request.message)
