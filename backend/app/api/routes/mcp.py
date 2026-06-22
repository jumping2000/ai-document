"""
MCP Connection API Routes

CRUD operations for MCP server connections.
Discovers server capabilities (tools, resources, prompts) via MCP protocol.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import MCPConnection
from app.mcp.client.mcp_client import MCPClient, MCPError

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/mcp/connections", tags=["mcp"])


# ── Request / Response schemas ────────────────────────────────────────────────

class CreateConnectionRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    url: str = Field(..., min_length=10, max_length=500)
    transport: str = Field(default="streamable-http", pattern="^(streamable-http|stdio)$")
    api_key: str | None = None
    default_kb_id: str | None = None


class UpdateConnectionRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    url: str | None = Field(default=None, min_length=10, max_length=500)
    transport: str | None = Field(default=None, pattern="^(streamable-http|stdio)$")
    api_key: str | None = None
    default_kb_id: str | None = None
    is_active: bool | None = None


class ConnectionResponse(BaseModel):
    id: str
    name: str
    description: str | None
    url: str
    transport: str
    is_active: bool
    health_status: str
    last_health_check: str | None
    default_kb_id: str | None
    discovered_tools: list[dict[str, Any]]
    discovered_resources: list[dict[str, Any]]
    discovered_prompts: list[dict[str, Any]]
    discovered_kbs: list[dict[str, Any]]
    created_at: str
    updated_at: str


class CallToolRequest(BaseModel):
    tool_name: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_response(conn: MCPConnection) -> ConnectionResponse:
    return ConnectionResponse(
        id=str(conn.id),
        name=conn.name,
        description=conn.description,
        url=conn.url,
        transport=conn.transport,
        is_active=conn.is_active,
        health_status=conn.health_status,
        last_health_check=conn.last_health_check.isoformat() if conn.last_health_check else None,
        default_kb_id=conn.default_kb_id,
        discovered_tools=conn.discovered_tools or [],
        discovered_resources=conn.discovered_resources or [],
        discovered_prompts=conn.discovered_prompts or [],
        discovered_kbs=conn.discovered_kbs or [],
        created_at=conn.created_at.isoformat() if conn.created_at else "",
        updated_at=conn.updated_at.isoformat() if conn.updated_at else "",
    )


async def _test_and_discover(url: str, api_key: str | None) -> dict[str, Any]:
    """Connect to MCP server and discover capabilities including KBs."""
    client = MCPClient(url=url, api_key=api_key)
    try:
        await client.connect()
        capabilities = await client.discover_all()

        # Also discover knowledge bases
        kbs = []
        try:
            tools = capabilities.get("tools", [])
            list_kb_tool = next((t for t in tools if "list_kbs" in t.get("name", "").lower()), None)
            if list_kb_tool:
                kb_result = await client.call_tool(list_kb_tool["name"], {})
                # Handle both single dict, list, and multiple content blocks
                if isinstance(kb_result, dict):
                    kbs = [kb_result]
                elif isinstance(kb_result, list):
                    kbs = kb_result
                else:
                    kbs = []
        except Exception as exc:
            log.warning("mcp_discover_kbs_failed", error=str(exc))

        await client.disconnect()
        return {"status": "ok", "capabilities": capabilities, "kbs": kbs}
    except Exception as exc:
        log.error("mcp_test_failed", url=url, error=str(exc))
        raise MCPError(f"Connection failed: {exc}") from exc
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", status_code=status.HTTP_200_OK)
async def list_connections(db: AsyncSession = Depends(get_db)) -> list[ConnectionResponse]:
    """List all MCP connections."""
    result = await db.execute(select(MCPConnection).order_by(MCPConnection.created_at.desc()))
    connections = result.scalars().all()
    return [_to_response(c) for c in connections]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_connection(
    req: CreateConnectionRequest,
    db: AsyncSession = Depends(get_db),
) -> ConnectionResponse:
    """Create a new MCP connection and discover capabilities."""
    # Test connection first
    try:
        test_result = await _test_and_discover(req.url, req.api_key)
    except MCPError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    capabilities = test_result["capabilities"]

    conn = MCPConnection(
        id=uuid.uuid4(),
        name=req.name,
        description=req.description,
        url=req.url,
        transport=req.transport,
        api_key=req.api_key,
        default_kb_id=req.default_kb_id,
        is_active=True,
        discovered_tools=capabilities.get("tools", []),
        discovered_resources=capabilities.get("resources", []),
        discovered_prompts=capabilities.get("prompts", []),
        discovered_kbs=test_result.get("kbs", []),
        health_status="connected",
        last_health_check=datetime.utcnow(),
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    log.info("mcp_connection_created", name=req.name, tools=len(capabilities.get("tools", [])))
    return _to_response(conn)


@router.get("/{connection_id}", status_code=status.HTTP_200_OK)
async def get_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
) -> ConnectionResponse:
    """Get a specific MCP connection."""
    try:
        conn = await db.get(MCPConnection, uuid.UUID(connection_id))
    except Exception:
        conn = None
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return _to_response(conn)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an MCP connection."""
    try:
        conn = await db.get(MCPConnection, uuid.UUID(connection_id))
    except Exception:
        conn = None
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    await db.delete(conn)
    await db.commit()
    log.info("mcp_connection_deleted", name=conn.name)


@router.post("/{connection_id}/refresh", status_code=status.HTTP_200_OK)
async def refresh_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
) -> ConnectionResponse:
    """Re-discover capabilities from the MCP server."""
    try:
        conn = await db.get(MCPConnection, uuid.UUID(connection_id))
    except Exception:
        conn = None
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        test_result = await _test_and_discover(conn.url, conn.api_key)
        capabilities = test_result["capabilities"]

        conn.discovered_tools = capabilities.get("tools", [])
        conn.discovered_resources = capabilities.get("resources", [])
        conn.discovered_prompts = capabilities.get("prompts", [])
        conn.health_status = "connected"
        conn.last_health_check = datetime.utcnow()
        conn.is_active = True
        await db.commit()
        await db.refresh(conn)

        log.info("mcp_connection_refreshed", name=conn.name)
        return _to_response(conn)

    except MCPError as exc:
        conn.health_status = "error"
        conn.is_active = False
        await db.commit()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{connection_id}/call", status_code=status.HTTP_200_OK)
async def call_tool(
    connection_id: str,
    req: CallToolRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Call a tool on the MCP server."""
    try:
        conn = await db.get(MCPConnection, uuid.UUID(connection_id))
    except Exception:
        conn = None
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    if not conn.is_active:
        raise HTTPException(status_code=400, detail="Connection is not active")

    client = MCPClient(url=conn.url, api_key=conn.api_key)
    try:
        await client.connect()
        result = await client.call_tool(req.tool_name, req.arguments)
        await client.disconnect()
        return {"result": result}
    except MCPError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


class TestConnectionRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=500)
    api_key: str | None = None


@router.post("/test", status_code=status.HTTP_200_OK)
async def test_connection(req: TestConnectionRequest) -> dict[str, Any]:
    """Test connection and discover available knowledge bases."""
    try:
        result = await _test_and_discover(req.url, req.api_key)
        return {"status": "ok", "kbs": result.get("kbs", []), "tools_count": len(result.get("capabilities", {}).get("tools", []))}
    except MCPError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{connection_id}/resource", status_code=status.HTTP_200_OK)
async def read_resource(
    connection_id: str,
    uri: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Read a resource from the MCP server."""
    try:
        conn = await db.get(MCPConnection, uuid.UUID(connection_id))
    except Exception:
        conn = None
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    if not conn.is_active:
        raise HTTPException(status_code=400, detail="Connection is not active")

    client = MCPClient(url=conn.url, api_key=conn.api_key)
    try:
        await client.connect()
        result = await client.read_resource(uri)
        await client.disconnect()
        return {"result": result}
    except MCPError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
