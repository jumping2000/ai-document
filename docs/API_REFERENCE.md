# AI Document Platform — API Reference

> **Base URL:** `http://localhost:8001/api/v1`
> **WebSocket:** `ws://localhost:8001/ws/workflow/{id}`
> **Version:** 1.0.0

---

## REST Endpoints

### Workflow Lifecycle

#### `POST /workflow/start`

Start a new document generation workflow (runs in background).

**Request Body:**
```json
{
  "document_type": "capitolato",
  "title": "Gara ERP Comune di Milano",
  "raw_description": "Descrizione dettagliata del progetto...",
  "form_data": {},
  "mcp_connection_id": null
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `document_type` | string | `capitolato` \| `requisiti` \| `documento` |
| `title` | string | 5–500 characters |
| `raw_description` | string | Min 20 characters |
| `form_data` | object | Default `{}` |
| `mcp_connection_id` | string \| null | Optional MCP connection UUID |

**Response:** `202 Accepted`
```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "INIT",
  "document_type": "capitolato",
  "title": "Gara ERP Comune di Milano",
  "retry_count": 0,
  "quality_score": null,
  "created_at": "2026-06-22T10:00:00Z",
  "updated_at": "2026-06-22T10:00:00Z"
}
```

---

#### `GET /workflow/{id}`

Get current workflow state and metadata.

**Response:** `200 OK`
```json
{
  "workflow_id": "550e8400-...",
  "state": "QUALITY_ANALYSIS",
  "document_type": "capitolato",
  "title": "Gara ERP Comune di Milano",
  "retry_count": 0,
  "quality_score": 0.92,
  "created_at": "2026-06-22T10:00:00Z",
  "updated_at": "2026-06-22T10:02:30Z"
}
```

---

#### `POST /workflow/{id}/approve`

Human-in-the-loop approval gate. Only valid when state is `QUALITY_ANALYSIS`.

**Request Body:**
```json
{
  "approved": true,
  "comment": "Documento conforme ai requisiti"
}
```

**Response:** `200 OK`
```json
{
  "workflow_id": "550e8400-...",
  "state": "COMPLETED",
  "...": "..."
}
```

---

#### `POST /workflow/{id}/retry`

Retry a failed workflow. Resets state from `FAILED` to `INIT`.

**Request Body:**
```json
{
  "reason": "Correzione requisiti SLA"
}
```

**Response:** `200 OK`

---

#### `GET /workflow/{id}/documents`

List all generated documents for a workflow.

**Response:** `200 OK`
```json
[
  {
    "id": "660e8400-...",
    "name": "capitolato_gara_erp.md",
    "format": "markdown",
    "version": 1,
    "file_path": "/app/documents/550e8400.../capitolato_a1b2c3d4.docx"
  }
]
```

---

#### `GET /workflow/{id}/quality-report`

Get the latest quality report.

**Response:** `200 OK`
```json
{
  "score": 0.92,
  "passed": true,
  "issues": [],
  "suggestions": ["Aggiungere dettagli sulla sicurezza"],
  "section_scores": {
    "premessa": 0.95,
    "sla": 0.88
  }
}
```

---

#### `POST /workflow/{id}/export/{format}`

Export document to `docx` or `pdf`.

**Path Parameters:** `format` = `docx` | `pdf`

**Request Body (optional):**
```json
{
  "content": "# Titolo\n\nContenuto markdown..."
}
```

**Response:** `200 OK`
```json
{
  "download_url": "/api/v1/workflow/550e8400.../download/docx"
}
```

---

#### `GET /workflow/{id}/download/{format}`

Download the exported file. Returns binary `FileResponse`.

---

### MCP Connections

#### `GET /mcp/connections`

List all MCP connections, sorted by `created_at` desc.

**Response:** `200 OK` — array of `MCPConnection` objects.

---

#### `POST /mcp/connections`

Create a new MCP connection and auto-discover its capabilities.

**Request Body:**
```json
{
  "name": "Knowledge Base Produzione",
  "description": "KB normativa appalti",
  "url": "http://kb-server:8100/sse",
  "transport": "streamable-http",
  "api_key": "kb-secret-key",
  "default_kb_id": "italian-procurement"
}
```

| Field | Constraints |
|-------|-------------|
| `name` | 2–100 chars |
| `url` | 10–500 chars |
| `transport` | `streamable-http` \| `stdio` (default: `streamable-http`) |
| `description` | Max 500 chars |

**Response:** `200 OK` — `MCPConnection` with `discovered_tools`, `discovered_resources`, `discovered_prompts`, `discovered_kbs`, `health_status`.

---

#### `GET /mcp/connections/{id}`

Get a single connection.

---

#### `DELETE /mcp/connections/{id}`

Delete a connection.

---

#### `POST /mcp/connections/{id}/refresh`

Re-discover capabilities (tools, resources, prompts, KBs) for a connection.

**Response:** `200 OK` — updated `MCPConnection`.

---

#### `POST /mcp/connections/{id}/call`

Call a tool on the MCP server.

**Request Body:**
```json
{
  "tool_name": "nanorag_chat",
  "arguments": {
    "message": "Quali sono i requisiti per un appalto pubblico?",
    "kb_id": "italian-procurement",
    "top_k": 5
  }
}
```

**Response:** `200 OK` — raw tool result.

---

#### `POST /mcp/test`

Test a connection without saving to DB.

**Request Body:**
```json
{
  "url": "http://kb-server:8100/sse",
  "api_key": "kb-secret-key"
}
```

**Response:** `200 OK`
```json
{
  "kbs": [
    {"id": "italian-procurement", "name": "Normativa Appalti", "documents": 42, "chunks": 1250}
  ]
}
```

---

#### `GET /mcp/connections/{id}/resource?uri={uri}`

Read a resource by its URI from the MCP server.

---

### Templates

#### `GET /templates/`

List all document types with section counts.

**Response:** `200 OK`
```json
[
  {"type": "capitolato", "name": "Capitolato di Gara", "sections": 11},
  {"type": "requisiti", "name": "Requisiti Tecnici", "sections": 6},
  {"type": "documento", "name": "Documento Tecnico", "sections": 3}
]
```

---

#### `GET /templates/{type}/config`

Get full template configuration (sections, required_fields, sla_rules, quality_checks, retrieval_queries).

**Response:** `200 OK` — full `template.yaml` content as JSON.

---

#### `PUT /templates/{type}/config`

Save template configuration override.

**Request Body (partial — only changed sections):**
```json
{
  "sections": [
    {"id": "premessa", "title": "Premessa", "required": true}
  ],
  "quality_checks": [
    {"id": "sla_values", "label": "Valori SLA espliciti", "enabled": false}
  ]
}
```

Writes to `{documents_base_path}/template_overrides/{type}/template.yaml`. Invalidates cache.

---

#### `POST /templates/{type}/reset`

Delete override YAML — reverts to default template configuration.

---

#### `POST /templates/{type}/validate-preview`

Run validation on a sample requirements payload.

**Request Body:**
```json
{
  "requirements": {
    "project": {"title": "Test", "organization": "Org"},
    "sla": {"K1": "99%", "K2": "1%", "K3": "0"}
  }
}
```

**Response:** `200 OK`
```json
{
  "valid": false,
  "confidence": 0.3,
  "missing_fields": ["functional_requirements", "technical_requirements"],
  "issues": ["Campo obbligatorio mancante: functional_requirements"],
  "warnings": []
}
```

---

### Health

#### `GET /health`

**Response:** `200 OK`
```json
{
  "status": "ok",
  "env": "development"
}
```

---

## WebSocket Events

**Endpoint:** `ws://localhost:8001/ws/workflow/{workflow_id}`

Connection auto-closes on terminal events (completed/failed). 30s heartbeat timeout.

### Event Format

```json
{
  "event": "<event_type>",
  "data": { }
}
```

### Event Types

| Event | Data Payload | Description |
|-------|-------------|-------------|
| `state_change` | `{"state": "BRIEFING"}` | Workflow entered new state |
| `agent_start` | `{"agent": "requirement"}` | Agent started execution |
| `agent_done` | `{"agent": "requirement", "duration_ms": 1200}` | Agent completed |
| `validation_result` | `{"valid": true, "confidence": 0.85}` | Validation passed |
| `validation_failed` | `{"issues": [...]}` | Validation failed, retrying |
| `richness_score` | `{"score": 0.7}` | Requirement richness score |
| `placeholders_detected` | `{"placeholders": ["[TBD]"]}` | Unfilled content found |
| `document_sections_warning` | `{"sections": [...]}` | Missing sections warning |
| `quality_report` | `{"score": 0.92, "passed": true, "issues": [...]}` | Quality analysis result |
| `completed` | `{"quality_score": 0.92}` | Workflow completed |
| `failed` | `{"error": "..."}` | Workflow failed |
| `heartbeat` | `{}` | Keep-alive (every 30s) |

### Frontend Integration

```typescript
// src/hooks/useWorkflowStream.ts
const ws = new WebSocket(`ws://${host}/ws/workflow/${workflowId}`);

ws.onmessage = (event) => {
  const { event: type, data } = JSON.parse(event.data);
  switch (type) {
    case 'state_change': store.updateWorkflowState(data.state); break;
    case 'agent_start': store.setAgentRunning(data.agent); break;
    case 'agent_done': store.setAgentDone(data.agent, data.duration_ms); break;
    case 'quality_report': store.setQualityReport(data); break;
    case 'completed': store.setDocumentContent(data.content); store.setStreaming(false); break;
    case 'failed': store.setStreaming(false); break;
  }
};
```

---

## Configuration Reference

### `.env` Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment: development, staging, production |
| `DEBUG` | `false` | Enable debug mode |
| `SECRET_KEY` | *(required)* | App secret (min 32 chars, padded in dev) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `DEFAULT_AI_PROVIDER` | `openai` | openai, anthropic, openrouter, ollama |
| `DEFAULT_AI_MODEL` | `gpt-4o` | Model ID for selected provider |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `OPENROUTER_API_KEY` | — | OpenRouter API key |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `MCP_SERVER_URL` | `http://localhost:8100/sse` | MCP server URL |
| `MCP_API_KEY` | — | MCP API key |
| `MCP_TIMEOUT_SECONDS` | `30` | MCP request timeout |
| `MCP_MAX_RETRIES` | `3` | MCP retry count |
| `WORKFLOW_MAX_RETRIES` | `3` | Max retries per phase |
| `WORKFLOW_QUALITY_THRESHOLD` | `0.75` | Quality pass threshold (0.0–1.0) |
| `WORKFLOW_TIMEOUT_MINUTES` | `60` | Workflow timeout |
| `DOCUMENTS_BASE_PATH` | `/app/documents` | Export storage path |
| `TEMPLATES_BASE_PATH` | `/app/app/templates` | Jinja2 templates path |
| `LOG_LEVEL` | `INFO` | Structlog level |

### YAML Runtime Config (`config/configuration.yaml`)

Accessible via `app_cfg("section.key", default)`:

| Key | Default | Description |
|-----|---------|-------------|
| `quality.severe_score_threshold` | `0.4` | Hard failure threshold |
| `quality.moderate_score_threshold` | `0.5` | Warning threshold |
| `quality.max_issues_threshold` | `5` | Max issues before fail |
| `validation.confidence_threshold` | `0.75` | Min confidence to pass |
| `runner.graceful_degradation_threshold` | `0.5` | Min score for graceful completion |
| `retrieval.max_docs` | `8` | Max KB docs per query |
| `retrieval.max_concurrency` | `2` | Parallel search limit |
| `retrieval.max_results_per_query` | `3` | Results per query |
