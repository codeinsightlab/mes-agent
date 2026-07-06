# Agent System Daily Report

Report date: {{ report_date }}

## 1. System Overview

- total_requests: {{ total_requests }}
- success_rate: {{ success_rate }}
- avg_latency: {{ avg_latency }}

## 2. Tool Usage

- most_used_tool: {{ most_used_tool }}
- tool_hit_rate: {{ tool_hit_rate }}

## 3. SQL Performance

- sql_success_rate: {{ sql_success_rate }}
- top_sql_errors:
{{ top_sql_errors }}

## 4. Failure Summary

- top_failure_types:
{{ top_failure_types }}
- root cause summary: {{ root_cause_summary }}

## 5. Replan Behavior

- replan_rate: {{ replan_rate }}
- avg_loop_depth: {{ avg_loop_depth }}
