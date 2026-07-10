# Capability Router Migration V1

Date: 2026-07-10

## Scope

This migration introduces `CapabilityRouter V1` between Planner semantic intent and execution.

Implemented in this round:

- `CapabilityRouter`
- Catalog-based `SemanticIntent -> Capability` matching
- Catalog status guard before execution
- Execution plan adaptation for Tool execution
- Execution trace catalog metadata

Not implemented in this round:

- LLM semantic router
- Cache
- New Tool
- Text-to-SQL enhancement
- Full Planner rewrite
- ToolRegistry / Repository / SQL Executor changes

## Runtime Flow

```text
User Input
-> DebuggablePlanner
-> SemanticIntent
-> CapabilityRouter
-> CapabilityRuntimeRegistry
-> CapabilityDefinition
-> PlanExecutionAdapter
-> ToolRegistry
-> Tool / Repository / SQL
-> ExecutionObservation trace
```

## Added Modules

- `backend/app/agent/capability/router/models.py`
- `backend/app/agent/capability/router/matcher.py`
- `backend/app/agent/capability/router/router.py`
- `backend/app/agent/capability/router/__init__.py`

## Migrated

| Capability | Domain | Intent | Catalog Source | Execution |
| --- | --- | --- | --- | --- |
| `heat_current_stage` | `heat_treatment` | `query_status` | `backend/app/agent/capability/definitions/heat-treatment.yaml` | `tool -> heat_current_stage` |

Planner now emits a semantic tool step for this flow:

```json
{
  "type": "tool",
  "name": null,
  "semantic_domain": "heat_treatment",
  "semantic_intent": "query_status",
  "args": {
    "record_no": "HT20260603-007"
  }
}
```

The Router resolves it to:

```json
{
  "status": "matched",
  "capability": "heat_current_stage",
  "execution_type": "tool",
  "executor": "heat_current_stage",
  "capability_source": "catalog",
  "catalog_version": "v1"
}
```

## Not Migrated

| Item | Current Status | Reason |
| --- | --- | --- |
| `legacy_keyword_router` | Still exists in `DebuggablePlanner` | Still used to produce transitional semantic intent from user text. |
| Mixed diagnostic steps | Legacy direct `name` path | Capabilities such as `production_status` and `quality_status` are not cataloged. |
| SQL route classification | Still Planner-owned | This round does not add analytical capability routing. |
| Graph matcher path | Eval-only legacy path | Not part of production `/api/agent/run` routing. |

## Planned Or Missing Catalog Matches

Router does not guess when Catalog has no matching capability.

Current expected behavior:

| Semantic Intent | Result |
| --- | --- |
| `heat_treatment.query_status` | `heat_current_stage` |
| `heat_treatment.query_equipment` | `capability_not_found` |
| Planned catalog capability | `capability_not_executable` |

## Trace Contract

Successful catalog-routed Tool execution records:

```json
{
  "capability_source": "catalog",
  "capability_name": "heat_current_stage",
  "catalog_version": "v1",
  "tool_name": "heat_current_stage"
}
```

This metadata is present on both the step observation trace and the outer execution trace.

## Follow-up Deletion Candidates

Do not delete these in this round. Remove only after Semantic Router V1 and parity tests are in place.

- Planner direct capability mapping helpers:
  - `_tool_capability_name`
  - `_tool_semantic_intent`
  - `_tool_label`
- Planner SQL keyword routing:
  - `_is_sql_query`
- Planner mixed diagnostic hardcoding:
  - `_is_mixed_diagnostic_query`
  - `_mixed_diagnostic_plan`
- Legacy graph matcher prompt:
  - `backend/app/agent/prompts/tool_matcher.py`

## Verification

```text
cd backend && .venv/bin/python -m compileall app scripts
```

Result: passed.

```text
cd backend && .venv/bin/pytest
```

Result: `131 passed, 159 warnings`.

```text
cd backend && .venv/bin/python scripts/run_agent_os_v1_tests.py
```

Result: `15 passed`, `0 failed`, `SYSTEM STATUS = PASS`.

```text
cd backend && .venv/bin/python scripts/run_production_acceptance_v1.py
```

Result: `32 passed`, `0 failed`, `SYSTEM STATUS = READY`.

## Status

```text
SYSTEM STATUS: CAPABILITY_ROUTER_V1_COMPLETE
CATALOG_ROUTING: enabled
MIGRATED_CAPABILITIES: heat_current_stage
LEGACY_ROUTING: still_exists
NEXT_PHASE: Semantic Router V1
```
