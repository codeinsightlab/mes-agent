# Capability Reasoning Experiment V1

Date: 2026-07-10

## Goal

This experiment validates whether MES Agent can move from classification-style routing toward capability reasoning:

```text
User Input
+ Capability Catalog
-> LLM Capability Reasoning
-> Capability Candidate
-> Capability Validator
-> Capability Router
-> Execution
```

This round is experimental only. It does not replace Semantic Router, does not modify Tool execution, and does not change Repository or SQL business logic.

## Before And Experiment Chain

Current production chain:

```text
User Input
-> Semantic Router
-> domain / intent
-> Capability Router
-> Capability Catalog
-> Execution
```

Experiment chain:

```text
User Input
+ Capability Catalog
-> Capability Reasoning
-> selected_capability + entities
-> Capability Reasoning Validator
-> Capability Router selected-name validation
-> existing Execution boundary
```

## New Module

Implemented under:

- `backend/app/agent/capability_reasoning/`

Files:

- `models.py`
- `reasoner.py`
- `generator.py`
- `validator.py`
- `audit.py`
- `prompt/capability_reasoning.md`

`CapabilityReasoningGenerator` is the LLM adapter for the same structured output protocol. The regression experiment uses deterministic reasoning so that results are repeatable without a real model token.

## Output Protocol

```json
{
  "goal": "查询热处理执行设备",
  "context_level": "catalog_with_business_facts",
  "candidate_capabilities": [
    {
      "name": "heat_device_trace",
      "confidence": 0.88,
      "reason": "Business Facts 将炉子归一为热处理设备。"
    }
  ],
  "selected_capability": "heat_device_trace",
  "entities": {
    "record_no": "TRACE-HTR-B-H-001"
  },
  "confidence": 0.88,
  "need_clarification": false,
  "clarification_reason": null
}
```

Forbidden output fields:

- `sql`
- `repository`
- `database`
- `api_call`
- `tool_call`

## Catalog Enhancements

Capability definitions now support:

- `business_context`
- `input_entities`
- `api_contract`

Heat-treatment Catalog enhancements:

- `heat_current_stage`: enriched status-query context.
- `heat_completion_count_monthly`: enriched statistical-query context.
- `heat_device_trace`: planned Capability contract only; no Tool implementation in this round.

## Business Facts Two-Stage Mode

Stage 1:

```text
context_level=catalog_only
```

Stage 2:

```text
context_level=catalog_with_business_facts
```

Business Facts used in this experiment:

- TRACE / HT identifiers are `record_no`.
- status / progress / current step maps to `heat_current_stage`.
- device / furnace / kiln expressions map to `heat_device_trace`.
- monthly completion count maps to `heat_completion_count_monthly`.
- ambiguous "怎么样" should clarify instead of executing.

## Experiment Entry

```text
cd backend && .venv/bin/python scripts/run_capability_reasoning_experiment.py
```

Outputs:

- `backend/results/capability_reasoning_experiment_report.json`
- `backend/results/capability_reasoning_experiment_report.md`
- `backend/results/capability_reasoning_audit.sqlite`

Audit table:

- `request_id`
- `user_input`
- `context_level`
- `candidate_capabilities`
- `selected_capability`
- `confidence`
- `reasoning_result`
- `validation_result`
- `execution_result`

## 30 Case Result

Latest result:

```json
{
  "total": 30,
  "top1_capability_accuracy": 1.0,
  "top3_candidate_coverage": 1.0,
  "catalog_only_top1_accuracy": 0.7333333333333333,
  "business_facts_top1_accuracy": 1.0,
  "business_facts_lift": 0.26666666666666666,
  "failed": 0,
  "system_status": "PASS"
}
```

Coverage:

- 10 status questions
- 8 device / furnace questions
- 5 statistical completion-count questions
- 4 ambiguous or missing-parameter questions
- 2 unrelated questions
- 1 explicit missing-record status question

## Failure Analysis

No final Top1 failures in the deterministic experiment.

Catalog-only weaknesses:

- Furnace expressions such as `哪个炉子` are weakly matched without Business Facts.
- Progress expressions such as `到哪了` improve when Business Facts explain that progress means status.
- Missing entity cases can choose the right Capability but must stop at validation.

Planned capability behavior:

- `heat_device_trace` can be selected as the correct candidate.
- It is blocked by validation with `capability_not_executable` because it is `planned`.
- No Tool is called.

## Recommendation

Do not replace Semantic Router yet.

Recommended next step:

1. Keep Semantic Router as the stable production path.
2. Run Capability Reasoning in parallel as an experiment path.
3. Replace or simplify Semantic Router only after a real LLM run on production-like samples proves stable Top1 / Top3 accuracy.
4. Use Business Facts as controlled context, not free-form memory or RAG.

The experiment supports further investigation of capability reasoning, but does not yet prove that it should replace the current classification routing architecture.
