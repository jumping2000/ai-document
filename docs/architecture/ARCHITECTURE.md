# AI Document Platform — Architecture

## Overview

Multi-agent AI platform for automatic generation of enterprise IT procurement documents
(Capitolato di Gara, Requisiti Funzionali e Tecnici).

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  WorkflowMonitor ← WebSocket ← Zustand ← useWorkflowStream      │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / WebSocket
┌────────────────────────────▼────────────────────────────────────┐
│                       FASTAPI BACKEND                           │
│  POST /workflow/start                                           │
│  GET  /workflow/{id}                                            │
│  WS   /ws/workflow/{id}  ← SSE event bus                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    WORKFLOW RUNNER                              │
│                                                                 │
│  StateMachine → drives state transitions                        │
│                                                                 │
│  INIT → BRIEFING → ENRICHMENT → VALIDATION → WRITING → QA → ✓   │
│              ↑_________↑__________↑                             │
│                    (retry loops)                                │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
       │          │          │          │          │
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

## Agent Responsibilities

| Agent         | State         | Input                  | Output                    |
|---------------|---------------|------------------------|---------------------------|
| Orchestrator  | VALIDATION    | WorkflowContext        | {valid, confidence, issues} |
| Requirement   | BRIEFING      | raw user input         | structured_requirements    |
| Procurement   | ENRICHMENT    | requirements + KB docs | enriched_requirements      |
| LeadWriter    | WRITING       | enriched_requirements  | {content, sections}        |
| Quality       | QUALITY_ANALYSIS | content + reqs     | quality_report             |

---

## State Machine Transitions

```
INIT           ──[start]──────────────────────► BRIEFING
BRIEFING       ──[requirements_collected]──────► ENRICHMENT
ENRICHMENT     ──[enrichment_done]────────────► VALIDATION
VALIDATION     ──[validation_passed]───────────► WRITING
VALIDATION     ──[validation_failed, retry<3]──► BRIEFING (loop)
VALIDATION     ──[validation_failed, retry≥3]──► FAILED
WRITING        ──[writing_done]────────────────► QUALITY_ANALYSIS
QUALITY_ANALYSIS ─[quality_passed]─────────────► COMPLETED
QUALITY_ANALYSIS ─[quality_failed_writing]──────► WRITING (loop)
QUALITY_ANALYSIS ─[quality_failed_enrichment]───► ENRICHMENT (loop)
ANY            ──[fatal_error]─────────────────► FAILED
```

---

## Retry Budget

| Loop             | Counter                | Max | Exhausted → |
|------------------|------------------------|-----|-------------|
| Validation       | ctx.retry_count        | 3   | FAILED      |
| Writing quality  | ctx.writing_retry_count| 3   | FAILED      |
| Enrichment       | ctx.enrichment_retry_count | 3 | FAILED    |

---

## MCP Client Contract

```python
# All methods: timeout=30s, retry=3, exponential backoff, in-process cache 15min
await mcp.search_documents(query, limit)    → list[Document]
await mcp.retrieve_context(doc_ids)         → list[ContextChunk]
await mcp.semantic_search(query, top_k)     → list[SearchResult]
await mcp.get_template(template_name)       → str
await mcp.get_regulations(domain)           → list[Regulation]
```

---

## Technology Constraints & Notes

1. **Agno framework**: Used for agent wrapping. Direct `arun()` call — 
   structured output enforced via JSON-only system prompts.

2. **MCP integration**: Standard HTTP REST stub in development.
   Production: replace `mcp_stub.py` with real vector-DB backed server
   (e.g., Qdrant + LlamaIndex or Weaviate).

3. **python-docx**: Does not support all markdown features natively.
   `ExportSkill._write_markdown_to_doc()` handles H1-H4, bullets, numbered
   lists, bold/italic inline. Tables require manual implementation.

4. **WebSocket event bus**: In-process `asyncio.Queue` per workflow.
   For multi-worker deployments, replace with Redis pub/sub.

5. **Authentication**: JWT scaffolded in config but routes not yet guarded.
   Add `Depends(get_current_user)` to each router before production deploy.

---

## Performance Targets

| Metric                    | Target  |
|---------------------------|---------|
| Workflow E2E (4o)         | < 90s   |
| Requirement agent         | < 15s   |
| Procurement + MCP         | < 20s   |
| Writing (full doc)        | < 40s   |
| Quality check             | < 15s   |
| WebSocket event latency   | < 200ms |
