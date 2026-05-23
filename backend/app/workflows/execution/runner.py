"""
Workflow execution runner.

Responsibilities:
- Load/persist WorkflowContext from DB
- Drive the StateMachine
- Dispatch to correct agent per state
- Emit SSE events for live UI streaming
- Handle retry budgets and fatal escalation
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.lead_writer.agent import LeadWriterAgent
from app.agents.procurement.agent import ProcurementAgent
from app.agents.quality.agent import QualityAgent
from app.agents.requirement.agent import RequirementAgent
from app.skills.validation.validation_skill import validate_requirements_completeness
from app.workflows.state_machine.machine import (
    StateMachine,
    WorkflowContext,
    WorkflowState,
    WorkflowTrigger,
)
# DB models imported lazily inside _persist_state to avoid heavy import at module load

log = structlog.get_logger(__name__)

# SSE event bus: workflow_id → list of queues
_event_queues: dict[str, list[asyncio.Queue]] = {}


class WorkflowRunner:
    """Drives a single workflow instance end-to-end."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sm = StateMachine()
        self.requirement_agent = RequirementAgent()
        self.procurement_agent = ProcurementAgent()
        self.writer_agent = LeadWriterAgent()
        self.quality_agent = QualityAgent()

    async def run(
        self,
        workflow_id: str,
        document_type: str,
        initial_input: dict[str, Any],
    ) -> dict[str, Any]:
        ctx = WorkflowContext(
            workflow_id=workflow_id,
            document_type=document_type,
            metadata=initial_input,
        )

        await self._emit(workflow_id, "state_change", {"state": ctx.state})

        try:
            # INIT → BRIEFING
            old = ctx.state
            self.sm.trigger(ctx, WorkflowTrigger.START)
            await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.START.value)
            await self._emit(workflow_id, "state_change", {"state": ctx.state})

            # BRIEFING
            req_output = await self._run_agent(
                workflow_id,
                "requirement",
                lambda: self.requirement_agent.collect(
                    workflow_id=workflow_id,
                    document_type=document_type,
                    existing=initial_input,
                ),
            )
            ctx.requirements = req_output.requirements
            old = ctx.state
            self.sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)
            await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.REQUIREMENTS_COLLECTED.value)
            await self._emit(workflow_id, "state_change", {"state": ctx.state})

            # ENRICHMENT
            enriched = await self._run_agent(
                workflow_id,
                "procurement",
                lambda: self.procurement_agent.enrich(
                    requirements=ctx.requirements,
                    document_type=document_type,
                ),
            )
            ctx.enriched_requirements = {**enriched.enriched, "_workflow_id": workflow_id}
            old = ctx.state
            self.sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)
            await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.ENRICHMENT_DONE.value)
            await self._emit(workflow_id, "state_change", {"state": ctx.state})

            # VALIDATION loop
            while ctx.state == WorkflowState.VALIDATION:
                validation = validate_requirements_completeness(ctx.enriched_requirements, document_type)
                if validation.valid:
                    old = ctx.state
                    self.sm.trigger(ctx, WorkflowTrigger.VALIDATION_PASSED)
                    await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.VALIDATION_PASSED.value)
                else:
                    await self._emit(
                        workflow_id,
                        "validation_failed",
                        {
                            "issues": validation.issues,
                            "missing_fields": validation.missing_fields,
                            "confidence": validation.confidence,
                        },
                    )
                    old = ctx.state
                    self.sm.trigger(ctx, WorkflowTrigger.VALIDATION_FAILED)
                    await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.VALIDATION_FAILED.value)

                    if ctx.state == WorkflowState.BRIEFING:
                        # re-collect requirements with clarifications
                        req_output = await self._run_agent(
                            workflow_id,
                            "requirement",
                            lambda: self.requirement_agent.collect(
                                workflow_id=workflow_id,
                                document_type=document_type,
                                existing={**initial_input, "clarifications": validation.issues},
                            ),
                        )
                        ctx.requirements = req_output.requirements
                        old = ctx.state
                        self.sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)
                        await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.REQUIREMENTS_COLLECTED.value)

                        enriched = await self._run_agent(
                            workflow_id,
                            "procurement",
                            lambda: self.procurement_agent.enrich(
                                requirements=ctx.requirements,
                                document_type=document_type,
                            ),
                        )
                        ctx.enriched_requirements = {**enriched.enriched, "_workflow_id": workflow_id}
                        old = ctx.state
                        self.sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)
                        await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.ENRICHMENT_DONE.value)

                    elif ctx.state == WorkflowState.FAILED:
                        raise RuntimeError("Validation retry budget exhausted")

                await self._emit(workflow_id, "state_change", {"state": ctx.state})

            # WRITING + QUALITY loop
            while ctx.state in (WorkflowState.WRITING, WorkflowState.QUALITY_ANALYSIS):
                if ctx.state == WorkflowState.WRITING:
                    draft = await self._run_agent(
                        workflow_id,
                        "lead_writer",
                        lambda: self.writer_agent.write(
                            enriched_requirements=ctx.enriched_requirements,
                            document_type=document_type,
                            quality_issues=ctx.quality_issues,
                        ),
                    )
                    ctx.draft_content = draft.markdown
                    old = ctx.state
                    self.sm.trigger(ctx, WorkflowTrigger.WRITING_DONE)
                    await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.WRITING_DONE.value)
                    await self._emit(workflow_id, "state_change", {"state": ctx.state})

                elif ctx.state == WorkflowState.QUALITY_ANALYSIS:
                    report = await self._run_agent(
                        workflow_id,
                        "quality",
                        lambda: self.quality_agent.review(
                            content=ctx.draft_content,
                            requirements=ctx.enriched_requirements,
                            document_type=document_type,
                        ),
                    )
                    ctx.quality_score = report.score
                    ctx.quality_issues = report.issues

                    await self._emit(workflow_id, "quality_report", {
                        "score": report.score,
                        "passed": report.passed,
                        "issues": report.issues,
                        "suggestions": report.suggestions,
                        "section_scores": report.section_scores,
                        "needs_enrichment": report.needs_enrichment,
                    })

                    if report.passed:
                        old = ctx.state
                        self.sm.trigger(ctx, WorkflowTrigger.QUALITY_PASSED)
                        await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.QUALITY_PASSED.value)
                    elif report.needs_enrichment:
                        old = ctx.state
                        self.sm.trigger(ctx, WorkflowTrigger.QUALITY_FAILED_ENRICHMENT)
                        await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.QUALITY_FAILED_ENRICHMENT.value)
                        if ctx.state == WorkflowState.ENRICHMENT:
                            enriched = await self._run_agent(
                                workflow_id,
                                "procurement",
                                lambda: self.procurement_agent.enrich(
                                    requirements=ctx.requirements,
                                    document_type=document_type,
                                ),
                            )
                            ctx.enriched_requirements = {**enriched.enriched, "_workflow_id": workflow_id}
                            old = ctx.state
                            self.sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)
                            await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.ENRICHMENT_DONE.value)
                            old = ctx.state
                            self.sm.trigger(ctx, WorkflowTrigger.VALIDATION_PASSED)
                            await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.VALIDATION_PASSED.value)
                    else:
                        old = ctx.state
                        self.sm.trigger(ctx, WorkflowTrigger.QUALITY_FAILED_WRITING)
                        await self._persist_state(workflow_id, old, ctx.state, WorkflowTrigger.QUALITY_FAILED_WRITING.value)

                    await self._emit(workflow_id, "state_change", {"state": ctx.state})

                    if ctx.state == WorkflowState.FAILED:
                        raise RuntimeError("Quality retry budget exhausted")

            # COMPLETED
            await self._emit(workflow_id, "completed", {"workflow_id": workflow_id, "quality_score": ctx.quality_score})
            return {"status": "completed", "quality_score": ctx.quality_score}

        except Exception as exc:
            log.error("workflow_failed", workflow_id=workflow_id, error=str(exc))
            old = ctx.state
            # Only trigger fatal_error if the state machine allows it from the current state
            if self.sm.can_trigger(ctx, WorkflowTrigger.FATAL_ERROR):
                self.sm.trigger(ctx, WorkflowTrigger.FATAL_ERROR)
            await self._persist_state(workflow_id, old, WorkflowState.FAILED, WorkflowTrigger.FATAL_ERROR.value, {"error": str(exc)})
            await self._emit(workflow_id, "failed", {"error": str(exc)})
            return {"status": "failed", "error": str(exc)}

    async def _run_agent(self, workflow_id: str, agent_name: str, fn: Callable[[], Awaitable[Any]]) -> dict[str, Any]:
        start = time.monotonic()
        await self._emit(workflow_id, "agent_start", {"agent": agent_name})
        result = await fn()
        duration_ms = int((time.monotonic() - start) * 1000)
        await self._emit(workflow_id, "agent_done", {"agent": agent_name, "duration_ms": duration_ms})
        log.info("agent_completed", agent=agent_name, duration_ms=duration_ms)
        return result

    async def _emit(self, workflow_id: str, event: str, data: dict[str, Any]) -> None:
        msg = {"event": event, "data": data}
        for q in _event_queues.get(workflow_id, []):
            await q.put(msg)

    async def _persist_state(self, workflow_id: str, from_state: WorkflowState | str, to_state: WorkflowState | str, trigger: str, payload: dict[str, Any] | None = None) -> None:
        """Persist workflow state and append an audit row. Safely no-ops when DB session is unavailable."""
        try:
            wf_id = uuid.UUID(workflow_id)
        except Exception:
            return

        if not hasattr(self.db, "get"):
            return

        # import models lazily so tests that stub sqlalchemy can import this module
        try:
            from app.db.models import Workflow, WorkflowState as DBWorkflowState
        except Exception:
            return

        wf = await self.db.get(Workflow, wf_id)
        if not wf:
            wf = Workflow(id=wf_id, document_type=str(to_state), title="", state=str(to_state))
            self.db.add(wf)

        wf.state = str(to_state)
        await self.db.flush()

        audit = DBWorkflowState(workflow_id=wf_id, from_state=str(from_state), to_state=str(to_state), trigger=trigger, payload=payload or {})
        self.db.add(audit)
        await self.db.commit()


# SSE subscription helpers
def subscribe(workflow_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _event_queues.setdefault(workflow_id, []).append(q)
    return q


def unsubscribe(workflow_id: str, q: asyncio.Queue) -> None:
    queues = _event_queues.get(workflow_id, [])
    if q in queues:
        queues.remove(q)
