# MES Agent MVP Evaluation

## Summary

- Total: 6
- Passed: 6
- Failed: 0
- Success rate: 1.00
- Capability hit rate: 0.67
- Clarification rate: 0.33
- Legacy usage rate: 0.00
- System status: PASS

## Cases

### explicit_heat_status

- Input: HT20260603-007热处理状态
- Passed: True
- Capability: heat_current_stage
- Routing source: semantic_router
- Execution type: tool
- Final status: success
- Error reason: None

### synonym_heat_step

- Input: HT20260603-007这个热处理做到哪一步了
- Passed: True
- Capability: heat_current_stage
- Routing source: semantic_router
- Execution type: tool
- Final status: success
- Error reason: None

### synonym_current_status

- Input: HT20260603-007当前状态怎么样
- Passed: True
- Capability: heat_current_stage
- Routing source: semantic_router
- Execution type: tool
- Final status: success
- Error reason: None

### missing_heat_target

- Input: 查一下热处理
- Passed: True
- Capability: None
- Routing source: semantic_router
- Execution type: None
- Final status: failed
- Error reason: plan.steps

### ambiguous_product_question

- Input: 这个产品怎么样
- Passed: True
- Capability: None
- Routing source: semantic_router
- Execution type: None
- Final status: failed
- Error reason: plan.steps

### heat_completion_count

- Input: 本月热处理完成多少批
- Passed: True
- Capability: heat_completion_count_monthly
- Routing source: semantic_router
- Execution type: readonly_sql
- Final status: success
- Error reason: None
