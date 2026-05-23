# Workflow Remediation Checklist

Updated: 2026-05-23

## 1. Immediate blockers

- [x] Align `WorkflowRunner` with the real agent interfaces (`collect`, `enrich`, `write`, `review`).
- [x] Remove the broken orchestrator dependency from the active runner path and validate requirements with the existing validation skill.
- [x] Fix `LeadWriterAgent` to use the existing export implementation and the shipped template filenames.
- [ ] Decide whether to delete or rebuild `OrchestratorAgent` so the repository no longer contains a stale, incompatible execution path.

## 2. High blast radius fixes

- [ ] Persist workflow state through the database instead of the in-memory `_workflows` store in `backend/app/api/routes/workflow.py`.
- [ ] Replace or guard the in-process `_workflows` and `_event_queues` stores for concurrent access.
- [ ] Add transaction boundaries around workflow execution and retry flows so partial failures do not leave inconsistent persisted state.

## 3. Reliability gaps

- [ ] Add an API integration test for `POST /workflow/start` that covers background execution and final state.
- [ ] Add a streaming test for the workflow WebSocket path to verify `state_change`, `quality_report`, `completed`, and `failed` events.
- [ ] Add a focused test for `LeadWriterAgent.write()` covering template resolution and export path generation.
- [ ] Add a pre-flight MCP health check before procurement begins so workflows fail early when the knowledge service is unavailable.

## 4. Input and failure handling

- [ ] Replace the loose `form_data: dict[str, Any]` API contract with a validated request schema per document type.
- [ ] Make JSON parsing failures in procurement and quality explicit in logs and surfaced workflow events.
- [ ] Validate MCP credentials and other required runtime settings at startup instead of failing lazily during workflow execution.

## 5. Lower-priority hardening

- [ ] Add cache eviction for expired MCP entries to avoid unbounded in-process memory growth.
- [ ] Remove remaining dead or duplicate orchestration logic once the active execution path is fully covered by tests.