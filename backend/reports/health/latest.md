# System Health Report

Report date: 2026-07-10

## Stability Metrics

- total_requests: 120
- success_rate: 0.5833
- avg_loop_depth: 1.4167
- tool_hit_rate: 0.5696
- sql_success_rate: 1.0
- planner_success_rate: 0.5833
- replan_rate: 0.4167
- failure_count: 50

## System Risk Level

- HIGH

## Degradation Signals

- loop instability: replan_rate above 20%
- rising failure patterns: missing_param
