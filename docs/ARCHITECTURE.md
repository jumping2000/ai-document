# AI Document Platform — Architecture

## Overview

Multi-agent AI platform for automatic generation of enterprise IT procurement documents.
Supports three document types: **Capitolato di Gara** (procurement specification), **Requisiti Funzionali e Tecnici** (functional/technical requirements), and **Documento Tecnico** (technical architecture document).

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React + TS)                      │
│  WorkflowMonitor ← WebSocket ← Zustand ← useWorkflowStream      │
│  MCPSettings ← REST API ← MCPConnection[]                       │
│  TemplateSettings ← REST API ← TemplateConfig                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / WebSocket
┌────────────────────────────▼────────────────────────────────────┐
│                       FASTAPI BACKEND                           │
│  /api/v1/workflow/*   — workflow lifecycle                       │
│  /api/v1/mcp/*        — MCP connection management               │
│  /api/v1/templates/*  — template configuration                  │
│  /ws/workflow/{id}    — real-time event streaming                │
│  /health              — health check                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    WORKFLOW RUNNER                              │
│                                                                 │
│  StateMachine → drives state transitions with guards            │
│                                                                 │
│  INIT → BRIEFING → ENRICHMENT → VALIDATION → WRITING → QA → ✓  │
│              ↑_________↑__________↑           ↑______↑          │
│                    (retry loops)            (retry loop)         │
└──────┬─────────┬──────────┬──────────┬──────────┬───────────────┘
       │         │          │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
  │ Orch.  │ │  Req.  │ │ Proc.  │ │ Writer │ │Quality │
  │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
  └────────┘ └────────┘ └───┬────┘ └────────┘ └────────┘
                             │
                    ┌────────▼────────┐
                    │   MCP Client    │
                    │  (RAG / KB)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  MCP Server     │
                    │  (Vector DB)    │
                    └─────────────────┘
```

---

## Document Types

| Type | Description | Sections |
|------|-------------|----------|
| `capitolato` | Procurement specification for public tenders | 11 sections: Premessa, Oggetto, Requisiti Funzionali, Requisiti Tecnici, Sicurezza, SLA, ecc. |
| `requisiti` | Functional and technical requirements document | 6 sections: Introduzione, Requisiti Funzionali, Requisiti Tecnici, Sicurezza, Architettura, Integrazione |
| `documento` | Technical architecture document | 3 main sections (with subsections): Ambito e Finalità, Descrizione Architettura, Linee Guida |

Each type is configured via `templates/{type}/template.yaml` (structure, validation rules, SLA) and `templates/{type}/base.j2` (Jinja2 rendering template).

---

## Agent Responsibilities

| Agent | State | Input | Output |
|-------|-------|-------|--------|
| **Requirement** | BRIEFING | raw user input, document_type | `RequirementResult` — structured requirements, summary, missing_fields, confidence |
| **Procurement** | ENRICHMENT | requirements, MCP context | `ProcurementResult` — enriched requirements, sources, standards_applied |
| **Orchestrator** | VALIDATION | WorkflowContext | validates completeness via internal LLM agent |
| **LeadWriter** | WRITING | enriched_requirements, quality_issues | `WriterResult` — markdown content, sections, docx_path, pdf_path |
| **Quality** | QUALITY_ANALYSIS | content, requirements, document_type | `QualityReport` — score, passed, issues, suggestions, section_scores |

### Requirement Agent

Collects and structures raw user input into the canonical schema:
- **project**: title, organization, reference_code, description
- **scope**: objectives, in_scope, out_of_scope
- **functional_requirements**: id, title, description, priority (MUST/SHOULD/COULD)
- **technical_requirements**: id, category, description, constraint
- **sla**: K1 (Qualità del Codice), K2 (Tasso Difettosità), K3 (Ritardo Consegna)
- **security_compliance**: standards, requirements, data_classification
- **timeline**: project_start, go_live, milestones
- **integrations**: system, type, protocol
- **stakeholders**: role, responsibilities
- **constraints**, **regulatory_references**, **evaluation_criteria**, **budget**

Critical fields (used for confidence scoring): `project.title`, `project.organization`, `scope.objectives`, `functional_requirements`, `technical_requirements`, `sla.K1`, `sla.K2`, `sla.K3`, `security_compliance.standards`, `timeline.go_live`.

### Procurement Agent

Enriches requirements with external knowledge:
- Loads KB context via `RetrievalSkill` (if MCP connection available)
- Applies standards: ISO 27001, ISO 9001, GDPR, OWASP, CIS benchmarks
- References Italian regulations: D.Lgs. 36/2023, AgID guidelines
- Adds SLA templates and security requirements from KB

### LeadWriter Agent

Generates the final document:
1. Loads Jinja2 template from `templates/{type}/base.j2`
2. Renders template with enriched requirements as context
3. Calls LLM with template + requirements + quality_issues (as revision notes)
4. Exports to DOCX and PDF via `ExportSkill`

Fallback templates exist for all three document types (capitolato, requisiti, documento) in case the Jinja2 template is unavailable.

### Quality Agent

Reviews generated document against:
- Hardcoded checklist (8 items: SLA values, security standards, structure, contradictions, etc.)
- Template-specific quality checks from `template.yaml`
- Scoring: 0.0–1.0, threshold at `workflow_quality_threshold` (default 0.75)
- Graceful degradation zones:
  - Score < 0.4: hard failure
  - 0.4 ≤ score < threshold: pass with warnings
  - Score ≥ threshold: pass
- `needs_enrichment` signal triggers re-enrichment instead of re-writing

---

## State Machine Transitions

```
INIT           ──[START]──────────────────────────► BRIEFING
BRIEFING       ──[REQUIREMENTS_COLLECTED]──────────► ENRICHMENT
ENRICHMENT     ──[ENRICHMENT_DONE]────────────────► VALIDATION
VALIDATION     ──[VALIDATION_PASSED]───────────────► WRITING
VALIDATION     ──[VALIDATION_FAILED, retry<3]──────► BRIEFING (loop)
VALIDATION     ──[VALIDATION_FAILED, retry≥3]──────► FAILED
WRITING        ──[WRITING_DONE]────────────────────► QUALITY_ANALYSIS
QUALITY_ANALYSIS ──[QUALITY_PASSED]────────────────► COMPLETED
QUALITY_ANALYSIS ──[QUALITY_FAILED_WRITING, retry<3]► WRITING (loop)
QUALITY_ANALYSIS ──[QUALITY_FAILED_WRITING, retry≥3]► FAILED
QUALITY_ANALYSIS ──[QUALITY_FAILED_ENRICHMENT, retry<3]► ENRICHMENT (loop)
QUALITY_ANALYSIS ──[QUALITY_FAILED_ENRICHMENT, retry≥3]► FAILED
ANY (non-terminal) ──[FATAL_ERROR]────────────────► FAILED
```

**Triggers enum:** `START`, `REQUIREMENTS_COLLECTED`, `ENRICHMENT_DONE`, `VALIDATION_PASSED`, `VALIDATION_FAILED`, `WRITING_DONE`, `QUALITY_PASSED`, `QUALITY_FAILED_WRITING`, `QUALITY_FAILED_ENRICHMENT`, `FATAL_ERROR`, `HUMAN_APPROVED`

**Human-in-the-loop:** the `QUALITY_ANALYSIS` → `COMPLETED` transition requires `HUMAN_APPROVED` trigger via `POST /workflow/{id}/approve`.

---

## Retry Budget

| Loop | Counter | Max | Exhausted → |
|------|---------|-----|-------------|
| Validation | `ctx.retry_count` | 3 | FAILED |
| Writing quality | `ctx.writing_retry_count` | 3 | FAILED |
| Enrichment | `ctx.enrichment_retry_count` | 3 | FAILED |

After all retries exhausted, graceful degradation may still allow completion if quality score > 0.5.

---

## Template System

Each document type has two files:

### `templates/{type}/template.yaml` — Structure & Configuration

```yaml
template_id: capitolato
name: Capitolato di Gara
description: ...
language: it

sections:
  - id: premessa
    title: Premessa
    required: true

required_fields:
  - path: project.title
    label: Titolo Progetto
  - path: functional_requirements
    label: Requisiti Funzionali
    min_items: 3

sla_rules:
  expected_kpis:
    - field: K1
      label: Qualità del Codice
  expected_kpos:
    - field: K2
      label: Tasso Difettosità

quality_checks:
  - id: sla_values
    label: Valori SLA espliciti
    enabled: true

retrieval_queries:
  - "standard {security_compliance.standards}"
  - "requisiti {project.title}"
```

### `templates/{type}/base.j2` — Jinja2 Rendering Template

Uses the enriched requirements dict as template context. Produces the final markdown.

### Template Overrides & Caching

- Templates can be overridden per-document via `{documents_base_path}/template_overrides/{type}/template.yaml`
- Config is cached with `@lru_cache(maxsize=10)` — call `invalidate_template_cache()` after writes
- If `template.yaml` missing, structure is derived by parsing `##` headings from `base.j2`
- Template API: `GET/PUT /api/v1/templates/{type}/config`, `POST /reset`, `POST /validate-preview`

---

## Skills

### Validation Skill (`skills/validation/`)

| Function | Purpose |
|----------|---------|
| `validate_requirements_completeness()` | Checks required_fields from template.yaml, enforces min_items |
| `validate_sla_consistency()` | Validates SLA has expected KPI/KPO fields (presence only) |
| `validate_document_sections()` | Checks required sections present in markdown via regex |
| `detect_placeholder_content()` | Finds [TBD], [TODO], [PLACEHOLDER] in content |
| `score_requirement_richness()` | Computes 0.0–1.0 score (weighted: 30% functional, 20% technical, 15% SLA, 10% integrations, 10% stakeholders, 10% security, 5% timeline) |

### Retrieval Skill (`skills/retrieval/`)

Builds KB context from requirements:
1. Loads `retrieval_queries` from template.yaml
2. Resolves `{placeholder}` tokens using dot-notation from requirements
3. Runs queries in parallel (Semaphore-limited, max 2 concurrent)
4. Deduplicates and sorts by relevance_score
5. Returns `RetrievedContext` with formatted markdown

### Export Skill (`skills/export/`)

| Method | Output | Styling |
|--------|--------|---------|
| `export_docx()` | .docx file | Calibri 10pt, 1" margins, dark blue (#1A1A2E) title |
| `export_pdf()` | .pdf file | A4, 2.5cm margins, ReportLab rendering; tables → bullet text |

Files stored at: `{documents_base_path}/{workflow_id}/{doc_type}_{uuid}.{docx|pdf}`

---

## MCP Integration

### MCP Client (`mcp/client/mcp_client.py`)

Protocol methods (all with 15-min TTL cache, 30s timeout, 3 retries):

| Method | Returns |
|--------|---------|
| `list_tools()` | `list[{name, description, input_schema}]` |
| `call_tool(name, args)` | `Any` (parsed JSON or text) |
| `list_resources()` | `list[{uri, name, description, mime_type}]` |
| `read_resource(uri)` | `Any` (text or binary) |
| `list_prompts()` | `list[{name, description, arguments}]` |
| `get_prompt(name, args)` | `{messages: [...]}` |
| `discover_all()` | `{tools, resources, prompts, summary}` |

Transport: auto-detects SSE (`/sse` URL suffix) vs StreamableHttp. Uses `X-API-Key` header for authentication.

### NanoRAG Adapter (`mcp/client/adapters/nanorag.py`)

High-level wrapper for RAG-specific operations:
- `search_documents(query, limit, kb_id)` — discovers search tool by name pattern, maps parameters, normalizes results

### MCP API Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/mcp/connections` | List all connections |
| POST | `/mcp/connections` | Create + discover capabilities |
| GET | `/mcp/connections/{id}` | Get connection details |
| DELETE | `/mcp/connections/{id}` | Delete connection |
| POST | `/mcp/connections/{id}/refresh` | Re-discover capabilities |
| POST | `/mcp/connections/{id}/call` | Call a tool on MCP server |
| POST | `/mcp/test` | Test connection without saving |
| GET | `/mcp/connections/{id}/resource?uri=` | Read a resource |

---

## Database Schema

PostgreSQL 16 via SQLAlchemy async + Alembic migrations (3 migrations).

### Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | User accounts | email (unique), hashed_password, role (default "user"), is_active |
| `workflows` | Workflow instances | owner_id (FK), title, document_type, state (indexed), retry_count, metadata (JSON), mcp_connection_id (FK) |
| `workflow_states` | State transition audit | workflow_id (FK, indexed), from_state, to_state, trigger, payload (JSON) |
| `agent_outputs` | Agent execution results | workflow_id (FK, indexed), agent_name, output_type, content (JSON), token_usage (JSON), duration_ms |
| `documents` | Generated documents | workflow_id (FK, indexed), name, format (markdown/docx/pdf), content_md, file_path, version |
| `quality_reports` | Quality review results | workflow_id (FK, indexed), score (float), passed (bool), issues/suggestions/section_scores (JSON) |
| `audit_logs` | Audit trail | workflow_id (FK, indexed), user_id, action, detail (JSON), ip_address |
| `mcp_connections` | MCP server connections | name, url, transport, api_key, default_kb_id, is_active, discovered_tools/resources/prompts/kbs (JSON), health_status |

All tables include `created_at` and `updated_at` timestamps via `TimestampMixin`.

---

## Real-Time Events

WebSocket endpoint: `ws://host/ws/workflow/{workflow_id}`

Implemented via in-process `asyncio.Queue` per workflow; for multi-worker deployments, replace with Redis pub/sub.

| Event | Data Payload |
|-------|------|
| `state_change` | `{state: "BRIEFING"}` |
| `agent_start` | `{agent: "requirement"}` |
| `agent_done` | `{agent: "requirement", duration_ms: 1200}` |
| `validation_result` | `{valid: true, confidence: 0.85}` |
| `validation_failed` | `{issues: [...]}` |
| `richness_score` | `{score: 0.7}` |
| `placeholders_detected` | `{placeholders: [...]}` |
| `document_sections_warning` | `{sections: [...]}` |
| `quality_report` | `{score: 0.92, passed: true, issues: [...]}` |
| `completed` | `{quality_score: 0.92}` |
| `failed` | `{error: "..."}` |
| `heartbeat` | `{}` (30s timeout) |

Terminal events (completed/failed) auto-close the WebSocket connection.

---

## LLM Provider Abstraction

4 providers supported, selected via `DEFAULT_AI_PROVIDER` env var:

| Provider | Setting | Agno Class |
|----------|---------|------------|
| OpenAI | `openai` | `OpenAIChat` |
| Anthropic | `anthropic` | `Claude` |
| OpenRouter | `openrouter` | `OpenRouter` |
| Ollama (local) | `ollama` | `Ollama` |

Default model: `gpt-4o`. All providers use unified interface via `get_model_adapter()` factory function.

---

## Application Configuration

Two config layers:

### 1. Pydantic Settings (`app/core/config.py`)
Environment variables with validation — server settings, API keys, database URLs, workflow thresholds.

### 2. YAML Configuration (`config/configuration.yaml`)
Runtime tunables loaded via `app_cfg("section.key", default)`:
- Quality thresholds (severe: 0.4, moderate: 0.5)
- Retrieval limits (max_docs: 8, max_concurrency: 2)
- Export styling (fonts, colors, margins)
- Runner graceful degradation threshold (0.5)

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, uvicorn |
| **AI/LLM** | Agno framework, OpenAI/Anthropic/OpenRouter/Ollama |
| **Database** | PostgreSQL 16, SQLAlchemy async, Alembic |
| **Cache** | Redis 7 |
| **Document** | Jinja2, python-docx, ReportLab |
| **MCP** | FastMCP, httpx |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS 3.4, Zustand 5 |
| **Observability** | structlog, OpenTelemetry, Prometheus |
| **Container** | Docker, Docker Compose v2 |

---

## Technology Constraints & Notes

1. **Agno framework**: Used for agent wrapping. Direct `arun()` call — structured output enforced via JSON-only system prompts. JSON extraction via `extract_json()` with code fence stripping and trailing comma recovery.

2. **MCP integration**: Standard HTTP REST stub in development (`scripts/mcp_stub.py`). Production: replace with real vector-DB backed server (e.g., Qdrant + LlamaIndex or Weaviate).

3. **python-docx**: Does not support all markdown features. `ExportSkill` handles H1-H4, bullets, numbered lists, bold/italic inline. Tables converted to bullet text in PDF (ReportLab limitation).

4. **WebSocket event bus**: In-process `asyncio.Queue` per workflow. For multi-worker deployments, replace with Redis pub/sub.

5. **Authentication**: JWT scaffolded in config but routes not yet guarded. Add `Depends(get_current_user)` to each router before production deploy. Frontend uses HTTP Basic Auth via Nginx `.htpasswd`.

6. **Template system**: `template.yaml` defines structure and validation rules; `base.j2` defines rendering. Both must be kept in sync. Cache invalidated on template save.

7. **SQLite in tests**: Test suite uses `aiosqlite` for speed; production uses PostgreSQL with `asyncpg`.

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Workflow E2E (GPT-4o) | < 90s |
| Requirement agent | < 15s |
| Procurement + MCP | < 20s |
| Writing (full doc) | < 40s |
| Quality check | < 15s |
| WebSocket event latency | < 200ms |
