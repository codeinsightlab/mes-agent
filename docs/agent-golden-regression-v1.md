# Agent Golden Regression V1

## 2026-07-09 - Golden Test And Regression Runner

### Goal

This document records the V1 Agent Golden Test and Regression Test system for the MES Agent OS.

The goal is regression protection, not Agent capability expansion. This round did not change Planner core logic, Tool Catalog, Text-to-SQL generation strategy, Execution Loop, Orchestrator flow, or frontend code.

The regression suite answers these questions after future Prompt, Model, Tool Catalog, Planner, or SQL Schema changes:

- Can previous questions still be answered correctly?
- Did Tool routing regress?
- Did Text-to-SQL still produce valid business SQL?
- Did Planner produce abnormal plans or loop too deeply?
- Are failures still explainable and non-destructive?

### Files

Golden cases:

- `backend/tests/golden/tool_cases.json`
- `backend/tests/golden/sql_cases.json`
- `backend/tests/golden/planner_cases.json`
- `backend/tests/golden/failure_cases.json`
- `backend/tests/golden/mixed_cases.json`

Regression runner:

- `backend/scripts/run_agent_regression.py`

Regression result:

- `backend/results/agent_regression_report.json`

### Golden Case Format

Each case uses the same core shape:

```json
{
  "id": "heat_current_stage_001",
  "category": "tool",
  "question": "TRACE-HTR-K2-T-FG-001现在在哪一步",
  "expected": {
    "route": "tool",
    "capability": "heat_current_stage",
    "arguments": {
      "record_no": "TRACE-HTR-K2-T-FG-001"
    }
  },
  "validation": {
    "required_events": ["TOOL_MATCH", "TOOL_EXECUTE_SUCCESS"],
    "max_loop_depth": 1
  }
}
```

### Test Categories

Tool cases cover:

- `heat_current_stage`
- `heat_equipment_assignment`
- `heat_batch_products`

SQL cases cover:

- Monthly heat-treatment batch count by equipment.
- Recent 10 heat-treatment records.
- Specific-month completed heat-treatment count.
- Recent completed record detail.
- Recent three-month average processing duration by equipment.

Planner cases cover:

- Tool plan stability.
- SQL plan stability.
- Unknown input explainability.

Failure cases cover:

- Missing parameter.
- Unsupported route or capability gap.
- Unknown SQL column.
- Non-allowlisted SQL table.
- Unbounded SQL scan.

Mixed cases cover:

- Mixed diagnostic planning with current tool gap.
- SQL safety rejection.

### Metrics

The runner computes:

- `route_accuracy`: expected route matches actual route.
- `tool_accuracy`: expected capability matches actual Tool.
- `argument_accuracy`: expected Tool arguments match exactly.
- `sql_accuracy`: SQL golden cases pass all SQL assertions.
- `sql_success_rate`: SQL golden cases validate and execute successfully.
- `failure_accuracy`: expected failure type and source match.
- `agent_quality_score`: average of route, tool, argument, SQL, and failure accuracy.

### Version Snapshot

Each report records:

- `agent_version`
- `planner_version`
- `prompt_version`
- `sql_prompt_version`
- `tool_version`
- `schema_version`
- `model_name`
- `model_temperature`

V1 runner uses FastAPI `TestClient` against `/api/agent/run` and overrides only the Text-to-SQL node with deterministic SQL generation and deterministic non-empty rows. This avoids model and database instability while still verifying the API surface, Planner, execution loop, SQL validator, result normalization, and failure classification.

### Text-to-SQL Semantic Checks

The report includes five manual semantic SQL checks. Each records:

- Question.
- Manual SQL.
- Manual non-empty result.
- Agent SQL.
- Agent result.
- Consistency flag.

The current V1 semantic checks validate table, field, `WHERE`, `GROUP BY`, time range, `LIMIT`, and non-empty result consistency.

### Current Result

Latest command:

```text
cd backend && .venv/bin/python scripts/run_agent_regression.py
```

Latest result:

```text
SYSTEM STATUS: READY
total: 23
passed: 23
failed: 0
route_accuracy: 1.0
tool_accuracy: 1.0
argument_accuracy: 1.0
sql_accuracy: 1.0
sql_success_rate: 1.0
failure_accuracy: 0.8571
agent_quality_score: 0.9714
```

Coverage:

- Tool cases: 9
- Tool capabilities: 3
- SQL cases: 5
- Failure-classified cases: 7
- Planner cases: 3
- Mixed cases: 2

### Current Risks

- The user phrase `这个热处理做完了吗` is currently classified as `unknown` with explainable `missing_param`, not as a Tool partial. This was recorded as a current behavior boundary because this round does not modify Planner logic.
- The unsupported question `查询热处理工艺路线` is currently classified as Planner `missing_param`; the target failure type would be closer to `tool_miss` after a future route/catalog policy change.
- The phrase `HT001当前绑定的设备是什么` currently conflicts with product-binding wording. The stable V1 equipment case uses `HT001设备名称是什么`.
- The phrase `查询本周已完成热处理记录的记录号、设备和完成时间` does not trigger SQL in the current Planner. The stable V1 SQL semantic case uses `查询最近本周已完成热处理记录的记录号、设备和完成时间`.
- Regression V1 uses deterministic SQL execution rows. It verifies semantic consistency and non-empty result handling, but does not replace a future real MES read-only database acceptance run.

### Fix Record

2026-07-09:

- Added Golden case files under `backend/tests/golden/`.
- Added `backend/scripts/run_agent_regression.py`.
- Added deterministic non-empty SQL semantic checks.
- Added version snapshot recording.
- Added JSON report output at `backend/results/agent_regression_report.json`.

