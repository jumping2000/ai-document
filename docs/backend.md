# Backend Components

## Overview

The backend is a Python 3.11+ FastAPI application that orchestrates multi-agent AI workflows for automatic document generation. It integrates LLM providers (OpenAI, Anthropic, OpenRouter, Ollama), MCP-based knowledge retrieval, and document export (DOCX, PDF).

**Entrypoint:** `app/main.py` — FastAPI app on `0.0.0.0:8001`
**Package manager:** `uv` (Astral)

---

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entrypoint, CORS, middleware, lifespan
│   ├── core/                # Configuration & utilities
│   │   ├── config.py        # Pydantic Settings (env vars)
│   │   ├── llm.py           # LLM provider factory (OpenAI/Anthropic/OpenRouter/Ollama)
│   │   ├── app_config.py    # YAML config loader (app_cfg function)
│   │   ├── agent_config.py  # Per-agent YAML config loader
│   │   └── json_extract.py  # JSON extraction from LLM responses
│   ├── api/
│   │   ├── routes/
│   │   │   ├── workflow.py  # Workflow lifecycle endpoints
│   │   │   ├── mcp.py       # MCP connection management
│   │   │   └── templates.py # Template configuration
│   │   └── websocket/
│   │       └── stream.py    # WebSocket event streaming
│   ├── agents/
│   │   ├── orchestrator/    # Orchestrates workflow phases
│   │   ├── requirement/     # Structures raw input → canonical schema
│   │   ├── procurement/     # Enriches requirements via MCP/KB
│   │   ├── lead_writer/     # Generates documents via Jinja2 + LLM
│   │   └── quality/         # Reviews generated documents
│   ├── skills/
│   │   ├── validation/      # Structural & SLA validation
│   │   ├── retrieval/       # KB context building
│   │   └── export/          # DOCX/PDF export
│   ├── db/
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   └── session.py       # Async session factory
│   ├── mcp/
│   │   └── client/
│   │       ├── mcp_client.py    # MCP protocol client (FastMCP)
│   │       └── adapters/
│   │           └── nanorag.py   # High-level RAG adapter
│   ├── workflows/
│   │   ├── execution/
│   │   │   └── runner.py    # WorkflowRunner — background task executor
│   │   └── state_machine/
│   │       └── machine.py   # StateMachine with guards & transitions
│   └── tests/               # pytest test suite (asyncio)
├── templates/
│   ├── capitolato/
│   │   ├── template.yaml    # Structure, validation rules, SLA
│   │   └── base.j2          # Jinja2 rendering template
│   ├── requisiti/
│   │   ├── template.yaml
│   │   └── base.j2
│   └── documento/
│       ├── template.yaml
│       └── base.j2
├── alembic/                 # DB migrations
├── config/
│   ├── configuration.yaml   # Runtime tunables
│   └── agents/              # Per-agent YAML configs
├── pyproject.toml           # Build, deps, tool configs
└── Dockerfile               # Multi-stage (builder + runtime)
```

---

## Core Configuration

### Settings (`app/core/config.py`)

Pydantic `BaseSettings` loaded from `.env` / environment variables.

| Category | Key Fields |
|----------|-----------|
| **App** | `app_name`, `app_env` (development/staging/production), `debug`, `secret_key`, `api_v1_prefix` |
| **Database** | `database_url` (postgresql+asyncpg://), `database_pool_size` (10), `database_max_overflow` (20) |
| **Redis** | `redis_url` |
| **JWT** | `jwt_secret_key`, `jwt_algorithm` (HS256), `jwt_access_token_expire_minutes` (480) |
| **AI Models** | `openai_api_key`, `anthropic_api_key`, `openrouter_api_key`, `ollama_url`, `default_ai_model` (gpt-4o), `default_ai_provider` (openai) |
| **MCP/RAG** | `mcp_server_url`, `mcp_api_key`, `mcp_timeout_seconds` (30), `mcp_max_retries` (3), `mcp_default_kb_id` |
| **Workflow** | `workflow_max_retries` (3), `workflow_quality_threshold` (0.75), `workflow_timeout_minutes` (60) |
| **Storage** | `documents_base_path` (/app/documents), `templates_base_path` (/app/app/templates) |
| **Observability** | `log_level` (INFO), `otlp_endpoint`, `prometheus_enabled` |

Validators: `secret_key` and `jwt_secret_key` are padded to 32 chars in development if too short.

### YAML Configuration (`config/configuration.yaml`)

Runtime tunables accessed via `app_cfg("section.key", default)`:
- `quality.severe_score_threshold`: 0.4
- `quality.moderate_score_threshold`: 0.5
- `quality.max_issues_threshold`: 5
- `validation.confidence_threshold`: 0.75
- `runner.graceful_degradation_threshold`: 0.5
- `retrieval.max_docs`: 8, `max_concurrency`: 2, `max_results_per_query`: 3

### Agent Configuration (`config/agents/{name}.yaml`)

Each agent loads config via `@lru_cache` `load_agent_config(name)`:

```yaml
system_prompt:                   # Agent personality (Agno instructions)
  - "Instruction 1"
  - "Instruction 2"
parameters:                      # Agent-specific parameters
  max_retries: 3
output_schema: {...}             # Expected JSON output structure
critical_fields: [...]           # Fields that must be present
prompt_template: |               # Runtime LLM prompt (string.Template, $var syntax)
  Extract structured requirements.
  Type: $document_type | Title: $title
  === INPUT ===
  $raw_text
  === END INPUT ===
  Return ONLY valid JSON. Structure: {...}
  RULES: ...
```

**`prompt_template`** is the actual prompt sent to the LLM at runtime. It uses `string.Template` syntax (`$variable`), avoiding conflicts with JSON braces `{}`. Variables are provided by each agent's Python code. Modifying a prompt only requires editing the YAML and restarting the backend — no Docker rebuild needed.

| YAML file | Template variables |
|---|---|
| `requirement.yaml` | `$document_type`, `$title`, `$clarifications_block`, `$raw_text`, `$min_fr`, `$min_tr` |
| `procurement.yaml` | `$document_type`, `$requirements_json`, `$kb_context` |
| `lead_writer.yaml` | `$document_type`, `$template_content`, `$enriched_requirements`, `$revision_note` |
| `quality.yaml` | `$document_type`, `$content`, `$requirements`, `$checklist` |
| `orchestrator.yaml` | `$document_type`, `$enriched_requirements` |

---

## LLM Provider Abstraction (`app/core/llm.py`)

Factory function `get_model_adapter()` routes to the correct Agno model class:

| Provider | Setting | Agno Class |
|----------|---------|------------|
| OpenAI | `openai` | `OpenAIChat(id=model, api_key=key)` |
| Anthropic | `anthropic` | `Claude(id=model, api_key=key)` |
| OpenRouter | `openrouter` | `OpenRouter(id=model, api_key=key)` |
| Ollama | `ollama` | `Ollama(id=model, host=url, api_key=key)` |

JSON extraction from LLM responses: `extract_json(text)` — strips markdown fences, finds first `{` with `raw_decode`, recovers trailing commas.

---

## FastAPI App (`app/main.py`)

**Middleware:**
- CORS: allows `localhost:5173`, `localhost:3001`, `localhost`, `127.0.0.1`
- GZip: minimum_size=1000

**Route Prefixes:**
- `/api/v1/workflow/*` — `workflow_router`
- `/api/v1/mcp/*` — `mcp_router`
- `/api/v1/templates/*` — `templates_router`
- `/ws/workflow/{id}` — `ws_router` (no prefix)
- `/health` — health check returning `{status, env}`

**Lifespan:** `@asynccontextmanager` logs startup/shutdown with env + default model.

---

## API Endpoints

### Workflow Routes (`app/api/routes/workflow.py`)

| Method | Path | Status | Purpose |
|--------|------|--------|---------|
| POST | `/workflow/start` | 202 | Create & start workflow (background) |
| GET | `/workflow/{id}` | 200 | Get workflow state + metadata |
| POST | `/workflow/{id}/approve` | 200 | Human-in-the-loop approval |
| POST | `/workflow/{id}/retry` | 200 | Retry from FAILED state |
| GET | `/workflow/{id}/documents` | 200 | List generated documents |
| GET | `/workflow/{id}/quality-report` | 200 | Latest quality report |
| POST | `/workflow/{id}/export/{format}` | 200 | Export to docx or pdf |
| GET | `/workflow/{id}/download/{format}` | 200 | Download exported file |

**StartWorkflowRequest:** `document_type` (pattern: capitolato|requisiti|documento), `title` (5-500 chars), `raw_description` (min 20 chars), `form_data` (dict), `mcp_connection_id` (optional).

### MCP Routes (`app/api/routes/mcp.py`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/mcp/connections` | List all connections |
| POST | `/mcp/connections` | Create + discover capabilities |
| GET | `/mcp/connections/{id}` | Get connection details |
| DELETE | `/mcp/connections/{id}` | Delete connection |
| POST | `/mcp/connections/{id}/refresh` | Re-discover capabilities |
| POST | `/mcp/connections/{id}/call` | Call a tool on MCP server |
| POST | `/mcp/test` | Test connection (no DB save) |
| GET | `/mcp/connections/{id}/resource?uri=` | Read a resource |

Transport: "streamable-http" (default) or "stdio". On create, auto-discovers tools, resources, prompts, and KBs via `_test_and_discover()`.

### Template Routes (`app/api/routes/templates.py`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/templates/` | List all document types |
| GET | `/templates/{type}/config` | Get full template config |
| PUT | `/templates/{type}/config` | Save config (writes YAML) |
| POST | `/templates/{type}/reset` | Delete override, revert to defaults |
| POST | `/templates/{type}/validate-preview` | Run validation on sample input |

Template overrides saved to `{documents_base_path}/template_overrides/{type}/template.yaml`.

---

## WebSocket Streaming (`app/api/websocket/stream.py`)

Endpoint: `ws://host/ws/workflow/{workflow_id}`

Events emitted as JSON:
```json
{"event": "state_change", "data": {"state": "BRIEFING"}}
{"event": "agent_start", "data": {"agent": "requirement"}}
{"event": "agent_done", "data": {"agent": "requirement", "duration_ms": 1200}}
{"event": "quality_report", "data": {"score": 0.92, "passed": true}}
{"event": "pending_approval", "data": {"score": 0.92, "issues": [...], "suggestions": [...]}}
{"event": "completed", "data": {"quality_score": 0.92}}
{"event": "failed", "data": {"error": "..."}}
```

Implementation: global `_event_queues: dict[str, list[asyncio.Queue]]` per workflow ID. 30s heartbeat timeout. Auto-close on terminal events.

---

## Agents

### RequirementAgent (`agents/requirement/agent.py`)

**Phase:** BRIEFING
**Output:** `RequirementResult` {requirements, summary, missing_fields, confidence}

Canonical schema includes 14 top-level sections: project, scope, functional_requirements, technical_requirements, sla (free-form metrics[] with {metric, target, note}), security_compliance, timeline, integrations, stakeholders, constraints, regulatory_references, evaluation_criteria, budget.

`normalize_to_canonical(raw)` maps flat keys to nested paths. Confidence = critical filled / total critical fields.

Also extracts `search_terms` — a list of specific technologies, products, standards, and systems mentioned in user input (max 10). These terms are passed to the RetrievalSkill for dynamic MCP queries.

### ProcurementAgent (`agents/procurement/agent.py`)

**Phase:** ENRICHMENT
**Output:** `ProcurementResult` {enriched, sources, standards_applied}

Builds KB context via `RetrievalSkill` (if MCP URL provided), then calls LLM with requirements + KB context. Fallback applies ISO 27001, ISO 9001, GDPR, OWASP, CIS, D.Lgs. 36/2023.

### OrchestratorAgent (`agents/orchestrator/agent.py`)

**Phase:** VALIDATION
**Role:** Coordinates workflow. Holds references to all agents and the `StateMachine`. Runs the main `run()` loop dispatching to `_step()` based on current state.

### LeadWriterAgent (`agents/lead_writer/agent.py`)

**Phase:** WRITING
**Output:** `WriterResult` {markdown, sections, docx_path, pdf_path}

Process:
1. Load Jinja2 template from `templates/{type}/base.j2`
2. Render with enriched requirements as context
3. Call LLM with template + requirements + quality_issues
4. Extract sections from markdown headings
5. Export to DOCX and PDF via `ExportSkill`

Fallback templates (hardcoded) for capitolato (11 sections), requisiti (6 sections), documento (3 sections).

### QualityAgent (`agents/quality/agent.py`)

**Phase:** QUALITY_ANALYSIS
**Output:** `QualityReport` {score, passed, issues, suggestions, section_scores, needs_enrichment, warnings}

Checklist (8 items): functional coverage, SLA metrics with measurable targets, security standards, structure, contradictions, technical constraints, stakeholders, measurable acceptance criteria. Scoring: LLM-based, threshold at 0.75. Graceful degradation: <0.4 = hard failure, 0.4-0.75 = pass with warnings, ≥0.75 = pass. `needs_enrichment` flag triggers re-enrichment instead of re-writing.

---

## State Machine (`workflows/state_machine/machine.py`)

**States enum (StrEnum):** INIT, BRIEFING, ENRICHMENT, VALIDATION, WRITING, QUALITY_ANALYSIS, PENDING_APPROVAL, COMPLETED, FAILED

**Triggers enum (StrEnum):** START, REQUIREMENTS_COLLECTED, ENRICHMENT_DONE, VALIDATION_PASSED, VALIDATION_FAILED, WRITING_DONE, QUALITY_PASSED, QUALITY_FAILED_WRITING, QUALITY_FAILED_ENRICHMENT, FATAL_ERROR, HUMAN_APPROVED

**WorkflowContext:** `@dataclass` with workflow_id, document_type, state, retry_count, writing_retry_count, enrichment_retry_count, max_retries, quality_threshold, requirements, enriched_requirements, draft_content, quality_score, quality_issues, human_approval_required, human_approved, metadata.

**Key methods:** `trigger(ctx, trigger) → new_state`, `can_trigger(ctx, trigger) → bool`, `terminal_states() → {COMPLETED, FAILED}`.

Transitions have guards checking retry counts vs max_retries.

---

## Workflow Runner (`workflows/execution/runner.py`)

`WorkflowRunner.run(workflow_id, document_type, initial_input) → dict`

Execution loop:
1. Creates agents and StateMachine
2. Steps through states, calling agent methods
3. Validation loop: re-collects if validation fails
4. Writing/Quality loop: re-writes or re-enriches based on quality feedback
5. After QA passes: transitions to PENDING_APPROVAL, creates `asyncio.Event`, awaits human approval
6. On approval: transitions to COMPLETED, persists document, emits completed event
7. On rejection/timeout: transitions to FAILED
8. Graceful degradation if retries exhausted but score > 0.5

Event emissions via `_emit(workflow_id, event, data)` → broadcasts to all registered asyncio.Queues via global `_event_queues`.

---

## Skills

### Validation Skill (`skills/validation/`)

- `validate_requirements_completeness()` — checks required_fields from template.yaml, enforces min_items, returns `ValidationResult` with confidence
- `validate_sla_metrics()` — validates free-form SLA metrics list (type-aware: documento skips validation, capitolato/requisiti require ≥1 metric with metric+target)
- `validate_document_sections()` — checks required sections present in markdown via regex
- `detect_placeholder_content()` — finds [TBD], [TODO], [PLACEHOLDER]
- `score_requirement_richness()` — weighted 0.0–1.0: 30% functional_reqs, 20% technical_reqs, 15% SLA detail, 10% integrations, 10% stakeholders, 10% security, 5% timeline

### Retrieval Skill (`skills/retrieval/`)

`build_context(requirements, document_type, max_docs, kb_id) → RetrievedContext`

Process:
1. Loads `retrieval_queries` from template.yaml
2. Resolves `{placeholder}` tokens using dot-notation from requirements
3. Runs queries in parallel (Semaphore-limited, max 2 concurrent)
4. Deduplicates and sorts by relevance_score
5. Returns `RetrievedContext` {context_text, sources, query_count, total_docs}

### Export Skill (`skills/export/`)

`ExportSkill.export_docx(content, title, workflow_id, doc_type) → str` (file path)
`ExportSkill.export_pdf(content, title, workflow_id, doc_type) → str` (file path)

DOCX: Calibri 10pt body, 18pt title, 1" margins top/bottom, 1.2" left/right, dark blue (#1A1A2E) title. Handles H1-H4 headings, lists, bold/italic.

PDF: A4, 2.5cm margins. Title 20pt, H1 14pt, H2 12pt, body 9pt/14pt leading. Tables converted to bullet text (ReportLab limitation).

Storage: `{documents_base_path}/{workflow_id}/{doc_type}_{uuid8}.{docx|pdf}`

---

## MCP Client (`mcp/client/mcp_client.py`)

`MCPClient(url, api_key)` — connects via auto-detected transport (SSE if URL ends with `/sse`, else StreamableHttp).

| Method | Returns | Cache |
|--------|---------|-------|
| `list_tools()` | `list[{name, description, input_schema}]` | 15 min |
| `call_tool(name, args)` | `Any` (JSON or text) | 15 min |
| `list_resources()` | `list[{uri, name, description, mime_type}]` | 15 min |
| `read_resource(uri)` | `Any` (text or binary) | 15 min |
| `list_prompts()` | `list[{name, description, arguments}]` | 15 min |
| `get_prompt(name, args)` | `{messages: [...]}` | 15 min |
| `discover_all()` | `{tools, resources, prompts, summary}` | — |

All with 30s timeout, 3 retries, idempotent connect/disconnect (async lock).

### NanoRAG Adapter (`mcp/client/adapters/nanorag.py`)

Extends `MCPClient` with `search_documents(query, limit, kb_id)`:
- Discovers search tool by name pattern (contains "search", "query", "retrieve", "ask", "chat")
- Maps parameters: query→[query, message, text, question], limit→[limit, top_k, max_results, count], kb_id→[kb_id, knowledge_base, database, collection]
- Normalizes results to `[{relevance_score, title, excerpt, source}]`

---

## Database (`app/db/`)

### Models (`models.py`)

All models inherit `TimestampMixin` (created_at, updated_at).

| Model | Key Fields |
|-------|-----------|
| `User` | id (UUID PK), email (unique), hashed_password, full_name, role (default "user"), is_active |
| `Workflow` | id (UUID PK), owner_id (FK→User), title, document_type, state (indexed, default "INIT"), retry_count, metadata_ (JSON), mcp_connection_id (FK→MCPConnection) |
| `WorkflowState` | id (UUID PK), workflow_id (FK, indexed), from_state, to_state, trigger, payload (JSON) |
| `AgentOutput` | id (UUID PK), workflow_id (FK, indexed), agent_name, output_type, content (JSON), token_usage (JSON), duration_ms |
| `Document` | id (UUID PK), workflow_id (FK, indexed), name, format (markdown/docx/pdf), content_md, file_path, version |
| `QualityReport` | id (UUID PK), workflow_id (FK, indexed), score (float), passed (bool), issues/suggestions/section_scores (JSON) |
| `AuditLog` | id (UUID PK), workflow_id (FK, indexed), user_id, action, detail (JSON), ip_address |
| `MCPConnection` | id (UUID PK), name, description, url, transport, api_key, default_kb_id, is_active, discovered_tools/resources/prompts/kbs (JSON), health_status, last_health_check |

### Session (`session.py`)

- Engine: `create_async_engine(settings.database_url)` with pool_size & max_overflow
- Session factory: `async_sessionmaker(expire_on_commit=False, autoflush=False)`
- Dependency: `async def get_db() → AsyncGenerator[AsyncSession]` (FastAPI Depends)

---

## Migrations

Alembic, 3 migration files:
1. `20260523_001_initial_workflows.py` — users, workflows, workflow_states, agent_outputs, documents, quality_reports, audit_logs
2. `20260621_002_add_mcp_connections.py` — mcp_connections table + FK on workflows
3. `20260622_003_add_mcp_kb_fields.py` — default_kb_id + discovered_kbs on mcp_connections

`alembic/env.py` uses async migration runner, reads `database_url` from `app.core.config.settings`.

---

## Template System

Each document type has two files:

### `template.yaml`
```yaml
template_id: capitolato
name: Capitolato di Gara
sections, required_fields, sla_rules (expected_kpis, expected_kpos),
quality_checks, retrieval_queries
```

Loaded via `load_template_config(type)` with `@lru_cache`. Overrides checked first at `{documents_base_path}/template_overrides/`, then defaults at `{templates_base_path}/`.

### `base.j2`
Jinja2 template rendered with enriched requirements as context. Fallback: if YAML missing, sections derived by parsing `##` headings from the `.j2` file.

---

## Testing

- Framework: pytest with `asyncio_mode="auto"`
- Test DB: aiosqlite (in-memory for speed)
- Coverage: pytest-cov
- Location: `app/tests/`
- 91 tests across 5 files: `test_state_machine.py`, `test_validation_skill.py`, `test_workflow_persistence.py`, `test_workflow_runner.py`, `conftest.py`

---

## Key Dependencies

| Category | Packages |
|----------|----------|
| Web | fastapi, uvicorn, websockets, python-multipart |
| DB | sqlalchemy[asyncio], asyncpg, alembic |
| Cache | redis[hiredis] |
| Auth | python-jose[cryptography], passlib[bcrypt] |
| AI | agno, openai, anthropic, ollama |
| Docs | jinja2, python-docx, markdown, reportlab |
| Config | pydantic, pydantic-settings, python-dotenv |
| MCP | httpx, fastmcp |
| Obs. | structlog, opentelemetry, prometheus-client |
| Dev | pytest, pytest-asyncio, pytest-cov, httpx, ruff, mypy, factory-boy |

