# Semantic Router V1

Date: 2026-07-10

## Scope

Semantic Router V1 separates user semantic understanding from Planner-owned execution planning.

Implemented in this round:

- `SemanticRouterResult`
- `SemanticRouter`
- Semantic Router prompt contract
- Orchestrator entry flow: `User Input -> Semantic Router -> Planner`
- Planner consumption of `SemanticRouterResult`
- Execution trace field: `semantic_router_result`
- Tests for explicit status query, synonyms, ambiguity, and Chinese normalization

Not implemented in this round:

- Tool selection
- Capability selection
- SQL generation
- Business execution
- RAG
- Memory
- Multi-agent routing
- Automatic capability discovery

## Runtime Flow

```text
User Input
-> SemanticRouter
-> SemanticRouterResult
-> DebuggablePlanner
-> CapabilityRouter
-> Capability Catalog
-> Execution
```

Semantic Router owns only:

- user intent understanding
- business domain recognition
- entity extraction
- uncertainty / clarification judgment

It must not return:

- `tool_name`
- `capability_name`
- `sql`
- `executor`

## Output Contract

Example:

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

Frozen fields:

- `semantic_router_version`
- `domain`
- `intent`
- `entities`
- `confidence`
- `need_clarification`
- `clarification_reason`

Forbidden fields:

- `tool`
- `capability`
- `sql`
- `repository`
- `execution_action`
- `tool_name`
- `capability_name`
- `executor`

## Implemented Files

- `backend/app/agent/semantic_router/models.py`
- `backend/app/agent/semantic_router/router.py`
- `backend/app/agent/semantic_router/prompt/semantic_router.md`
- `backend/app/agent/semantic_router/__init__.py`
- `backend/app/agent/planner/legacy_fallback_router.py`
- `backend/tests/test_semantic_router.py`
- `backend/tests/golden/semantic_router/cases.json`

## Planner Responsibility Change

Planner now accepts `semantic_router_result` on `PlannerRequest`.

For migrated semantic results:

```text
heat_treatment.query_status
```

Planner creates a semantic tool step:

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

Planner does not choose Tool name or Capability name for this path. Capability Router still resolves the executable capability from Catalog.

For ambiguous heat-treatment input such as:

```text
这个热处理怎么样
```

Planner produces no execution step and preserves the clarification reason from Semantic Router.

## Legacy Routing Status

Legacy keyword routing still exists and was not deleted. It is isolated in:

- `backend/app/agent/planner/legacy_fallback_router.py`

Current legacy paths:

- `LegacyFallbackRouter.tool_capability_name`
- `LegacyFallbackRouter.is_sql_query`
- `LegacyFallbackRouter.is_mixed_diagnostic_query`
- replan branches based on missing facts

Reason:

- SQL analytical routing is not migrated to Semantic Router V1.
- Mixed diagnosis capabilities are not cataloged.
- The task explicitly required adding the new chain without deleting old Planner logic.

Legacy plans and steps are marked:

```json
{
  "routing_source": "legacy_fallback",
  "legacy": true
}
```

## Trace Contract

Execution trace now records:

```json
{
  "semantic_router_version": "v1",
  "routing_source": "semantic_router",
  "semantic_router_result": {
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
}
```

This appears in the execution trace wrapper and in the observation trace.

## Golden Coverage

Golden cases live in:

- `backend/tests/golden/semantic_router/cases.json`

Coverage:

- explicit heat-treatment status query with `record_no`
- synonym status expressions
- missing record number
- ambiguous heat-treatment expression
- unrelated weather question

## MVP Extension

Date: 2026-07-10

Semantic Router V1 now recognizes the MVP analytical intent:

```json
{
  "semantic_router_version": "v1",
  "domain": "heat_treatment",
  "intent": "analyze_completion_count",
  "entities": {
    "time_range": "current_month"
  },
  "confidence": 0.86,
  "need_clarification": false,
  "clarification_reason": null
}
```

This intent is routed through Capability Catalog V2 to:

- `heat_completion_count_monthly`

The Semantic Router still does not return Tool, Capability, SQL, Repository, or execution action fields.

MVP evaluation entry:

```text
cd backend && .venv/bin/python scripts/run_agent_mvp_evaluation.py
```

Detailed MVP record:

- `docs/capabilities/mvp-evaluation-v1.md`

## Verification

```text
cd backend && .venv/bin/python -m compileall app scripts
```

Result: passed.

```text
cd backend && .venv/bin/pytest
```

Result: `145 passed, 159 warnings`.

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
SYSTEM STATUS: SEMANTIC_ROUTER_V1_COMPLETE
SEMANTIC_ROUTING: enabled
SEMANTIC_ROUTER_VERSION: v1
MIGRATED_INTENTS: heat_treatment.query_status
LEGACY_KEYWORD_ROUTING: still_exists
LEGACY_FALLBACK_ROUTER: isolated
NEXT_PHASE: Semantic Router LLM Adapter or analytical intent migration
```
