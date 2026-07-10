import re

from pydantic import BaseModel


RECORD_NO_PATTERN = re.compile(r"(TRACE-[A-Z0-9-]+|HT[0-9A-Z-]+)", re.I)


class LegacyFallbackDecision(BaseModel):
    route: str
    capability_name: str | None = None
    legacy: bool = True


class LegacyFallbackRouter:
    def route(self, query: str) -> LegacyFallbackDecision:
        if self.is_mixed_diagnostic_query(query):
            return LegacyFallbackDecision(route="mixed")
        if self.is_sql_query(query):
            return LegacyFallbackDecision(route="sql")
        capability_name = self.tool_capability_name(query)
        if capability_name is not None:
            return LegacyFallbackDecision(route="tool", capability_name=capability_name)
        return LegacyFallbackDecision(route="unknown")

    def is_tool_query(self, query: str) -> bool:
        return self.tool_capability_name(query) is not None

    def tool_capability_name(self, query: str) -> str | None:
        if any(keyword in query for keyword in ["到哪", "哪一步", "状态", "处理完", "结束", "阶段"]):
            return "heat_current_stage"
        if any(keyword in query for keyword in ["分配", "哪个炉子", "哪台", "绑定设备", "使用什么设备", "设备编码", "设备名称"]):
            return "heat_equipment_assignment"
        if any(keyword in query for keyword in ["包含", "批次", "绑定", "产品"]):
            return "heat_batch_products"
        return None

    def is_sql_query(self, query: str) -> bool:
        return any(keyword in query for keyword in ["统计", "每台", "产量", "平均", "最近", "多少", "排行"])

    def is_mixed_diagnostic_query(self, query: str) -> bool:
        return "为什么" in query and any(keyword in query for keyword in ["不能入库", "无法入库", "入不了库"])

    def extract_record_no(self, query: str) -> str | None:
        matched = RECORD_NO_PATTERN.search(query)
        if not matched:
            return None
        return matched.group(1).upper()
