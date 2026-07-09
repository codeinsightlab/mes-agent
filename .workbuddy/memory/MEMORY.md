# MEMORY.md — Long-term Memory

## Project: MES Agent (`/Users/user/Documents/mes-agent`)

### Tech Stack
- Frontend: Vue 3 + Vite (single `App.vue`, no router, no state management)
- Backend: Python + FastAPI (layered: api → application → domain → infrastructure)
- Agent: LangGraph + LangChain + DeepSeek LLM
- Database: MySQL (two databases: `mes_agent` metadata + `j2eedb` MES readonly)
- No Docker, no CI/CD, no ESLint/Ruff

### Architecture Notes
- Two Agent paths exist: `LangGraph StateGraph` (legacy `graph.py`) and `AgentOrchestrator` (current `/api/agent/run`)
- Planner uses hardcoded keyword matching, NOT LLM (despite `LangChainToolMatcher` existing)
- 3 heat treatment Tools: only `heat_current_stage` queries real DB; other 2 return mock data
- Text-to-SQL has strong safety: Schema whitelist → sqlglot validator → readonly executor with LIMIT enforcement

### Known Issues (as of 2026-07-09)
- `.env` contains real production credentials (needs immediate rotation)
- Admin APIs have no authentication
- `agent_orchestrator.py` is 876 lines (needs splitting)
- `App.vue` is 838 lines (needs component extraction)
- Engine creation is duplicated in `executor.py` and `heat_treatment_repository.py`
