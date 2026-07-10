# Agent OS Architecture Consolidation V1

Date: 2026-07-09

## 1. Review Goal

This review freezes the current Agent OS architecture before the next phase: `Capability Catalog V1`.

The target direction is:

```text
MES Business Capability
-> Capability Catalog
-> Tool / SQL Capability
-> Agent Router
-> Execution
-> Trace / Analytics
```

This review did not add Agent capability, Tool capability, Planner strategy, business SQL, database schema, frontend behavior, or a new framework.

## 2. Current Architecture

Current public Agent entry:

```text
POST /api/agent/run
-> app.api.agent.get_orchestrator()
-> DebuggablePlanner
-> ExecutionFeedbackLoop
-> PlanExecutionAdapter
   |-> ToolRegistry
   |-> TextToSqlNode
-> ExecutionObservation
-> AgentEventCollector
-> agent_trace / agent_event / agent_failure
```

Current secondary graph/evaluation path:

```text
evaluate_heat_tool_matcher.py
-> LangChainToolMatcher
-> build_agent_graph()
-> tool_matcher / tool_executor / blocked / clarification / text_to_sql / result_builder nodes
```

The secondary graph path is not the production `/api/agent/run` entry. It is currently used by matcher evaluation and graph-focused tests.

## 3. Target Architecture

Target formal chain:

```text
User Input
-> Semantic Understanding Layer
-> Capability Router
-> Capability Catalog
-> Execution Strategy
   |-> Tool Capability
   |-> Text-to-SQL Capability
-> Observation
-> Trace / Analytics
```

Target responsibility split:

- Semantic Understanding Layer: understands user intent and extracts business objects/arguments.
- Capability Router: chooses a registered capability from the catalog.
- Capability Catalog: single source of business capability definitions, arguments, execution strategy, status, examples, and constraints.
- Planner: generates an execution plan from semantic/capability decisions; it should not own business keyword rules.
- Tool: executes deterministic business capability through repository/service and records trace.
- Text-to-SQL: handles analytical or unknown structured query capabilities only; it must not replace existing canonical Tools.
- Analytics/Trace: records route, Tool/SQL execution, observations, failure type, loop depth, and version metadata.

## 4. Difference Analysis

| Area | Current State | Target State | Gap |
| --- | --- | --- | --- |
| Agent entry | Only `/api/agent/run` is public for Agent OS. Tests assert `/api/agent/query` and `/api/agent/plan` return 404. | Keep single public Agent run entry. | Good. No API cleanup required now. |
| Planner | `DebuggablePlanner` performs route classification, keyword matching, record number extraction, Tool selection, and execution plan generation. | Planner consumes semantic/capability decision and emits plan steps. | Planner still contains legacy router and matcher logic. |
| Capability Catalog | `backend/app/agent/catalog/heat_treatment.py` defines `CapabilitySpec` for heat-treatment Tools. | Single source for capability metadata and routing constraints. | Capability metadata is duplicated in Planner labels, Tool matcher prompt, tests, and SQL schema semantics. |
| Tool execution | `heat_current_stage` is real and repository-backed. `heat_equipment_assignment` and `heat_batch_products` still return fixed mock data. | Every enabled Tool should be `Capability + Repository/Service + Execution + Trace`. | Two enabled Tools are still mock implementations. |
| Text-to-SQL | Runs for statistical/analytical route and has whitelist schema/provider/validator/executor. | Analytical or unknown structured query capability, not a default replacement for known Tool facts. | Planner currently enforces this for status Tool paths, but the rule lives in Planner rather than Catalog/Router. |
| Graph path | LangGraph-based `build_agent_graph()` and matcher prompt exist beside Orchestrator path. | One production orchestration path, optional eval-only experiments clearly labeled. | Graph path is transitional/eval-only but not marked as such in code. |
| Tests | Golden regression, graph tests, planner tests, and fixture matcher cases coexist. | Golden cases should become primary behavior baseline. | `tests/fixtures/heat_treatment_tool_match_cases.json` overlaps with golden Tool cases. |

## 5. Agent Entry Review

Observed files:

- `backend/app/api/agent.py`
- `backend/app/main.py`
- `backend/tests/test_agent_api.py`

Findings:

- `backend/app/api/agent.py` registers only `POST /api/agent/run`.
- `backend/tests/test_agent_api.py` asserts `/api/agent/query` and `/api/agent/plan` are not public entrypoints.
- Analytics trace replay is under `/api/analytics/report/traces/{trace_id}` and is not an Agent execution entry.

Conclusion:

```text
Agent entry status: clean
```

No delete/deprecate action is required for Agent API routes in this round.

## 6. Planner Status

Observed file:

- `backend/app/agent/planner/planner.py`

Current responsibilities:

- Builds execution plan.
- Classifies Tool / SQL / mixed / unknown.
- Extracts `record_no` using `RECORD_NO_PATTERN`.
- Maps Chinese keyword groups to Tool capability names.
- Hardcodes SQL intent keywords.
- Hardcodes mixed diagnostic plan with unregistered `production_status` and `quality_status` Tools.
- Performs limited replan based on `ExecutionObservation`.
- Generates debug reasons and risk assessments.

Legacy planner logic list:

| Location | Logic | Issue | Recommendation |
| --- | --- | --- | --- |
| `RECORD_NO_PATTERN` | Extracts `TRACE-*` and `HT*` identifiers. | Semantic extraction lives inside Planner. | Move to Semantic Understanding / Capability Router later. |
| `_tool_capability_name()` | Keyword matching maps status/device/product phrases to capability names. | Duplicates Catalog `applicable_when` and Tool matcher prompt examples. | Mark legacy; replace with Catalog-driven router. |
| `_tool_label()` | Hardcoded goal/query_goal/reason/expected_output per Tool. | Duplicates capability metadata and result schemas. | Generate from Capability Catalog. |
| `_is_sql_query()` | Keywords such as `统计`, `每台`, `平均`, `最近`, `多少`, `排行`. | Text-to-SQL routing policy is embedded in Planner. | Move to Capability Router strategy rules. |
| `_is_mixed_diagnostic_query()` | Detects `为什么...不能入库`. | Business diagnosis intent hardcoded and outside Catalog. | Convert to blocked or planned capability once cataloged. |
| `_mixed_diagnostic_plan()` | Plans `production_status` and `quality_status`, neither registered. | Planner can produce unregistered capability names. | Deprecate after Capability Catalog V1 or mark as experimental. |
| `_replan_from_observation()` | Branches on `QC/quality/质检`, `factory/工厂`, and missing facts. | Replan policy has business-specific facts. | Keep temporarily; move to capability-aware failure policy later. |

Conclusion:

```text
Planner status: functional but legacy-heavy
```

The Planner should be treated as a V1 transitional router/planner until `Capability Router + Catalog V1` replaces keyword ownership.

## 7. Tool Layer Status

Observed files:

- `backend/app/agent/tools/heat_treatment.py`
- `backend/app/agent/tools/registry.py`
- `backend/app/agent/tools/repository/heat_treatment_repository.py`

| Tool | Catalog Status | Execution Status | Trace Status | Notes |
| --- | --- | --- | --- | --- |
| `heat_current_stage` | enabled | real | SQL trace present | Uses `HeatTreatmentRepository`, fixed readonly SQL, `mes_heat_treatment_record`. |
| `heat_equipment_assignment` | enabled | mock | no SQL trace | Returns `mock-equipment-001`, `FURNACE-01`, and fixed equipment name. |
| `heat_batch_products` | enabled | mock | no SQL trace | Returns fixed/default item, lot, and quantity. |
| `heat_param_submitted` | blocked | not executable | n/a | Correctly marked blocked because business口径 is not stable. |

Mock / fixed business result findings:

| File | Function | Evidence | Recommendation |
| --- | --- | --- | --- |
| `backend/app/agent/tools/heat_treatment.py` | `heat_equipment_assignment` | Returns fixed `equipment_id`, `equipment_code`, `equipment_name`. | Deprecate mock implementation; keep Catalog enabled only if acceptance tests tolerate mock, otherwise mark Catalog blocked before real repository work. |
| `backend/app/agent/tools/heat_treatment.py` | `heat_batch_products` | Returns fixed/default `item_code`, `lot_code`, `quantity=12`. | Deprecate mock implementation; replace with repository-backed Tool in a dedicated phase. |

Conclusion:

```text
Tool layer status: partially real
```

`heat_current_stage` matches the target shape. The other enabled heat-treatment Tools do not.

## 8. Capability Catalog Consolidation

Primary catalog:

- `backend/app/agent/catalog/heat_treatment.py`

Other capability definition or duplication sources:

| Source | What It Defines | Duplication Risk | Recommendation |
| --- | --- | --- | --- |
| `backend/app/agent/catalog/heat_treatment.py` | Capability name, status, arguments, examples, result schema. | Intended primary source. | Keep and expand into Catalog V1. |
| `backend/app/agent/planner/planner.py` | Keyword-to-capability mapping and Tool labels. | High. | Move ownership to Catalog Router. |
| `backend/app/agent/prompts/tool_matcher.py` | Capability examples and fallback route instructions. | High. | Generate prompt content from Catalog or retire with graph path. |
| `backend/tests/fixtures/heat_treatment_tool_match_cases.json` | Matcher route/capability cases. | Medium, overlaps golden cases. | Merge into golden regression or keep eval-only with clear label. |
| `backend/tests/golden/*.json` | Golden behavior contracts. | Intended regression source. | Keep; should become primary behavior baseline. |
| `backend/app/agent/text_to_sql/schema_provider.py` | SQL schema, status semantics, business rules. | Medium; status semantics overlap Catalog `HEAT_STATUS_NAMES`. | Keep as SQL schema package, but link to Catalog semantic source later. |
| `backend/scripts/run_agent_os_v1_tests.py` | Deterministic expected Tool/SQL outcomes. | Medium. | Keep as acceptance runner, but source cases from golden catalog long-term. |
| `backend/scripts/run_agent_regression.py` | Regression case validation and metrics. | Intended test runner. | Keep; align case loading with Catalog V1 metadata later. |

Conclusion:

```text
Capability source status: multiple definitions exist
```

## 9. Capability Runtime V1

Capability Runtime V1 adds a machine-readable runtime source beside the existing legacy Python catalog.

Runtime chain:

```text
backend/app/agent/capability/definitions/*.yaml
-> CapabilityLoader
-> CapabilityValidator
-> CapabilityRuntimeRegistry
```

New files:

- `backend/app/agent/capability/models.py`
- `backend/app/agent/capability/loader.py`
- `backend/app/agent/capability/validator.py`
- `backend/app/agent/capability/registry.py`
- `backend/app/agent/capability/definitions/heat-treatment.yaml`

Schema fields:

| Field | Purpose |
| --- | --- |
| `name` | Stable capability name, for example `heat_current_stage`. |
| `domain` | Business domain, for example `heat_treatment`. |
| `description` | Human-readable business description. |
| `intent` | User intent phrases used later by router migration. |
| `status` | Lifecycle state: `enabled`, `planned`, `experimental`, `blocked`, `disabled`. |
| `execution_type` | Runtime execution strategy: `tool`, `readonly_sql`, `action`, or `reference`. |
| `executor` | Registered executor name. For V1, `heat_current_stage` maps to the existing Tool executor. |
| `input_schema` | Required/optional input fields and machine-readable properties. |
| `output_schema` | Required output fields and properties. |
| `data_sources` | Tables or external sources used by the capability. |
| `examples` | Example user questions. |
| `boundaries` | Explicit non-responsibilities. |
| `legacy_source` | Migration marker, currently `old python constant` for migrated legacy capability. |

Validation behavior:

- Invalid YAML fails startup/loading with `CapabilityCatalogLoadError`.
- Missing required schema fields fail loading through Pydantic validation.
- Duplicate capability names fail validation.
- Unknown tool executor names fail validation.
- `planned`, `blocked`, `disabled`, and `experimental` capabilities may be loaded, but `CapabilityRuntimeRegistry.require_executable()` rejects them unless status is `enabled`.

Migration status:

| Capability | Runtime source | Executor | Legacy source |
| --- | --- | --- | --- |
| `heat_current_stage` | `definitions/heat-treatment.yaml` | `heat_current_stage` | `old python constant` |

The old Python catalog still exists:

- `backend/app/agent/catalog/heat_treatment.py`

It remains the production source for current Planner / ToolRegistry behavior until `Capability Router Migration`.

Next migration step:

```text
Capability Runtime Registry
-> Capability Router
-> Planner / ToolRegistry adapter
```

Catalog V1 should make `CapabilitySpec` the only source of capability identity, status, argument requirements, examples, execution strategy, and route constraints.

## 9. Text-to-SQL Positioning

Observed files:

- `backend/app/agent/nodes/text_to_sql.py`
- `backend/app/agent/text_to_sql/generator.py`
- `backend/app/agent/text_to_sql/schema_provider.py`
- `backend/app/agent/text_to_sql/validator.py`
- `backend/app/agent/text_to_sql/executor.py`

Current behavior:

- `TextToSqlNode` loads a fixed heat-treatment schema package.
- `TextToSqlGenerator` produces candidate SQL only.
- `SqlValidator` validates against whitelist tables and columns.
- `ReadonlySqlExecutor` executes read-only SQL.
- Planner prevents status Tool paths from falling back to SQL when a Tool argument is missing.

Positioning decision:

```text
Text-to-SQL is an analytical / unknown structured query execution strategy.
It is not the default route for existing Tool capabilities.
```

Examples:

- `TRACE-HTR-K2-T-FG-001状态` must use `heat_current_stage`.
- `统计本月每台热处理设备处理了多少批次` may use Text-to-SQL until a first-class analytical capability exists.
- Missing Tool parameter cases must fail explainably or ask for clarification; they must not broaden to SQL.

## 10. Candidate Removal / Deprecation List

No code was deleted in this review. The following are candidates for the next cleanup phase.

| File | Role | Why Candidate | Recommendation |
| --- | --- | --- | --- |
| `backend/app/agent/graph.py` | LangGraph-style route graph. | Not used by `/api/agent/run`; parallel orchestration path. | Deprecated/eval-only until Capability Router V1 decides whether to keep it. |
| `backend/app/agent/nodes/tool_matcher.py` | LLM Tool matcher node. | Parallel semantic router beside `DebuggablePlanner`. | Deprecated/eval-only or refactor into Semantic Understanding Layer. |
| `backend/app/agent/nodes/tool_executor.py` | Graph Tool executor node. | Duplicates `PlanExecutionAdapter` Tool execution path. | Deprecated if graph path is retired. |
| `backend/app/agent/nodes/blocked_capability.py` | Graph blocked capability node. | Graph-only handling, not production Orchestrator path. | Deprecated if graph path is retired. |
| `backend/app/agent/nodes/clarification.py` | Graph clarification node. | Graph-only handling. | Deprecated if graph path is retired. |
| `backend/app/agent/nodes/result_builder.py` | Graph final result builder. | Produces schema different from `/api/agent/run`. | Deprecated if graph path is retired. |
| `backend/app/agent/state.py` | Graph state TypedDict. | Supports graph path only. | Deprecated if graph path is retired. |
| `backend/app/agent/prompts/tool_matcher.py` | Hardcoded matcher prompt. | Duplicates Catalog capability examples and route rules. | Replace with Catalog-generated prompt or remove with graph path. |
| `backend/scripts/evaluate_heat_tool_matcher.py` | Matcher evaluation runner. | Depends on graph/matcher path, not production route. | Keep as eval-only until Catalog Router evaluation exists. |
| `backend/tests/fixtures/heat_treatment_tool_match_cases.json` | Legacy matcher fixture cases. | Overlaps `backend/tests/golden/tool_cases.json`. | Merge into golden cases after Catalog Router V1. |
| `backend/app/agent/planner/planner.py` keyword helper functions | Transitional router logic. | Planner owns semantic matching and business keywords. | Keep now; mark legacy; replace with Semantic Understanding + Capability Router. |
| `backend/app/agent/tools/heat_treatment.py` mock Tool functions | Fixed business results for two enabled Tools. | Enabled Tools can return non-MES facts. | Replace with repositories or mark blocked in a scoped phase. |
| `backend/**/__pycache__/` | Generated Python bytecode artifacts. | Not source code; noisy in review. | Remove from working tree and ignore if tracked/unignored. |

## 11. Next Phase Recommendation

Recommended next phase:

```text
Capability Catalog V1
```

Suggested minimum scope:

1. Extend `CapabilitySpec` to include `execution_strategy`: `tool`, `text_to_sql`, `blocked`, or `external`.
2. Add explicit `semantic_triggers`, `argument_extractors`, and `route_policy`.
3. Generate Tool matcher prompt content from the Catalog instead of hardcoding examples.
4. Move Planner keyword matching into a `CapabilityRouter`.
5. Make Planner accept a semantic/capability result and only generate execution steps.
6. Mark graph/matcher path as eval-only or retire it after parity tests pass.
7. Decide whether enabled mock Tools should become blocked until repository-backed implementations exist.

## 12. Current Assessment

```text
SYSTEM STATUS: ARCHITECTURE_REVIEW_COMPLETE

CURRENT_ARCHITECTURE:
Single public Agent run API with Orchestrator + Planner + Execution Loop. Capability Catalog exists, but Planner and matcher prompt still duplicate routing semantics.

TARGET_ARCHITECTURE:
MES Capability Driven Agent with Catalog-owned capability definitions, Capability Router-owned selection, Planner-owned execution plan generation, and Tool/SQL strategies selected from Catalog metadata.

LEGACY_ITEMS:
Planner keyword router, graph/matcher parallel path, hardcoded matcher prompt, enabled mock Tools, duplicated fixture/golden cases, generated __pycache__ artifacts.

NEXT_PHASE:
Capability Catalog V1
```

## 13. Capability Router Migration V1

Date: 2026-07-10

Capability Router V1 has been added as the first production migration from Planner-owned Tool selection toward Catalog-owned capability routing.

New runtime chain:

```text
DebuggablePlanner
-> SemanticIntent
-> CapabilityRouter
-> CapabilityRuntimeRegistry
-> CapabilityDefinition
-> PlanExecutionAdapter
-> ToolRegistry / TextToSqlNode
```

Migrated capability:

| Capability | Domain | Intent | Execution |
| --- | --- | --- | --- |
| `heat_current_stage` | `heat_treatment` | `query_status` | `tool -> heat_current_stage` |

Key changes:

- Planner Tool steps for migrated heat-treatment status queries now carry `semantic_domain` and `semantic_intent`.
- Planner no longer places `heat_current_stage` in `PlanStep.name` for the migrated path.
- `CapabilityRouter` resolves `heat_treatment.query_status` from the YAML Catalog.
- Router returns `capability_not_found` for uncataloged intents such as `heat_treatment.query_equipment`.
- Router returns `capability_not_executable` when a matching Catalog capability is not `enabled`.
- Execution trace now records `capability_source`, `capability_name`, and `catalog_version`.

Still legacy:

- Planner keyword detection still exists as the temporary Semantic Intent producer.
- SQL route classification still lives in Planner.
- Mixed diagnostic direct Tool names still exist for legacy behavior.
- Graph matcher path remains eval-only / legacy.

Detailed migration note:

- `docs/capabilities/router-migration-v1.md`

Validation snapshot:

```text
compileall app scripts: passed
pytest: 131 passed, 159 warnings
run_agent_os_v1_tests.py: 15 passed, 0 failed, SYSTEM STATUS = PASS
run_production_acceptance_v1.py: 32 passed, 0 failed, SYSTEM STATUS = READY
```

```text
SYSTEM STATUS: CAPABILITY_ROUTER_V1_COMPLETE
CATALOG_ROUTING: enabled
MIGRATED_CAPABILITIES: heat_current_stage
LEGACY_ROUTING: still_exists
NEXT_PHASE: Semantic Router V1
```

## 14. Semantic Router V1

Date: 2026-07-10

Semantic Router V1 has been added before Planner to separate user semantic understanding from execution planning.

New runtime chain:

```text
User Input
-> SemanticRouter
-> SemanticRouterResult
-> DebuggablePlanner
-> CapabilityRouter
-> Capability Catalog
-> Execution
```

Semantic Router responsibilities:

- understand user intent
- identify business domain
- extract entities
- judge uncertainty and clarification need

Explicit non-responsibilities:

- Tool selection
- Capability selection
- SQL generation
- business execution
- database access

Migrated semantic intent:

| Domain | Intent | Entities | Downstream |
| --- | --- | --- | --- |
| `heat_treatment` | `query_status` | `record_no` when present | Planner semantic step -> Capability Router |

Planner change:

- `PlannerRequest` now accepts `semantic_router_result`.
- Planner uses `SemanticRouterResult` for `heat_treatment.query_status`.
- Planner no longer places a Tool name in `PlanStep.name` for this migrated semantic path.
- Ambiguous heat-treatment questions such as `这个热处理怎么样` produce no execution step.

Trace change:

- `execution_trace[].semantic_router_result` records `domain`, `intent`, `entities`, `confidence`, and `need_clarification`.

Legacy status:

- Keyword routing still exists as fallback.
- SQL route classification remains Planner-owned.
- Mixed diagnostic planning remains legacy.
- Replan branches still inspect missing facts.

Detailed migration note:

- `docs/capabilities/semantic-router-v1.md`

Validation snapshot:

```text
compileall app scripts: passed
pytest: 137 passed, 159 warnings
run_agent_os_v1_tests.py: 15 passed, 0 failed, SYSTEM STATUS = PASS
run_production_acceptance_v1.py: 32 passed, 0 failed, SYSTEM STATUS = READY
```

```text
SYSTEM STATUS: SEMANTIC_ROUTER_V1_COMPLETE
SEMANTIC_ROUTING: enabled
MIGRATED_INTENTS: heat_treatment.query_status
LEGACY_KEYWORD_ROUTING: still_exists
NEXT_PHASE: Semantic Router LLM Adapter or analytical intent migration
```

## 15. Semantic Router V1 Protocol Freeze And Legacy Fallback Isolation

Date: 2026-07-10

Semantic Router V1 protocol is now fixed with explicit version metadata.

Frozen output protocol:

```json
{
  "semantic_router_version": "v1",
  "domain": "heat_treatment",
  "intent": "query_status",
  "entities": {
    "record_no": "HT20260603-007"
  },
  "confidence": 0.95,
  "need_clarification": false,
  "clarification_reason": null
}
```

Semantic Router remains forbidden from outputting Tool, Capability, SQL, Repository, or execution action fields.

Legacy fallback position:

```text
Planner
-> SemanticRouterResult handling

LegacyFallbackRouter
-> historical keyword / regex fallback
```

Legacy fallback implementation:

- `backend/app/agent/planner/legacy_fallback_router.py`

Legacy plans are marked with:

```json
{
  "routing_source": "legacy_fallback",
  "legacy": true
}
```

Trace fields:

- `semantic_router_version`
- `semantic_router_result`
- `routing_source`

Routing source values:

- `semantic_router`
- `legacy_fallback`

Semantic Router golden tests:

- `backend/tests/golden/semantic_router/cases.json`

Coverage:

- explicit heat-treatment status query
- synonym normalization
- missing `record_no`
- ambiguous heat-treatment question
- unrelated question

Validation snapshot:

```text
compileall app scripts: passed
pytest: 145 passed, 159 warnings
run_agent_os_v1_tests.py: 15 passed, 0 failed, SYSTEM STATUS = PASS
run_production_acceptance_v1.py: 32 passed, 0 failed, SYSTEM STATUS = READY
```

Current risks:

- Analytical SQL routing still depends on legacy fallback.
- Mixed diagnostic planning still depends on legacy fallback and uncataloged names.
- Replan policy still contains missing-fact business branches.
- Semantic Router V1 is deterministic; future LLM adapter must preserve the frozen output protocol.

## 16. Capability Catalog V2 And MVP Evaluation

Date: 2026-07-10

The project has entered the first MVP experiment stage.

Validated MVP flow:

```text
User Input
-> Semantic Router
-> Planner
-> Capability Router
-> Capability Catalog
-> Execution
-> Trace / Analytics
```

Capability Catalog V2 contract now standardizes:

- `name`
- `catalog_version`
- `domain`
- `intent`
- `description`
- `required_entities`
- `execution_type`
- `input_schema`
- `output_schema`
- `trace_fields`
- `example_queries`

Current MVP capabilities:

- `heat_current_stage`: enabled Tool capability for heat-treatment status.
- `heat_completion_count_monthly`: enabled read-only SQL capability for monthly heat-treatment completion count.
- `work_order_status`: planned production-order status contract, not executable.
- `inspection_status`: planned inspection-status contract, not executable.

Catalog remains the only source of capability boundaries. Planner and Semantic Router do not define executable capability names.

Legacy fallback status:

- `LegacyFallbackRouter` still exists.
- MVP evaluation cases do not depend on legacy fallback.
- Trace records `legacy_used=true/false` for future migration metrics.

Trace fields added or confirmed for the MVP:

- `user_input`
- `semantic_router_version`
- `semantic_router_result`
- `plan`
- `capability_name`
- `capability_source`
- `catalog_version`
- `routing_source`
- `legacy_used`
- `execution_type`
- `success`
- `error_reason`

Stable MVP evaluation entry:

```text
cd backend && .venv/bin/python scripts/run_agent_mvp_evaluation.py
```

Latest MVP result:

```text
total=6
passed=6
failed=0
success_rate=1.00
capability_hit_rate=0.67
clarification_rate=0.33
legacy_usage_rate=0.00
system_status=PASS
```

Detailed record:

- `docs/capabilities/mvp-evaluation-v1.md`
- `backend/results/agent_mvp_evaluation_report.json`
- `backend/results/agent_mvp_evaluation_report.md`
