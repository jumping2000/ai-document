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
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator.agent import OrchestratorAgent
from app.agents.procurement.agent import ProcurementAgent
from app.agents.quality.agent import QualityAgent
from app.agents.requirement.agent import RequirementAgent
from app.agents.lead_writer.agent import LeadWriterAgent
from app.workflows.state_machine.machine import (
    StateMachine,
    WorkflowContext,
    WorkflowState,
    WorkflowTrigger,
)

log = structlog.get_logger(__name__)

# SSE event bus: workflow_id → list of queues
_event_queues: dict[str, list[asyncio.Queue]] = {}


class WorkflowRunner:
    """
    Drives a single workflow instance end-to-end.

    Input:  workflow_id, document_type, initial_user_input
    Output: persisted documents + quality report
    Side-effects: SSE events emitted to subscribed clients
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sm = StateMachine()
        self.orchestrator = OrchestratorAgent()
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
            self.sm.trigger(ctx, WorkflowTrigger.START)
            await self._emit(workflow_id, "state_change", {"state": ctx.state})

            # ── BRIEFING ────────────────────────────────────────────────────
            req_output = await self._run_agent(
                workflow_id,
                "requirement",
                self.requirement_agent.run,
                initial_input,
            )
            ctx.requirements = req_output
            self.sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)
            await self._emit(workflow_id, "state_change", {"state": ctx.state})

            # ── ENRICHMENT ──────────────────────────────────────────────────
            enriched = await self._run_agent(
                workflow_id,
                "procurement",
                self.procurement_agent.run,
                ctx.requirements,
            )
            ctx.enriched_requirements = enriched
            self.sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)
            await self._emit(workflow_id, "state_change", {"state": ctx.state})

            # ── VALIDATION loop ─────────────────────────────────────────────
            while ctx.state == WorkflowState.VALIDATION:
                validation = await self.orchestrator.validate_requirements(ctx)
                if validation["valid"]:
                    self.sm.trigger(ctx, WorkflowTrigger.VALIDATION_PASSED)
                else:
                    await self._emit(workflow_id, "validation_failed", validation)
                    self.sm.trigger(ctx, WorkflowTrigger.VALIDATION_FAILED)

                    if ctx.state == WorkflowState.BRIEFING:
                        # re-collect requirements with clarifications
                        req_output = await self._run_agent(
                            workflow_id,
                            "requirement",
                            self.requirement_agent.run,
                            {**initial_input, "clarifications": validation["issues"]},
                        )
                        ctx.requirements = req_output
                        self.sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)

                        enriched = await self._run_agent(
                            workflow_id,
                            "procurement",
                            self.procurement_agent.run,
                            ctx.requirements,
                        )
                        ctx.enriched_requirements = enriched
                        self.sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)

                    elif ctx.state == WorkflowState.FAILED:
                        raise RuntimeError("Validation retry budget exhausted")

                await self._emit(workflow_id, "state_change", {"state": ctx.state})

            # ── WRITING + QUALITY loop ───────────────────────────────────────
            while ctx.state in (WorkflowState.WRITING, WorkflowState.QUALITY_ANALYSIS):
                if ctx.state == WorkflowState.WRITING:
                    draft = await self._run_agent(
                        workflow_id,
                        "lead_writer",
                        self.writer_agent.run,
                        ctx.enriched_requirements,
                    )
                    ctx.draft_content = draft["content"]
                    self.sm.trigger(ctx, WorkflowTrigger.WRITING_DONE)
                    await self._emit(workflow_id, "state_change", {"state": ctx.state})

                elif ctx.state == WorkflowState.QUALITY_ANALYSIS:
                    report = await self._run_agent(
                        workflow_id,
                        "quality",
                        self.quality_agent.run,
                        {"content": ctx.draft_content, "requirements": ctx.enriched_requirements},
                    )
                    ctx.quality_score = report["score"]
                    ctx.quality_issues = report.get("issues", [])

                    await self._emit(workflow_id, "quality_report", report)

                    if report["passed"]:
                        self.sm.trigger(ctx, WorkflowTrigger.QUALITY_PASSED)
                    elif report.get("needs_enrichment"):
                        self.sm.trigger(ctx, WorkflowTrigger.QUALITY_FAILED_ENRICHMENT)
                        if ctx.state == WorkflowState.ENRICHMENT:
                            enriched = await self._run_agent(
                                workflow_id,
                                "procurement",
                                self.procurement_agent.run,
                                ctx.requirements,
                            )
                            ctx.enriched_requirements = enriched
                            self.sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)
                            self.sm.trigger(ctx, WorkflowTrigger.VALIDATION_PASSED)
                    else:
                        self.sm.trigger(ctx, WorkflowTrigger.QUALITY_FAILED_WRITING)

                    await self._emit(workflow_id, "state_change", {"state": ctx.state})

                    if ctx.state == WorkflowState.FAILED:
                        raise RuntimeError("Quality retry budget exhausted")

            # ── COMPLETED ───────────────────────────────────────────────────
            await self._emit(workflow_id, "completed", {
                "workflow_id": workflow_id,
                "quality_score": ctx.quality_score,
            })
            return {"status": "completed", "quality_score": ctx.quality_score}

        except Exception as exc:
            log.error("workflow_failed", workflow_id=workflow_id, error=str(exc))
            self.sm.trigger(ctx, WorkflowTrigger.FATAL_ERROR)
            await self._emit(workflow_id, "failed", {"error": str(exc)})
            return {"status": "failed", "error": str(exc)}

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _run_agent(
        self,
        workflow_id: str,
        agent_name: str,
        fn,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        start = time.monotonic()
        await self._emit(workflow_id, "agent_start", {"agent": agent_name})
        result = await fn(payload)
        duration_ms = int((time.monotonic() - start) * 1000)
        await self._emit(workflow_id, "agent_done", {
            "agent": agent_name,
            "duration_ms": duration_ms,
        })
        log.info("agent_completed", agent=agent_name, duration_ms=duration_ms)
        return result

    async def _emit(self, workflow_id: str, event: str, data: dict[str, Any]) -> None:
        msg = {"event": event, "data": data}
        for q in _event_queues.get(workflow_id, []):
            await q.put(msg)


# ── SSE subscription helpers (used by WebSocket route) ───────────────────────

def subscribe(workflow_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _event_queues.setdefault(workflow_id, []).append(q)
    return q


def unsubscribe(workflow_id: str, q: asyncio.Queue) -> None:
    queues = _event_queues.get(workflow_id, [])
    if q in queues:
        queues.remove(q)
