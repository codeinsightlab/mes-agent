# Capability Reasoning V2: LLM Native Business Reasoning

Date: 2026-07-14

## 1. Goal and Scope

Capability Reasoning V2 replaces the production deterministic keyword scorer with an LLM-native business-understanding adapter. The LLM receives the user question, current MES Capability Catalog, and Heat Treatment Business Facts, then returns a structured capability-selection decision.

This change does not let the LLM execute anything. It does not modify Agent Router, Capability Runtime, Execution Engine, MES API, Repository, SQL, Text-to-SQL, RAG, Memory, or multi-Agent behavior.

## 2. Chain Change

Before:

```text
HeatTreatmentAgent
-> deterministic keyword CapabilityReasoner
-> CapabilityReasoningValidator
-> CapabilityRuntime
-> Execution
```

After:

```text
HeatTreatmentAgent
-> CapabilityReasoner service
-> LlmCapabilityReasoningAdapter
   |-> capability-reasoning-v2 prompt
   |-> shared LlmRuntime structured output
   |-> reasoning audit
-> CapabilityReasoningValidator
-> CapabilityRuntime
-> Execution
```

The public `MesAgent`, `AgentRouter`, `HeatTreatmentAgent`, `CapabilityRuntime`, and Execution interfaces remain unchanged. The V1 deterministic scorer and earlier generator/audit implementation were retained under `agent/archive/deprecated/capability_reasoning_v1/`.

## 3. Capability Catalog as MES Knowledge

The Catalog remains the only allowed capability namespace. Heat-treatment entries now expose:

- `name`;
- `description`;
- `business_goal`;
- `when_to_use`, including negative boundaries;
- `examples`;
- `input_entities`;
- `execution_type`;
- `api_contract`;
- lifecycle `status`.

`status: planned` does not prevent Reasoning from selecting a semantically correct capability. The existing Validator/Runtime still prevents execution.

The important distinction is:

```text
LLM selects a known business capability
!=
LLM is allowed to execute that capability
```

## 4. Prompt V2

Source:

- `backend/app/agent/reasoning/capability_reasoning/prompt/capability_reasoning_v2.md`

Prompt version:

- `capability-reasoning-v2`

The prompt defines the model as an MES business-understanding assistant, not an answer generator. It includes:

- the original user question;
- JSON capability knowledge;
- current Business Facts;
- the strict output protocol;
- no-SQL/no-API/no-database/no-Tool constraints;
- no invented capability rule;
- object-word versus business-goal boundary;
- explicit handling for missing parameters and ambiguous goals;
- explicit instruction that `selected_capability` contains only `name` and `reason`.

## 5. Output Protocol

```json
{
  "goal": "查询热处理当前状态",
  "domain": "heat_treatment",
  "selected_capability": {
    "name": "heat_current_stage",
    "reason": "用户询问指定热处理是否完成"
  },
  "entities": {
    "record_no": "TRACE-HTR-001"
  },
  "confidence": 0.95,
  "need_clarification": false,
  "clarification_reason": null
}
```

Protocol enforcement:

- Pydantic rejects extra output fields.
- Confidence must be between 0 and 1.
- SQL, Repository, database, API-call, and Tool-call fields are rejected recursively.
- An unknown capability name is normalized to no selection plus clarification.
- Missing required entities and capability lifecycle status are still checked by the existing Validator.

## 6. LLM Runtime and Adapter

`LlmCapabilityReasoningAdapter` owns only:

- Prompt assembly;
- structured LLM invocation through shared `LlmRuntime`;
- Catalog-name enforcement;
- Reasoning audit emission.

It does not import Capability Runtime, Execution Engine, Repository, database, API clients, or Text-to-SQL.

The shared `LlmRuntime` supports native structured output and a JSON-content fallback for providers that return a LangChain `AIMessage` rather than a parsed Pydantic object.

## 7. Reasoning Audit

Every successfully parsed decision records:

- `user_input`;
- `prompt_version`;
- `available_capabilities`;
- `business_fact_version`;
- original parsed `llm_output`;
- accepted `selected_capability`;
- `confidence`;
- `need_clarification`.

Production uses a structured logging sink. The Benchmark uses a collecting sink and writes audit records into its JSON result. If strict parsing fails, the audit stores the raw model JSON and parse error before rejecting the decision.

## 8. Safety Boundaries Preserved

- The model cannot select outside the supplied Catalog without being normalized to clarification.
- The model cannot execute a `planned` capability.
- The model cannot generate an execution request in the Reasoning schema.
- The model cannot access MES data or a Repository from the adapter.
- Existing execution validation remains authoritative.

## 9. Verification

- V2 tests cover the full status/device/statistics/clarification chain with a fake structured model.
- Prompt content and Catalog-knowledge fields are asserted.
- Unknown capability normalization is tested.
- Recursive rejection of execution fields is tested.
- Real DeepSeek Benchmark uses 30 cases from the existing heat-treatment question set.

Benchmark evidence and errors are documented in `reports/capability-reasoning-v2-benchmark.md`.
