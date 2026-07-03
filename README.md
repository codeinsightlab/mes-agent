# MES Agent

Independent MES Agent research project. The current skeleton verifies project structure, startup commands, HTTP communication, a minimal provider-independent LLM chat layer, and anonymous feedback for saved assistant answers.

DeepSeek is the first supported LLM provider. Single-turn chat persistence stores each request in MySQL. Anonymous feedback stores likes or dislikes in `agent_feedback`. Disliked feedback can be manually converted into `agent_issue` through development/test admin APIs. A standalone LangGraph Agent development endpoint now routes heat-treatment Tool matches and controlled Text-to-SQL fallback without replacing `/api/chat`.

The current chat page supports one independent request and one response at a time. Each request creates a new conversation record, but it does not send prior messages as context or display a message history.

## Project Structure

```text
.
├── backend
│   ├── .env.example
│   ├── README.md
│   ├── app
│   │   ├── api
│   │   ├── application
│   │   ├── core
│   │   ├── domain
│   │   ├── infrastructure
│   │   ├── main.py
│   │   └── schemas
│   ├── tests
│   └── requirements.txt
├── docs
│   ├── agent-conversation-storage.md
│   ├── agent-tool-text-to-sql-routing-v1.md
│   ├── anonymous-feedback-flow.md
│   ├── chat-persistence-flow.md
│   ├── disliked-feedback-issue-flow.md
│   └── llm-client-layer.md
├── frontend
│   ├── .env.example
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── src
│   │   ├── App.vue
│   │   ├── api.js
│   │   ├── main.js
│   │   └── style.css
│   └── vite.config.js
└── log
    └── codex-task-log.md
```

## Environment Requirements

- Node.js 18 or newer
- Python 3.10 or newer

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create local backend environment configuration:

```bash
cp .env.example .env
```

Then edit `backend/.env` and set `LLM_API_KEY` and database variables to your own local values. Do not put real tokens or database passwords in `.env.example`, README, logs, or tests.

## Backend Startup

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Chat API:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"hello"}'
```

Feedback API:

```bash
curl -X POST http://127.0.0.1:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{"response_message_key":"assistant-message-key","visitor_id":"anonymous-visitor-id","feedback_type":1}'
```

Development/test issue management APIs:

```text
GET  /api/admin/feedbacks/disliked
GET  /api/admin/feedbacks/{feedback_key}
POST /api/admin/issues
GET  /api/admin/issues
GET  /api/admin/issues/{issue_key}
PUT  /api/admin/issues/{issue_key}
```

These admin APIs do not include real authentication in the current version.

Agent development API:

```bash
curl -X POST http://127.0.0.1:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"message":"TRACE-HTR-K2-T-FG-001到哪了"}'
```

This endpoint uses LangGraph orchestration. Heat-treatment Tool hits still execute the existing mock Tools. Unmatched heat-treatment analysis questions enter a controlled Text-to-SQL path:

```text
HeatTreatmentSchemaProvider
-> TextToSqlGenerator
-> SqlValidator
-> ReadonlySqlExecutor
-> ResultNormalizer
```

Text-to-SQL uses an independent MES read-only data source configured with `AGENT_MES_DB_*`. It does not use the Agent metadata database. If the MES read-only configuration is missing, the endpoint returns a stable `mes_db_configuration_error`.

If `LLM_API_KEY` is missing, `/api/chat` returns a stable configuration error instead of calling the provider. `/api/health` does not require an API key.

Response fields:

- `content`: model answer
- `model`: model name returned by the provider or configured fallback
- `provider`: provider name
- `conversation_key`: stable key for the saved conversation
- `response_message_key`: stable key for the saved assistant message
- `call_key`: stable key for the saved model call
- `finish_reason`: optional provider finish reason
- `usage`: optional token usage

## Frontend Setup

```bash
cd frontend
npm install
```

## Frontend Startup

```bash
cd frontend
npm run dev
```

Default frontend address:

```text
http://127.0.0.1:5173
```

The frontend uses `VITE_API_BASE_URL=/api` and the Vite development proxy forwards `/api` requests to `http://127.0.0.1:8000`.

The frontend trims blank input, disables the send button while a request is in flight, replaces the previous answer with the latest response, and shows explicit errors when the backend or model call fails.

After a successful assistant answer, the frontend shows like and dislike feedback controls when `response_message_key` is present. It stores an anonymous `visitor_id` in `localStorage` under `mes_agent_visitor_id`; this value is only used for anonymous feedback ownership and is not an authentication credential.

## LLM Configuration

Backend variables:

```text
LLM_PROVIDER=deepseek
LLM_API_KEY=replace-with-your-deepseek-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_TIMEOUT_SECONDS=30
```

The LLM abstraction is documented in [docs/llm-client-layer.md](/Users/user/Documents/mes-agent/docs/llm-client-layer.md).

## Database Configuration

Backend database variables:

```text
DB_HOST=replace-with-db-host
DB_PORT=3306
DB_NAME=mes_agent
DB_USER=replace-with-db-user
DB_PASSWORD=replace-with-db-password
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE_SECONDS=1800
DB_CONNECT_TIMEOUT_SECONDS=5
AGENT_VERSION=0.1.0
PROMPT_VERSION=chat-v1
TOOL_VERSION=
AGENT_TOOL_MATCH_THRESHOLD=0.75
AGENT_MES_DB_HOST=replace-with-readonly-mes-db-host
AGENT_MES_DB_PORT=3306
AGENT_MES_DB_NAME=replace-with-readonly-mes-db-name
AGENT_MES_DB_USER=replace-with-readonly-mes-db-user
AGENT_MES_DB_PASSWORD=replace-with-readonly-mes-db-password
AGENT_MES_DB_CONNECT_TIMEOUT_SECONDS=5
AGENT_TEXT_TO_SQL_MAX_LIMIT=100
AGENT_TEXT_TO_SQL_TIMEOUT_SECONDS=5
```

FastAPI must not use a long-lived `root` account. Use a least-privilege application account scoped to `mes_agent` with the required `SELECT`, `INSERT`, and `UPDATE` permissions.

The persistence flow is documented in [docs/chat-persistence-flow.md](/Users/user/Documents/mes-agent/docs/chat-persistence-flow.md).
Anonymous feedback is documented in [docs/anonymous-feedback-flow.md](/Users/user/Documents/mes-agent/docs/anonymous-feedback-flow.md).
Manual disliked-feedback issue management is documented in [docs/disliked-feedback-issue-flow.md](/Users/user/Documents/mes-agent/docs/disliked-feedback-issue-flow.md).
Agent Tool/Text-to-SQL routing is documented in [docs/agent-tool-text-to-sql-routing-v1.md](/Users/user/Documents/mes-agent/docs/agent-tool-text-to-sql-routing-v1.md).
