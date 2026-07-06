from fastapi import APIRouter, Depends, HTTPException

from app.agent.nodes.text_to_sql import TextToSqlNode
from app.agent.orchestrator.agent_orchestrator import (
    AgentOrchestrator,
    AgentRunInput,
    AgentRunResult,
    PlanExecutionAdapter,
)
from app.agent.planner.planner import DebuggablePlanner
from app.agent.text_to_sql.executor import ReadonlySqlExecutor
from app.agent.text_to_sql.generator import TextToSqlGenerator
from app.agent.text_to_sql.normalizer import ResultNormalizer
from app.agent.text_to_sql.schema_provider import HeatTreatmentSchemaProvider
from app.agent.text_to_sql.validator import SqlValidator
from app.analytics.event.collector import AgentEventCollector
from app.core.config import get_settings
from app.domain.llm.exceptions import LlmConfigurationError
from app.domain.persistence.exceptions import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
)
from app.infrastructure.agent.langchain_factory import create_agent_chat_model
from app.infrastructure.database.engine import check_database_connection, create_database_engine


router = APIRouter(prefix="/api/agent", tags=["agent"])
_planner: DebuggablePlanner | None = None
_orchestrator: AgentOrchestrator | None = None
_analytics_engine = None


def build_text_to_sql_node(settings, chat_model) -> TextToSqlNode:
    return TextToSqlNode(
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


def close_agent_query_service():
    global _orchestrator, _analytics_engine
    _orchestrator = None
    if _analytics_engine is not None:
        _analytics_engine.dispose()
        _analytics_engine = None


def get_planner() -> DebuggablePlanner:
    global _planner
    if _planner is None:
        _planner = DebuggablePlanner()
    return _planner


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator, _analytics_engine
    if _orchestrator is not None:
        return _orchestrator
    try:
        settings = get_settings()
        _analytics_engine = create_database_engine(settings)
        check_database_connection(_analytics_engine)
        chat_model = create_agent_chat_model(settings)
        text_to_sql_node = build_text_to_sql_node(settings, chat_model)
        _orchestrator = AgentOrchestrator(
            planner=get_planner(),
            execution_layer=PlanExecutionAdapter(text_to_sql_node=text_to_sql_node),
            event_collector=AgentEventCollector(_analytics_engine),
        )
        return _orchestrator
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
    except DatabaseConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "database_connection_error", "message": "Database connection failed."},
        ) from exc


@router.post("/run", response_model=AgentRunResult)
def agent_run(
    request: AgentRunInput,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    return orchestrator.run(request)
