# Heat Treatment Business Question Coverage Evaluation V1

Date: 2026-07-14

## 1. Evaluation Goal

Use manufacturing-site questions to evaluate the current MES Agent V2 heat-treatment coverage. This evaluation does not add Business Facts, change the Capability Catalog, modify Capability Reasoning, add an executor, or change MES business code.

Truth sources used:

- question source and business vocabulary: existing review documents under `docs/capabilities/heat-treatment/`;
- runtime Business Facts: `backend/app/agent/agents/heat_treatment/business_facts/facts.py`;
- runtime Capability Catalog: `backend/app/agent/capability/catalog/definitions/heat-treatment.yaml`;
- actual selection behavior: current `CapabilityReasoner.reason_with_business_facts()`;
- executability and missing-entity behavior: current `CapabilityReasoningValidator`.

The review documents contain broader discovered business facts and candidate capabilities. They were used to design realistic questions, but a documented candidate was not counted as a current runtime capability unless it exists in the runtime YAML Catalog.

## 2. Question Set

Source:

- `docs/business-scenarios/heat-treatment/heat-treatment-question-set-v1.yaml`

Coverage:

| Dimension | Distribution |
| --- | --- |
| Total questions | 56 |
| Categories | 7 categories, 8 questions each |
| Production manager | 17 |
| Production operator | 13 |
| Quality engineer | 10 |
| Process engineer | 9 |
| Equipment engineer | 7 |
| Expected execute | 17 |
| Expected clarify | 19 |
| Expected gap | 20 |

All questions use business language. There are no framework, API, database, prompt, or other technical questions in the question set.

## 3. Classification Rules

The executable evaluation script assigns one primary status:

1. `supported`: current Reasoning selects the expected executable runtime capability and Validator allows execution.
2. `missing_capability`: the business goal requires a capability that is absent from the runtime Catalog.
3. `missing_fact`: the expected capability exists in the runtime Catalog, but current Reasoning does not select it for the given business expression.
4. `need_clarification`: current Reasoning/Validator correctly stops on an ambiguous goal or missing required condition.

Reasoning-correct but non-executable capabilities use `missing_capability`, with `API/Execution 缺口` retained in the reason field. Primary classification uses this order to avoid double counting. False-positive routing is recorded as a secondary finding when a question primarily lacks a capability but Reasoning selects a different existing capability.

## 4. Overall Result

| Outcome | Count | Rate |
| --- | ---: | ---: |
| Supported | 8 | 14.3% |
| Need clarification | 12 | 21.4% |
| Missing Capability | 33 | 58.9% |
| Missing Fact | 3 | 5.4% |
| Total | 56 | 100.0% |

The 20 safe behaviors consist of:

- 8 direct executions: five current-status questions and three current-month completion-count questions;
- 12 correct clarifications: missing identifiers/time range and deliberately ambiguous questions.

Current direct business-answer support is `8 / 56 = 14.3%`. Safe-behavior coverage including clarification is `20 / 56 = 35.7%`.

## 5. Category Result

| Category | Supported | Need clarification | Missing Capability | Missing Fact | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Status | 5 | 0 | 0 | 3 | 8 |
| Device trace | 0 | 2 | 6 | 0 | 8 |
| Process parameters | 0 | 0 | 8 | 0 | 8 |
| Exception analysis | 0 | 0 | 8 | 0 | 8 |
| Statistical analysis | 3 | 0 | 5 | 0 | 8 |
| Ambiguous questions | 0 | 5 | 3 | 0 | 8 |
| Missing conditions | 0 | 5 | 3 | 0 | 8 |

## 6. Supported Boundary

### 6.1 Directly executable

- `HT-Q-001` to `HT-Q-005`: record status/stage/current-condition queries with recognizable language and a valid `record_no`.
- `HT-Q-033` to `HT-Q-035`: current-month heat-treatment completion-count questions.

### 6.2 Correct clarification

- `HT-Q-015`, `HT-Q-016`: device intent is recognized but `record_no` is missing.
- `HT-Q-041` to `HT-Q-044`, `HT-Q-047`: broad or ambiguous questions stop before execution.
- `HT-Q-049` to `HT-Q-052`, `HT-Q-054`: known capability intent is recognized, while the required record number or time range is missing.

The current clarification mechanism is useful for known narrow capabilities. It does not prove that the Agent can eventually answer a question whose required capability is absent.

## 7. Missing Business Facts

The following questions target the existing `heat_current_stage` capability but current Reasoning selects nothing:

| ID | Business expression | Current result | Gap |
| --- | --- | --- | --- |
| HT-Q-006 | `还在做吗` | clarification, no capability | Ongoing/running expression is not mapped to current stage. |
| HT-Q-007 | `有没有结束` | clarification, no capability | Ended expression is not mapped to current stage. |
| HT-Q-008 | `是不是已经转序了` | clarification, no capability | Transferred expression is not mapped to current stage. |

These are knowledge/expression gaps because the runtime Catalog already contains `heat_current_stage` and its output status set includes `RUNNING`, `ENDED`, and `TRANSFERRED`.

No Business Fact was added in this round.

## 8. Missing API / Execution Subset

Six fully specified device-trace questions (`HT-Q-009` to `HT-Q-014`) correctly select `heat_device_trace`, with confidence from `0.88` to `0.90`. Validation then returns `capability_not_executable` because the runtime Catalog status is `planned`.

The JSON primary status is `missing_capability`; the reason identifies this API/Execution subtype. This is not a Reasoning gap. It is one shared execution gap:

```text
heat_device_trace
-> recognized
-> required record_no extracted
-> Catalog contract found
-> blocked because planned / no executable Tool
```

The two device questions without a record number (`HT-Q-015`, `HT-Q-016`) correctly clarify before reaching the execution boundary.

## 9. Missing Capability Inventory

### 9.1 Process parameters: 8 questions

Missing business goals include:

- actual temperature and holding time;
- parameter completeness;
- parameter change trace;
- last parameter submitter;
- parameter/photo evidence completeness;
- parameter-template matching.

The review documents contain facts and candidate APIs for parameters, submits, templates, and photos, but none of these goals exists as a current runtime Capability.

### 9.2 Exception analysis: 8 questions

Missing business goals include:

- incomplete reason analysis;
- recent abnormal overview;
- device abnormal ranking;
- void reason;
- parameter deviation;
- device downtime reason;
- overdue heat-treatment records;
- parameter-change statistics.

The current status Tool can report state but cannot explain causes. Device record status must also remain separate from PLC/device downtime state.

### 9.3 Statistical analysis: 5 questions

Current coverage is limited to current-month completion count. Missing goals include:

- today/previous-month/custom-period completion count;
- device output ranking;
- multi-month completion trend;
- average duration by process stage.

### 9.4 Ambiguous and missing-condition questions: 6 questions

These questions need capabilities that do not exist even after clarification:

- parameter deviation judgment;
- device operating status;
- heat-treatment risk assessment;
- parameter query;
- product-to-heat-treatment-record lookup;
- incomplete-record list by time period.

## 10. False-Positive Routing Findings

Four questions primarily expose missing capabilities but current Reasoning selects a different existing capability:

| ID | Question intent | Incorrect selection | Trigger |
| --- | --- | --- | --- |
| HT-Q-027 | Furnace abnormal ranking | `heat_device_trace` | Contains `炉子`. |
| HT-Q-030 | Device downtime reason | `heat_device_trace` | Contains `炉`. |
| HT-Q-037 | Previous-month completion count | `heat_completion_count_monthly` | Contains completion-count expression, but only current-month entity extraction exists. |
| HT-Q-038 | Device output ranking | `heat_device_trace` | Contains `设备`. |

These cases show that current keyword scoring can confuse the object mentioned in a question with the actual analytical goal. This is recorded as evaluation evidence only; the Reasoning algorithm was not changed.

## 11. Prioritized Gap List for a Later Round

This is a sequencing input, not an implementation performed in this evaluation:

| Priority | Gap | Evidence | Why first/later |
| --- | --- | --- | --- |
| P1 | Complete `heat_device_trace` execution | 6 correctly reasoned, fully specified questions blocked only at execution | Smallest gap between recognized intent and usable answer. |
| P1 | Status expression coverage | 3 questions target an existing executable capability | No new business capability is required. |
| P2 | Parameter query/read model | 8 process questions plus existing reviewed parameter facts | Broad shop-floor value, but requires capability contract decisions. |
| P2 | Time-range completion statistics | 3 statistical gaps are variants of the existing monthly count | Requires explicit period schema and execution boundary. |
| P3 | Exception analysis | 8 questions | Requires stable abnormal/cause/timeout definitions before implementation. |
| P3 | Device/risk analytical capabilities | false-positive routing and ambiguous cases | Must keep record state, equipment state, and risk rules distinct. |

## 12. Conclusion

The current HeatTreatmentAgent reliably covers only two narrow answer domains:

1. current status for a recognized record number and recognized status expression;
2. current-month completion count.

It also provides useful safe clarification for some missing-condition and ambiguous questions. Device trace Reasoning is ready at the selection level but not at the execution level. Process parameters, exception analysis, broader statistics, risk, and product/batch lookup are not current runtime capabilities.

The next round should choose gaps from this evidence rather than expanding Business Facts broadly in advance.
