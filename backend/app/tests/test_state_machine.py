"""
Tests for the workflow state machine and key agent contracts.

Run with:  pytest app/tests/ -v --cov=app
"""

from __future__ import annotations

import pytest

from app.workflows.state_machine.machine import (
    StateMachine,
    WorkflowContext,
    WorkflowState,
    WorkflowTrigger,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def ctx() -> WorkflowContext:
    return WorkflowContext(workflow_id="test-wf-001", document_type="capitolato")


@pytest.fixture
def sm() -> StateMachine:
    return StateMachine()


# ── Happy path ────────────────────────────────────────────────────────────────


class TestStateMachineHappyPath:
    def test_full_happy_path(self, sm: StateMachine, ctx: WorkflowContext) -> None:
        """Drive through all states without loops."""
        assert ctx.state == WorkflowState.INIT

        sm.trigger(ctx, WorkflowTrigger.START)
        assert ctx.state == WorkflowState.BRIEFING

        sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)
        assert ctx.state == WorkflowState.ENRICHMENT

        sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)
        assert ctx.state == WorkflowState.VALIDATION

        sm.trigger(ctx, WorkflowTrigger.VALIDATION_PASSED)
        assert ctx.state == WorkflowState.WRITING

        sm.trigger(ctx, WorkflowTrigger.WRITING_DONE)
        assert ctx.state == WorkflowState.QUALITY_ANALYSIS

        sm.trigger(ctx, WorkflowTrigger.QUALITY_PASSED)
        assert ctx.state == WorkflowState.PENDING_APPROVAL

        ctx.human_approval_required = True
        ctx.human_approved = True
        sm.trigger(ctx, WorkflowTrigger.HUMAN_APPROVED)
        assert ctx.state == WorkflowState.COMPLETED

    def test_terminal_state_is_completed(self, ctx: WorkflowContext) -> None:
        assert WorkflowState.COMPLETED in StateMachine.terminal_states()
        assert WorkflowState.FAILED in StateMachine.terminal_states()


# ── Retry loops ───────────────────────────────────────────────────────────────


class TestRetryLoops:
    def test_validation_retry_increments_counter(
        self, sm: StateMachine, ctx: WorkflowContext
    ) -> None:
        sm.trigger(ctx, WorkflowTrigger.START)
        sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)
        sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)
        assert ctx.state == WorkflowState.VALIDATION

        sm.trigger(ctx, WorkflowTrigger.VALIDATION_FAILED)
        assert ctx.retry_count == 1
        assert ctx.state == WorkflowState.BRIEFING

    def test_validation_exhausted_goes_to_failed(
        self, sm: StateMachine, ctx: WorkflowContext
    ) -> None:
        ctx.max_retries = 1
        sm.trigger(ctx, WorkflowTrigger.START)
        sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)
        sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)

        sm.trigger(ctx, WorkflowTrigger.VALIDATION_FAILED)
        assert ctx.state == WorkflowState.BRIEFING  # retry 1

        sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)
        sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)

        sm.trigger(ctx, WorkflowTrigger.VALIDATION_FAILED)
        assert ctx.state == WorkflowState.FAILED  # budget exhausted

    def test_quality_writing_retry(self, sm: StateMachine, ctx: WorkflowContext) -> None:
        # Fast-forward to QUALITY_ANALYSIS
        sm.trigger(ctx, WorkflowTrigger.START)
        sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)
        sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)
        sm.trigger(ctx, WorkflowTrigger.VALIDATION_PASSED)
        sm.trigger(ctx, WorkflowTrigger.WRITING_DONE)
        assert ctx.state == WorkflowState.QUALITY_ANALYSIS

        sm.trigger(ctx, WorkflowTrigger.QUALITY_FAILED_WRITING)
        assert ctx.state == WorkflowState.WRITING
        assert ctx.writing_retry_count == 1

    def test_quality_budget_exhausted(self, sm: StateMachine, ctx: WorkflowContext) -> None:
        ctx.max_retries = 0  # no retries allowed

        sm.trigger(ctx, WorkflowTrigger.START)
        sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)
        sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)
        sm.trigger(ctx, WorkflowTrigger.VALIDATION_PASSED)
        sm.trigger(ctx, WorkflowTrigger.WRITING_DONE)

        sm.trigger(ctx, WorkflowTrigger.QUALITY_FAILED_WRITING)
        assert ctx.state == WorkflowState.FAILED


# ── Fatal error ───────────────────────────────────────────────────────────────


class TestFatalError:
    def test_fatal_error_from_briefing(self, sm: StateMachine, ctx: WorkflowContext) -> None:
        sm.trigger(ctx, WorkflowTrigger.START)
        sm.trigger(ctx, WorkflowTrigger.FATAL_ERROR)
        assert ctx.state == WorkflowState.FAILED

    def test_fatal_error_from_writing(self, sm: StateMachine, ctx: WorkflowContext) -> None:
        sm.trigger(ctx, WorkflowTrigger.START)
        sm.trigger(ctx, WorkflowTrigger.REQUIREMENTS_COLLECTED)
        sm.trigger(ctx, WorkflowTrigger.ENRICHMENT_DONE)
        sm.trigger(ctx, WorkflowTrigger.VALIDATION_PASSED)
        sm.trigger(ctx, WorkflowTrigger.FATAL_ERROR)
        assert ctx.state == WorkflowState.FAILED


# ── Invalid transitions ───────────────────────────────────────────────────────


class TestInvalidTransitions:
    def test_invalid_trigger_raises(self, sm: StateMachine, ctx: WorkflowContext) -> None:
        with pytest.raises(ValueError, match="No transition"):
            sm.trigger(ctx, WorkflowTrigger.QUALITY_PASSED)  # INIT → invalid

    def test_cannot_trigger_from_completed(self, sm: StateMachine, ctx: WorkflowContext) -> None:
        ctx.state = WorkflowState.COMPLETED
        with pytest.raises(ValueError):
            sm.trigger(ctx, WorkflowTrigger.START)

    def test_can_trigger_check(self, sm: StateMachine, ctx: WorkflowContext) -> None:
        assert sm.can_trigger(ctx, WorkflowTrigger.START) is True
        assert sm.can_trigger(ctx, WorkflowTrigger.QUALITY_PASSED) is False


# ── Context defaults ──────────────────────────────────────────────────────────


class TestWorkflowContext:
    def test_default_state(self, ctx: WorkflowContext) -> None:
        assert ctx.state == WorkflowState.INIT
        assert ctx.retry_count == 0
        assert ctx.writing_retry_count == 0
        assert ctx.quality_score == 0.0

    def test_max_retries_default(self, ctx: WorkflowContext) -> None:
        assert ctx.max_retries == 3


# ── Pending Approval ──────────────────────────────────────────────────────────


def _make_ctx(state: WorkflowState = WorkflowState.QUALITY_ANALYSIS) -> WorkflowContext:
    return WorkflowContext(
        workflow_id="test-001",
        document_type="capitolato",
        state=state,
        quality_score=0.92,
    )


class TestPendingApproval:
    def test_quality_passed_goes_to_pending_approval(self, sm: StateMachine) -> None:
        ctx = _make_ctx(WorkflowState.QUALITY_ANALYSIS)
        new_state = sm.trigger(ctx, WorkflowTrigger.QUALITY_PASSED)
        assert new_state == WorkflowState.PENDING_APPROVAL

    def test_human_approved_goes_to_completed(self, sm: StateMachine) -> None:
        ctx = _make_ctx(WorkflowState.PENDING_APPROVAL)
        ctx.human_approval_required = True
        ctx.human_approved = True
        new_state = sm.trigger(ctx, WorkflowTrigger.HUMAN_APPROVED)
        assert new_state == WorkflowState.COMPLETED

    def test_human_rejected_goes_to_failed(self, sm: StateMachine) -> None:
        ctx = _make_ctx(WorkflowState.PENDING_APPROVAL)
        ctx.human_approval_required = True
        ctx.human_approved = False
        new_state = sm.trigger(ctx, WorkflowTrigger.HUMAN_APPROVED)
        assert new_state == WorkflowState.FAILED

    def test_human_approved_without_flag_raises(self, sm: StateMachine) -> None:
        ctx = _make_ctx(WorkflowState.PENDING_APPROVAL)
        ctx.human_approval_required = False
        with pytest.raises(ValueError, match="All guards failed"):
            sm.trigger(ctx, WorkflowTrigger.HUMAN_APPROVED)

    def test_cannot_skip_pending_approval_to_completed(self, sm: StateMachine) -> None:
        ctx = _make_ctx(WorkflowState.QUALITY_ANALYSIS)
        new_state = sm.trigger(ctx, WorkflowTrigger.QUALITY_PASSED)
        assert new_state != WorkflowState.COMPLETED
        assert new_state == WorkflowState.PENDING_APPROVAL
