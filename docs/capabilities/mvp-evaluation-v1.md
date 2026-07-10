# MES Agent MVP Evaluation V1

Date: 2026-07-10

## Goal

This round validates a minimal runnable MES Agent loop:

```text
User Input
-> Semantic Router
-> Planner
-> Capability Router
-> Capability Catalog
-> Execution
-> Trace / Analytics
```

The goal is not broad AI capability. The goal is to prove that natural language can be mapped to a small set of existing MES business capabilities in a traceable and repeatable way.

## Capability Catalog V2 Contract

Every MVP capability definition must include:

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

Capability Catalog remains the only source of executable capability boundaries. Semantic Router returns semantic intent only. Planner creates plans from semantics. Capability Router maps semantics to Catalog capabilities.

## Current Capability List

### heat_current_stage

- Status: `enabled`
- Catalog version: `v2`
- Domain: `heat_treatment`
- Intent: `query_status`
- Execution type: `tool`
- Executor: `heat_current_stage`
- Required input: `record_no`
- Optional input: `record_id`, `object_id`
- Output: `found`, `record_no`, `status`, `status_name`
- Data source: `mes_heat_treatment_record(record_no, status)`
- Boundary: single heat-treatment status queries must use this Tool path, not SQL.

### heat_completion_count_monthly

- Status: `enabled`
- Catalog version: `v2`
- Domain: `heat_treatment`
- Intent: `analyze_completion_count`
- Execution type: `readonly_sql`
- Executor: `text_to_sql`
- Required input: `question`
- Optional input: `time_range`
- Output: `rows`, `row_count`, `validated_sql`
- Data source: `mes_heat_treatment_record(status, finished_time)`
- Boundary: only read-only statistical analysis. It must not replace single-record status Tool queries.

### work_order_status

- Status: `planned`
- Catalog version: `v2`
- Domain: `production`
- Intent: `query_status`
- Execution type: `tool`
- Executor: `work_order_status`
- Required input: `work_order_no`
- Output contract: `found`, `work_order_no`, `status`
- Boundary: contract only in this MVP round. It is not executable until a real MES source and Tool are bound.

### inspection_status

- Status: `planned`
- Catalog version: `v2`
- Domain: `quality`
- Intent: `query_status`
- Execution type: `tool`
- Executor: `inspection_status`
- Required input: `inspection_no`
- Optional input: `lot_no`
- Output contract: `found`, `status`, optional `reject_reason`
- Boundary: contract only in this MVP round. It is not executable until a real MES source and Tool are bound.

## MVP Evaluation Entry

Stable batch entry:

```text
cd backend && .venv/bin/python scripts/run_agent_mvp_evaluation.py
```

Outputs:

- `backend/results/agent_mvp_evaluation_report.json`
- `backend/results/agent_mvp_evaluation_report.md`

The script uses the real Agent orchestration path and a deterministic in-process test repository / SQL node. It does not add new Tools or new business execution paths.

## MVP Test Coverage

Covered user inputs:

- `HT20260603-007热处理状态`
- `HT20260603-007这个热处理做到哪一步了`
- `HT20260603-007当前状态怎么样`
- `查一下热处理`
- `这个产品怎么样`
- `本月热处理完成多少批`

Validation checks:

- Semantic Router result
- Planner result
- Capability hit
- Routing source
- Legacy usage
- Execution type
- Final execution status
- Clarification behavior

## MVP Test Result

Latest result:

```json
{
  "total": 6,
  "passed": 6,
  "failed": 0,
  "success_rate": 1.0,
  "capability_hit_rate": 0.6666666666666666,
  "clarification_rate": 0.3333333333333333,
  "legacy_usage_rate": 0.0,
  "system_status": "PASS"
}
```

Interpretation:

- Four cases reached executable or cataloged capability decisions.
- Two cases correctly stopped for clarification.
- No MVP case depended on legacy fallback.

## Trace Fields

MVP traces now include:

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

These fields make each request answerable:

- What did the user ask?
- What did Semantic Router understand?
- What did Planner plan?
- Which Capability was selected?
- Was it selected from Catalog or legacy fallback?
- What execution type ran?
- Did it succeed?

## Failure Cases

Current MVP evaluation has no failing cases.

Known non-executable cases:

- `work_order_status` is `planned` and must not execute.
- `inspection_status` is `planned` and must not execute.

Known intentionally clarified cases:

- `查一下热处理`
- `这个产品怎么样`

## Current Limitations

- Only heat-treatment status query is backed by a real Tool.
- The SQL MVP capability is limited to the explicit heat-treatment monthly completion count intent.
- Production order and inspection capabilities are contracts only.
- Legacy fallback still exists for historical routes outside the MVP set.
- Semantic Router V1 is deterministic and rule-based; future LLM adapters must preserve the frozen result protocol.

## Next Round Suggestions

1. Bind `work_order_status` to one real read-only MES source and enable it only after contract tests pass.
2. Bind `inspection_status` to one real read-only MES source and keep ambiguous product questions in clarification.
3. Add more MVP samples from real user phrasing, then expand Catalog only when failure samples justify it.
4. Track legacy usage rate over repeated MVP runs before deleting legacy routing.
