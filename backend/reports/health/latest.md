# System Health Report

Report date: 2026-07-10

## Stability Metrics

- total_requests: 191
- success_rate: 0.5916
- avg_loop_depth: 1.4084
- tool_hit_rate: 0.5938
- sql_success_rate: 1.0
- planner_success_rate: 0.5969
- replan_rate: 0.4084
- failure_count: 78

## System Risk Level

- HIGH

## Degradation Signals

- loop instability: replan_rate above 20%
- rising failure patterns: missing_param, tool_miss
