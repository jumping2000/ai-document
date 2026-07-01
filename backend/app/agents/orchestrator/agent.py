"""
Orchestrator Agent — controls the workflow state machine,
coordinates all agents, manages retry loops and human-in-the-loop.
"""

import time

import structlog
from agno.agent import Agent

from app.core.agent_config import load_agent_config
from app.core.config import settings
from app.core.json_extract import extract_json
from app.core.llm import get_model_adapter
from app.workflows.state_machine.machine import (
    StateMachine,
    WorkflowContext,
    WorkflowState,
    WorkflowTrigger,
)

log = structlog.get_logger(__name__)


def _parse_json_response(content: str) -> dict:
    data = extract_json(content)
    if data:
        return data
    return {"complete": False, "missing": ["parse_error"], "reason": content}


class OrchestratorAgent:
    """
    Drives the full document-generation workflow.
    Owns the StateMachine; delegates to specialist agents;
    emits SSE events so the frontend can stream progress.
    """

    def __init__(self, context: WorkflowContext, event_bus) -> None:
        self.sm = StateMachine(context)
        self.event_bus = event_bus
        self.ctx = context

        # Lazy imports to avoid circular deps
        from app.agents.lead_writer.agent import LeadWriterAgent
        from app.agents.procurement.agent import ProcurementAgent
        from app.agents.quality.agent import QualityAgent
        from app.agents.requirement.agent import RequirementAgent

        self.requirement_agent = RequirementAgent()
        self.procurement_agent = ProcurementAgent()
        self.lead_writer_agent = LeadWriterAgent()
        self.quality_agent = QualityAgent()

        cfg = load_agent_config("orchestrator")
        system_prompt = cfg.get("system_prompt", []) if cfg else []
        if isinstance(system_prompt, list):
            instructions = [s.strip() for s in system_prompt if s.strip()]
        elif isinstance(system_prompt, str) and system_prompt.strip():
            instructions = [
                line.strip() for line in system_prompt.strip().split("\n") if line.strip()
            ]
        else:
            instructions = ["Coordinate a multi-agent workflow for IT document generation."]
        self._max_retries = (
            cfg.get("parameters", {}).get("max_retries", settings.workflow_max_retries)
            if cfg
            else settings.workflow_max_retries
        )

        self._agno = Agent(
            name="orchestrator",
            role="Workflow Orchestrator",
            description="Ensure document generation workflow completes successfully",
            instructions=instructions,
            model=get_model_adapter(),
            markdown=True,
        )

    async def run(self) -> WorkflowContext:
        log.info("workflow.start", workflow_id=self.ctx.workflow_id, state=self.ctx.state)
        self.sm.trigger(WorkflowTrigger.START)
        await self._emit("state_change", {"state": WorkflowState.BRIEFING})

        while not self.sm.is_terminal:
            try:
                await self._step()
            except Exception as exc:
                log.error("workflow.error", workflow_id=self.ctx.workflow_id, error=str(exc))
                self.ctx.error_message = str(exc)
                self.sm.trigger(WorkflowTrigger.ERROR)
                await self._emit("state_change", {"state": WorkflowState.FAILED, "error": str(exc)})
                break

        log.info(
            "workflow.finished",
            workflow_id=self.ctx.workflow_id,
            final_state=self.ctx.state,
            quality_score=self.ctx.quality_score,
        )
        return self.ctx

    async def _step(self) -> None:
        match self.sm.current_state:
            case WorkflowState.BRIEFING:
                await self._run_briefing()
            case WorkflowState.ENRICHMENT:
                await self._run_enrichment()
            case WorkflowState.VALIDATION:
                await self._run_validation()
            case WorkflowState.WRITING:
                await self._run_writing()
            case WorkflowState.QUALITY_ANALYSIS:
                await self._run_quality()
            case _:
                self.sm.trigger(WorkflowTrigger.ERROR)

    async def _run_briefing(self) -> None:
        await self._emit("agent_start", {"agent": "requirement"})
        t0 = time.monotonic()
        result = await self.requirement_agent.collect(
            workflow_id=self.ctx.workflow_id,
            document_type=self.ctx.document_type,
            existing=self.ctx.requirements,
        )
        self.ctx.requirements = result.requirements
        await self._emit(
            "agent_done",
            {
                "agent": "requirement",
                "duration_ms": int((time.monotonic() - t0) * 1000),
                "summary": result.summary,
            },
        )
        self.sm.trigger(WorkflowTrigger.REQUIREMENTS_COLLECTED)
        await self._emit("state_change", {"state": WorkflowState.ENRICHMENT})

    async def _run_enrichment(self) -> None:
        await self._emit("agent_start", {"agent": "procurement"})
        t0 = time.monotonic()
        result = await self.procurement_agent.enrich(
            requirements=self.ctx.requirements,
            document_type=self.ctx.document_type,
        )
        self.ctx.enriched_requirements = result.enriched
        self.ctx.enrichment_retries += 1
        await self._emit(
            "agent_done",
            {
                "agent": "procurement",
                "duration_ms": int((time.monotonic() - t0) * 1000),
                "sources_count": len(result.sources),
            },
        )
        self.sm.trigger(WorkflowTrigger.ENRICHMENT_DONE)
        await self._emit("state_change", {"state": WorkflowState.VALIDATION})

    async def _run_validation(self) -> None:
        await self._emit("agent_start", {"agent": "orchestrator/validation"})

        import string

        cfg = load_agent_config("orchestrator")
        prompt = string.Template(cfg["prompt_template"]).substitute(
            document_type=self.ctx.document_type,
            enriched_requirements=str(self.ctx.enriched_requirements),
        )
        response = await self._agno.arun(prompt)
        validation = _parse_json_response(response.content)

        if validation.get("complete", False):
            self.sm.trigger(WorkflowTrigger.VALIDATION_PASSED)
            await self._emit("state_change", {"state": WorkflowState.WRITING})
        else:
            self.ctx.briefing_retries += 1
            self.sm.trigger(WorkflowTrigger.VALIDATION_FAILED)
            await self._emit(
                "validation_failed",
                {
                    "missing": validation.get("missing", []),
                    "retry": self.ctx.briefing_retries,
                },
            )
            await self._emit("state_change", {"state": self.sm.current_state})

    async def _run_writing(self) -> None:
        await self._emit("agent_start", {"agent": "lead_writer"})
        t0 = time.monotonic()
        result = await self.lead_writer_agent.write(
            enriched_requirements=self.ctx.enriched_requirements,
            document_type=self.ctx.document_type,
            quality_issues=self.ctx.quality_issues,
        )
        self.ctx.draft_content = result.markdown
        self.ctx.writing_retries += 1
        await self._emit(
            "agent_done",
            {
                "agent": "lead_writer",
                "duration_ms": int((time.monotonic() - t0) * 1000),
                "word_count": len(result.markdown.split()),
            },
        )
        self.sm.trigger(WorkflowTrigger.WRITING_DONE)
        await self._emit("state_change", {"state": WorkflowState.QUALITY_ANALYSIS})

    async def _run_quality(self) -> None:
        await self._emit("agent_start", {"agent": "quality"})
        t0 = time.monotonic()
        report = await self.quality_agent.review(
            content=self.ctx.draft_content,
            requirements=self.ctx.enriched_requirements,
            document_type=self.ctx.document_type,
        )
        self.ctx.quality_score = report.score
        self.ctx.quality_issues = report.issues
        await self._emit(
            "quality_report",
            {
                "score": report.score,
                "passed": report.passed,
                "issues": report.issues,
                "duration_ms": int((time.monotonic() - t0) * 1000),
            },
        )
        if report.passed:
            self.sm.trigger(WorkflowTrigger.QUALITY_PASSED)
            await self._emit("state_change", {"state": WorkflowState.COMPLETED})
        elif report.needs_enrichment:
            self.sm.trigger(WorkflowTrigger.QUALITY_FAILED_ENRICHMENT)
            await self._emit("state_change", {"state": self.sm.current_state})
        else:
            self.sm.trigger(WorkflowTrigger.QUALITY_FAILED_WRITING)
            await self._emit("state_change", {"state": self.sm.current_state})

    async def _emit(self, event_type: str, payload: dict) -> None:
        await self.event_bus.emit(
            workflow_id=self.ctx.workflow_id,
            event_type=event_type,
            payload=payload,
        )
