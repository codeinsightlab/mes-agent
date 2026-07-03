# Agent Tool / Text-to-SQL Routing V1

## 2026-07-03 - LangGraph Skeleton And Heat Treatment Tool Matcher

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
