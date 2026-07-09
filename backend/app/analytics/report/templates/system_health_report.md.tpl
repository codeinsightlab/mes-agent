# System Health Report

Report date: {{ report_date }}

## Stability Metrics

- total_requests: {{ total_requests }}
- success_rate: {{ success_rate }}
- avg_loop_depth: {{ avg_loop_depth }}
- tool_hit_rate: {{ tool_hit_rate }}
- sql_success_rate: {{ sql_success_rate }}
- planner_success_rate: {{ planner_success_rate }}
- replan_rate: {{ replan_rate }}
- failure_count: {{ failure_count }}

## System Risk Level

- {{ system_risk_level }}

## Degradation Signals

{{ degradation_signals }}
