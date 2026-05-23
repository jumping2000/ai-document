# Architecture Decision Records

## ADR-001 — State Machine vs LLM-driven orchestration

**Decision:** Use an explicit deterministic state machine (not an LLM loop) for workflow orchestration.

**Rationale:**
- Deterministic: same input always produces same state transitions
- Testable: unit tests cover all transition paths without LLM calls
- Observable: every transition is logged with workflow_id + trigger
- Retries bounded: guards prevent infinite loops at compile time
- Debuggable: state history is persisted and auditable

**Rejected alternative:** Letting the OrchestratorAgent decide the next state via free-text LLM output. Too non-deterministic, hard to test, risk of hallucinated transitions.

---

## ADR-002 — Agno as AI framework

**Decision:** Use Agno for agent definition and execution.

**Rationale:**
- Clean Agent abstraction with system prompt, tools, structured output
- Provider-agnostic (OpenAI / Anthropic / Ollama switchable via config)
- Lightweight — no heavy opinionated framework lock-in
- `arun()` is naturally async

**Constraint:** Agno 1.x API may evolve. Agent definitions are isolated in `agents/*/agent.py` — swapping to another framework only requires editing those files.

---

## ADR-003 — SSE via WebSocket (not HTTP SSE)

**Decision:** Use WebSocket for live event streaming instead of HTTP SSE.

**Rationale:**
- WebSocket is bidirectional — future use cases (human-in-the-loop chat) don't require a second channel
- Single persistent connection, simpler reconnection logic in React
- FastAPI WebSocket support is native and well-tested

**Trade-off:** WebSocket requires a proxy that supports `Upgrade: websocket`. Nginx config handles this.

---

## ADR-004 — In-process event bus for SSE

**Decision:** Use in-memory `asyncio.Queue` for event broadcasting (not Redis pub/sub).

**Rationale:**
- Simpler: no Redis dependency for basic use
- Sufficient for single-worker deployment (development + small production)

**Upgrade path:** For multi-worker / multi-pod: replace `_event_queues` in `runner.py` with Redis pub/sub. The interface (`subscribe()`, `unsubscribe()`, `_emit()`) stays the same.

---

## ADR-005 — MCP client with in-process cache

**Decision:** Cache MCP responses in a process-level dict with TTL instead of Redis.

**Rationale:**
- Zero extra dependency for the common case
- MCP responses (regulations, templates) are stable within a workflow run
- TTL = 15 minutes prevents stale data

**Upgrade path:** Replace `_cache` dict in `MCPClient` with `aioredis` calls. Interface unchanged.

---

## Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  React Frontend                                                 │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────────┐  │
│  │ WorkflowForm │  │ WorkflowMonitor│  │  DocumentViewer     │  │
│  └──────┬───────┘  └───────┬────────┘  └──────────┬──────────┘  │
│         │ POST /start      │ WS events            │ GET /docs   │
└─────────┼──────────────────┼──────────────────────┼─────────────┘
          │                  │                      │
┌─────────▼──────────────────▼──────────────────────▼─────────────┐
│  FastAPI Backend                                                │
│  ┌────────────────┐   ┌──────────────────────┐                  │
│  │  WorkflowRoute │   │  WebSocket /ws/{id}  │                  │
│  └───────┬────────┘   └──────────┬───────────┘                  │
│          │ BackgroundTask        │ asyncio.Queue                │
│  ┌───────▼──────────────────────┐│                              │
│  │       WorkflowRunner         ││                              │
│  │  ┌──────────────────────┐    ││                              │
│  │  │    StateMachine      │    ││                              │
│  │  └──────────────────────┘    ││                              │
│  │                              ││                              │
│  │  RequirementAgent  ──────────┘│                              │
│  │  ProcurementAgent  ──────────┘│                              │
│  │  OrchestratorAgent ──────────┘│                              │
│  │  LeadWriterAgent   ──────────┘│                              │
│  │  QualityAgent      ──────────┘                               │
│  └───────────────────┬──────────────────────────────────────────│
│                      │                                          │
│  ┌───────────────────▼───────────────────────────────────────┐  │
│  │  Infrastructure                                           │  │
│  │  PostgreSQL  │  Redis  │  MCPClient → External RAG        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```
