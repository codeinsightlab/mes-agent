# Agent Logging Observability V1

Date: 2026-07-10

## Goal

Add a standard Python logging layer for observing the full MES Agent execution path:

```text
User Input
-> Semantic Router
-> Planner
-> Capability Router
-> Capability Catalog
-> Execution
-> Tool / SQL
-> Trace / Analytics
```

This round only adds Observability. It does not add business capabilities, Tools, RAG, Memory, Multi Agent, or SQL logic.

## Logger Names

The logging layer uses Python standard `logging`.

Logger names:

- `agent`
- `agent.semantic_router`
- `agent.planner`
- `agent.capability_router`
- `agent.execution`
- `agent.sql`

SQL logging is isolated under `agent.sql`.

## Configuration

Default config file:

- `backend/logging.yaml`

Runtime initialization:

- `app.core.logging.configure_logging`

Environment controls:

```text
AGENT_LOG_LEVEL=INFO
AGENT_SQL_LOG_LEVEL=INFO
AGENT_LOG_FORMAT=json
```

Recommended local SQL debugging:

```text
AGENT_LOG_LEVEL=INFO
AGENT_SQL_LOG_LEVEL=DEBUG
AGENT_LOG_FORMAT=json
```

Production default:

```text
AGENT_LOG_LEVEL=INFO
AGENT_SQL_LOG_LEVEL=INFO
```

At `INFO`, SQL text is not emitted. SQL text is emitted only when `agent.sql` is set to `DEBUG`.

## Log Format

Default format is structured JSON.

Required fields:

- `time`
- `level`
- `logger`
- `trace_id`
- `event`

Example:

```json
{
  "time": "2026-07-10T10:00:01+00:00",
  "level": "INFO",
  "logger": "agent.execution",
  "trace_id": "abc123",
  "event": "tool.execute.start",
  "tool_name": "heat_current_stage",
  "capability_name": "heat_current_stage"
}
```

## Trace ID Propagation

`trace_id` is generated once per Agent request in `AgentOrchestrator.run`.

It is stored in a context variable and attached to every Agent logger record through:

- `set_trace_id`
- `reset_trace_id`
- `TraceIdFilter`
- `log_event`

The same `trace_id` appears in:

- Agent API response
- Execution trace
- Agent lifecycle logs
- Tool execution logs
- SQL debug logs

## Agent Lifecycle Events

Request lifecycle:

- `agent.request.start`
- `semantic_router.completed`
- `semantic_router.entities` at `DEBUG`
- `planner.completed`
- `planner.plan` at `DEBUG`
- `capability.matched`
- `capability.not_found` at `WARNING`
- `execution.started`
- `execution.completed`
- `tool.execute.start`
- `tool.execute.completed`
- `tool.execute.failed` at `ERROR`
- `agent.request.finished`
- `agent.request.failed` at `ERROR`

## SQL Logging

SQL logger:

- `agent.sql`

At `DEBUG`, SQL logs include:

- `event=sql.execute`
- `sql`
- `parameters`
- `duration_ms`
- `success`

At `INFO`, SQL text is not emitted.

Example DEBUG record:

```json
{
  "time": "2026-07-10T10:00:02+00:00",
  "level": "DEBUG",
  "logger": "agent.sql",
  "trace_id": "abc123",
  "event": "sql.execute",
  "sql": "SELECT record_no, status FROM mes_heat_treatment_record WHERE record_no = :record_no LIMIT 1",
  "parameters": {},
  "duration_ms": 3,
  "success": true
}
```

## Trace Field Alignment

The execution trace and logs now consistently expose:

- `capability_name`
- `tool_name`
- `execution_type`

For status query Tool execution:

- `capability_name=heat_current_stage`
- `tool_name=heat_current_stage`
- `execution_type=tool`

For read-only SQL execution:

- `capability_name=heat_completion_count_monthly`
- `tool_name=null`
- `execution_type=readonly_sql`

## Test Coverage

Added:

- `backend/tests/test_agent_logging.py`

Covered:

- Agent lifecycle events for `HT20260603-007热处理状态`
- Same-request `trace_id` consistency across Agent logs
- SQL text emitted when `agent.sql` is `DEBUG`
- SQL text not emitted when `agent.sql` is `INFO`

## Current Limitations

- Logs are console-oriented; file rotation is not configured yet.
- Logs are structured but not shipped to an external system.
- SQL parameters are currently captured from the Agent step arguments, not from DB-driver bind internals.
- Analytics persistence and logging are parallel observability channels; they are not yet correlated through a log aggregation backend.
