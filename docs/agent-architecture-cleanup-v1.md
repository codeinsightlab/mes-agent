# Agent Architecture Cleanup V1

Date: 2026-07-09

## 1. Scope

Goal:

```text
Move the current experimental Agent OS closer to a Capability Driven Agent
before Capability Catalog V1.
```

This cleanup did not add Agent abilities, Tool abilities, Planner strategy, Text-to-SQL scope, database schema, frontend behavior, or a new framework.

## 2. Current Directory Structure

Reviewed scope:

```text
backend/app/agent/
├── catalog/
├── nodes/
├── orchestrator/
├── planner/
├── prompts/
├── text_to_sql/
├── tools/
├── execution_loop.py
├── execution_observation.py
├── graph.py
├── models.py
└── state.py

backend/tests/
├── fixtures/
├── golden/
├── heat_tool_test_utils.py
└── test_*.py

backend/scripts/
├── evaluate_heat_tool_matcher.py
├── run_agent_os_v1_tests.py
├── run_agent_regression.py
└── run_production_acceptance_v1.py
```

## 3. Legacy Inventory

| File | Role | Current Status | Recommendation |
| --- | --- | --- | --- |
| `backend/app/agent/orchestrator/agent_orchestrator.py` | Production Agent orchestration and execution adapter. | keep | Keep as current `/api/agent/run` execution path. |
| `backend/app/agent/planner/planner.py` | Planner plus legacy semantic router. | deprecate-partial | Keep execution planning; migrate keyword routing/extraction to Capability Router later. |
| `backend/app/agent/catalog/heat_treatment.py` | Current capability metadata source. | keep | Keep and evolve into Capability Catalog V1. |
| `backend/app/agent/tools/registry.py` | Capability-to-Tool execution registry. | keep | Keep; only `enabled` capabilities are executable. |
| `backend/app/agent/tools/heat_treatment.py` | Heat-treatment Tool functions. | mixed | Keep real `heat_current_stage`; mock functions are planned-only until repository-backed. |
| `backend/app/agent/tools/repository/heat_treatment_repository.py` | Real readonly heat-treatment repository. | keep | Keep as target Tool implementation pattern. |
| `backend/app/agent/text_to_sql/*` | Controlled SQL generation, validation, execution, normalization. | keep | Keep as analytical/unknown structured query strategy. |
| `backend/app/agent/graph.py` | LangGraph-style route graph. | deprecated | Marked eval-only; production uses Orchestrator. |
| `backend/app/agent/nodes/tool_matcher.py` | LLM Tool matcher node. | deprecated | Marked eval-only; future replacement is Semantic Understanding + Capability Router. |
| `backend/app/agent/prompts/tool_matcher.py` | Hardcoded matcher prompt. | deprecate | Keep only for eval path; generate from Catalog or remove later. |
| `backend/app/agent/nodes/tool_executor.py` | Graph-only Tool executor. | deprecate | Remove if graph path is retired. |
| `backend/app/agent/nodes/blocked_capability.py` | Graph-only blocked capability result. | deprecate | Remove if graph path is retired. |
| `backend/app/agent/nodes/clarification.py` | Graph-only clarification result. | deprecate | Remove if graph path is retired. |
| `backend/app/agent/nodes/result_builder.py` | Graph-only result shaping. | deprecate | Remove if graph path is retired. |
| `backend/app/agent/state.py` | Graph state shape. | deprecate | Remove if graph path is retired. |
| `backend/scripts/evaluate_heat_tool_matcher.py` | Matcher evaluation script. | deprecate | Keep as eval-only until Catalog Router evaluation replaces it. |
| `backend/tests/fixtures/heat_treatment_tool_match_cases.json` | Legacy matcher evaluation cases. | deprecate | Keep as eval-only; merge into golden cases later. |
| `backend/tests/golden/*.json` | Golden regression cases. | keep | Keep as regression source; align with Catalog V1. |

## 4. REMOVE / DEPRECATE / KEEP

### A. REMOVE

No source file was removed in this cleanup.

Reason:

- The candidate graph/matcher files still have active tests and an evaluation script.
- Removing them now would be a wider refactor than this phase requires.
- Generated `__pycache__` files are not tracked source files and were not treated as architecture code.

### B. DEPRECATE

Code-level deprecation markers were added to:

- `backend/app/agent/graph.py`
- `backend/app/agent/nodes/tool_matcher.py`

Catalog governance changes:

- `heat_equipment_assignment` changed from `enabled` to `planned`.
- `heat_batch_products` changed from `enabled` to `planned`.

Execution governance changes:

- `PlanExecutionAdapter` now refuses non-`enabled` capabilities before invoking the Tool function.
- `ToolRegistry` already refused non-`enabled` capabilities and remains the second guardrail.
- Matcher graph treats `blocked`, `planned`, and `experimental` capabilities as blocked/unavailable routes.

### C. KEEP

Current production path remains:

```text
POST /api/agent/run
-> AgentOrchestrator
-> DebuggablePlanner
-> ExecutionFeedbackLoop
-> PlanExecutionAdapter
-> ToolRegistry / TextToSqlNode
-> Trace / Analytics
```

Kept as production-critical:

- Orchestrator
- Planner V1, with legacy router responsibilities documented
- Execution Loop
- Tool Registry
- Real `heat_current_stage` Tool and repository
- Text-to-SQL controlled pipeline
- Trace and Analytics

## 5. Agent Entry Review

Current public Agent entry:

```text
POST /api/agent/run
```

Findings:

- No public `/api/agent/query` route exists.
- No public `/api/agent/plan` route exists.
- Tests assert both debug-style routes return 404.
- Analytics trace replay is under `/api/analytics/report/traces/{trace_id}` and is not an Agent execution entry.

Action:

```text
No API route removed.
```

## 6. Planner Legacy List

| Legacy Item | Current Role | Replacement Direction | Delete Now |
| --- | --- | --- | --- |
| `legacy_keyword_router` | `_tool_capability_name()` maps Chinese keyword groups to Tool names. | Capability Router using Catalog semantic triggers. | No |
| `legacy_regex_extractor` | `RECORD_NO_PATTERN` extracts `TRACE-*` and `HT*` IDs. | Semantic Understanding Layer argument extraction. | No |
| `legacy_sql_classifier` | `_is_sql_query()` uses keyword list for analytical SQL route. | Catalog route policy / analytical capability strategy. | No |
| `legacy_mixed_diagnostic_plan` | `_mixed_diagnostic_plan()` emits unregistered `production_status` and `quality_status`. | Cataloged diagnostic capabilities or blocked capability records. | No |
| `legacy_tool_label_map` | `_tool_label()` duplicates capability descriptions and expected outputs. | Generate plan labels from Capability Catalog metadata. | No |
| `legacy_replan_business_facts` | `_replan_from_observation()` checks QC/factory/missing facts. | Capability-aware failure policy. | No |

Reason for not deleting now:

- These branches still protect current tests from unsafe SQL fallback and unbounded execution.
- Capability Router V1 should replace them under golden regression protection.

## 7. Tool Governance

| Tool | Before | After | Reason |
| --- | --- | --- | --- |
| `heat_current_stage` | enabled / real | enabled / real | Repository-backed, SQL trace present. |
| `heat_equipment_assignment` | enabled / mock | planned / mock | Fixed fake equipment result must not be executable. |
| `heat_batch_products` | enabled / mock | planned / mock | Fixed fake product/lot result must not be executable. |
| `heat_param_submitted` | blocked | blocked | Still lacks stable business口径. |

Mock search result:

| File | Evidence | Action |
| --- | --- | --- |
| `backend/app/agent/tools/heat_treatment.py` | `mock-equipment-001`, `FURNACE-01`, fixed equipment name. | Marked capability `planned`; guarded execution. |
| `backend/app/agent/tools/heat_treatment.py` | Default `K2-T-FG`, `LOT-001`, `quantity=12`. | Marked capability `planned`; guarded execution. |

## 8. Capability Definition Duplication Report

| Source | Definition Type | Migration Need |
| --- | --- | --- |
| `backend/app/agent/catalog/heat_treatment.py` | Primary `CapabilitySpec`. | Keep as future source of truth. |
| `backend/app/agent/planner/planner.py` | Keywords, labels, route policy. | Move into Catalog Router. |
| `backend/app/agent/prompts/tool_matcher.py` | Prompt examples and status rules. | Generate from Catalog or retire with matcher graph. |
| `backend/tests/fixtures/heat_treatment_tool_match_cases.json` | Matcher expected routes/capabilities. | Merge or mark eval-only after Catalog Router V1. |
| `backend/tests/golden/*.json` | Regression behavior baseline. | Keep; update as Catalog status changes. |
| `backend/app/agent/text_to_sql/schema_provider.py` | SQL schema and status semantics. | Keep schema-specific; link semantics to Catalog later. |
| `backend/scripts/run_agent_os_v1_tests.py` | Agent OS behavior baseline. | Keep as smoke/integration acceptance. |
| `backend/scripts/run_agent_regression.py` | Golden runner and metrics. | Keep; align case groups with Catalog V1. |

## 9. Text-to-SQL Boundary Check

Current positioning is acceptable:

```text
Text-to-SQL = analytical / unknown structured query strategy
```

Guardrails observed:

- Status query examples route to `heat_current_stage`.
- Missing Tool parameter cases do not broaden to SQL.
- SQL Validator enforces read-only, whitelist tables/columns, and limit constraints.
- Existing tests verify Tool path does not execute Text-to-SQL.

No case was found where a fixed `heat_current_stage` status fact is intentionally replaced by SQL.

## 10. Execution Summary

Removed:

```text
none
```

Deprecated:

```text
backend/app/agent/graph.py
backend/app/agent/nodes/tool_matcher.py
```

Governed:

```text
heat_equipment_assignment: enabled -> planned
heat_batch_products: enabled -> planned
PlanExecutionAdapter refuses non-enabled capability execution
Matcher graph routes planned/experimental/blocked as unavailable
```

Kept:

```text
Orchestrator
Planner V1
Execution Loop
Tool Registry
Real heat_current_stage executor
Text-to-SQL controlled pipeline
Trace / Analytics
Golden tests
```

## 11. Status

Validation:

```text
cd backend && .venv/bin/python -m compileall app scripts
passed

cd backend && .venv/bin/pytest
122 passed, 159 warnings

cd backend && .venv/bin/python scripts/run_agent_os_v1_tests.py
15 passed, 0 failed, system_status=PASS

cd backend && .venv/bin/python scripts/run_agent_regression.py
23 passed, 0 failed, system_status=READY, agent_quality_score=0.9818
```

```text
SYSTEM STATUS: ARCHITECTURE_CLEANUP_COMPLETE
CAPABILITY_MIGRATION_PREPARED: true
NEXT_PHASE: Capability Catalog V1
```
