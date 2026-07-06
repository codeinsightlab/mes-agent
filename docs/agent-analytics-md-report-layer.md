# Agent Analytics MD Report Layer

## 2026-07-06 - Report Layer V1

### Objective

Add a Markdown report layer on top of the existing Agent OS analytics data:

```text
MySQL analytics tables
-> reusable metrics engine
-> Markdown report generator
-> human-readable reports
```

This round does not modify Planner, Execution Loop, Tool, SQL, Schema, Orchestrator, or the existing Agent API response structure.

### Data Boundary

The report layer reads only the following Agent analytics MySQL tables:

```text
agent_trace
agent_event
agent_metrics_snapshot
agent_failure
```

The generated Markdown files contain aggregate metrics, summaries, and conclusions. They do not store raw trace rows, event payloads, or raw failure records.

### Added Modules

```text
backend/app/analytics/report/models.py
backend/app/analytics/report/repository.py
backend/app/analytics/report/report_generator.py
backend/app/analytics/report/scheduler.py
backend/app/analytics/report/templates/daily_report.md.tpl
backend/app/analytics/report/templates/failure_report.md.tpl
backend/app/analytics/report/templates/system_health_report.md.tpl
backend/app/api/analytics_report.py
```

### Report Types

Daily report:

```text
backend/reports/daily/YYYY-MM-DD.md
```

Failure analysis report:

```text
backend/reports/failure/YYYY-MM-DD.md
```

System health report:

```text
backend/reports/health/latest.md
```

### API Trigger

```text
POST /api/analytics/report/generate
```

Request:

```json
{
  "type": "daily"
}
```

Supported values:

```text
daily
failure
health
```

Response:

```text
type
path
status
metrics
```

### Scheduler

`DailyReportScheduler` supports daily report generation at:

```text
00:10
```

It is controlled by:

```text
ANALYTICS_REPORT_SCHEDULER_ENABLED
```

The default is `false` to avoid local startup failures when the analytics tables are not available.

### Analytics Metrics

The shared metrics engine calculates:

- total request count
- success rate
- average latency
- tool usage
- tool hit rate
- SQL success rate
- SQL error patterns
- top failure types
- root cause summary
- replan rate
- average loop depth
- planner success rate
- system risk level
- degradation signals

### Idempotency

Reports are regenerated to deterministic paths:

- daily and failure reports are keyed by date
- health report always writes `latest.md`

Running the same report generation for the same date overwrites the same file path with the same aggregate content for the same MySQL data window.

### Validation

Automated tests cover:

- generating all three report types
- idempotent regeneration
- no raw trace id in generated Markdown
- API-triggered generation
- unknown report type validation
- scheduler next-run calculation for `00:10`

Validation command:

```text
cd backend && .venv/bin/pytest tests/test_analytics_report.py
```

Result:

```text
5 passed
```

Compile check:

```text
cd backend && .venv/bin/python -m compileall app
```

Result:

```text
passed
```

### Historical Limits Before Production Grounding

- Tests use a fake analytics repository and do not require a live MySQL database.
- This round does not create or migrate the analytics tables.
- The scheduler is implemented but disabled by default; enable it explicitly with `ANALYTICS_REPORT_SCHEDULER_ENABLED=true`.

## 2026-07-06 - Production Data Grounding V1

### Objective

Upgrade the analytics and report path from a fake/in-memory test harness to a MySQL-grounded data loop:

```text
Execution
-> Agent Event
-> MySQL trace/event/failure tables
-> SQL Analytics
-> Metrics Snapshot
-> Markdown Report
```

This update keeps Planner, Execution Loop, Tool Layer, SQL Generator, SQL Validator, SQL Executor, Orchestrator response schema, and frontend behavior unchanged.

### Added Production Tables

DDL is documented in:

```text
backend/app/analytics/schema.sql
```

Tables:

```text
agent_trace
agent_event
agent_failure
agent_metrics_snapshot
```

### Event Collector

Added:

```text
backend/app/analytics/event/collector.py
```

`AgentEventCollector` writes:

- `agent_event`
- `agent_trace`
- `agent_failure`

The Orchestrator accepts the collector as an optional dependency. When configured by `/api/agent/run`, every Agent run writes a trace and event stream to MySQL. The public `/api/agent/run` response structure is unchanged.

Required event families now recorded:

- `PLANNER_START`
- `PLANNER_END`
- `TOOL_MATCH`
- `TOOL_EXECUTE_SUCCESS`
- `TOOL_EXECUTE_FAIL`
- `SQL_GENERATE`
- `SQL_VALIDATE`
- `SQL_EXECUTE_SUCCESS`
- `SQL_EXECUTE_FAIL`
- `REPLAN_TRIGGER`
- `LOOP_START`
- `LOOP_END`

### SQL Analytics

Removed the Python in-memory metrics engine. `SqlAlchemyAnalyticsRepository` now calculates report metrics with SQL queries against MySQL tables.

Metrics include:

- total requests
- success rate
- average latency
- tool hit rate
- SQL success rate
- replan rate
- average loop depth
- planner success rate
- top failure types
- top SQL errors
- tool usage
- system risk level

### Metrics Snapshot

Added:

```text
backend/app/analytics/metrics/snapshot.py
```

`MetricsSnapshotService` computes metrics through SQL and writes `agent_metrics_snapshot`.

Supported scheduler interval:

```text
10 / 30 / 60 minutes
```

Config:

```text
ANALYTICS_METRICS_SNAPSHOT_ENABLED=false
ANALYTICS_METRICS_SNAPSHOT_INTERVAL_MINUTES=30
```

The scheduler is disabled by default for local development.

### Trace Replay

Added read-only replay endpoint:

```text
GET /api/analytics/report/traces/{trace_id}
```

It reads from `agent_trace` and returns:

```text
trace_id
user_query
plan_json
final_result
status
loop_depth
created_at
```

### Report Layer

Report generation still supports:

- `daily`
- `failure`
- `health`

The generator now uses:

```text
MySQL -> SQL aggregation -> Markdown render
```

No fake analytics repository is required for the production path.

### Validation

Automated tests now use a real SQLAlchemy engine with SQL tables named like production tables. They no longer use a fake analytics repository.

Validation command:

```text
cd backend && .venv/bin/pytest tests/test_agent_api.py tests/test_agent_orchestrator.py tests/test_analytics_report.py
```

Result:

```text
17 passed
```

Focused analytics tests:

```text
cd backend && .venv/bin/pytest tests/test_analytics_report.py
```

Result:

```text
9 passed
```

### Current Limits

- DDL is provided but not automatically applied by the application.
- Local automated tests use SQLite with production-shaped SQL tables; live MySQL validation depends on applying `backend/app/analytics/schema.sql` to the configured Agent metadata database.
