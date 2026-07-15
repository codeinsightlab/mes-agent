# Heat Treatment Knowledge Gap V1

Date: 2026-07-14

## 1. Evaluation Baseline

- Question set: `docs/business-scenarios/heat-treatment/heat-treatment-question-set-v1.yaml`
- Evaluation script: `scripts/run_heat_question_evaluation.py`
- Result: `results/heat-treatment-question-evaluation.json`
- Questions: 56
- Current inputs: runtime HeatTreatment Business Facts, runtime Capability Catalog, current Capability Reasoning and Validator

No Business Fact, Capability, Reasoning rule, MES API, Repository, or execution implementation was changed.

## 2. Result Summary

| Status | Count | Rate | Meaning |
| --- | ---: | ---: | --- |
| `supported` | 8 | 14.3% | Correctly selects an executable capability. |
| `need_clarification` | 12 | 21.4% | Correctly stops because the business goal or required condition is missing. |
| `missing_capability` | 33 | 58.9% | Required runtime capability is absent, or Reasoning is correct but execution is unavailable. |
| `missing_fact` | 3 | 5.4% | Target capability exists, but current Business Facts/expressions do not select it. |

Safe-behavior coverage, counting both execution and correct clarification, is `20 / 56 = 35.7%`. Direct answer support is `8 / 56 = 14.3%`.

## 3. Supported Questions

| ID | Question | Capability | Confidence |
| --- | --- | --- | ---: |
| HT-Q-001 | TRACE-HTR-B-H-001现在什么状态？ | `heat_current_stage` | 0.93 |
| HT-Q-002 | HT20260603-007热处理做到哪一步了？ | `heat_current_stage` | 0.93 |
| HT-Q-003 | TRACE-HTR-K2-T-FG-001这个热处理完成了吗？ | `heat_current_stage` | 0.93 |
| HT-Q-004 | HT20260714-001现在进度怎么样？ | `heat_current_stage` | 0.87 |
| HT-Q-005 | TRACE-HTR-A-002当前情况是什么？ | `heat_current_stage` | 0.87 |
| HT-Q-033 | 本月热处理完成多少批？ | `heat_completion_count_monthly` | 0.92 |
| HT-Q-034 | 统计本月热处理完成数量。 | `heat_completion_count_monthly` | 0.92 |
| HT-Q-035 | 这个月完成了多少批热处理？ | `heat_completion_count_monthly` | 0.84 |

Supported direct answers are therefore limited to current status and current-month completion count.

## 4. Correct Clarification Questions

The following 12 questions safely stop instead of executing with incomplete input:

- Device trace missing record: `HT-Q-015`, `HT-Q-016`, `HT-Q-051`.
- Broad/ambiguous goal: `HT-Q-041`, `HT-Q-042`, `HT-Q-043`, `HT-Q-044`, `HT-Q-047`.
- Status/progress missing record: `HT-Q-049`, `HT-Q-050`, `HT-Q-052`.
- Completion count missing time range: `HT-Q-054`.

Clarification is a supported behavior, but it is not counted as a directly answered question.

## 5. Missing Capability Questions

### Top 10 missing capability targets

| Rank | Expected capability | Questions | Gap type |
| ---: | --- | ---: | --- |
| 1 | `heat_device_trace` | 6 | Catalog contract exists, but API/Execution is unavailable. |
| 2 | `heat_process_parameters` | 4 | Runtime capability absent. |
| 3 | `heat_parameter_deviation_analysis` | 2 | Runtime capability absent. |
| 4 | `heat_completion_count_by_period` | 2 | Runtime capability absent. |
| 5 | `heat_parameter_completeness` | 1 | Runtime capability absent. |
| 6 | `heat_parameter_change_trace` | 1 | Runtime capability absent. |
| 7 | `heat_parameter_submit_trace` | 1 | Runtime capability absent. |
| 8 | `heat_parameter_evidence_completeness` | 1 | Runtime capability absent. |
| 9 | `heat_parameter_template_match` | 1 | Runtime capability absent. |
| 10 | `heat_incomplete_reason_analysis` | 1 | Runtime capability absent. |

The remaining missing-capability questions cover abnormal overview/ranking, void reason, device downtime, overdue records, parameter-change statistics, device output ranking, completion trend, stage duration, device status, risk assessment, product-record lookup, and incomplete-record lists.

### Missing API / Execution subset

`HT-Q-009` through `HT-Q-014` all select `heat_device_trace` correctly with confidence between `0.88` and `0.90`, but Validator returns `capability_not_executable` because the Catalog contract remains `planned`.

Per the evaluation status contract, these six records use:

```text
status = missing_capability
reason = API/Execution 缺口: ...
```

They are not Business Fact or Reasoning failures.

## 6. Missing Business Facts

Only three observed questions meet the strict `missing_fact` definition, so the list is shorter than Top 10 and is not padded with unobserved assumptions.

| Rank | ID | Missing expression mapping | Existing target capability |
| ---: | --- | --- | --- |
| 1 | HT-Q-006 | `还在做吗` should express current/running status. | `heat_current_stage` |
| 2 | HT-Q-007 | `有没有结束` should express ended status. | `heat_current_stage` |
| 3 | HT-Q-008 | `是不是已经转序了` should express transferred status. | `heat_current_stage` |

These are fact/expression gaps because `heat_current_stage` already exists and its result status domain already contains `RUNNING`, `ENDED`, and `TRANSFERRED`.

## 7. Secondary Reasoning Risks

Four missing-capability questions also show false-positive selection:

- `HT-Q-027`: furnace abnormal ranking selects `heat_device_trace` because of `炉子`.
- `HT-Q-030`: device downtime reason selects `heat_device_trace` because of `炉`.
- `HT-Q-037`: previous-month count selects the current-month capability but cannot extract the required period.
- `HT-Q-038`: device output ranking selects device trace because of `设备`.

The current Reasoning tends to treat an object word as the goal, even when the actual goal is ranking, cause analysis, or period statistics.

## 8. Suggested Next-Round Route

The evaluation supports the following sequence, but implements none of it:

1. Decide whether to complete the existing `heat_device_trace` execution contract. It has six correctly reasoned, fully specified questions and is the clearest execution-only gap.
2. Review the three observed status-expression gaps. They target an existing executable capability and do not require a new business domain.
3. Define one bounded read-only process-parameter capability from the eight parameter questions, using the already reviewed parameter/submit facts as evidence.
4. Generalize completion statistics only after agreeing on an explicit time-range schema; current coverage is limited to the current month.
5. Defer exception analysis until abnormal, timeout, deviation, downtime, and causal boundaries have deterministic definitions.
6. Evaluate false-positive routing separately before adding broad object keywords, so `设备` and `炉子` do not override analytical intent.

## 9. Conclusion

The first manufacturing question benchmark shows a narrow but explainable current boundary:

- status and current-month count can answer directly;
- clarification works for several incomplete or broad requests;
- device trace is reasoned but not executable;
- parameter, exception, broader statistics, risk, and cross-object lookup goals lack runtime capabilities;
- three common status expressions are missing from current Business Fact coverage.

This benchmark should remain unchanged as the V1 baseline while later scoped rounds address selected gaps.
