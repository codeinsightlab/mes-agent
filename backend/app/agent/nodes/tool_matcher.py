from collections.abc import Callable
import json
import re

from langchain_core.language_models.chat_models import BaseChatModel

from app.agent.exceptions import ToolMatchError
from app.agent.catalog.heat_treatment import CAPABILITY_BY_NAME
from app.agent.models import ToolMatchDecision
from app.agent.prompts.tool_matcher import build_tool_matcher_prompt
from app.agent.state import AgentState


MatcherFn = Callable[[str], ToolMatchDecision]


class LangChainToolMatcher:
    def __init__(self, chat_model: BaseChatModel):
        self._chat_model = chat_model
        self._structured_model = chat_model.with_structured_output(ToolMatchDecision)
        self._system_prompt = build_tool_matcher_prompt()

    def __call__(self, user_query: str) -> ToolMatchDecision:
        messages = [
            ("system", self._system_prompt),
            ("user", user_query),
        ]
        try:
            return self._structured_model.invoke(messages)
        except Exception:
            response = self._chat_model.invoke(
                [
                    (
                        "system",
                        self._system_prompt
                        + "\n\n必须只返回 JSON 对象，字段为 matched, capability_name, confidence, extracted_arguments, missing_fields, reason, candidate_capabilities。",
                    ),
                    ("user", user_query),
                ]
            )
            data = _extract_json_object(str(response.content))
            return ToolMatchDecision.model_validate(data)


def _extract_json_object(content: str) -> dict:
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ToolMatchError("Matcher response did not contain a JSON object.")
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ToolMatchError("Matcher response JSON could not be parsed.") from exc


def make_tool_matcher_node(
    matcher: MatcherFn,
    match_threshold: float,
) -> Callable[[AgentState], AgentState]:
    def node(state: AgentState) -> AgentState:
        decision = matcher(state["user_query"])
        if decision.capability_name is not None and decision.capability_name not in CAPABILITY_BY_NAME:
            return {
                **state,
                "route": "error",
                "matched": decision.matched,
                "capability_name": decision.capability_name,
                "confidence": decision.confidence,
                "extracted_arguments": decision.extracted_arguments.model_dump(exclude_none=True),
                "missing_fields": decision.missing_fields,
                "matcher_reason": "Matcher returned an unregistered capability.",
                "candidate_capabilities": decision.candidate_capabilities,
                "error_code": "unknown_capability",
                "error_message": "Matcher returned an unregistered capability.",
            }

        if not decision.matched:
            route = "text_to_sql"
            status = None
            missing_fields = decision.missing_fields
        else:
            capability = CAPABILITY_BY_NAME[decision.capability_name]
            status = capability.status
            missing_fields = _missing_required_fields(
                capability.required_argument_groups,
                decision.extracted_arguments.model_dump(exclude_none=True),
            )
            if status == "blocked":
                route = "blocked"
            elif status != "enabled":
                route = "error"
            elif decision.confidence < match_threshold:
                route = "clarification"
                if not missing_fields:
                    missing_fields = ["需要确认要查询的热处理业务事实"]
            elif missing_fields:
                route = "clarification"
            else:
                route = "tool"

        return {
            **state,
            "route": route,
            "matched": decision.matched,
            "capability_name": decision.capability_name,
            "capability_status": status,
            "confidence": decision.confidence,
            "extracted_arguments": decision.extracted_arguments.model_dump(exclude_none=True),
            "missing_fields": missing_fields,
            "matcher_reason": decision.reason,
            "candidate_capabilities": decision.candidate_capabilities,
        }

    return node


def _missing_required_fields(
    required_argument_groups: list[list[str]],
    arguments: dict,
) -> list[str]:
    for group in required_argument_groups:
        if all(arguments.get(field) for field in group):
            return []
    if len(required_argument_groups) > 1 and all(len(group) == 1 for group in required_argument_groups):
        return ["record identifier: record_id or record_no or object_id"]
    return [field for field in required_argument_groups[0] if not arguments.get(field)]
