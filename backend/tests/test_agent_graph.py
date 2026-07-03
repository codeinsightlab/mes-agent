from app.agent.graph import build_agent_graph
from app.agent.models import HeatToolArguments, ToolMatchDecision
from app.agent.text_to_sql.models import (
    NormalizedTextToSqlResult,
    TextToSqlGeneration,
)


def fake_matcher_for(message: str) -> ToolMatchDecision:
    if "参数" in message:
        return ToolMatchDecision(
            matched=True,
            capability_name="heat_param_submitted",
            confidence=0.96,
            extracted_arguments=HeatToolArguments(record_no="TRACE-HTR-K2-T-FG-001" if "TRACE" in message else None),
            reason="参数提交属于 blocked capability",
            candidate_capabilities=["heat_param_submitted"],
        )
    if "统计" in message or "对比" in message:
        return ToolMatchDecision(
            matched=False,
            capability_name=None,
            confidence=0.2,
            reason="未匹配当前 Tool Catalog",
            candidate_capabilities=[],
        )
    if "做完" in message and "TRACE" not in message:
        return ToolMatchDecision(
            matched=True,
            capability_name="heat_current_stage",
            confidence=0.91,
            extracted_arguments=HeatToolArguments(),
            reason="询问热处理状态但缺少记录标识",
            candidate_capabilities=["heat_current_stage"],
        )
    if "炉子" in message and "哪个" in message:
        return ToolMatchDecision(
            matched=True,
            capability_name="heat_equipment_assignment",
            confidence=0.93,
            extracted_arguments=HeatToolArguments(record_no="TRACE-HTR-K2-T-FG-001"),
            reason="询问设备分配",
            candidate_capabilities=["heat_equipment_assignment"],
        )
    return ToolMatchDecision(
        matched=True,
        capability_name="heat_current_stage",
        confidence=0.94,
        extracted_arguments=HeatToolArguments(record_no="TRACE-HTR-K2-T-FG-001"),
        reason="询问热处理当前阶段",
        candidate_capabilities=["heat_current_stage"],
    )


def invoke(message: str):
    graph = build_agent_graph(
        fake_matcher_for,
        match_threshold=0.75,
        text_to_sql_node=FakeTextToSqlNode(),
    )
    result = graph.invoke(
        {
            "user_query": message,
            "conversation_key": None,
            "agent_version": "0.1.0",
            "prompt_version": "chat-v1",
            "tool_version": "heat-treatment-tools-v1",
        }
    )
    return result["final_result"]


def invoke_with_text_to_sql(message: str):
    graph = build_agent_graph(
        fake_matcher_for,
        match_threshold=0.75,
        text_to_sql_node=FakeTextToSqlNode(),
    )
    result = graph.invoke(
        {
            "user_query": message,
            "conversation_key": None,
            "agent_version": "0.1.0",
            "prompt_version": "chat-v1",
            "tool_version": "heat-treatment-tools-v1",
        }
    )
    return result["final_result"]


class FakeTextToSqlNode:
    def __call__(self, state):
        generation = TextToSqlGeneration(
            sql=(
                "SELECT equipment_name, COUNT(*) AS batch_count "
                "FROM mes_heat_treatment_record "
                "WHERE status IN ('FINISHED','TRANSFERRED','ENDED') "
                "GROUP BY equipment_name LIMIT 100"
            ),
            used_tables=["mes_heat_treatment_record"],
            query_intent="统计每台热处理设备完成批次",
            assumptions=["测试 fake 节点不访问真实数据库"],
        )
        result = NormalizedTextToSqlResult(
            status="success",
            generated_sql=generation.sql,
            validated_sql=generation.sql,
            used_tables=generation.used_tables,
            columns=["equipment_name", "batch_count"],
            rows=[{"equipment_name": "HT-01", "batch_count": 3}],
            row_count=1,
            duration_ms=2,
            schema_version="heat-treatment-schema-v1",
            query_intent=generation.query_intent,
            assumptions=generation.assumptions,
        )
        return {
            **state,
            "text_to_sql_status": "success",
            "tool_result": result.model_dump(),
        }


def test_graph_routes_complete_match_to_tool_executor():
    result = invoke("TRACE-HTR-K2-T-FG-001到哪了")

    assert result["route"] == "tool"
    assert result["capability_name"] == "heat_current_stage"
    assert result["tool_result"]["status"] == "FINISHED"


def test_graph_routes_missing_parameters_to_clarification():
    result = invoke("这个热处理做完了吗")

    assert result["route"] == "clarification"
    assert result["capability_name"] == "heat_current_stage"
    assert result["missing_fields"]


def test_graph_routes_blocked_capability_without_tool_execution():
    result = invoke("TRACE-HTR-K2-T-FG-001参数提交了吗")

    assert result["route"] == "blocked"
    assert result["capability_name"] == "heat_param_submitted"
    assert result["tool_result"]["status"] == "blocked"


def test_graph_routes_unmatched_to_text_to_sql_node():
    result = invoke("统计本月每台热处理设备处理了多少批次")

    assert result["route"] == "text_to_sql"
    assert result["matched"] is False
    assert result["tool_result"]["status"] == "success"


def test_graph_routes_unmatched_to_real_text_to_sql_node_when_injected():
    result = invoke_with_text_to_sql("统计本月每台热处理设备处理了多少批次")

    assert result["route"] == "text_to_sql"
    assert result["matched"] is False
    assert result["tool_result"]["status"] == "success"
    assert result["tool_result"]["validated_sql"].startswith("SELECT equipment_name")
    assert result["tool_result"]["rows"] == [{"equipment_name": "HT-01", "batch_count": 3}]


def test_tool_path_does_not_execute_text_to_sql_node():
    result = invoke_with_text_to_sql("TRACE-HTR-K2-T-FG-001到哪了")

    assert result["route"] == "tool"
    assert result["capability_name"] == "heat_current_stage"
    assert result["tool_result"]["status"] == "FINISHED"
