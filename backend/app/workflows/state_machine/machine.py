"""
Explicit state machine for the document generation workflow.

States:  INIT → BRIEFING → ENRICHMENT → VALIDATION → WRITING → QUALITY_ANALYSIS → COMPLETED
                    ↑___________↑___________↑                          |
                                                                    (loop back on fail)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

import structlog

log = structlog.get_logger(__name__)


class WorkflowState(StrEnum):
    INIT = "INIT"
    BRIEFING = "BRIEFING"
    ENRICHMENT = "ENRICHMENT"
    VALIDATION = "VALIDATION"
    WRITING = "WRITING"
    QUALITY_ANALYSIS = "QUALITY_ANALYSIS"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowTrigger(StrEnum):
    START = "start"
    REQUIREMENTS_COLLECTED = "requirements_collected"
    ENRICHMENT_DONE = "enrichment_done"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    WRITING_DONE = "writing_done"
    QUALITY_PASSED = "quality_passed"
    QUALITY_FAILED_WRITING = "quality_failed_writing"
    QUALITY_FAILED_ENRICHMENT = "quality_failed_enrichment"
    FATAL_ERROR = "fatal_error"
    HUMAN_APPROVED = "human_approved"


@dataclass
class Transition:
    from_state: WorkflowState
    trigger: WorkflowTrigger
    to_state: WorkflowState
    guard: Callable[[WorkflowContext], bool] | None = None
    action: Callable[[WorkflowContext], None] | None = None


@dataclass
class WorkflowContext:
    workflow_id: str
    document_type: str
    state: WorkflowState = WorkflowState.INIT
    retry_count: int = 0
    writing_retry_count: int = 0
    enrichment_retry_count: int = 0
    max_retries: int = 3
    quality_threshold: float = 0.75
    requirements: dict = field(default_factory=dict)
    enriched_requirements: dict = field(default_factory=dict)
    draft_content: str = ""
    quality_score: float = 0.0
    quality_issues: list = field(default_factory=list)
    human_approval_required: bool = False
    human_approved: bool = False
    metadata: dict = field(default_factory=dict)


class StateMachine:
    """
    Deterministic, stateless state machine.
    All mutable state lives in WorkflowContext.
    Raises ValueError on illegal transitions.
    """

    def __init__(self) -> None:
        self._transitions: list[Transition] = [
            Transition(WorkflowState.INIT, WorkflowTrigger.START, WorkflowState.BRIEFING),
            Transition(
                WorkflowState.BRIEFING,
                WorkflowTrigger.REQUIREMENTS_COLLECTED,
                WorkflowState.ENRICHMENT,
            ),
            Transition(
                WorkflowState.ENRICHMENT, WorkflowTrigger.ENRICHMENT_DONE, WorkflowState.VALIDATION
            ),
            Transition(
                WorkflowState.VALIDATION, WorkflowTrigger.VALIDATION_PASSED, WorkflowState.WRITING
            ),
            Transition(
                WorkflowState.VALIDATION,
                WorkflowTrigger.VALIDATION_FAILED,
                WorkflowState.BRIEFING,
                guard=lambda ctx: ctx.retry_count < ctx.max_retries,
            ),
            Transition(
                WorkflowState.VALIDATION,
                WorkflowTrigger.VALIDATION_FAILED,
                WorkflowState.FAILED,
                guard=lambda ctx: ctx.retry_count >= ctx.max_retries,
            ),
            Transition(
                WorkflowState.WRITING, WorkflowTrigger.WRITING_DONE, WorkflowState.QUALITY_ANALYSIS
            ),
            Transition(
                WorkflowState.QUALITY_ANALYSIS,
                WorkflowTrigger.QUALITY_PASSED,
                WorkflowState.PENDING_APPROVAL,
            ),
            Transition(
                WorkflowState.PENDING_APPROVAL,
                WorkflowTrigger.HUMAN_APPROVED,
                WorkflowState.COMPLETED,
                guard=lambda ctx: ctx.human_approval_required and ctx.human_approved,
            ),
            Transition(
                WorkflowState.PENDING_APPROVAL,
                WorkflowTrigger.HUMAN_APPROVED,
                WorkflowState.FAILED,
                guard=lambda ctx: ctx.human_approval_required and not ctx.human_approved,
            ),
            Transition(
                WorkflowState.QUALITY_ANALYSIS,
                WorkflowTrigger.QUALITY_FAILED_WRITING,
                WorkflowState.WRITING,
                guard=lambda ctx: ctx.writing_retry_count < ctx.max_retries,
            ),
            Transition(
                WorkflowState.QUALITY_ANALYSIS,
                WorkflowTrigger.QUALITY_FAILED_WRITING,
                WorkflowState.FAILED,
                guard=lambda ctx: ctx.writing_retry_count >= ctx.max_retries,
            ),
            Transition(
                WorkflowState.QUALITY_ANALYSIS,
                WorkflowTrigger.QUALITY_FAILED_ENRICHMENT,
                WorkflowState.ENRICHMENT,
                guard=lambda ctx: ctx.enrichment_retry_count < ctx.max_retries,
            ),
            Transition(
                WorkflowState.QUALITY_ANALYSIS,
                WorkflowTrigger.QUALITY_FAILED_ENRICHMENT,
                WorkflowState.FAILED,
                guard=lambda ctx: ctx.enrichment_retry_count >= ctx.max_retries,
            ),
            *[
                Transition(s, WorkflowTrigger.FATAL_ERROR, WorkflowState.FAILED)
                for s in WorkflowState
                if s not in (WorkflowState.COMPLETED, WorkflowState.FAILED)
            ],
        ]

    def trigger(self, ctx: WorkflowContext, trigger: WorkflowTrigger) -> WorkflowState:
        candidates = [
            t for t in self._transitions if t.from_state == ctx.state and t.trigger == trigger
        ]
        if not candidates:
            raise ValueError(f"No transition from {ctx.state!r} via {trigger!r}")

        for transition in candidates:
            if transition.guard is None or transition.guard(ctx):
                old_state = ctx.state
                ctx.state = transition.to_state

                if trigger == WorkflowTrigger.VALIDATION_FAILED:
                    ctx.retry_count += 1
                elif trigger == WorkflowTrigger.QUALITY_FAILED_WRITING:
                    ctx.writing_retry_count += 1
                elif trigger == WorkflowTrigger.QUALITY_FAILED_ENRICHMENT:
                    ctx.enrichment_retry_count += 1

                if transition.action:
                    transition.action(ctx)

                log.info(
                    "state_transition",
                    workflow_id=ctx.workflow_id,
                    from_state=old_state,
                    to_state=ctx.state,
                    trigger=trigger,
                )
                return ctx.state

        raise ValueError(f"All guards failed for {ctx.state!r} via {trigger!r}")

    def can_trigger(self, ctx: WorkflowContext, trigger: WorkflowTrigger) -> bool:
        return any(
            t.guard is None or t.guard(ctx)
            for t in self._transitions
            if t.from_state == ctx.state and t.trigger == trigger
        )

    @staticmethod
    def terminal_states() -> set[WorkflowState]:
        return {WorkflowState.COMPLETED, WorkflowState.FAILED}
