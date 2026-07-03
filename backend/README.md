# MES Agent Backend

FastAPI backend for the MES Agent research project.

Current backend capabilities:

- `GET /api/health`
- `POST /api/chat`
- Provider-independent LLM client protocol with DeepSeek as the first provider.

It does not include MES data access, Agent orchestration, tool calling, streaming, or session persistence.

The chat API is single-turn only: one request produces one response, and the backend does not store or reuse previous user messages.

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

Set `LLM_API_KEY` in `.env` before calling `/api/chat`.

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
- `finish_reason`
- `usage`
