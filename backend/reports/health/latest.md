# System Health Report

Report date: 2026-07-10

## Stability Metrics

- total_requests: 64
- success_rate: 0.5625
- avg_loop_depth: 1.4375
- tool_hit_rate: 0.561
- sql_success_rate: 1.0
- planner_success_rate: 0.5625
- replan_rate: 0.4375
- failure_count: 28

## System Risk Level

- HIGH

## Degradation Signals

- loop instability: replan_rate above 20%
- rising failure patterns: missing_param
