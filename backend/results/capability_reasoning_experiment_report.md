# Capability Reasoning Experiment V1

## Summary

- Total: 30
- Top1 capability accuracy: 1.00
- Top3 candidate coverage: 1.00
- Catalog-only top1 accuracy: 0.73
- Business-facts top1 accuracy: 1.00
- Business-facts lift: 0.27
- Failed: 0
- System status: PASS
- Audit DB: /Users/user/Documents/mes-agent/backend/results/capability_reasoning_audit.sqlite

## Cases

### status_001

- Input: TRACE-HTR-B-H-001什么状态
- Expected: heat_current_stage
- Selected: heat_current_stage
- Context: catalog_only
- Confidence: 0.93
- Validation: matched
- Top1 pass: True

### status_002

- Input: TRACE-HTR-B-H-002热处理状态
- Expected: heat_current_stage
- Selected: heat_current_stage
- Context: catalog_only
- Confidence: 0.93
- Validation: matched
- Top1 pass: True

### status_003

- Input: TRACE-HTR-B-H-003做到哪一步了
- Expected: heat_current_stage
- Selected: heat_current_stage
- Context: catalog_only
- Confidence: 0.93
- Validation: matched
- Top1 pass: True

### status_004

- Input: TRACE-HTR-B-H-004做完了吗
- Expected: heat_current_stage
- Selected: heat_current_stage
- Context: catalog_only
- Confidence: 0.93
- Validation: matched
- Top1 pass: True

### status_005

- Input: TRACE-HTR-B-H-005当前情况
- Expected: heat_current_stage
- Selected: heat_current_stage
- Context: catalog_with_business_facts
- Confidence: 0.87
- Validation: matched
- Top1 pass: True

### status_006

- Input: HT20260603-007热处理的状态
- Expected: heat_current_stage
- Selected: heat_current_stage
- Context: catalog_only
- Confidence: 0.93
- Validation: matched
- Top1 pass: True

### status_007

- Input: HT20260603-008现在到哪了
- Expected: heat_current_stage
- Selected: heat_current_stage
- Context: catalog_with_business_facts
- Confidence: 0.87
- Validation: matched
- Top1 pass: True

### status_008

- Input: 查TRACE-HTR-B-H-008进度
- Expected: heat_current_stage
- Selected: heat_current_stage
- Context: catalog_with_business_facts
- Confidence: 0.87
- Validation: matched
- Top1 pass: True

### status_009

- Input: TRACE-HTR-B-H-009完成了吗
- Expected: heat_current_stage
- Selected: heat_current_stage
- Context: catalog_only
- Confidence: 0.93
- Validation: matched
- Top1 pass: True

### status_010

- Input: TRACE-HTR-B-H-010目前哪一步
- Expected: heat_current_stage
- Selected: heat_current_stage
- Context: catalog_only
- Confidence: 0.93
- Validation: matched
- Top1 pass: True

### device_001

- Input: TRACE-HTR-B-H-001在哪个设备进行
- Expected: heat_device_trace
- Selected: heat_device_trace
- Context: catalog_only
- Confidence: 0.9
- Validation: capability_not_executable
- Top1 pass: True

### device_002

- Input: TRACE-HTR-B-H-002在哪个炉子完成
- Expected: heat_device_trace
- Selected: heat_device_trace
- Context: catalog_with_business_facts
- Confidence: 0.88
- Validation: capability_not_executable
- Top1 pass: True

### device_003

- Input: TRACE-HTR-B-H-003哪台炉做的
- Expected: heat_device_trace
- Selected: heat_device_trace
- Context: catalog_with_business_facts
- Confidence: 0.88
- Validation: capability_not_executable
- Top1 pass: True

### device_004

- Input: TRACE-HTR-B-H-004生产设备是什么
- Expected: heat_device_trace
- Selected: heat_device_trace
- Context: catalog_only
- Confidence: 0.9
- Validation: capability_not_executable
- Top1 pass: True

### device_005

- Input: TRACE-HTR-B-H-005用的哪个炉
- Expected: heat_device_trace
- Selected: heat_device_trace
- Context: catalog_with_business_facts
- Confidence: 0.88
- Validation: capability_not_executable
- Top1 pass: True

### device_006

- Input: 这个热处理在哪个设备 TRACE-HTR-B-H-006
- Expected: heat_device_trace
- Selected: heat_device_trace
- Context: catalog_only
- Confidence: 0.9
- Validation: capability_not_executable
- Top1 pass: True

### device_007

- Input: TRACE-HTR-B-H-007设备追溯
- Expected: heat_device_trace
- Selected: heat_device_trace
- Context: catalog_only
- Confidence: 0.9
- Validation: capability_not_executable
- Top1 pass: True

### device_008

- Input: TRACE-HTR-B-H-008在哪完成
- Expected: heat_device_trace
- Selected: heat_device_trace
- Context: catalog_with_business_facts
- Confidence: 0.88
- Validation: capability_not_executable
- Top1 pass: True

### analysis_001

- Input: 本月热处理完成多少批
- Expected: heat_completion_count_monthly
- Selected: heat_completion_count_monthly
- Context: catalog_only
- Confidence: 0.92
- Validation: matched
- Top1 pass: True

### analysis_002

- Input: 统计本月热处理完成数量
- Expected: heat_completion_count_monthly
- Selected: heat_completion_count_monthly
- Context: catalog_only
- Confidence: 0.92
- Validation: matched
- Top1 pass: True

### analysis_003

- Input: 这个月热处理完成多少批次
- Expected: heat_completion_count_monthly
- Selected: heat_completion_count_monthly
- Context: catalog_only
- Confidence: 0.92
- Validation: matched
- Top1 pass: True

### analysis_004

- Input: 热处理本月完成数量是多少
- Expected: heat_completion_count_monthly
- Selected: heat_completion_count_monthly
- Context: catalog_only
- Confidence: 0.92
- Validation: matched
- Top1 pass: True

### analysis_005

- Input: 帮我统计热处理完成多少批
- Expected: heat_completion_count_monthly
- Selected: heat_completion_count_monthly
- Context: catalog_only
- Confidence: 0.92
- Validation: missing_required_entities
- Top1 pass: True

### ambiguous_001

- Input: 这个热处理怎么样
- Expected: None
- Selected: None
- Context: catalog_with_business_facts
- Confidence: 0.0
- Validation: need_clarification
- Top1 pass: True

### ambiguous_002

- Input: 这个产品怎么样
- Expected: None
- Selected: None
- Context: catalog_with_business_facts
- Confidence: 0.0
- Validation: need_clarification
- Top1 pass: True

### missing_001

- Input: 查热处理状态
- Expected: heat_current_stage
- Selected: heat_current_stage
- Context: catalog_only
- Confidence: 0.78
- Validation: missing_required_entities
- Top1 pass: True

### missing_002

- Input: 查一下热处理
- Expected: None
- Selected: None
- Context: catalog_with_business_facts
- Confidence: 0.0
- Validation: need_clarification
- Top1 pass: True

### missing_003

- Input: 这个热处理在哪个炉子完成
- Expected: heat_device_trace
- Selected: heat_device_trace
- Context: catalog_with_business_facts
- Confidence: 0.8
- Validation: missing_required_entities
- Top1 pass: True

### unrelated_001

- Input: 今天天气怎么样
- Expected: None
- Selected: None
- Context: catalog_with_business_facts
- Confidence: 0.0
- Validation: need_clarification
- Top1 pass: True

### unrelated_002

- Input: 帮我写一首诗
- Expected: None
- Selected: None
- Context: catalog_with_business_facts
- Confidence: 0.0
- Validation: need_clarification
- Top1 pass: True
