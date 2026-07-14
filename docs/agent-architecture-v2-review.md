# MES Agent V2 架构评审报告

**评审日期**: 2026-07-10  
**评审视角**: 内部实验 Agent，验证架构有效性（非生产上线视角）  
**架构版本**: V2（2026-07-10 完成）  
**参考文件**: AGENTS.md, docs/agent-architecture-v2.md, 全量代码审查

---

## 一、V2 架构演进回顾

### 1.1 演进时间线

```
2026-07-09: V1 架构巩固（Planner → Execution Loop → Tool/SQL）
            ├─ Capability Runtime V1（YAML 定义引入）
            ├─ Capability Router V1（首个性别迁移）
            ├─ Semantic Router V1（语义理解独立）
            └─ Legacy Fallback 隔离

2026-07-10: V2 架构重构
            ├─ Capability Catalog V2 + MVP 评估
            ├─ Capability Reasoning 实验（规则匹配）
            ├─ V1 代码归档（archive/v1/）
            └─ V2 核心链路确立（MesAgent → AgentRouter → HeatTreatmentAgent）
```

### 1.2 V2 当前架构

```
POST /api/agent/run
  → MesAgent.run(request)
    → AgentRouter.route()           ← 固定路由，目前仅 HeatTreatmentAgent
    → HeatTreatmentAgent.run()
      → CapabilityReasoner.reason() ← 确定性规则匹配（非 LLM）
      → CapabilityReasoningValidator.validate()
      → CapabilityRuntime.execute()
        → ExecutionEngine.dispatch()
          ├─ heat_current_stage   → Tool (真实 DB 查询)
          └─ text_to_sql          → TextToSqlNode (安全链)
    → TraceRuntime.finish()
    → AuditRuntime.record()
```

---

## 二、V2 架构优势（做得好的地方）

### 2.1 架构演进质量极高

V1 → V2 的演进过程堪称教科书级别：

- **每一步都有明确的文档记录**：`docs/agent-architecture-consolidation-v1.md` 详细记录了 17 个阶段的变更，从 "Planner keyword router still exists" 到 "Legacy fallback isolated" 再到 "Capability Catalog V2 and MVP evaluation"，每一笔决策都有迹可循
- **每次变更都有验证快照**：compileall、pytest、acceptance tests、regression tests 四重验证
- **V1 代码完整归档而非删除**：`archive/v1/` 保留了所有旧代码，`archive/experiments/` 保留了一次性实验脚本
- **"先实验再迁移"的策略**：Capability Reasoning 先作为并行实验路径验证（30 个 case，accuracy 1.00），确认稳定后才成为生产路径

### 2.2 核心链路极度精简

V2 生产链核心文件总共约 **350 行**（不含工具实现）：

| 文件 | 行数 | 职责 |
|------|------|------|
| `core/mes_agent.py` | 29 | 统一入口，trace/audit 包装 |
| `core/agent_router.py` | 20 | 固定路由 seam |
| `agents/heat_treatment/agent.py` | 41 | 领域编排（reasoning → validate → execute） |
| `context/models.py` | 23 | 请求/响应模型 |
| `reasoning/reasoner.py` | 160 | 确定性规则匹配 |
| `runtime/capability/runtime.py` | 20 | 执行网关 |
| `execution/engine/engine.py` | 18 | 执行器调度 |

**对比 V1 的 `agent_orchestrator.py`（1336 行）**：V2 核心逻辑减少了约 **80%**。

### 2.3 Capability Catalog 驱动设计

YAML 定义 → Pydantic 模型 → Loader → Registry → Router → Execution 的链条设计合理：

```yaml
# heat-treatment.yaml 示例
- name: heat_current_stage
  status: enabled
  execution_type: tool
  executor: heat_current_stage
  required_entities: [record_no]
  boundaries:
    - 不负责转序单状态
    - 不负责检验状态
```

关键设计决策：
- **status 作为执行门控**：`enabled` / `planned` / `blocked` 三级控制，`planned` 能力可被 reasoning 选中但 validator 阻止执行
- **execution_type 作为策略标记**：`tool` / `readonly_sql` 区分固定查询和动态 SQL
- **boundaries 作为能力边界**：明确声明能力不负责什么，防止 Agent 越界

### 2.4 依赖注入和可测试性

V2 的依赖注入设计非常干净：

```python
# api/agent.py - 组装层
HeatTreatmentAgent(
    CapabilityReasoner(registry, LlmRuntime(chat_model)),
    capability_runtime,
    trace_runtime,
)

# tests/v2/test_mes_agent_v2.py - 测试层
HeatTreatmentAgent(
    CapabilityReasoner(registry, LlmRuntime()),  # 空 LLM Runtime
    CapabilityRuntime(registry, ExecutionEngine({
        "heat_current_stage": lambda args: {"found": True, ...},  # Fake executor
        "text_to_sql": lambda args: {"rows": [...]},
    })),
    trace_runtime,
)
```

- **HeatTreatmentAgent 不创建任何运行时**，全部通过构造函数注入
- **测试可以完全替换执行引擎**，无需真实数据库或 LLM
- **Runtime 抽象层**（LlmRuntime / TraceRuntime / AuditRuntime / CapabilityRuntime）通过 Protocol 解耦

### 2.5 明确的扩展缝（Extension Seams）

V2 架构文档中明确列出了 "Unimplemented Extension Points"：

- Router policies for WorkOrderAgent and InspectionAgent
- Intelligent/LLM/embedding routing
- Model-backed Capability Reasoning
- Persistent Trace Runtime
- Executable implementation for planned heat_device_trace
- RAG, Memory, multi-Agent collaboration

这些都是**显式设计预留**而非**半成品实现**，区别在于：后者会让代码充满 if-else 分支和未完成的逻辑，前者只是声明了未来可以插入的点。

---

## 三、架构不足分析

### 3.1 CapabilityReasoner 仍是硬编码规则匹配（中优先级）

当前 `reasoner.py` 的核心匹配逻辑：

```python
# _score_capability() 中的硬编码关键词匹配
if capability_name == "heat_completion_count_monthly":
    if _contains_any(message, ["完成多少批", "完成数量", "统计"]) and "热处理" in message:
        return 0.92, "用户询问热处理完成数量统计。"
if capability_name == "heat_device_trace":
    if _contains_any(message, ["设备", "生产设备"]):
        return (0.9 if has_record else 0.82), "..."
```

**问题**：这本质上是 V1 Planner 中 `_tool_capability_name()` 关键词匹配的进化版，虽然结构更清晰（返回 confidence + reason 而非直接映射），但仍是硬编码的中文关键词。

**影响**：
- 每新增一个 capability 需要手动添加匹配规则
- 无法处理同义词变体（除非手动枚举）
- 匹配准确度完全依赖开发者的关键词枚举完整性

**但需要注意的是**：V2 设计文档明确说 "V2 deterministic reasoning is retained in this round; no new model behavior was introduced"，且实验数据表明规则匹配在当前 5 个 capability 范围内 top1 accuracy 达到 1.00。所以在当前范围内这不是问题，只是扩展瓶颈。

**演进方向**：`generator.py` 中已有 `CapabilityReasoningGenerator`（LLM 驱动版本），代码完整但未启用。实验中已验证 business_facts 可将 catalog_only 的 0.73 提升到 1.00，说明 LLM + business_facts 的组合方案已有原型。

### 3.2 AgentRouter 固定路由是故意的设计约束，但需要明确演进时间点（低优先级）

```python
class AgentRouter:
    def route(self, request: AgentRequest) -> DomainAgent:
        del request
        return self._heat_treatment_agent
```

当前只有一个 DomainAgent（HeatTreatmentAgent），所以固定路由是正确的。但 V2 文档中也列出了 `WorkOrderAgent` 和 `InspectionAgent` 作为未来扩展点，且 `mvp-planned.yaml` 中已定义了 `work_order_status` 和 `inspection_status` 两个 planned 能力。

**建议**：当第二个 DomainAgent 准备就绪时，Router 的演进路径应该是：

```
阶段 1 (当前):   固定路由 → HeatTreatmentAgent
阶段 2 (近期):   关键词/领域路由 → {HeatTreatmentAgent, WorkOrderAgent}
阶段 3 (远期):   LLM 领域路由 → 动态选择
```

### 3.3 双轨 Capability 定义并存（中优先级）

当前存在两套 Capability 定义体系：

| 来源 | 格式 | 用途 |
|------|------|------|
| `capability/catalog/definitions/*.yaml` | YAML | V2 生产路径，CapabilityLoader 加载 |
| `capability/catalog/heat_treatment.py` | Python CapabilitySpec | V1 遗留，ToolRegistry 仍在使用 |

**问题**：
- `heat_treatment.py` 定义了 4 个 CapabilitySpec（含 `heat_param_submitted`），YAML 只定义了 3 个（不含 `heat_param_submitted`）
- `heat_treatment.py` 中的 `heat_equipment_assignment` 和 `heat_batch_products` 状态是 `planned`，但 YAML 中没有对应的定义
- 新同学看代码时会困惑：到底哪个是真正的 capability 定义源？

**建议**：
- 短期：在 `heat_treatment.py` 顶部添加明确的 deprecation notice，指向 YAML 定义
- 中期：将所有 CapabilitySpec 迁移到 YAML，Python 常量仅保留 `HEAT_STATUS_NAMES` 等业务常量
- 长期：Python CapabilitySpec 类可以退役

### 3.4 agent/context/state.py 是 LangGraph 遗留（低优先级）

```python
# context/state.py
class AgentState(TypedDict):
    """DEPRECATED: LangGraph 遗留状态定义。V2 使用 AgentRequest/AgentResponse。"""
    user_query: str
    ...
```

虽然已经标注 DEPRECATED，但 `api/agent.py` 的 `_sql_executor()` 仍在构建 `AgentState` 并传给 `TextToSqlNode`：

```python
def _sql_executor(node: TextToSqlNode):
    def execute(arguments: dict[str, Any]) -> dict[str, Any]:
        initial_state: AgentState = {
            "user_query": str(arguments.get("question", "")),
            ...
        }
        state = node(initial_state)
        return cast(dict[str, Any], state.get("tool_result") or {})
```

`TextToSqlNode.__call__` 的签名是 `(self, state: AgentState) -> AgentState`，这是 LangGraph 时代的节点签名风格。

**建议**：将 `TextToSqlNode` 重构为接受普通参数而非 TypedDict state，去掉对 `AgentState` 的依赖。

### 3.5 ExecutionEngine 的 executor 注册在 API 组装层（中优先级）

```python
# api/agent.py
ExecutionEngine({
    "heat_current_stage": lambda arguments: tool_registry.execute("heat_current_stage", arguments),
    "text_to_sql": _sql_executor(text_to_sql),
})
```

**问题**：
- Executor 的注册散落在 API 组装层，而非与 capability 定义放在一起
- 每新增一个 capability executor 需要同时修改 YAML 定义 + API 组装代码
- 如果未来有多个 DomainAgent，每个都需要在 API 层注册自己的 executor

**建议**：
- 将 executor 注册逻辑收敛到 `CapabilityRuntime` 或一个独立的 `ExecutorRegistry`
- 让每个 DomainAgent 声明自己需要的 executor，由 Runtime 统一管理
- 目标：API 组装层只做"把零件拼起来"，不做"定义零件是什么"

### 3.6 测试覆盖与代码量不匹配（中优先级）

| 层级 | V2 测试用例数 | V1 archive 测试用例数 |
|------|-------------|---------------------|
| Agent 核心链路 | 6 | 33 个文件，122+ 用例 |
| 覆盖场景 | 成功路径 + planned 阻止 + 澄清 + 固定路由 | Orchestrator、Planner、Graph、SemanticRouter、Text-to-SQL 全链 |

V2 的 6 个测试用例虽然覆盖了核心路径，但缺少：
- CapabilityReasoner 的边界测试（零候选、多候选平局、低置信度）
- ExecutionEngine 的 executor 未注册异常
- TraceRuntime 记录不完整时的行为
- 并发请求下的行为
- 不同 capability status 组合的矩阵测试

**建议**：随着 capability 数量增长，为每个 capability 增加 golden case 测试。

### 3.7 TextToSqlNode 仍使用 AgentState TypedDict（中优先级）

这是 LangGraph 时代的遗留接口。`TextToSqlNode.__call__` 接收和返回 `AgentState`，但在 V2 架构中它被包装成一个普通函数 `_sql_executor` 调用。内部仍然通过 `state["user_query"]`、`state["tool_result"]` 等字典键访问数据。

**建议**：将 `TextToSqlNode` 重构为接受明确的输入参数（`user_query: str`），返回明确的结果对象，不再依赖 TypedDict。

---

## 四、未来演进路线图

### 阶段 1: 架构收敛（1-2 周，低风险）

**目标**：消除 V2 架构中的 V1 残留

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 迁移 CapabilitySpec → YAML | P1 | 统一 capability 定义源，Python 常量仅保留业务枚举 |
| 重构 TextToSqlNode 接口 | P1 | 去掉 AgentState 依赖，改为普通函数签名 |
| 收敛 executor 注册逻辑 | P2 | 从 API 层移到 Runtime 层 |
| 清理 application/agent_query_service.py | P2 | 确认无调用方后移除 |

### 阶段 2: 确定性推理 → LLM 推理（2-4 周，中风险）

**目标**：将 CapabilityReasoner 从规则匹配升级为 LLM 驱动

**当前状态**：`CapabilityReasoningGenerator` 已有完整实现但未启用

```
当前: CapabilityReasoner (规则匹配)
      └─ _score_capability() 硬编码关键词

目标: CapabilityReasoner (两阶段)
      ├─ 阶段1: reason_catalog_only()  ← 规则匹配（快速路径）
      └─ 阶段2: reason_with_business_facts()  ← LLM 推理（兜底路径）
           └─ CapabilityReasoningGenerator.generate()
```

**实验数据支撑**：
- catalog_only accuracy: 0.73
- business_facts accuracy: 1.00
- business_facts lift: 0.27

**风险控制**：
- 保留规则匹配作为快速路径
- LLM 仅在规则匹配低置信度时触发
- 用 golden regression tests 验证切换前后行为一致

### 阶段 3: 多领域扩展（2-4 周，中风险）

**目标**：支持第二个 DomainAgent（WorkOrder 或 Inspection）

```
当前: AgentRouter → HeatTreatmentAgent

目标: AgentRouter → DomainRouter → {HeatTreatmentAgent, WorkOrderAgent}
```

**需要做的工作**：
1. 实现 `WorkOrderAgent`（参照 `HeatTreatmentAgent` 的模式）
2. 将 `AgentRouter` 从固定路由升级为领域路由
3. 新增 `work_order` 相关的 YAML capability 定义
4. 实现对应的 executor 和 repository
5. 新增 `WorkOrderAgent` 的 golden tests

**架构约束**：
- `WorkOrderAgent` 必须遵循与 `HeatTreatmentAgent` 相同的接口契约（`DomainAgent` Protocol）
- 共享 Runtime 层（CapabilityRuntime、ExecutionEngine、TraceRuntime、AuditRuntime）
- 不共享业务逻辑（各自拥有独立的 BusinessFacts 和 capability allow-list）

### 阶段 4: 可观测性增强（2-4 周，低风险）

**目标**：完善 Agent 运行时的可观测性

| 任务 | 说明 |
|------|------|
| 持久化 TraceRuntime | 当前 trace 仅存在于请求生命周期，应持久化到数据库 |
| Capability Reasoning 审计 | 记录每次 reasoning 的候选列表、置信度、最终选择 |
| LLM 调用链追踪 | 关联 reasoning LLM 调用 → capability 选择 → 执行结果 |
| Dashboard | 简单的 Agent 运行统计面板（capability 命中率、平均延迟、错误分布） |

### 阶段 5: 高级能力（远期，高风险）

**目标**：在架构验证完成后，探索更复杂的 Agent 能力

| 能力 | 说明 | 风险 |
|------|------|------|
| 多步推理 | Agent 自主组合多个 capability 完成复杂查询 | 高 |
| RAG | 将 MES 文档/规范作为推理上下文 | 中 |
| Memory | 跨会话的用户上下文记忆 | 中 |
| 多 Agent 协作 | 不同领域 Agent 协同完成跨领域查询 | 高 |

---

## 五、总体评估

### 5.1 架构成熟度评分（实验项目视角）

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计质量 | **9/10** | 分层清晰、依赖方向正确、扩展缝明确、文档完整 |
| 代码质量 | **8/10** | V2 核心极简、依赖注入到位、无 TODO/FIXME |
| 演进过程管理 | **9.5/10** | 17 个阶段的文档记录、每步验证、归档而非删除 |
| 可测试性 | **8/10** | 依赖注入设计优秀，V2 测试覆盖基本路径 |
| 架构一致性 | **7/10** | V2 核心一致性强，但仍有 V1 残留（双轨定义、AgentState） |
| 可扩展性 | **8/10** | Capability Catalog 设计可扩展，Router 扩展点明确 |
| 文档完整性 | **9/10** | AGENTS.md + docs/ 17 个文档 + V2 架构文档 |

**综合评分：8.5 / 10**

### 5.2 一句话总结

> V2 架构是一次**高质量的架构演进**：V1 的 1336 行 Orchestrator 被收敛为 350 行的核心链路，Capability Catalog 成为唯一的业务能力定义源，每一步演进都有文档和验证支撑。当前的主要不足集中在 V1 残留的清理和确定性推理的升级，而非架构设计本身的问题。

### 5.3 与 V1 的关键差异

| 维度 | V1 | V2 |
|------|-----|-----|
| 核心文件大小 | agent_orchestrator.py 1336 行 | mes_agent.py 29 行 |
| 路由方式 | Planner 硬编码关键词 | CapabilityReasoner 规则匹配 + CapabilityRouter |
| 能力定义 | Python CapabilitySpec 散落多处 | YAML 统一定义 + Pydantic 验证 |
| 测试策略 | 122+ 用例覆盖全链 | 6 个核心用例 + archive 保留 |
| 依赖框架 | LangGraph StateGraph | 纯 Python，LangGraph 仅 archive 使用 |
| 文档追溯 | 单次 cleanup 文档 | 17 个阶段完整记录 |
