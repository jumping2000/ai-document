# Code Review Report — Allineamento Data Flow MCP

**Date:** 2026-06-25
**Branch:** `dev-improvment` (uncommitted changes on top of `e67a304`)
**Reviewer:** Automated code review (GitHub Copilot)

---

## Scope

Allineamento del data flow MCP per la piattaforma AI document generation:

1. Canonical schema (`schema.py`) — TypedDict nested schema
2. `RequirementAgent` — CANONICAL_SCHEMA prompt + normalize_to_canonical() adapter
3. `MCPClient` — search_documents() convenience method
4. `RetrievalSkill` — constructor overrides + kb_id parameter
5. `ProcurementAgent` — removed inline MCP logic, uses RetrievalSkill
6. `WorkflowRunner` — full validation wiring + post-write checks
7. Jinja2 template — fixed double-nesting bug
8. Integration tests — full pipeline

**Files changed:** 9 files, +877 / -244 lines

---

## Strengths

1. **Canonical schema is well-designed.** `schema.py` provides clean TypedDicts as documentation, and `CANONICAL_SCHEMA` in `agent.py` serves as the LLM prompt example — a pragmatic dual-use approach. The `normalize_to_canonical()` adapter handles ~10 flat→nested mappings without over-engineering.

2. **MCP data flow is clean.** `MCPClient.search_documents()` → `RetrievalSkill.build_context()` → `ProcurementAgent.enrich()` is a clear pipeline with proper separation of concerns. The pattern-matching tool discovery in `search_documents()` is elegant and server-agnostic.

3. **Validation integration is non-blocking and informative.** SLA checks during VALIDATION, richness scoring, placeholder detection, and document-section checks during WRITING — all emit SSE events for the UI without breaking the workflow.

4. **Template fix is correct.** Removing the double `.get("enriched_requirements", {})` nesting directly addresses the bug.

5. **Test quality is solid.** The spy pattern for `validate_sla_consistency`, SSE event queue assertions, and the `FakeProcurementAgent.enrich(**kwargs)` adaptation all test real behavior at the integration boundary.

---

## Issues Found & Fixed

### Critical (blocks release)

| # | File | Issue | Fix | Status |
|---|------|-------|-----|--------|
| 1 | `runner.py:207` | MCP connection params lost on validation retry path — re-enrichment skips KB retrieval entirely | Added `mcp_url`, `mcp_api_key`, `mcp_tools`, `mcp_kb_id` to retry `enrich()` calls | ✅ Fixed |
| 2 | `runner.py:325` | Same MCP param loss on quality-failure re-enrichment path | Same fix — forward MCP params | ✅ Fixed |

### Important (fix before merge)

| # | File | Issue | Fix | Status |
|---|------|-------|-----|--------|
| 3 | `mcp_client.py:133` | `hash(frozenset(arguments.items()))` crashes with unhashable arguments (list/dict) | Replaced with `json.dumps(arguments, sort_keys=True)` | ✅ Fixed |
| 4 | `validation_skill.py:95-126` | `validate_sla_consistency()` only validates availability, ignores RTO/RPO and response_time | Added `_parse_duration_hours()` helper, RTO>RPO check, positive response_time check | ✅ Fixed |
| 5 | `runner.py:376` | `_run_agent` return type `-> dict[str, Any]` but returns dataclass instances | Changed to `-> Any` | ✅ Fixed |
| 6 | `validation_skill.py:256` | `validate_document_sections` section matching uses fragile substring matching | Now extracts markdown headings with regex first, falls back to body text | ✅ Fixed |
| 7 | `test_workflow_runner.py:176` | MCPClient stub uses `filters` param instead of `kb_id` | Fixed stub signature to match real API | ✅ Fixed |
| 8 | `test_validation_skill.py` | Missing SLA edge-case tests (RTO≤RPO, unparsable response_time) | Added 4 new tests | ✅ Fixed |

### Minor (nice to have)

| # | File | Issue | Status |
|---|------|-------|--------|
| 9 | `runner.py:143` | SLA validation merges into `validation.issues` but `validation.valid` is already computed — SLA issues don't block (intentional, documented with comment) | ✅ Documented |
| 10 | `validation_skill.py:94` | `_parse_duration_hours` imports `re` inside function body | Noted (style preference) |
| 11 | `retrieval_skill.py:113` | Long single-line format after change | Noted (cosmetic) |

---

## Test Results

```
70 passed, 1 failed (pre-existing: test_workflow_persistence — agno import issue)
```

**New tests added:**
- `test_rto_less_than_rpo_fails` — validates RTO>RPO enforcement
- `test_rto_equals_rpo_fails` — validates RTO=RPO is rejected
- `test_unparsable_response_time_warning` — validates warning on bad input
- `test_zero_response_time_fails` — validates positive check

---

## Assessment

**✅ APPROVED — Ready for commit.**

All Critical and Important issues have been fixed. The single pre-existing test failure (`test_workflow_persistence`) is unrelated to these changes (agno module import issue).
