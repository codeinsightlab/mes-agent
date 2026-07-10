import re

from app.agent.capability.catalog.registry import CapabilityRuntimeRegistry
from app.agent.reasoning.capability_reasoning.models import (
    BusinessFacts,
    CapabilityCandidate,
    CapabilityReasoningResult,
)
from app.core.type_defs import JsonObject


RECORD_NO_PATTERN = re.compile(r"(TRACE-[A-Z0-9-]+|HT[0-9A-Z-]+)", re.I)


class CapabilityReasoner:
    def __init__(
        self,
        registry: CapabilityRuntimeRegistry,
        confidence_threshold: float = 0.75,
    ):
        self._registry = registry
        self._confidence_threshold = confidence_threshold

    def reason(
        self,
        user_input: str,
        business_facts: BusinessFacts | None = None,
    ) -> CapabilityReasoningResult:
        catalog_only = self.reason_catalog_only(user_input)
        if (
            catalog_only.selected_capability
            and catalog_only.confidence >= self._confidence_threshold
        ):
            return catalog_only
        return self.reason_with_business_facts(
            user_input,
            business_facts=business_facts or default_heat_treatment_business_facts(),
        )

    def reason_catalog_only(self, user_input: str) -> CapabilityReasoningResult:
        return self._reason_once(user_input, context_level="catalog_only")

    def reason_with_business_facts(
        self,
        user_input: str,
        business_facts: BusinessFacts | None = None,
    ) -> CapabilityReasoningResult:
        return self._reason_once(
            user_input,
            context_level="catalog_with_business_facts",
            business_facts=business_facts or default_heat_treatment_business_facts(),
        )

    def _reason_once(
        self,
        user_input: str,
        *,
        context_level: str,
        business_facts: BusinessFacts | None = None,
    ) -> CapabilityReasoningResult:
        message = user_input.strip()
        entities = _extract_entities(message)
        candidates = _rank_candidates(message, context_level, self._registry, business_facts)
        selected = candidates[0].name if candidates and candidates[0].confidence >= self._confidence_threshold else None
        confidence = candidates[0].confidence if candidates else 0.0
        return CapabilityReasoningResult(
            goal=_infer_goal(message, selected),
            context_level=context_level,  # type: ignore[arg-type]
            candidate_capabilities=candidates[:3],
            selected_capability=selected,
            entities=entities,
            confidence=confidence,
            need_clarification=selected is None,
            clarification_reason=None if selected else "无法从 Catalog 稳定选择唯一 MES Capability。",
        )


def default_heat_treatment_business_facts() -> BusinessFacts:
    return BusinessFacts(
        facts=[
            "热处理追溯编号、热处理记录号、TRACE 编号、HT 编号都可作为 record_no。",
            "用户询问状态、做到哪一步、进度、是否完成时，通常是 heat_current_stage。",
            "用户询问在哪个设备、哪个炉子、哪台炉时，通常是 heat_device_trace。",
            "用户询问完成多少批、完成数量、统计本月完成时，通常是 heat_completion_count_monthly。",
            "用户只说这个热处理怎么样时，不应强行选择能力，需要澄清。",
        ]
    )


def _rank_candidates(
    message: str,
    context_level: str,
    registry: CapabilityRuntimeRegistry,
    business_facts: BusinessFacts | None,
) -> list[CapabilityCandidate]:
    scored: list[CapabilityCandidate] = []
    for capability in registry.all():
        if capability.domain != "heat_treatment":
            continue
        score, reason = _score_capability(message, capability.name, context_level, business_facts)
        if score > 0:
            scored.append(CapabilityCandidate(name=capability.name, confidence=score, reason=reason))
    return sorted(scored, key=lambda item: item.confidence, reverse=True)


def _score_capability(
    message: str,
    capability_name: str,
    context_level: str,
    business_facts: BusinessFacts | None,
) -> tuple[float, str]:
    has_record = bool(_extract_entities(message).get("record_no"))
    has_business_facts = context_level == "catalog_with_business_facts" and bool(
        business_facts and business_facts.facts
    )
    if capability_name == "heat_completion_count_monthly":
        if _contains_any(message, ["完成多少批", "完成数量", "统计"]) and "热处理" in message:
            return 0.92, "用户询问热处理完成数量统计。"
        if has_business_facts and _contains_any(message, ["多少批", "本月完成"]):
            return 0.84, "Business Facts 将完成批次数识别为热处理统计能力。"
    if capability_name == "heat_device_trace":
        if _contains_any(message, ["设备", "生产设备"]):
            return (0.9 if has_record else 0.82), "用户询问热处理记录对应设备。"
        if has_business_facts and _contains_any(message, ["炉子", "炉", "哪台炉", "在哪完成"]):
            return (0.88 if has_record else 0.8), "Business Facts 将炉子归一为热处理设备。"
        if _contains_any(message, ["炉子", "哪台炉"]):
            return 0.58, "Catalog-only 阶段仅弱匹配炉子表达。"
    if capability_name == "heat_current_stage":
        if _contains_any(message, ["状态", "做到哪", "哪一步", "做完", "完成了吗"]):
            if "怎么样" in message and not has_record:
                return 0.42, "表达过于模糊，不能强行选择状态能力。"
            return (0.93 if has_record else 0.78), "用户询问热处理当前状态或阶段。"
        if has_business_facts and _contains_any(message, ["进度", "到哪了", "当前情况"]):
            return (0.87 if has_record else 0.76), "Business Facts 将进度类表达归一到状态查询。"
        if has_record and "热处理" in message:
            return 0.62, "存在热处理记录号，但目标不够明确。"
    return 0, ""


def _infer_goal(message: str, selected_capability: str | None) -> str:
    if selected_capability == "heat_device_trace":
        return "查询热处理执行设备"
    if selected_capability == "heat_completion_count_monthly":
        return "统计热处理完成批次数"
    if selected_capability == "heat_current_stage":
        return "查询热处理当前状态"
    return f"理解用户业务目标：{message}"


def _extract_entities(message: str) -> JsonObject:
    matched = RECORD_NO_PATTERN.search(message)
    if matched:
        return {"record_no": matched.group(1).upper()}
    if _contains_any(message, ["本月", "这个月"]):
        return {"time_range": "current_month"}
    return {}


def _contains_any(message: str, keywords: list[str]) -> bool:
    return any(keyword in message for keyword in keywords)
