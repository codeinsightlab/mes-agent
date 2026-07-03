# MES Agent

Independent MES Agent research project. The current skeleton verifies project structure, startup commands, HTTP communication, and a minimal provider-independent LLM chat layer.

DeepSeek is the first supported LLM provider. No Agent orchestration, MES database, login, permission, queue, cache, vector-store, tool calling, streaming, or session persistence functionality is included.

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

Then edit `backend/.env` and set `LLM_API_KEY` to your own DeepSeek API key. Do not put real tokens in `.env.example`, README, logs, or tests.

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
