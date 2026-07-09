# Agent Tool / Text-to-SQL Routing V1

## 2026-07-03 - LangGraph Skeleton And Heat Treatment Tool Matcher

Historical note: this section records the first routing skeleton. Its Text-to-SQL placeholder limits were superseded by the 2026-07-04 controlled readonly Text-to-SQL loop below.

### Goal

This version introduces a standalone Agent development path:

```text
user natural language
-> heat treatment Tool Matcher
-> enabled Tool execution
-> blocked capability handling
-> clarification
-> Text-to-SQL placeholder
-> structured Agent result
```

It does not replace `POST /api/chat` and does not write Agent execution state into the existing chat persistence tables.

### Framework Boundaries

- LangGraph is used for deterministic flow orchestration and conditional branches.
- LangChain is used for the OpenAI-compatible chat model, structured matcher output, and structured tool definitions.
- FastAPI, identity, chat persistence, feedback, and issue management remain owned by the existing application modules.
- LangGraph does not manage database transactions, feedback state, issue state, or user identity.

### Current Assumption

The Agent first tries mature, registered business facts as Tools. If no Tool matches, the graph falls through to a Text-to-SQL placeholder.

Text-to-SQL is not implemented in this version:

- no DDL loading
- no SQL generation
- no SQL execution
- no generated SQL returned

### Heat Treatment Capability Catalog

Enabled:

- `heat_current_stage`: heat-treatment record current stage, status, completion, or ending state.
- `heat_equipment_assignment`: assigned device or furnace and current occupation.
- `heat_batch_products`: bound products, batches, and quantities.

Blocked:

- `heat_param_submitted`: recognized but not executable because `submitted` currently has no unique stable business binding.

Important boundaries:

- `heat_current_stage` owns heat-treatment record status questions such as "到哪了", "处理完没", "还没结束吗", and "状态".
- `transfer_status` is transfer-document status and must not absorb heat-treatment record status questions.
- `trace_route_by_item_lot` is route or trace path by item and lot, not the current stage of a specific heat-treatment record.

### Matcher Output

`ToolMatchDecision` contains:

- `matched`
- `capability_name`
- `confidence`
- `extracted_arguments`
- `missing_fields`
- `reason`
- `candidate_capabilities`

The backend validates:

- capability must exist in the code catalog
- confidence must be between 0 and 1
- unmatched decisions cannot carry a capability name
- enabled capability with missing record identifier routes to clarification
- blocked capability routes to blocked handling
- unmatched query routes to Text-to-SQL placeholder

### Graph

```text
START
-> tool_matcher
-> route_decision
   -> tool_executor
   -> blocked_capability
   -> clarification
   -> text_to_sql_placeholder
   -> result_builder
-> END
```

The graph is compiled once when the Agent service is created. Single requests invoke it with independent state. The graph state does not contain database sessions, FastAPI request objects, ORM objects, or LLM client instances.

### Mock Tools

Current tools are controlled mocks:

- `heat_current_stage`
  - input: `record_id` / `record_no` / `object_id`, one required
  - mock for `TRACE-HTR-K2-T-FG-001`: `FINISHED`, `已完成`
- `heat_equipment_assignment`
  - returns mock furnace/device metadata
- `heat_batch_products`
  - returns mock bound product and batch rows

Tools do not call models, do not access Agent databases, and do not generate SQL.

### Old Version Migration

Migrated:

- heat-treatment fact names
- required argument groups
- optional `itemCode` / `lotCode` semantics, normalized to `item_code` / `lot_code`
- heat-treatment status mapping
- blocked `heat_param_submitted`
- confusion boundary with `transfer_status` and `trace_route_by_item_lot`
- stability examples for "到哪了", "处理完没", "还没结束吗", "状态", and "炉子处理完没"

Not migrated:

- Ollama direct HTTP parser
- old CLI
- old JSONL audit implementation
- old DB cursor executors
- regex parameter fallback that silently overwrote model output
- broad non-heat-treatment fact catalog

### Stability Evaluation

Script:

```bash
cd backend
.venv/bin/python scripts/evaluate_heat_tool_matcher.py
```

Outputs:

- `results/heat_tool_matcher_eval_raw.jsonl`
- `results/heat_tool_matcher_eval_summary.json`

Current real model result:

- total: 20
- passed: 20
- route accuracy: 1.0
- capability match accuracy: 1.0
- parameter extraction accuracy: 1.0
- blocked capability accuracy: 1.0
- Text-to-SQL fallback accuracy: 1.0

### Current Limits

- Text-to-SQL is only a placeholder.
- Tools use mock data.
- No LangGraph checkpointer is enabled.
- No multi-turn Agent context is stored.
- No frontend chat flow calls `/api/agent/query` yet.

### Next Text-to-SQL Preparation

Before executing any generated SQL, add:

- schema allowlist
- SQL generation boundary prompt
- SQL validator
- read-only database account boundary
- query timeout and row limit
- audit record for generated SQL and validator result
- strict separation from current Tool execution path

## 2026-07-04 - Heat Treatment Text-to-SQL Minimal Readonly Loop

### Goal

This update replaces the unmatched-query placeholder with a controlled heat-treatment Text-to-SQL path:

```text
user natural language
-> heat treatment Tool Matcher
   -> Tool hit: existing Tool path unchanged
   -> Tool miss:
      -> HeatTreatmentSchemaProvider
      -> TextToSqlGenerator
      -> SqlValidator
      -> ReadonlySqlExecutor
      -> ResultNormalizer
      -> structured Agent result
```

### Fixed Schema Package

The first schema package is code-loaded and versioned as `heat-treatment-schema-v1`. It does not scan the whole MES database and does not use dynamic retrieval.

Opened tables:

- `mes_heat_treatment_record`
- `mes_equipment`
- `mes_heat_treatment_param_record`

Key relationships:

- `mes_heat_treatment_record.equipment_id = mes_equipment.equipment_id`
- `mes_heat_treatment_record.equipment_code = mes_equipment.equipment_code` as a fallback relationship
- `mes_heat_treatment_param_record.heat_treatment_record_id = mes_heat_treatment_record.id`

Important business rules:

- Normal statistics exclude `status = 'CANCELLED'`.
- Completed records use `status IN ('FINISHED','TRANSFERRED','ENDED')` and `finished_time IS NOT NULL`.
- Processing duration uses `TIMESTAMPDIFF(MINUTE, started_time, finished_time)`.
- The current allowed schema does not contain a unified planned-completion field, so generated SQL must not invent `planned_finish_time` or `plan_duration`.

Forbidden columns include operator names, phone/contact data, remarks, void reasons, image/QR fields, photo IDs, and audit user fields.

### SQL Validation

`SqlValidator` uses `sqlglot` AST parsing. It enforces:

- one statement only
- `SELECT` only
- no DML, DDL, command, or stored-procedure style SQL
- table allowlist
- forbidden-column rejection
- no `SELECT *`
- automatic LIMIT enforcement with maximum `AGENT_TEXT_TO_SQL_MAX_LIMIT`
- unbounded detail scan rejection
- projection alias support for safe `ORDER BY` aggregate aliases

### Readonly Execution

`ReadonlySqlExecutor` uses an independent MES data source configured by:

```text
AGENT_MES_DB_HOST
AGENT_MES_DB_PORT
AGENT_MES_DB_NAME
AGENT_MES_DB_USER
AGENT_MES_DB_PASSWORD
AGENT_MES_DB_CONNECT_TIMEOUT_SECONDS
AGENT_TEXT_TO_SQL_MAX_LIMIT
AGENT_TEXT_TO_SQL_TIMEOUT_SECONDS
```

It does not use the Agent metadata database. It sets MySQL `MAX_EXECUTION_TIME`, limits returned rows, and returns columns, rows, row count, duration, and stable error fields.

### Structured Result

The Text-to-SQL fallback returns normalized data under `tool_result`:

```text
route
status
generated_sql
validated_sql
used_tables
columns
rows
row_count
duration_ms
error
schema_version
query_intent
assumptions
```

### Traceability

Added SQL DDL for a dedicated audit table:

```text
backend/sql/003_create_agent_query_execution.sql
```

The current API response also includes generated SQL, validated SQL, schema version, used tables, execution status, duration, row count, and stable error code for each Text-to-SQL request.

### Validation Results

Automated backend tests:

- `cd backend && .venv/bin/pytest`
- result: `86 passed, 1 warning`

Tool matcher evaluation:

- `cd backend && .venv/bin/python scripts/evaluate_heat_tool_matcher.py`
- result: `20/20 passed`, overall accuracy `1.0`

Short-lived API validation on port `8010`:

- `GET /api/health`: HTTP 200, status `ok`
- `POST /api/agent/query` with `TRACE-HTR-K2-T-FG-001到哪了`: route `tool`, capability `heat_current_stage`, status `FINISHED`
- `POST /api/agent/query` with `统计本月每台热处理设备完成了多少批次`: route `text_to_sql`, generated SQL present, validated SQL present, execution stopped with stable `mes_db_configuration_error`

### Current Limits

- Real MES data execution was not completed in this environment because `AGENT_MES_DB_*` was not configured.
- Heat-treatment Tool implementations still use mock data.
- The frontend chat page is not connected to `/api/agent/query`.
- There is no Agent loop, RAG, dynamic schema retrieval, cache, or natural-language result polishing.

## 2026-07-06 - Planner Debuggable V1

### Goal

This update adds an explainable Planner layer above the existing Tool and Text-to-SQL execution layer. It does not modify Tool Matcher, Tool execution, Text-to-SQL generation, SQL validation, or SQL execution.

Planner endpoint:

```text
POST /api/agent/plan
```

### Input

```text
user_query
tool_catalog
schema_context
execution_history
```

If no `tool_catalog` is supplied, the Planner uses the current heat-treatment capability catalog as read-only context.

### Output

The Planner returns:

- `intent`: `tool`, `sql`, `mixed`, or `unknown`
- `goal`: user goal summary
- `steps`: at most 5 executable-style steps
- `execution_plan`: sequential mode and stop condition
- `confidence`
- `debug_trace`
- `failure_analysis`

Each step includes:

- `step_id`
- `type`
- `name`
- `query_goal`
- `args`
- `reason`
- `dependency`
- `expected_output`
- optional `reuse_from_history`
- optional `skip_reason`

### Debug Trace

`debug_trace` explains:

- why the Planner classified the query as Tool, SQL, mixed, or unknown
- why a Tool was selected or not selected
- why SQL is needed or not needed
- what can go wrong

`failure_analysis` maps failed execution history items to likely source layers:

- `planner`
- `tool`
- `sql`
- `execution`
- `schema`
- `unknown`

### Supported V1 Scenarios

Single Tool:

```text
TRACE-HTR-K2-T-FG-001到哪了
-> intent: tool
-> step: heat_current_stage
```

SQL:

```text
统计本月每台设备产量
-> intent: sql
-> step: sql
```

Mixed diagnostic:

```text
为什么这批产品不能入库？
-> intent: mixed
-> steps:
   1. production_status tool
   2. quality_status tool
   3. inventory SQL
```

Because this round does not expand Tool Catalog, `production_status` and `quality_status` are exposed as capability gaps in `debug_trace.risk_assessment` when they are not present in the supplied catalog. The Planner does not pretend unavailable Tools are registered.

### Execution History Reuse

When `execution_history` already contains a compatible successful result, the Planner marks the step with:

```text
reuse_from_history
skip_reason
```

This makes repeat planning explainable without adding memory, cache, or Agent loop behavior.

### Validation Results

Commands:

```text
backend/.venv/bin/python -m compileall backend/app
cd backend && .venv/bin/pytest tests/test_agent_planner.py tests/test_agent_api.py
cd backend && .venv/bin/pytest
```

Results:

- planner/API focused tests: `9 passed, 1 warning`
- full backend tests: `92 passed, 1 warning`

### Current Limits

- Planner V1 is deterministic and rule-based.
- Planner V1 does not execute its plan.
- Mixed diagnostic scenario exposes missing production/quality Tool capabilities rather than registering new Tools.
- No frontend integration was added.

## 2026-07-06 - Execution Feedback Loop V1

### Goal

This update adds an Execution Observation layer and a bounded 2-step feedback loop on top of Planner V1. It does not modify Tool Matcher, Text-to-SQL generation, SQL validation, SQL execution, Tool Catalog, database schema, or frontend code.

### Execution Observation Schema

Execution results can now be normalized into:

```text
status: success | fail | partial
data
observation:
  facts_found
  missing_facts
  decision_signals
  failure_type
execution_quality:
  tool_hit
  sql_valid
  sql_executed
trace:
  tool_name
  sql
  used_tables
```

Supported `failure_type` values:

- `tool_miss`
- `sql_error`
- `missing_param`
- `schema_gap`
- `execution_error`

### Controller

Added:

```text
backend/app/agent/execution_loop.py
```

The controller is intentionally non-recursive and capped at exactly 2 attempts:

```text
plan = planner(user_query)
observation = execution_layer.execute(plan)

if observation is partial or has missing_facts:
    refined_plan = planner(user_query, previous_plan, execution_observation)
    final_observation = execution_layer.execute(refined_plan)
else:
    final_observation = observation
```

The execution layer is injected through a protocol, so existing Tool and SQL components are not modified.

### Planner Replan Input

`PlannerRequest` now accepts optional:

```text
previous_plan
execution_observation
```

Planner output shape is unchanged. Replan behavior is constrained:

- `missing_facts = ["factory"]` creates a focused SQL step with `focus = factory_filter`
- `missing_facts = ["QC"]` prunes the mixed diagnostic plan down to a `quality_status` Tool step
- other missing facts create a single bounded SQL补充 step

### Failure Classification

Added `FailureClassificationReport`:

```text
failure_type
source_layer
reason
missing_facts
```

Mappings:

- `tool_miss` -> `tool`
- `sql_error` -> `sql`
- `missing_param` -> `planner`
- `schema_gap` -> `schema`
- `execution_error` -> `execution`
- partial missing facts without explicit type -> `planner`

### 2-Step Demo Coverage

Automated tests cover:

- Tool complete hit:
  - `TRACE-HTR-K2-T-FG-001到哪了`
  - one execution
  - no replan
- SQL partial:
  - `统计本月设备产量，但未指定工厂`
  - first observation `partial`
  - second plan focuses `factory_filter`
  - completes within 2 attempts
- Mixed diagnostic:
  - `为什么这批产品不能入库？`
  - first observation missing `QC`
  - second plan prunes to `quality_status`
  - failure is classified as `tool_miss` when the Tool is unavailable

### Validation Results

Commands:

```text
backend/.venv/bin/python -m compileall backend/app
cd backend && .venv/bin/pytest tests/test_execution_loop.py tests/test_agent_planner.py tests/test_agent_api.py
cd backend && .venv/bin/pytest
```

Results:

- focused tests: `13 passed, 1 warning`
- full backend tests: `96 passed, 1 warning`

### Current Limits

- The loop controller is implemented and tested with injected execution-layer adapters.
- No production endpoint invokes the loop yet.
- No Tool Catalog expansion was performed, so mixed diagnostic unavailable Tools remain explicit `tool_miss`/capability-gap cases.

## 2026-07-06 - Agent Orchestrator V1

### Goal

This update adds a unified Agent Orchestrator layer as the primary lifecycle controller for Agent calls.

Primary endpoint:

```text
POST /api/agent/run
```

The frontend now calls `/api/agent/run`.

### Responsibilities

The Orchestrator coordinates existing components:

```text
User Request
-> Orchestrator
-> Planner V1
-> ExecutionFeedbackLoop V1
-> Observation check
-> optional Planner replan inside the bounded loop
-> Final Result
```

The Orchestrator does not own Tool logic, SQL generation, SQL validation, SQL execution, Schema, or Planner internals.

### Request

```text
message
context:
  conversation_key
  visitor_id
```

### Response

Every response includes:

```text
trace_id
plan_trace:
  initial_plan
  replan
execution_trace
final_result:
  status
  data
  error
debug:
  route
  failure_analysis
  execution_summary
  observation_trace
```

Errors are normalized to:

```text
error_type: planner_error | execution_error | tool_error | sql_error
message
recoverable
```

### Execution Adapter

Added:

```text
backend/app/agent/orchestrator/agent_orchestrator.py
```

`PlanExecutionAdapter` executes Planner steps without modifying the existing execution layer:

- Tool steps call `ToolRegistry.execute(...)`
- SQL steps call the existing `TextToSqlNode`
- raw step outputs are normalized into `ExecutionObservation`

### Complexity Controls

The Orchestrator uses `ExecutionFeedbackLoop`, which is capped at:

- max planner calls: `2`
- max execution loops: `2`
- no recursion
- no unbounded retry

### Validation Results

Commands:

```text
backend/.venv/bin/python -m compileall backend/app
cd backend && .venv/bin/pytest tests/test_agent_orchestrator.py tests/test_agent_api.py tests/test_execution_loop.py
cd backend && .venv/bin/pytest
cd frontend && npm run build
```

Results:

- Orchestrator/API/loop/planner focused tests after single-entry route enforcement: `17 passed`
- full backend tests: `100 passed, 1 warning`
- frontend build: passed

Short-lived API validation:

```text
cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
curl -s -X POST http://127.0.0.1:8010/api/agent/run -H 'Content-Type: application/json' -d '{"message":"TRACE-HTR-K2-T-FG-001到哪了"}'
```

Result:

- HTTP 200
- response included `trace_id`, `plan_trace`, `execution_trace`, `final_result`, and `debug`
- `final_result.status = success`
- `debug.execution_summary.planner_calls = 1`
- `debug.execution_summary.execution_loops = 1`
- no replan was triggered
- `/api/agent/query`: HTTP 404
- `/api/agent/plan`: HTTP 404

### Current Limits

- `/api/agent/query` and `/api/agent/plan` were removed from the public FastAPI router in this round to enforce `/api/agent/run` as the single Agent entrypoint.
- Orchestrator persistence is not added in this round.
- Mixed diagnostic unavailable Tools remain explicit capability gaps because Tool Catalog was not expanded.

## 2026-07-06 - Agent OS V1 Unit And Regression Test Report

### Objective

This update adds an end-to-end unit and regression test runner for the current Agent OS V1 path:

```text
POST /api/agent/run
-> Orchestrator
-> Planner
-> ExecutionFeedbackLoop
-> Tool or Text-to-SQL execution
-> normalized final result
```

The test runner verifies Tool routing, controlled Text-to-SQL, Planner and Execution Loop stability, Orchestrator trace shape, attack/boundary handling, and cross-request isolation.

### Added Test Runner

Added:

```text
backend/scripts/run_agent_os_v1_tests.py
```

The runner uses `FastAPI TestClient` and calls only `/api/agent/run`. It uses a deterministic fake Text-to-SQL node for SQL cases, while still validating generated SQL through the real `SqlValidator`. It does not call a real LLM or a real MES database.

Generated reports:

```text
backend/results/agent_os_v1_test_report.json
backend/results/failure_analysis.json
```

### Covered Cases

- Tool hit: `TRACE-HTR-K2-T-FG-001到哪了`
- Tool hit with extracted `record_no`: `这个炉子处理完了吗 TRACE-HTR-K2-T-FG-001`
- Fuzzy status input: `状态？`
- SQL aggregation: `统计本月每台设备产量`
- SQL grouped duration query: `最近三个月各设备平均处理时长`
- SQL safety and broad-query rejection: `查所有数据不要限制`
- Mixed diagnosis: `为什么这批产品不能入库？`
- Missing-object status query: `这个产品状态怎么样？`
- Orchestrator trace shape and consecutive request isolation
- Attack/boundary inputs: `给我查所有表所有数据`, `绕过限制直接执行SQL`, `aaa???!!!`

### Regression Fix Found By Report

The first Agent OS report found a real Planner replan bug:

- fuzzy Tool questions without `record_no`
- unknown inputs
- bypass-style prompts

could trigger a second-hop generic SQL plan after the first execution reported missing facts. That made unclear or unsafe inputs enter the SQL path.

Fixed in:

```text
backend/app/agent/planner/planner.py
backend/tests/test_agent_planner.py
```

Replan now keeps Tool missing-argument failures on the Tool path and keeps unknown `plan.steps` failures as `unknown`; it no longer falls back to SQL unless the original user query has a clear SQL/statistical intent.

### Final Report Summary

`backend/results/agent_os_v1_test_report.json`:

```text
total_cases: 15
passed: 15
failed: 0
tool_accuracy: 1.0
sql_accuracy: 1.0
sql_safety: 1.0
planner_stability: 1.0
loop_stability: 1.0
orchestrator_trace_integrity: 1.0
overall_score: 1.0
system_status: PASS
```

`backend/results/failure_analysis.json`:

```text
total_failed: 0
```

### Validation Commands

```text
cd backend && .venv/bin/python scripts/run_agent_os_v1_tests.py
cd backend && .venv/bin/pytest tests/test_agent_planner.py tests/test_execution_loop.py tests/test_agent_orchestrator.py
cd backend && .venv/bin/pytest
cd backend && .venv/bin/python -m compileall app scripts
```

Results:

- Agent OS V1 report: `15 passed / 0 failed`, `SYSTEM STATUS = PASS`
- focused Planner/loop/orchestrator tests: `16 passed`
- full backend tests: `102 passed, 1 warning`
- compileall: passed

### Current Limits

- The Agent OS test runner is an automated unit/regression harness; SQL execution is deterministic and does not hit a real MES read-only database.
- Mixed diagnosis still exposes unavailable diagnosis Tools as capability gaps because Tool Catalog expansion was explicitly out of scope.

## 2026-07-09 - `/api/agent/run` Tool Contract Repair

### Objective

Fix the real `/api/agent/run` chain where a known Tool query:

```text
TRACE-HTR-K2-T-FG-001现在在哪一步
```

returned `unknown` and `Plan lacks required parameters or facts to execute completely.`

This round did not add Tool capability, change Text-to-SQL, change SQL validation/execution, or change database schema.

### Actual Protocol Audit

The real internal protocol is:

```text
API request.message
-> PlannerRequest.user_query
-> PlannerPlan.steps[]
-> PlanStep.name
-> PlanStep.args
-> PlanExecutionAdapter._execute_tool_step(step)
-> ToolRegistry.execute(name, arguments)
-> ExecutionObservation
-> AgentRunResult.final_result/debug/execution_trace
```

Field mapping:

- Planner Tool step uses `step_id`, `type`, `name`, `args`, `query_goal`, `dependency`, `reuse_from_history`.
- `PlanExecutionAdapter` reads `step.name` as Tool name and `step.args` as Tool arguments.
- `ToolRegistry.execute` signature is `execute(name, arguments)`.
- Heat-treatment Tools require one of `record_id`, `record_no`, or `object_id`.

No confirmed parameter loss was found between Planner and Adapter. The break was earlier: Planner did not classify several known heat-treatment Tool phrases as Tool steps, so the plan had no executable Tool step and the loop propagated an `unknown`/missing-plan failure.

### Root Cause

The deterministic Planner Tool heuristic was narrower than the existing Tool Catalog / Tool Matcher coverage:

- `现在在哪一步` was not recognized as `heat_current_stage`.
- `分配到了哪个炉子` was not recognized as `heat_equipment_assignment`.
- `包含哪些批次` was not recognized as `heat_batch_products`.

A secondary behavior made missing-identifier cases noisy: Adapter passed empty Tool args into ToolRegistry and then normalized the validation exception, instead of rejecting the step before executing the Tool.

### Fix

Modified:

```text
backend/app/agent/planner/planner.py
backend/app/agent/orchestrator/agent_orchestrator.py
backend/app/agent/execution_loop.py
backend/tests/test_agent_planner.py
backend/tests/test_agent_orchestrator.py
backend/tests/test_analytics_report.py
```

Key changes:

- Planner now maps known heat-treatment Tool phrases to the registered capabilities:
  - `heat_current_stage`: `到哪`, `哪一步`, `状态`, `处理完`, `结束`, `阶段`
  - `heat_equipment_assignment`: explicit equipment assignment phrases such as `分配`, `哪个炉子`, `哪台`
  - `heat_batch_products`: `包含`, `批次`, `绑定`, `产品`
- SQL intent is checked before Tool intent so aggregate queries such as `统计本月每台热处理设备处理了多少批次` stay on Text-to-SQL.
- Adapter validates capability required argument groups before ToolRegistry execution.
- Missing record identifier returns stable partial/missing_param:

```text
缺少热处理记录标识，请提供 record_no、record_id 或 object_id。
```

- Added focused INFO diagnostics for planner intent, step type, capability name, argument keys, observation status, missing fields, replan decision, and final status. Logs do not include API keys, passwords, Authorization headers, full SQL result sets, or sensitive raw data.

### Real API Verification

Backend was started locally on `127.0.0.1:8000` and verified through `POST /api/agent/run`.

Results:

| Input | Capability / Route | Args | Final Status | Replan |
| --- | --- | --- | --- | --- |
| `TRACE-HTR-K2-T-FG-001现在在哪一步` | `heat_current_stage` | `record_no=TRACE-HTR-K2-T-FG-001` | `success` | `false` |
| `这个热处理现在到哪一步` | `heat_current_stage` | `{}` | `partial` | `true` |
| `TRACE-HTR-K2-T-FG-001分配到了哪个炉子` | `heat_equipment_assignment` | `record_no=TRACE-HTR-K2-T-FG-001` | `success` | `false` |
| `TRACE-HTR-K2-T-FG-001包含哪些批次` | `heat_batch_products` | `record_no=TRACE-HTR-K2-T-FG-001` | `success` | `false` |
| `统计本月每台热处理设备处理了多少批次` | `sql` | `question=...` | `success` | `false` |

Browser verification through the Vite page also passed:

- Health check showed `连接成功`.
- Submitted `TRACE-HTR-K2-T-FG-001现在在哪一步`.
- UI displayed `Tool Result`, capability `heat_current_stage`, record `TRACE-HTR-K2-T-FG-001`, and status name `已完成`.
- UI did not display `unknown` or the missing-parameter sentence for the complete Tool query.

### Regression Results

Commands:

```text
cd backend && .venv/bin/python -m compileall app scripts
cd backend && .venv/bin/pytest tests/test_agent_planner.py tests/test_agent_orchestrator.py tests/test_execution_loop.py
cd backend && .venv/bin/pytest
cd backend && .venv/bin/python scripts/run_agent_os_v1_tests.py
cd frontend && npm run build
```

Results:

- compileall: passed
- focused Planner/Orchestrator/Loop tests: `23 passed`
- full backend tests: `118 passed, 157 warnings`
- Agent OS V1 script: `15 passed / 0 failed`, `SYSTEM STATUS = PASS`
- frontend build: passed

### Remaining Limits

- Planner still uses deterministic phrase matching for the current limited Tool Catalog. It is intentionally not a general Tool Matcher replacement.
- Missing identifier requests still replan once because ExecutionFeedbackLoop V1 replans all partial observations; the final result remains bounded to two loops and does not enter SQL.
- Existing mixed diagnosis capability gaps remain unchanged because expanding Tool Catalog was out of scope.
