"""
WebSocket streaming endpoint for real-time workflow events.

Clients subscribe to WS /ws/workflow/{id} and receive JSON frames:
  {"event": "state_change", "data": {"state": "BRIEFING"}}
  {"event": "agent_start",  "data": {"agent": "requirement"}}
  {"event": "agent_done",   "data": {"agent": "requirement", "duration_ms": 1200}}
  {"event": "quality_report", "data": {...}}
  {"event": "completed",    "data": {"quality_score": 0.92}}
  {"event": "failed",       "data": {"error": "..."}}
"""

from __future__ import annotations

import asyncio
import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.workflows.execution.runner import subscribe, unsubscribe

log = structlog.get_logger(__name__)
router = APIRouter(tags=["streaming"])


@router.websocket("/ws/workflow/{workflow_id}")
async def workflow_stream(websocket: WebSocket, workflow_id: str) -> None:
    """
    WebSocket endpoint for live workflow event streaming.

    The client connects and receives all events emitted by WorkflowRunner
    for the given workflow_id.

    Connection closes automatically when the workflow reaches COMPLETED or FAILED.
    """
    await websocket.accept()
    queue = subscribe(workflow_id)
    log.info("ws_connected", workflow_id=workflow_id)

    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_text(json.dumps({"event": "heartbeat", "data": {}}))
                continue

            await websocket.send_text(json.dumps(msg))

            # Close on terminal events
            if msg.get("event") in ("completed", "failed"):
                break

    except WebSocketDisconnect:
        log.info("ws_disconnected", workflow_id=workflow_id)
    except Exception as exc:
        log.error("ws_error", workflow_id=workflow_id, error=str(exc))
    finally:
        unsubscribe(workflow_id, queue)
        log.info("ws_cleanup", workflow_id=workflow_id)
