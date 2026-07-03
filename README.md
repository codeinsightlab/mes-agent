# MES Agent

Independent MES Agent research project. This initial skeleton only verifies project structure, startup commands, and HTTP communication between a Vue frontend and FastAPI backend.

No model, Agent orchestration, database, login, permission, queue, cache, or vector-store functionality is included.

## Project Structure

```text
.
├── backend
│   ├── .env.example
│   ├── README.md
│   ├── app
│   │   └── main.py
│   └── requirements.txt
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
