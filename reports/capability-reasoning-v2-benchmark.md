# Capability Reasoning V2 Benchmark

Date: 2026-07-14

## 1. Benchmark Setup

- Model: `deepseek-chat`
- Prompt: `capability-reasoning-v2`
- Question source: `docs/business-scenarios/heat-treatment/heat-treatment-question-set-v1.yaml`
- Cases: 30 fixed IDs
- Execution: disabled; only Reasoning was invoked
- Result: `results/capability-reasoning-v2-benchmark.json`
- Audit records: 30 decisions

Case composition:

- status: 8;
- device trace: 6;
- process parameters with no current capability: 2;
- exception analysis/no-capability behavior: 3;
- statistics: 5;
- ambiguous questions: 6.

For a capability absent from the runtime Catalog, the expected result is `selected_capability = null` and `need_clarification = true`. For `heat_device_trace`, the expected result is a correct selection even though the later Validator blocks execution because it remains `planned`.

## 2. Final Result

| Metric | Result |
| --- | ---: |
| Total | 30 |
| Passed | 30 |
| Pass rate | 100.0% |
| Selection accuracy | 100.0% |
| Clarification accuracy | 100.0% |
| Structured-output errors | 0 |
| Average latency | 1667 ms |
| Maximum latency | 2149 ms |

Category result:

| Category | Passed / Total |
| --- | ---: |
| Status | 8 / 8 |
| Device trace | 6 / 6 |
| Process parameters | 2 / 2 |
| Exception analysis | 3 / 3 |
| Statistical analysis | 5 / 5 |
| Ambiguous | 6 / 6 |

## 3. Positive Evidence

### Device capability selection

All six fully specified device questions selected `heat_device_trace`, even though the capability is `planned`. This proves that Reasoning and execution lifecycle gating remain separate.

### Broader status language

The LLM correctly mapped natural expressions including:

- `还在做吗`;
- `有没有结束`;
- `是不是已经转序了`;
- `现在进度怎么样`.

These expressions were failures in the earlier deterministic question evaluation.

### Missing-capability refusal

The LLM correctly refused to substitute existing capabilities for:

- actual process temperature;
- parameter completeness;
- recent abnormal overview;
- furnace abnormal ranking;
- device output ranking;
- completion trend;
- device operating condition.

### Ambiguous questions

All six ambiguous cases correctly returned no capability and requested clarification after the V2 Prompt/Catalog boundaries were made explicit.

## 4. Error Cases Observed During Iteration

The final persisted run has no failed cases. Two failure modes were observed in the immediately preceding real-model run and remain important stability evidence.

### HT-Q-001: strict output protocol failure

Question:

```text
TRACE-HTR-B-H-001现在什么状态？
```

The model selected the semantically correct status capability but added `input_entities` inside `selected_capability`. The Pydantic protocol correctly rejected the extra field. The final run returned the valid protocol for the same case.

Classification:

- semantic direction: correct;
- structured protocol: failed;
- final Benchmark result: failed.

This shows that provider structured-output compliance is not perfectly stable even with temperature zero and explicit schema instructions. Invalid extra fields are not silently stripped; current audit records their raw output and parse error.

### HT-Q-025: status versus cause-analysis confusion

Question:

```text
TRACE-HTR-B-H-001为什么还没有完成？
```

Expected:

- no capability;
- clarification because the Catalog has no incomplete-reason analysis capability.

Actual:

- selected `heat_current_stage` with confidence `0.95`;
- interpreted “why not completed” as a request for current state/progress.

This was a genuine semantic boundary error in the preceding run. The current status capability can report state but cannot explain the reason. The final run correctly returned no capability, but the observed variation remains a stability risk.

## 5. Initial-to-Final Iteration Evidence

Observed real-model runs during implementation were:

```text
run 1 after response-unwrapping fix: 24 / 30
run 2 after Prompt/Catalog boundary hardening: 28 / 30
final persisted run with failure audit support: 30 / 30
```

The `24 / 30` run contained:

- three strict-schema failures caused by extra `input_entities` fields;
- three semantic over-selections for incomplete reason and ambiguous questions.

The Prompt and Catalog knowledge were tightened only for protocol shape and explicit negative boundaries. No Business Facts or deterministic Reasoning rules were added. Although the final persisted run reached `30 / 30`, the variation across the three runs means a single perfect run must not be presented as stability proof.

## 6. Feasibility Decision

The result supports the direction as technically feasible for a bounded MES capability-selection layer:

- 100% on the final persisted fixed 30-case run;
- perfect device selection despite non-executable lifecycle state;
- correct refusal for most absent capabilities;
- materially better understanding of natural status expressions than the deterministic matcher.

It does not prove production readiness:

- preceding runs varied from 80.0% to 93.3% before the final 100% run;
- strict-schema and high-confidence semantic errors were both observed;
- no repeated-run acceptance threshold was defined;
- stability across model versions and broader business domains was not evaluated.

Recommended next step is not to add more capabilities immediately. First add repeated-run stability evaluation and decide how strict-output failures should be surfaced operationally without silently accepting invalid schemas.
