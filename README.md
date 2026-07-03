# MES Agent

Independent MES Agent research project. The current skeleton verifies project structure, startup commands, HTTP communication, and a minimal provider-independent LLM chat layer.

DeepSeek is the first supported LLM provider. Single-turn chat persistence stores each request in MySQL. No Agent orchestration, MES data access, login, permission, queue, cache, vector-store, tool calling, streaming, or history-query functionality is included.

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
│   ├── chat-persistence-flow.md
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
```

FastAPI must not use a long-lived `root` account. Use a least-privilege application account scoped to `mes_agent` with the required `SELECT`, `INSERT`, and `UPDATE` permissions.

The persistence flow is documented in [docs/chat-persistence-flow.md](/Users/user/Documents/mes-agent/docs/chat-persistence-flow.md).
