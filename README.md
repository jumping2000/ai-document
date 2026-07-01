# AI Document Platform

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Enterprise AI platform for automated IT procurement document generation.**

Generates three document types via a multi-agent workflow:
- **Capitolato di Gara** — Public procurement specifications (11 sections)
- **Requisiti Funzionali e Tecnici** — Functional & technical requirements (6 sections)
- **Documento Tecnico** — Technical architecture document (3 sections with subsections)

## Features

- 🧠 **Multi-agent workflow**: 5 specialized agents (Requirement, Procurement, Orchestrator, LeadWriter, Quality) with state machine orchestration
- 🔄 **Retry budgets**: Automatic retry loops for validation, writing quality, and enrichment phases with graceful degradation
- 📡 **Real-time monitoring**: WebSocket event streaming for live UI updates during document generation
- 🌐 **MCP integration**: Model Context Protocol support for external knowledge bases (RAG)
- 📄 **Flexible templates**: YAML-driven template and prompt configuration with Jinja2 rendering, editable via API. Agent LLM prompts live in `config/agents/*.yaml` — modifiable without Docker rebuild
- 🎨 **Multi-provider LLM**: OpenAI, Anthropic, OpenRouter, or Ollama (local) — selectable via environment variable
- 📤 **Multi-format export**: DOCX (python-docx) and PDF (ReportLab) export
- 🌍 **i18n**: Italian and English UI with locale persistence
- 🎭 **Theme support**: Light, dark, and system-following themes
- 🐳 **Docker Compose**: Single-command deployment with PostgreSQL, Redis, Nginx

## Architecture Overview

```
React UI (Vite + TypeScript + Tailwind + Zustand)
        │
        ▼  POST /api/v1/workflow/start
FastAPI Backend (port 8001)
        │
        ▼
WorkflowRunner (background task)
        │
        ├── StateMachine (8 states, 12 transitions, 3 retry budgets)
        │
        ├── RequirementAgent   ─ structures raw input → canonical schema
        ├── ProcurementAgent   ─ enriches via MCP/RAG (ISO, GDPR, D.Lgs 36/2023)
        ├── OrchestratorAgent  ─ validates completeness
        ├── LeadWriterAgent    ─ generates Jinja2 + LLM content
        └── QualityAgent       ─ scores output (0.0–1.0), issues & suggestions
        │
        ▼  WebSocket /ws/workflow/{id}
React WorkflowMonitor (live state, agents, quality gauge, event log)
        │
        ▼
Export: .docx (python-docx) + .pdf (ReportLab)
```

### State Machine

```
INIT → BRIEFING → ENRICHMENT → VALIDATION → WRITING → QUALITY_ANALYSIS → COMPLETED
         ↑___________↑____________↑            ↑_________↑
              (retry loops)                (retry loops)
                                                  ↓
                                               FAILED
```

Three independent retry budgets (3 max each): validation, writing quality, enrichment.

---

## Quick Start

### Prerequisites
- Docker + Docker Compose v2
- LLM API key (OpenAI, Anthropic, OpenRouter, or Ollama)

### 1. Configure

```bash
cp .env.example .env
# Set at minimum: OPENAI_API_KEY (or your chosen provider)
```

### 2. Run

```bash
# Full stack (frontend + backend + postgres + redis)
docker compose up --build

# Dev stack (includes pgAdmin + Redis Commander)
docker compose --profile dev up --build
```

### 3. Access

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://localhost:3001 | HTTP Basic Auth (default: admin/admin) |
| API (Swagger) | http://localhost:8001/docs | Interactive API docs |
| Health check | http://localhost:8001/health | `{"status": "ok"}` |
| pgAdmin (dev) | http://localhost:5050 | admin@local.dev / admin |
| Redis Commander (dev) | http://localhost:8081 | Redis browser |

---

## Local Development

### Backend (Python 3.11+)

```bash
cd backend
# Windows: .venv\Scripts\Activate.ps1
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8001
```

### Frontend (Node.js + fnm on Windows)

```bash
cd frontend
npm install
npm run dev        # → http://localhost:5173 (proxies API to :8001)
```

### Running Tests

```bash
cd backend
uv run pytest app/tests/ -v --cov=app --cov-report=html
```

---

## Document Types

| Type | Template | Sections | Use Case |
|------|----------|----------|----------|
| `capitolato` | `templates/capitolato/` | 11 | Public procurement specification (Capitolato di Gara) |
| `requisiti` | `templates/requisiti/` | 6 | Functional and technical requirements document |
| `documento` | `templates/documento/` | 3 (with subsections) | Technical architecture document |

Each type has a `template.yaml` (structure, SLA rules, quality checks, retrieval queries) and a `base.j2` (Jinja2 rendering template). Templates are configurable via the Template Settings UI and API.

### SLA Model

All documents use K1/K2/K3 SLA metrics:
- **K1** — Qualità del Codice (Code Quality)
- **K2** — Tasso Difettosità in Esercizio (Defect Rate)
- **K3** — Ritardo Consegna Deliverable (Delivery Delay)

---

## API Endpoints

### Workflow

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/workflow/start` | Start a new workflow |
| `GET` | `/api/v1/workflow/{id}` | Get workflow status |
| `POST` | `/api/v1/workflow/{id}/approve` | Human-in-the-loop approval |
| `POST` | `/api/v1/workflow/{id}/retry` | Retry failed workflow |
| `GET` | `/api/v1/workflow/{id}/documents` | List generated documents |
| `GET` | `/api/v1/workflow/{id}/quality-report` | Get quality report |
| `POST` | `/api/v1/workflow/{id}/export/{format}` | Export to docx/pdf |
| `GET` | `/api/v1/workflow/{id}/download/{format}` | Download exported file |

### MCP Connections

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/mcp/connections` | List connections |
| `POST` | `/api/v1/mcp/connections` | Create + discover capabilities |
| `DELETE` | `/api/v1/mcp/connections/{id}` | Delete connection |
| `POST` | `/api/v1/mcp/connections/{id}/refresh` | Re-discover capabilities |
| `POST` | `/api/v1/mcp/connections/{id}/call` | Call MCP tool |
| `POST` | `/api/v1/mcp/test` | Test connection (no save) |

### Templates

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/templates/` | List document types |
| `GET` | `/api/v1/templates/{type}/config` | Get template config |
| `PUT` | `/api/v1/templates/{type}/config` | Update template config |
| `POST` | `/api/v1/templates/{type}/reset` | Revert to defaults |
| `POST` | `/api/v1/templates/{type}/validate-preview` | Test validation |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://host/ws/workflow/{id}` | Real-time event stream |

Events: `state_change`, `agent_start`, `agent_done`, `validation_result`, `validation_failed`, `quality_report`, `completed`, `failed`, `heartbeat`

---

## Configuration

### LLM Providers

Set `DEFAULT_AI_PROVIDER` and `DEFAULT_AI_MODEL` in `.env`:

```env
# OpenAI
DEFAULT_AI_PROVIDER=openai
DEFAULT_AI_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Anthropic
DEFAULT_AI_PROVIDER=anthropic
DEFAULT_AI_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...

# OpenRouter (multi-provider)
DEFAULT_AI_PROVIDER=openrouter
DEFAULT_AI_MODEL=openai/gpt-4o
OPENROUTER_API_KEY=or-...

# Ollama (local/on-prem)
DEFAULT_AI_PROVIDER=ollama
DEFAULT_AI_MODEL=llama3.1
OLLAMA_URL=http://localhost:11434
```

### Key Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_TOKENS` | `16384` | Max output tokens per LLM call. The requirement agent needs ~8000+ to produce complete structured JSON for large inputs. Lower values risk truncated (invalid) JSON |
| `WORKFLOW_QUALITY_THRESHOLD` | `0.75` | Minimum quality score (0.0–1.0) |
| `WORKFLOW_MAX_RETRIES` | `3` | Max retries per phase |
| `MCP_SERVER_URL` | — | External MCP/RAG server URL |
| `MCP_TIMEOUT_SECONDS` | `30` | MCP request timeout |

---

## Project Structure

```
ai-document/
├── backend/                  # Python FastAPI application
│   ├── app/
│   │   ├── main.py           # Entrypoint (CORS, middleware, routes)
│   │   ├── core/             # Config, LLM factory, YAML loader
│   │   ├── api/routes/       # REST endpoints (workflow, MCP, templates)
│   │   ├── api/websocket/    # WebSocket event streaming
│   │   ├── agents/           # 5 LLM agents (orchestrator, requirement, etc.)
│   │   ├── skills/           # Validation, retrieval, export skills
│   │   ├── db/               # SQLAlchemy models + async session
│   │   ├── mcp/client/       # MCP protocol client + NanoRAG adapter
│   │   └── workflows/        # State machine + runner
│   ├── templates/            # Jinja2 templates + YAML configs
│   ├── alembic/              # DB migrations
│   └── tests/                # pytest test suite (91 tests)
├── frontend/                 # React + TypeScript + Vite SPA
│   └── src/
│       ├── pages/            # WorkflowMonitor, MCPSettings, TemplateSettings
│       ├── stores/           # Zustand global state
│       ├── hooks/            # useWorkflowStream (WebSocket)
│       ├── i18n/             # Italian/English translations
│       └── types/            # TypeScript interfaces
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   ├── backend.md
│   └── frontend.md
├── nginx/                    # Nginx config + .htpasswd
├── scripts/                  # Example workflow, MCP stub, init.sql
├── docker-compose.yml        # Full stack deployment
└── .env.example              # Configuration template
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, uvicorn, Agno (multi-agent) |
| **Database** | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic |
| **Cache** | Redis 7 |
| **LLM** | OpenAI, Anthropic, OpenRouter, Ollama |
| **Documents** | Jinja2, python-docx, ReportLab |
| **MCP** | FastMCP, httpx |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS 3.4, Zustand 5 |
| **Observability** | structlog, OpenTelemetry, Prometheus |
| **Infrastructure** | Docker, Docker Compose v2, Nginx |

---

## Extending

**Add a new agent:** Create `agents/<name>/agent.py`, add to `OrchestratorAgent` and `WorkflowRunner`, extend the `StateMachine`, update frontend agent metadata.

**Add a new document type:** Create `templates/<type>/template.yaml` + `templates/<type>/base.j2`, add to `LeadWriterAgent` fallback templates, extend `document_type` pattern in `workflow.py` route, add frontend form option and translations.

**Connect MCP:** Set `MCP_SERVER_URL` + `MCP_API_KEY` in `.env`. The `MCPClient` auto-discovers tools, resources, prompts, and KBs.

---

## License

MIT

