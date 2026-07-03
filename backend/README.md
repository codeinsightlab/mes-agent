# MES Agent Backend

FastAPI backend for the MES Agent research project.

Current backend capabilities:

- `GET /api/health`
- `POST /api/chat`
- Provider-independent LLM client protocol with DeepSeek as the first provider.

It does not include MES data access, Agent orchestration, tool calling, streaming, multi-turn context, or history-query APIs.

The chat API is single-turn only: one request creates one independent conversation, stores the user message and model call, then stores the assistant message on success. The backend does not load or reuse previous user messages as model context.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create local configuration:

```bash
cp .env.example .env
```

Set `LLM_API_KEY` and database variables in `.env` before calling `/api/chat`.

## Run

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Chat request:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"hello"}'
```

If `LLM_API_KEY` is not configured, `/api/chat` returns a configuration error. Health checks remain available without LLM credentials.

Response fields:

- `content`
- `model`
- `provider`
- `conversation_key`
- `response_message_key`
- `call_key`
- `finish_reason`
- `usage`

Database variables:

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

Use a least-privilege application database account. Do not run the FastAPI application with a long-lived `root` account.
