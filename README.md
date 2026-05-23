# AI Document Platform

**Enterprise AI platform for automated IT procurement document generation.**
Multi-agent workflow (Agno) · FastAPI · React · PostgreSQL · Redis · Docker

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
cp backend/.env.example backend/.env
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
| API Docs         | http://localhost:8000/api/docs |
| pgAdmin (dev)    | http://localhost:5050        |
| Redis (dev)      | http://localhost:8081        |

---

## Local Development

### Backend

```bash
cd backend
pip install uv
uv pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
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

---

## Extending

**Add a new agent:** create `agents/<name>/agent.py`, add to `WorkflowRunner`, extend the `StateMachine`, update frontend `AGENT_META`.

**Add a document type:** add Jinja2 template in `templates/<type>/base.j2`, extend the route validator, add option to the frontend form.

**Connect MCP:** set `MCP_SERVER_URL` + `MCP_API_KEY`. The `MCPClient` expects: `/search`, `/retrieve`, `/semantic-search`, `/templates`, `/regulations`, `/health`.

---

## License

MIT
