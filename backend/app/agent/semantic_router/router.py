import re

from app.agent.semantic_router.models import SemanticRouterResult


RECORD_NO_PATTERN = re.compile(r"(TRACE-[A-Z0-9-]+|HT[0-9A-Z-]+)", re.I)
STATUS_KEYWORDS = [
    "状态",
    "到哪一步",
    "哪一步",
    "做到哪",
    "做完",
    "完成",
    "结束",
    "当前什么情况",
    "什么情况",
]
AMBIGUOUS_HEAT_KEYWORDS = ["怎么样", "情况怎么样"]


class SemanticRouter:
    def route(self, user_message: str) -> SemanticRouterResult:
        message = user_message.strip()
        record_no = _extract_record_no(message)
        entities = {"record_no": record_no} if record_no else {}

        if _is_heat_status_query(message):
            if _is_generic_heat_status_query(message) and record_no is None:
                return SemanticRouterResult(
                    domain="heat_treatment",
                    intent="query_status",
                    entities=entities,
                    confidence=0.78,
                    need_clarification=True,
                    clarification_reason="缺少记录编号。",
                )
            return SemanticRouterResult(
                domain="heat_treatment",
                intent="query_status",
                entities=entities,
                confidence=0.95 if record_no else 0.82,
                need_clarification=False,
            )

        if _is_ambiguous_heat_query(message):
            return SemanticRouterResult(
                domain="heat_treatment",
                intent="unknown",
                entities=entities,
                confidence=0.42,
                need_clarification=True,
                clarification_reason="用户表达了热处理对象，但没有明确要查询状态、设备、批次或统计。",
            )

        return SemanticRouterResult(
            domain="unknown",
            intent="unknown",
            entities=entities,
            confidence=0.2,
            need_clarification=True,
            clarification_reason="未能稳定识别业务领域或用户意图。",
        )


def _extract_record_no(message: str) -> str | None:
    matched = RECORD_NO_PATTERN.search(message)
    if not matched:
        return None
    return matched.group(1).upper()


def _is_heat_status_query(message: str) -> bool:
    if any(keyword in message for keyword in STATUS_KEYWORDS):
        return "热处理" in message or _extract_record_no(message) is not None or len(message) <= 12
    return False


def _is_ambiguous_heat_query(message: str) -> bool:
    return "热处理" in message and any(keyword in message for keyword in AMBIGUOUS_HEAT_KEYWORDS)


def _is_generic_heat_status_query(message: str) -> bool:
    return message.startswith("查询") and "热处理" in message and "状态" in message
