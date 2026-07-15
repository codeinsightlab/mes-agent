from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException

from app.agent.agents.heat_treatment import HeatTreatmentAgent
from app.agent.capability.catalog.loader import CapabilityLoader
from app.agent.core import AgentRequest, AgentResponse, AgentRouter, MesAgent
from app.agent.execution import ExecutionEngine
from app.agent.execution.tools.text_to_sql.node import TextToSqlNode
from app.agent.reasoning import CapabilityReasoner
from app.agent.runtime import CapabilityRuntime, LlmRuntime, TraceRuntime
from app.agent.context.state import AgentState
from app.agent.execution.tools.text_to_sql.executor import ReadonlySqlExecutor
from app.agent.execution.tools.text_to_sql.generator import TextToSqlGenerator
from app.agent.execution.tools.text_to_sql.normalizer import ResultNormalizer
from app.agent.execution.tools.text_to_sql.schema_provider import HeatTreatmentSchemaProvider
from app.agent.execution.tools.text_to_sql.validator import SqlValidator
from app.agent.execution.tools.registry import ToolRegistry
from app.analytics.event.collector import AgentEventCollector
from app.core.config import get_settings
from app.domain.llm.exceptions import LlmConfigurationError
from app.domain.persistence.exceptions import DatabaseConfigurationError, DatabaseConnectionError
from app.infrastructure.agent.audit_runtime import AnalyticsAuditRuntime
from app.infrastructure.agent.langchain_factory import create_agent_chat_model
from app.infrastructure.database.engine import check_database_connection, create_database_engine


router = APIRouter(prefix="/api/agent", tags=["agent"])
_mes_agent: MesAgent | None = None
_analytics_engine = None


def build_text_to_sql_node(settings, chat_model) -> TextToSqlNode:
    return TextToSqlNode(
        schema_provider=HeatTreatmentSchemaProvider(),
        generator=TextToSqlGenerator(chat_model=chat_model, max_limit=settings.agent_text_to_sql_max_limit),
        validator=SqlValidator(max_limit=settings.agent_text_to_sql_max_limit),
        executor=ReadonlySqlExecutor(
            settings=settings,
            max_rows=settings.agent_text_to_sql_max_limit,
            timeout_seconds=settings.agent_text_to_sql_timeout_seconds,
        ),
        normalizer=ResultNormalizer(),
    )


def close_agent_query_service():
    global _mes_agent, _analytics_engine
    _mes_agent = None
    if _analytics_engine is not None:
        _analytics_engine.dispose()
        _analytics_engine = None


def _sql_executor(node: TextToSqlNode):
    def execute(arguments: dict[str, Any]) -> dict[str, Any]:
        initial_state: AgentState = {
            "user_query": str(arguments.get("question", "")),
            "conversation_key": None,
            "agent_version": "v2",
            "prompt_version": "capability-reasoning-v2",
            "tool_version": "v2",
        }
        state = node(initial_state)
        return cast(dict[str, Any], state.get("tool_result") or {})

    return execute


def get_mes_agent() -> MesAgent:
    global _mes_agent, _analytics_engine
    if _mes_agent is not None:
        return _mes_agent
    try:
        settings = get_settings()
        _analytics_engine = create_database_engine(settings)
        check_database_connection(_analytics_engine)
        chat_model = create_agent_chat_model(settings)
        registry = CapabilityLoader().load()
        tool_registry = ToolRegistry()
        text_to_sql = build_text_to_sql_node(settings, chat_model)
        capability_runtime = CapabilityRuntime(
            registry,
            ExecutionEngine({
                "heat_current_stage": lambda arguments: tool_registry.execute("heat_current_stage", arguments),
                "text_to_sql": _sql_executor(text_to_sql),
            }),
        )
        trace_runtime = TraceRuntime()
        domain_agent = HeatTreatmentAgent(
            CapabilityReasoner(registry, LlmRuntime(chat_model)),
            capability_runtime,
            trace_runtime,
        )
        _mes_agent = MesAgent(
            AgentRouter(domain_agent),
            trace_runtime,
            AnalyticsAuditRuntime(AgentEventCollector(_analytics_engine)),
        )
        return _mes_agent
    except LlmConfigurationError as exc:
        raise HTTPException(status_code=500, detail={"error": "llm_configuration_error", "message": str(exc)}) from exc
    except DatabaseConfigurationError as exc:
        raise HTTPException(status_code=500, detail={"error": "database_configuration_error", "message": str(exc)}) from exc
    except DatabaseConnectionError as exc:
        raise HTTPException(status_code=503, detail={"error": "database_connection_error", "message": "Database connection failed."}) from exc


@router.post("/run", response_model=AgentResponse)
def agent_run(request: AgentRequest, mes_agent: MesAgent = Depends(get_mes_agent)):
    return mes_agent.run(request)
