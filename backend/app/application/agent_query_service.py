import logging
import time
import uuid

from app.agent.models import AgentResult


logger = logging.getLogger(__name__)


class AgentQueryService:
    def __init__(
        self,
        compiled_graph,
        agent_version: str,
        prompt_version: str,
        tool_version: str,
    ):
        self._compiled_graph = compiled_graph
        self._agent_version = agent_version
        self._prompt_version = prompt_version
        self._tool_version = tool_version

    def query(self, message: str) -> AgentResult:
        request_id = uuid.uuid4().hex
        start = time.perf_counter()
        state = {
            "user_query": message,
            "conversation_key": None,
            "agent_version": self._agent_version,
            "prompt_version": self._prompt_version,
            "tool_version": self._tool_version,
        }
        result_state = self._compiled_graph.invoke(state)
        final_result = result_state["final_result"]
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "Agent query completed request_id=%s route=%s capability_name=%s confidence=%s missing_fields=%s duration_ms=%s",
            request_id,
            final_result.get("route"),
            final_result.get("capability_name"),
            final_result.get("confidence"),
            final_result.get("missing_fields"),
            duration_ms,
        )
        return AgentResult.model_validate(final_result)
