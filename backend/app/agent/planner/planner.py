import re
from typing import cast

from app.agent.catalog.heat_treatment import CAPABILITIES
from app.agent.execution_observation import ExecutionObservation
from app.agent.planner.models import (
    DebugTrace,
    ExecutionHistoryItem,
    ExecutionPlanPolicy,
    FailureAnalysis,
    PlannerPlan,
    PlannerRequest,
    PlanStep,
)
from app.core.type_defs import JsonObject


RECORD_NO_PATTERN = re.compile(r"(TRACE-[A-Z0-9-]+|HT[0-9A-Z-]+)", re.I)


class DebuggablePlanner:
    def plan(self, request: PlannerRequest) -> PlannerPlan:
        query = request.user_query
        catalog = request.tool_catalog or _default_tool_catalog()
        catalog_names = {
            name
            for item in catalog
            if isinstance(name := item.get("name"), str)
        }
        history = request.execution_history

        if request.execution_observation is not None:
            return self._replan_from_observation(
                query=query,
                catalog_names=catalog_names,
                history=history,
                observation=request.execution_observation,
            )

        if _is_mixed_diagnostic_query(query):
            return self._mixed_diagnostic_plan(query, catalog_names, history)
        if _is_tool_query(query):
            return self._tool_plan(query, catalog_names, history)
        if _is_sql_query(query):
            return self._sql_plan(query, history)
        return self._unknown_plan(query, history)

    def _tool_plan(
        self,
        query: str,
        catalog_names: set[str],
        history: list[ExecutionHistoryItem],
    ) -> PlannerPlan:
        record_no = _extract_record_no(query)
        step = PlanStep(
            step_id=1,
            type="tool",
            name="heat_current_stage",
            query_goal="查询热处理记录当前阶段、状态或是否已完成。",
            args={"record_no": record_no} if record_no else {},
            reason="用户询问'到哪了/状态/是否完成'，该语义由 heat_current_stage Tool 负责。",
            dependency=[],
            expected_output="包含 found、record_no、status、status_name 的 Tool 结构化结果。",
        )
        _apply_history_reuse(step, history)
        confidence = 0.9 if record_no else 0.72
        risk = "主要风险是 record_no 未抽取或抽取错误。" if record_no else "缺少记录编号，执行层可能进入澄清。"
        if step.name not in catalog_names:
            risk += " 当前 Tool Catalog 未注册 heat_current_stage。"
            confidence = min(confidence, 0.45)

        return PlannerPlan(
            intent="tool",
            goal="确认指定热处理记录的当前状态。",
            steps=[step],
            execution_plan=ExecutionPlanPolicy(
                stop_condition="when heat_current_stage returns a found status or asks for a missing record identifier"
            ),
            confidence=confidence,
            debug_trace=DebugTrace(
                classification_reason="问题包含热处理阶段/状态类表达，适合 Tool 查询。",
                tool_selection_reason="heat_current_stage 是当前 Catalog 中负责热处理当前阶段和完成状态的 Tool。",
                sql_intent_reason="不需要聚合、统计或自由条件查询，因此不进入 SQL。",
                risk_assessment=risk,
            ),
            failure_analysis=_analyze_history(history),
        )

    def _sql_plan(
        self,
        query: str,
        history: list[ExecutionHistoryItem],
    ) -> PlannerPlan:
        step = PlanStep(
            step_id=1,
            type="sql",
            name=None,
            query_goal="基于限定 Schema 生成并执行只读统计查询。",
            args={"question": query},
            reason="用户问题是统计/聚合/按设备分组类问题，需要 Text-to-SQL 生成候选 SQL 后由 Validator 和只读执行器处理。",
            dependency=[],
            expected_output="包含 generated_sql、validated_sql、columns、rows、row_count、duration_ms 的结构化 SQL 结果。",
        )
        _apply_history_reuse(step, history)
        return PlannerPlan(
            intent="sql",
            goal="得到用户请求的统计查询结果。",
            steps=[step],
            execution_plan=ExecutionPlanPolicy(
                stop_condition="when SQL validation and readonly execution produce enough rows or a stable SQL error"
            ),
            confidence=0.84,
            debug_trace=DebugTrace(
                classification_reason="问题包含统计、每台、产量、平均、最近等分析型表达。",
                tool_selection_reason="当前 Tool Catalog 只覆盖单记录事实，不覆盖聚合统计。",
                sql_intent_reason="需要按 Schema 生成只读 SELECT 并返回表格数据。",
                risk_assessment="主要风险是 Schema 字段不存在、SQL 生成错误、Validator 拦截或 MES 只读库执行失败。",
            ),
            failure_analysis=_analyze_history(history),
        )

    def _mixed_diagnostic_plan(
        self,
        query: str,
        catalog_names: set[str],
        history: list[ExecutionHistoryItem],
    ) -> PlannerPlan:
        steps = [
            PlanStep(
                step_id=1,
                type="tool",
                name="production_status",
                query_goal="确认这批产品是否已经完成生产或处于可入库前置状态。",
                args={"question": query},
                reason="不能入库通常先要排查生产状态是否满足入库前置条件。",
                dependency=[],
                expected_output="生产状态、完成状态、阻断原因。",
            ),
            PlanStep(
                step_id=2,
                type="tool",
                name="quality_status",
                query_goal="确认质检是否通过、是否存在不良或待检状态。",
                args={"question": query},
                reason="入库受质检结果影响，质检失败或未检会阻断入库。",
                dependency=[1],
                expected_output="质检状态、检验结论、不良原因。",
            ),
            PlanStep(
                step_id=3,
                type="sql",
                name=None,
                query_goal="查询库存或入库相关记录，确认是否已有库存、库位或入库约束。",
                args={"question": query},
                reason="库存和入库约束通常需要通过只读 SQL 汇总当前业务数据。",
                dependency=[1, 2],
                expected_output="库存/入库约束相关 columns、rows、row_count。",
            ),
        ]
        for step in steps:
            _apply_history_reuse(step, history)

        missing_tools = [
            step.name
            for step in steps
            if step.type == "tool" and isinstance(step.name, str) and step.name not in catalog_names
        ]
        risk = (
            "当前 Catalog 未注册以下诊断 Tool："
            + ", ".join(missing_tools)
            + "；Planner 可表达诊断计划，但执行前需要能力映射或补充执行层。"
            if missing_tools
            else "主要风险是跨域诊断 step 的参数绑定和执行层返回口径不一致。"
        )

        return PlannerPlan(
            intent="mixed",
            goal="定位这批产品不能入库的原因，并区分生产、质检、库存/入库约束来源。",
            steps=steps,
            execution_plan=ExecutionPlanPolicy(
                stop_condition="when production, quality, and inventory evidence identify a blocking reason"
            ),
            confidence=0.62 if missing_tools else 0.82,
            debug_trace=DebugTrace(
                classification_reason="问题是原因诊断，不是单点事实或单一统计，需要多个证据源。",
                tool_selection_reason="生产状态和质检状态应优先走确定性 Tool；未注册时必须在风险中暴露能力缺口。",
                sql_intent_reason="库存/入库约束通常需要结构化数据查询，因此规划一个 SQL step。",
                risk_assessment=risk,
            ),
            failure_analysis=_analyze_history(history),
        )

    def _unknown_plan(
        self,
        query: str,
        history: list[ExecutionHistoryItem],
    ) -> PlannerPlan:
        return PlannerPlan(
            intent="unknown",
            goal=f"暂无法稳定规划：{query}",
            steps=[],
            execution_plan=ExecutionPlanPolicy(
                stop_condition="when user provides a clearer business object, identifier, or analysis goal"
            ),
            confidence=0.2,
            debug_trace=DebugTrace(
                classification_reason="问题未命中当前 Planner V1 的 Tool、SQL 或混合诊断规则。",
                tool_selection_reason="没有足够证据选择已注册 Tool。",
                sql_intent_reason="没有足够证据进入 SQL。",
                risk_assessment="主要风险是意图不明确，需要用户补充业务对象或目标。",
            ),
            failure_analysis=_analyze_history(history),
        )

    def _replan_from_observation(
        self,
        query: str,
        catalog_names: set[str],
        history: list[ExecutionHistoryItem],
        observation: ExecutionObservation,
    ) -> PlannerPlan:
        missing_facts = observation.observation.missing_facts
        failure_analysis = _analyze_history(history) + _analyze_observation(observation)
        if _contains_fact(missing_facts, ["qc", "quality", "质检"]):
            step = PlanStep(
                step_id=1,
                type="tool",
                name="quality_status",
                query_goal="补齐上一轮执行缺失的质检事实。",
                args={"question": query, "focus": "QC"},
                reason="上一轮 observation 明确缺少 QC/质检事实，因此 replan 剪枝为只聚焦质检状态。",
                dependency=[],
                expected_output="质检状态、检验结论、不良原因或缺失原因。",
            )
            risk = (
                "quality_status 未注册，执行层会暴露 tool_miss；本轮按禁止扩 Tool 要求仅输出可排查计划。"
                if step.name not in catalog_names
                else "主要风险是质检参数不足或 Tool 返回口径不完整。"
            )
            return PlannerPlan(
                intent="tool",
                goal="补齐不能入库诊断中的质检证据。",
                steps=[step],
                execution_plan=ExecutionPlanPolicy(
                    stop_condition="when QC evidence is found or a stable tool_miss/missing_param is returned"
                ),
                confidence=0.68 if step.name not in catalog_names else 0.86,
                debug_trace=DebugTrace(
                    classification_reason="这是基于 execution_observation 的第二次规划，不重新扩展全部步骤。",
                    tool_selection_reason="missing_facts 指向 QC，因此只保留 quality_status 相关 step。",
                    sql_intent_reason="当前缺口是质检事实，不优先进入 SQL。",
                    risk_assessment=risk,
                ),
                failure_analysis=failure_analysis,
            )

        if _contains_fact(missing_facts, ["factory", "工厂"]):
            step = PlanStep(
                step_id=1,
                type="sql",
                name=None,
                query_goal="补齐上一轮 SQL 统计缺少的工厂过滤条件或工厂维度。",
                args={"question": query, "missing_facts": missing_facts, "focus": "factory_filter"},
                reason="上一轮 SQL observation 标记缺少工厂事实，因此第二轮计划只聚焦工厂过滤条件。",
                dependency=[],
                expected_output="带工厂过滤或工厂维度的 generated_sql、validated_sql、columns、rows。",
            )
            return PlannerPlan(
                intent="sql",
                goal="补齐工厂条件后完成设备产量统计。",
                steps=[step],
                execution_plan=ExecutionPlanPolicy(
                    stop_condition="when SQL returns rows with factory-scoped production statistics or a stable missing_param is returned"
                ),
                confidence=0.78,
                debug_trace=DebugTrace(
                    classification_reason="这是对 partial SQL observation 的第二次规划。",
                    tool_selection_reason="缺失事实不是当前 Tool Catalog 的单记录事实，因此不选择 Tool。",
                    sql_intent_reason="缺失工厂过滤属于 SQL 查询条件补齐。",
                    risk_assessment="如果用户仍未提供具体工厂，执行层应返回 missing_param 而不是扩大查询范围。",
                ),
                failure_analysis=failure_analysis,
            )

        if _contains_fact(missing_facts, ["plan.steps"]):
            plan = self._unknown_plan(query, history)
            return plan.model_copy(
                update={
                    "failure_analysis": failure_analysis,
                    "debug_trace": plan.debug_trace.model_copy(
                        update={
                            "classification_reason": (
                                "上一轮没有可执行 step，且原始问题未形成明确 Tool 或 SQL 意图。"
                            ),
                            "risk_assessment": (
                                "继续执行会扩大查询范围，因此保持 unknown 并要求用户补充业务对象或目标。"
                            ),
                        }
                    ),
                }
            )

        if _is_tool_query(query) and not _is_sql_query(query):
            plan = self._tool_plan(query, catalog_names, history)
            return plan.model_copy(
                update={
                    "failure_analysis": failure_analysis,
                    "debug_trace": plan.debug_trace.model_copy(
                        update={
                            "classification_reason": (
                                "上一轮 Tool 执行缺少必要参数，replan 保持 Tool 路径以暴露缺参问题。"
                            ),
                            "sql_intent_reason": (
                                "原始问题不是统计或分析型查询，不能用 SQL 兜底补齐 Tool 参数。"
                            ),
                            "risk_assessment": (
                                "缺少记录编号或业务标识，执行层应返回 missing_param，而不是扩大为数据库查询。"
                            ),
                        }
                    ),
                }
            )

        if missing_facts:
            if not _is_sql_query(query):
                plan = self._unknown_plan(query, history)
                return plan.model_copy(
                    update={
                        "failure_analysis": failure_analysis,
                        "debug_trace": plan.debug_trace.model_copy(
                            update={
                                "classification_reason": (
                                    "上一轮 observation 有缺失事实，但原始问题没有明确 SQL 统计意图。"
                                ),
                                "sql_intent_reason": "缺失事实不能自动扩大为 SQL 查询。",
                                "risk_assessment": (
                                    "保持可排查失败，避免 unknown 或攻击性输入触发默认 SQL。"
                                ),
                            }
                        ),
                    }
                )

            step = PlanStep(
                step_id=1,
                type="sql",
                name=None,
                query_goal="补齐上一轮执行报告的缺失事实。",
                args={"question": query, "missing_facts": missing_facts},
                reason="上一轮 execution_observation 返回 partial，Planner V1 进行一次有限补充规划。",
                dependency=[],
                expected_output="缺失事实相关的结构化查询结果或稳定失败原因。",
            )
            return PlannerPlan(
                intent="sql",
                goal="补齐缺失事实以完成闭环。",
                steps=[step],
                execution_plan=ExecutionPlanPolicy(
                    stop_condition="when missing facts are resolved or a stable failure type is returned"
                ),
                confidence=0.55,
                debug_trace=DebugTrace(
                    classification_reason="根据 execution_observation.missing_facts 触发 replan。",
                    tool_selection_reason="缺失事实未映射到当前已注册 Tool。",
                    sql_intent_reason="使用受控 SQL 查询补齐缺失事实。",
                    risk_assessment="缺失事实可能不在允许 Schema 中，可能产生 schema_gap。",
                ),
                failure_analysis=failure_analysis,
            )

        return self._unknown_plan(query, history)


def _default_tool_catalog() -> list[JsonObject]:
    return [cast(JsonObject, capability.model_dump(mode="json")) for capability in CAPABILITIES]


def _is_tool_query(query: str) -> bool:
    return any(keyword in query for keyword in ["到哪", "状态", "处理完", "结束", "阶段"])


def _is_sql_query(query: str) -> bool:
    return any(keyword in query for keyword in ["统计", "每台", "产量", "平均", "最近", "多少", "排行"])


def _is_mixed_diagnostic_query(query: str) -> bool:
    return "为什么" in query and any(keyword in query for keyword in ["不能入库", "无法入库", "入不了库"])


def _extract_record_no(query: str) -> str | None:
    matched = RECORD_NO_PATTERN.search(query)
    if not matched:
        return None
    return matched.group(1).upper()


def _apply_history_reuse(step: PlanStep, history: list[ExecutionHistoryItem]) -> None:
    for item in history:
        if item.status != "success":
            continue
        if step.type == item.route or (step.type == "sql" and item.route == "text_to_sql"):
            step.reuse_from_history = item.step
            step.skip_reason = "execution_history contains a successful compatible result."
            return


def _analyze_history(history: list[ExecutionHistoryItem]) -> list[FailureAnalysis]:
    analyses: list[FailureAnalysis] = []
    for item in history:
        if item.status != "failed":
            continue
        output_text = str(item.output).lower()
        if item.route == "tool":
            source = "tool"
            reason = "Tool execution failed or returned an unusable result."
        elif item.route in {"sql", "text_to_sql"} and "validator" in output_text:
            source = "sql"
            reason = "SQL validator rejected the generated SQL."
        elif item.route in {"sql", "text_to_sql"} and "schema" in output_text:
            source = "schema"
            reason = "SQL result indicates possible Schema understanding mismatch."
        elif item.route in {"sql", "text_to_sql"} and any(word in output_text for word in ["db", "database", "timeout"]):
            source = "execution"
            reason = "Readonly SQL execution failed at database or timeout boundary."
        elif item.route in {"sql", "text_to_sql"}:
            source = "sql"
            reason = "Text-to-SQL generation or SQL execution returned failure."
        else:
            source = "unknown"
            reason = "Failed history item does not map cleanly to a known layer."
        analyses.append(FailureAnalysis(source=source, reason=reason, related_step=item.step))
    return analyses


def _analyze_observation(observation: ExecutionObservation) -> list[FailureAnalysis]:
    failure_type = observation.observation.failure_type
    missing_facts = observation.observation.missing_facts
    if observation.status == "success" and not failure_type and not missing_facts:
        return []
    if failure_type == "tool_miss":
        source = "tool"
        reason = "Execution observation reports a missing or mismatched Tool."
    elif failure_type == "sql_error":
        source = "sql"
        reason = "Execution observation reports SQL generation, validation, or execution failure."
    elif failure_type == "missing_param":
        source = "planner"
        reason = "Execution observation reports missing parameters or facts."
    elif failure_type == "schema_gap":
        source = "schema"
        reason = "Execution observation reports that requested facts are not in Schema."
    elif failure_type == "execution_error":
        source = "execution"
        reason = "Execution observation reports execution-layer failure."
    else:
        source = "unknown"
        reason = "Execution observation is incomplete or partial without a specific failure type."
    return [FailureAnalysis(source=source, reason=reason, related_step=None)]


def _contains_fact(facts: list[str], keywords: list[str]) -> bool:
    lowered = [fact.lower() for fact in facts]
    return any(keyword.lower() in fact for fact in lowered for keyword in keywords)
