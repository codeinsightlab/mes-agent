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
backend/app/analytics/report/metrics_engine.py
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

### Current Limits

- Tests use a fake analytics repository and do not require a live MySQL database.
- This round does not create or migrate the analytics tables.
- The scheduler is implemented but disabled by default; enable it explicitly with `ANALYTICS_REPORT_SCHEDULER_ENABLED=true`.
