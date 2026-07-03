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
