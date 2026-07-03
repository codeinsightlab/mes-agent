# MES Agent Backend

FastAPI backend for the MES Agent research project.

Current backend capabilities:

- `GET /api/health`
- `POST /api/chat`
- `POST /api/feedback`
- `GET /api/admin/feedbacks/disliked`
- `GET /api/admin/feedbacks/{feedback_key}`
- `POST /api/admin/issues`
- `GET /api/admin/issues`
- `GET /api/admin/issues/{issue_key}`
- `PUT /api/admin/issues/{issue_key}`
- `POST /api/agent/query`
- Provider-independent LLM client protocol with DeepSeek as the first provider.

It does not include MES production data access, streaming, multi-turn context, login, JWT, authentication service calls, automatic issue analysis, issue verification, or history-query APIs. The Agent endpoint currently uses mock heat-treatment Tools and a controlled heat-treatment Text-to-SQL fallback for unmatched analysis questions.

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
Set `AGENT_MES_DB_*` only when validating `/api/agent/query` Text-to-SQL against an independent MES read-only test database.
The backend loads this file from `backend/.env` using an absolute path derived from the code location, so behavior is stable whether `uvicorn` is started from the repository root or from `backend/`.

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

Feedback request:

```bash
curl -X POST http://127.0.0.1:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{"response_message_key":"assistant-message-key","visitor_id":"anonymous-visitor-id","feedback_type":1}'
```

Create issue from disliked feedback:

```bash
curl -X POST http://127.0.0.1:8000/api/admin/issues \
  -H "Content-Type: application/json" \
  -d '{"feedback_key":"feedback-key","priority":2}'
```

The `/api/admin/*` APIs are current development/test management APIs and do not include real administrator authentication.

Agent query:

```bash
curl -X POST http://127.0.0.1:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"message":"TRACE-HTR-K2-T-FG-001到哪了"}'
```

`/api/agent/query` does not replace `/api/chat` and does not write to chat persistence.

For unmatched heat-treatment analysis questions, `/api/agent/query` uses:

```text
HeatTreatmentSchemaProvider
-> TextToSqlGenerator
-> SqlValidator
-> ReadonlySqlExecutor
-> ResultNormalizer
```

The Text-to-SQL path only allows the fixed heat-treatment Schema allowlist, validates generated SQL before execution, enforces SELECT-only single statements and row limits, and uses the independent `AGENT_MES_DB_*` read-only database configuration. If that configuration is missing, the endpoint returns `mes_db_configuration_error`.

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

Feedback response fields:

- `feedback_key`
- `response_message_key`
- `feedback_type`
- `feedback_type_label`
- `reason_type`
- `reason_type_label`
- `comment`
- `created_at`
- `updated_at`

Feedback can only target a saved assistant message. The same anonymous visitor updating feedback for the same message updates the existing active row instead of inserting duplicates. `visitor_id` is received through `IdentityContext` as an anonymous identifier, not as a trusted authentication credential.

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
AGENT_TOOL_MATCH_THRESHOLD=0.75
```

Use a least-privilege application database account. Do not run the FastAPI application with a long-lived `root` account.

## Persistence Checks

On application startup, the backend performs a read-only database connectivity check with `SELECT DATABASE()` and `SELECT 1`. Logs include the driver, host, port, database name, and user, but never the password or full connection URL.

For each `/api/chat` request, persistence logs show:

- `stage=initializing`
- `stage=initialized`
- model call result with `call_key` and `duration_ms`
- `stage=success_saved` or `stage=failure_saved`

For each `/api/feedback` request, logs show submit start, response message key, hashed visitor digest, feedback type, create/update action, feedback key, and commit success. Logs do not include the full visitor ID or full comment.

If `/api/chat` returns 200 but no rows appear in MySQL, check in this order:

1. Confirm the response contains `conversation_key`, `response_message_key`, and `call_key`.
2. Confirm the running process is using the latest code and the expected virtualenv.
3. Confirm logs show the persistence stages above.
4. Confirm `backend/.env` contains DB variables and is the file being loaded.
5. Confirm startup database check reports `mes_agent`.
6. Confirm no old `uvicorn` process is still serving port 8000.
