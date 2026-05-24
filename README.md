# AI Document Platform

[![Build Status](https://img.shields.io/github/actions/workflow/status/jumping2000/ai-document/ci.yml?branch=master)](https://github.com/jumping2000/ai-document/actions)
[![Codecov](https://img.shields.io/codecov/c/github/jumping2000/ai-document.svg)](https://codecov.io/gh/jumping2000/ai-document)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Enterprise AI platform for automated IT procurement document generation.**

- 🧭 Overview: a modular platform that automatically generates procurement documents, technical specifications, and tender dossiers using a multi-agent workflow.
- ⚙️ Architecture: Python backend (FastAPI) for asynchronous workflows, React/TypeScript frontend for real-time monitoring, persistent services (Postgres) and cache (Redis).
- 🧠 LLM & Agents: provider-agnostic LLM integration (OpenAI, Anthropic, OpenRouter, Ollama) orchestrated by specialized agents (Requirement, Procurement, Orchestrator, LeadWriter, Quality).
- 🔒 Security & governance: secret management via `.env`/CI, on-premise options (Ollama) for sensitive data, and non-sharing policies.
- ⚡ Scalability: containerized components for deployment with Docker Compose/orchestration; asynchronous workers and retry budgets for resilience.
- 🧾 Output: export to `docx`, `pdf`, and markdown formats; audit trail and quality reports.

Primary technologies: Agno (multi-agent), FastAPI, React, SQLAlchemy/AsyncPG, Redis, Alembic, Structlog, Jinja2, Docker.

---

## Architecture Overview

```
User Input (React UI)
        │
        ▼
POST /api/v1/workflow/start
        │
        ▼
WorkflowRunner (background task)
        │
        ├── StateMachine (explicit states + guards)
        │
        ├── RequirementAgent   ─ structures raw input
        ├── ProcurementAgent   ─ enriches via MCP/RAG
        ├── OrchestratorAgent  ─ validates completeness
        ├── LeadWriterAgent    ─ generates Jinja2 + AI content
        └── QualityAgent       ─ scores and reviews output
        │
        ▼
WebSocket /ws/workflow/{id}  ←→  React WorkflowMonitor (live events)
        │
        ▼
Export: .docx (python-docx) + .pdf (reportlab)
```

### State Machine

```
INIT → BRIEFING → ENRICHMENT → VALIDATION → WRITING → QUALITY_ANALYSIS → COMPLETED
            ↑__________↑__________↑ (retry)        ↑_________↑ (retry)
                                                              ↓
                                                           FAILED
```

---

## Quick Start

### Prerequisites
- Docker + Docker Compose v2
- OpenAI API key (or Anthropic)

### 1. Configure

```bash
cp .env.example .env
# Set OPENAI_API_KEY at minimum
```

### 2. Run

```bash
# Full stack
docker compose up --build

# Dev stack (pgAdmin + Redis Commander included)
docker compose --profile dev up --build
```

### 3. Access

| Service          | URL                          |
|------------------|------------------------------|
| Frontend         | http://localhost:3000        |
| API Docs         | http://localhost:8001/api/docs |
| pgAdmin (dev)    | http://localhost:5050        |
| Redis (dev)      | http://localhost:8081        |

---

## Local Development

### Backend

```bash
cd backend
pip install uv
uv pip install -e ".[dev]"
cp ../.env.example ../.env
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # → http://localhost:5173
```

---

## API Reference

```
POST /api/v1/workflow/start          Start a new workflow
GET  /api/v1/workflow/{id}           Get workflow status
POST /api/v1/workflow/{id}/approve   Human-in-the-loop approval
POST /api/v1/workflow/{id}/retry     Retry a failed workflow
GET  /api/v1/workflow/{id}/documents List generated documents
GET  /api/v1/workflow/{id}/quality-report Quality report
WS   /ws/workflow/{id}              Live event stream
```

### WebSocket Events

| Event             | Description                        |
|-------------------|------------------------------------|
| `state_change`    | Workflow moved to a new state      |
| `agent_start`     | Agent started execution            |
| `agent_done`      | Agent finished with duration       |
| `quality_report`  | Quality analysis completed         |
| `completed`       | Workflow finished successfully     |
| `failed`          | Workflow failed                    |
| `heartbeat`       | Keep-alive ping                    |

---

## Testing

```bash
cd backend
pytest app/tests/ -v --cov=app --cov-report=html
```

---

## Configuration

Key `.env` variables:

```env
OPENAI_API_KEY=sk-...
DEFAULT_AI_MODEL=gpt-4o
MCP_SERVER_URL=http://...          # External RAG/KB (optional)
WORKFLOW_QUALITY_THRESHOLD=0.75    # Min pass score (0.0–1.0)
WORKFLOW_MAX_RETRIES=3             # Retry budget per loop
```

### Env file placement and Docker Compose

- The single `.env` file in the project root serves both Docker Compose variable substitution (e.g. `${POSTGRES_PASSWORD}`) and backend runtime configuration (loaded via `env_file:` in `docker-compose.yml` and by Pydantic Settings locally).
- Copy from `.env.example`:
```bash
cp .env.example .env
```
- Do NOT commit `.env`. Use CI/CD secrets for production.

To run with the optional development services (Ollama, pgAdmin, Redis Commander):

```bash
docker compose --profile dev up --build
```

### LLM Providers (examples)

You can select the LLM provider via `DEFAULT_AI_PROVIDER` and the model via `DEFAULT_AI_MODEL` in `.env`.

- OpenAI (cloud)

```env
DEFAULT_AI_PROVIDER=openai
DEFAULT_AI_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

Quick smoke test (requires `openai` Python SDK installed):

```bash
python - <<'PY'
import os
import openai
openai.api_key = os.getenv('OPENAI_API_KEY')
print(openai.Model.list()[:1])
PY
```

- OpenRouter (broker/multi-provider)

```env
DEFAULT_AI_PROVIDER=openrouter
DEFAULT_AI_MODEL=gpt-5.4-mini
OPENROUTER_API_KEY=or-...
OPENROUTER_BASE_URL=https://api.openrouter.ai
```

Quick check (basic HTTP health/example request — adjust endpoint per OpenRouter docs):

```bash
curl -s -H "Authorization: Bearer $OPENROUTER_API_KEY" "$OPENROUTER_BASE_URL/health" || echo "no health endpoint; try provider-specific chat endpoint"
```

- Ollama (local / on‑prem)

```env
DEFAULT_AI_PROVIDER=ollama
DEFAULT_AI_MODEL=llama3.1
OLLAMA_URL=http://localhost:11434
OLLAMA_API_KEY=
```

Smoke test (health):

```bash
curl -fsS $OLLAMA_URL/health && echo "Ollama OK" || echo "Ollama not responding"
```

Notes:
- Use `.env` in the project root for all configuration (copy from `.env.example`).
- For production, set provider keys in your CI/CD secret store rather than committing `.env` files.


---

## Extending

**Add a new agent:** create `agents/<name>/agent.py`, add to `WorkflowRunner`, extend the `StateMachine`, update frontend `AGENT_META`.

**Add a document type:** add Jinja2 template in `templates/<type>/base.j2`, extend the route validator, add option to the frontend form.

**Connect MCP:** set `MCP_SERVER_URL` + `MCP_API_KEY`. The `MCPClient` expects: `/search`, `/retrieve`, `/semantic-search`, `/templates`, `/regulations`, `/health`.

---

## License

MIT
