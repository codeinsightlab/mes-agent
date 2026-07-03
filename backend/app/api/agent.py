from fastapi import APIRouter, Depends, HTTPException

from app.agent.catalog.heat_treatment import TOOL_VERSION
from app.agent.graph import build_agent_graph
from app.agent.nodes.text_to_sql import TextToSqlNode
from app.agent.nodes.tool_matcher import LangChainToolMatcher
from app.agent.text_to_sql.executor import ReadonlySqlExecutor
from app.agent.text_to_sql.generator import TextToSqlGenerator
from app.agent.text_to_sql.normalizer import ResultNormalizer
from app.agent.text_to_sql.schema_provider import HeatTreatmentSchemaProvider
from app.agent.text_to_sql.validator import SqlValidator
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
        chat_model = create_agent_chat_model(settings)
        matcher = LangChainToolMatcher(chat_model)
        text_to_sql_node = TextToSqlNode(
            schema_provider=HeatTreatmentSchemaProvider(),
            generator=TextToSqlGenerator(
                chat_model=chat_model,
                max_limit=settings.agent_text_to_sql_max_limit,
            ),
            validator=SqlValidator(max_limit=settings.agent_text_to_sql_max_limit),
            executor=ReadonlySqlExecutor(
                settings=settings,
                max_rows=settings.agent_text_to_sql_max_limit,
                timeout_seconds=settings.agent_text_to_sql_timeout_seconds,
            ),
            normalizer=ResultNormalizer(),
        )
        compiled_graph = build_agent_graph(
            matcher=matcher,
            match_threshold=settings.agent_tool_match_threshold,
            text_to_sql_node=text_to_sql_node,
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
