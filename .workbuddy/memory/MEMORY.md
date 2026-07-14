# MEMORY.md — Long-term Memory

## Project: MES Agent (`/Users/user/Documents/mes-agent`)

### Tech Stack
- Frontend: Vue 3 + Vite (single `App.vue`, no router, no state management)
- Backend: Python + FastAPI (layered: api → application → domain → infrastructure)
- Agent: **V2**: Pure Python (MesAgent + AgentRouter + Capability Catalog YAML); **V1 archived**: LangGraph StateGraph
- LLM: DeepSeek via httpx (direct), langchain_openai ChatOpenAI for Text-to-SQL
- Database: MySQL (two databases: `mes_agent` metadata + `j2eedb` MES readonly)
- No Docker, no CI/CD, no ESLint/Ruff

### Architecture (as of 2026-07-10, V2)
- **V2 Production Chain**: `POST /api/agent/run` → `MesAgent` → `AgentRouter`(fixed) → `HeatTreatmentAgent` → `CapabilityReasoner`(rule-based) → `CapabilityRuntime` → `ExecutionEngine`
- **Capability Catalog**: YAML-driven (`definitions/*.yaml`), loaded by `CapabilityLoader`, validated by `CapabilityValidator`
- **Status gating**: `enabled`/`planned`/`blocked` — planned capabilities are selectable but not executable
- **Runtime abstractions**: `LlmRuntime`, `TraceRuntime`, `AuditRuntime`, `CapabilityRuntime` — all Protocol-based DI
- **V1 code archived**: `agent/archive/v1/` (Orchestrator, Planner, Graph, nodes) — not imported by V2
- **V2 core is ~350 lines** (vs V1's 1336-line orchestrator)
- **17-stage documented evolution** in `docs/agent-architecture-consolidation-v1.md`

### Known Issues (as of 2026-07-10)
- `.env` contains real production credentials (needs rotation)
- Admin APIs have no authentication
- Dual-track Capability definitions: YAML + Python `CapabilitySpec` coexist
- `CapabilityReasoner` is rule-based keyword matching (LLM `CapabilityReasoningGenerator` exists but not enabled)
- `TextToSqlNode` still uses `AgentState` TypedDict (LangGraph legacy)
- Executor registration scattered in `api/agent.py` assembly layer
- V2 has only 6 test cases vs V1 archive's 122+

### V2 Architecture Score (experiment/evaluation perspective)
- 8.5/10 overall
- Strongest: evolution process management (9.5), architecture design quality (9)
- Weakest: architecture consistency (7) due to V1 residuals
