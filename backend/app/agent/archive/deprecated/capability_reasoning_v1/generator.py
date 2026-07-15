import json
import re
from typing import cast

from langchain_core.language_models.chat_models import BaseChatModel

from app.agent.capability.catalog.registry import CapabilityRuntimeRegistry
from .models import (
    BusinessFacts,
    CapabilityReasoningResult,
)
from app.core.type_defs import JsonObject


PROMPT_VERSION = "capability-reasoning-v1"


class CapabilityReasoningGenerator:
    def __init__(self, chat_model: BaseChatModel):
        self._chat_model = chat_model.with_structured_output(CapabilityReasoningResult)
        self._fallback_model = chat_model

    def generate(
        self,
        user_input: str,
        registry: CapabilityRuntimeRegistry,
        context_level: str,
        business_facts: BusinessFacts | None = None,
    ) -> CapabilityReasoningResult:
        prompt = build_prompt(user_input, registry, context_level, business_facts)
        try:
            result = self._chat_model.invoke(prompt)
            if isinstance(result, CapabilityReasoningResult):
                return result
            return CapabilityReasoningResult.model_validate(result)
        except Exception:
            response = self._fallback_model.invoke(
                prompt
                + "\n\n必须只返回 JSON 对象，不要使用 Markdown 代码块，不得输出 sql/repository/database/api_call/tool_call。"
            )
            return CapabilityReasoningResult.model_validate(
                _extract_json_object(str(response.content))
            )


def build_prompt(
    user_input: str,
    registry: CapabilityRuntimeRegistry,
    context_level: str,
    business_facts: BusinessFacts | None = None,
) -> str:
    return f"""
你是 MES 业务能力匹配模块。

你的任务：
1. 根据用户问题和 Capability Catalog 选择最适合的 MES Capability。
2. 只能选择 Catalog 中提供的 Capability，不能创造不存在的能力。
3. 如果多个能力都可能，输出候选列表。
4. 如果无法判断，不强行选择。
5. 提取调用所需业务实体。

禁止：
1. 输出 SQL。
2. 输出 Repository、数据库、API 调用、Tool 调用。
3. 直接执行业务逻辑。

context_level:
{context_level}

Capability Catalog:
{_catalog_json(registry)}

Business Facts:
{business_facts.model_dump_json(indent=2) if business_facts else "[]"}

用户问题：
{user_input}

输出严格 JSON，字段必须符合 CapabilityReasoningResult。
""".strip()


def _catalog_json(registry: CapabilityRuntimeRegistry) -> str:
    payload = [
        {
            "name": capability.name,
            "domain": capability.domain,
            "description": capability.description,
            "business_context": capability.business_context,
            "examples": capability.examples or capability.example_queries,
            "input_entities": capability.input_entities or capability.required_entities,
            "api_contract": capability.api_contract,
            "execution_type": capability.execution_type,
            "status": capability.status,
        }
        for capability in registry.all()
        if capability.domain == "heat_treatment"
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _extract_json_object(content: str) -> JsonObject:
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Capability reasoning response did not contain a JSON object.")
    decoded = json.loads(cleaned[start : end + 1])
    if not isinstance(decoded, dict):
        raise ValueError("Capability reasoning response JSON must be an object.")
    return cast(JsonObject, decoded)
