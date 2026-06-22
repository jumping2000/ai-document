"""
Workflow API Routes

POST /workflow/start          — create and start a new workflow
GET  /workflow/{id}           — get workflow status + outputs
POST /workflow/{id}/approve   — human-in-the-loop approval
POST /workflow/{id}/retry     — manual retry from current state
GET  /workflow/{id}/documents — list generated documents
GET  /workflow/{id}/quality-report — latest quality report
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, AsyncSessionLocal
from app.db.models import Workflow
from app.workflows.execution.runner import WorkflowRunner

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/workflow", tags=["workflow"])


# ── Request / Response schemas ────────────────────────────────────────────────

class StartWorkflowRequest(BaseModel):
    document_type: str = Field(..., pattern="^(capitolato|requisiti)$")
    title: str = Field(..., min_length=5, max_length=500)
    raw_description: str = Field(..., min_length=20)
    form_data: dict[str, Any] = Field(default_factory=dict)
    mcp_connection_id: str | None = None


class WorkflowResponse(BaseModel):
    workflow_id: str
    state: str
    document_type: str
    title: str
    retry_count: int
    quality_score: float | None = None
    created_at: str
    updated_at: str


class ApproveRequest(BaseModel):
    approved: bool
    comment: str = ""


class RetryRequest(BaseModel):
    reason: str = ""


# ── In-memory workflow store (replace with DB in production) ──────────────────
# NOTE: For production use SQLAlchemy session + Redis pub/sub

_workflows: dict[str, dict[str, Any]] = {}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/start", status_code=status.HTTP_202_ACCEPTED)
async def start_workflow(
    req: StartWorkflowRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create a new workflow and start execution in the background.

    Returns workflow_id immediately; use GET /workflow/{id} or WS to track progress.
    """
    workflow_id = str(uuid.uuid4())

    initial_input = {
        "document_type": req.document_type,
        "raw_description": req.raw_description,
        "form_data": req.form_data,
        "title": req.title,
        "mcp_connection_id": req.mcp_connection_id,
    }

    # Persist initial workflow row so clients can query immediately
    wf = Workflow(
        id=uuid.UUID(workflow_id),
        title=req.title,
        document_type=req.document_type,
        state="INIT",
        retry_count=0,
        metadata_=initial_input,
        mcp_connection_id=uuid.UUID(req.mcp_connection_id) if req.mcp_connection_id else None,
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)

    async def _run_workflow() -> None:
        async with AsyncSessionLocal() as bg_db:
            # Small delay to allow WebSocket to connect first
            await asyncio.sleep(0.5)
            runner = WorkflowRunner(bg_db)
            await runner.run(workflow_id, req.document_type, initial_input)

    background_tasks.add_task(_run_workflow)

    log.info("workflow_started", workflow_id=workflow_id, doc_type=req.document_type)
    return {"workflow_id": workflow_id, "state": "INIT", "message": "Workflow started"}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Get current workflow state and metadata."""
    try:
        wf = await db.get(Workflow, uuid.UUID(workflow_id))
    except Exception:
        wf = None
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "workflow_id": str(wf.id),
        "state": wf.state,
        "document_type": wf.document_type,
        "title": wf.title,
        "retry_count": wf.retry_count,
        "quality_score": None,
        "created_at": wf.created_at.isoformat() if wf.created_at else None,
        "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
    }


@router.post("/{workflow_id}/approve")
async def approve_workflow(
    workflow_id: str,
    req: ApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Human-in-the-loop approval gate."""
    try:
        wf = await db.get(Workflow, uuid.UUID(workflow_id))
    except Exception:
        wf = None
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if wf.state not in ("QUALITY_ANALYSIS", "COMPLETED"):
        raise HTTPException(
            status_code=400,
            detail=f"Workflow in state {wf.state} does not require approval",
        )

    action = "approved" if req.approved else "rejected"
    log.info("workflow_approval", workflow_id=workflow_id, action=action, comment=req.comment)

    wf.state = "COMPLETED" if req.approved else "FAILED"
    wf.metadata_ = {**(wf.metadata_ or {}), "approval": {"approved": req.approved, "comment": req.comment}}
    db.add(wf)
    await db.commit()
    return {"workflow_id": workflow_id, "action": action}


@router.post("/{workflow_id}/retry")
async def retry_workflow(
    workflow_id: str,
    req: RetryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually trigger retry from FAILED state."""
    try:
        wf = await db.get(Workflow, uuid.UUID(workflow_id))
    except Exception:
        wf = None
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if wf.state != "FAILED":
        raise HTTPException(status_code=400, detail="Only FAILED workflows can be retried")

    wf.state = "INIT"
    wf.retry_count = (wf.retry_count or 0) + 1
    db.add(wf)
    await db.commit()

    async def _retry() -> None:
        async with AsyncSessionLocal() as bg_db:
            runner = WorkflowRunner(bg_db)
            await runner.run(workflow_id, wf.document_type, wf.metadata_ or {})

    background_tasks.add_task(_retry)
    log.info("workflow_retry", workflow_id=workflow_id, reason=req.reason)
    return {"workflow_id": workflow_id, "state": "INIT", "message": "Retry started"}


@router.get("/{workflow_id}/documents")
async def list_documents(workflow_id: str) -> dict[str, Any]:
    """List all generated documents for a workflow."""
    workflow = _workflows.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # In production: query Document table
    return {
        "workflow_id": workflow_id,
        "documents": workflow.get("documents", []),
    }


@router.get("/{workflow_id}/quality-report")
async def get_quality_report(workflow_id: str) -> dict[str, Any]:
    """Get the latest quality report for a workflow."""
    workflow = _workflows.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    report = workflow.get("quality_report")
    if not report:
        raise HTTPException(status_code=404, detail="No quality report available yet")
    return report
