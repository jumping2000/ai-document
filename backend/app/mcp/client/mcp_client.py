"""
MCP Client — nanoRAG via FastMCP

Connects to a nanoRAG MCP server (SSE transport) and exposes
all tools as typed async methods with:
- lazy connection + explicit lifecycle
- in-process TTL cache for search/chat
- structured logging

All functions raise MCPError on unrecoverable failure.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from fastmcp import Client

from app.core.config import settings

log = structlog.get_logger(__name__)


class MCPError(Exception):
    """Raised when the MCP server returns an error or is unreachable."""


class MCPClient:
    """
    FastMCP client for the nanoRAG knowledge-base server.

    Tools exposed by the server:

    ┌──────────────────────────┬────────────────────────────────────────┐
    │ Tool                     │ Signature                              │
    ├──────────────────────────┼────────────────────────────────────────┤
    │ nanorag_health           │ () → dict                              │
    │ nanorag_list_kbs         │ () → list[dict]                        │
    │ nanorag_list_documents   │ (kb_id: str) → list[dict]              │
    │ nanorag_get_graph        │ (kb_id, limit=18, min_weight=1) → dict │
    │ nanorag_get_node_detail  │ (kb_id, entity_id, limit=12) → dict    │
    │ nanorag_chat             │ (kb_id, message, top_k=6) → dict       │
    │ nanorag_upload_document  │ (kb_id, file_content, filename) → dict │
    │ nanorag_delete_document  │ (kb_id, document_id) → dict            │
    └──────────────────────────┴────────────────────────────────────────┘

    Caching:  search/chat results cached in-process for 15 minutes.
    """

    def __init__(self) -> None:
        self._url = settings.mcp_server_url.rstrip("/")
        self._kb_id = settings.mcp_default_kb_id
        self._client: Client | None = None
        self._connected = False

        # In-process TTL cache
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 900  # 15 minutes

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Open SSE transport to the MCP server (idempotent)."""
        if self._connected:
            return
        self._client = Client(self._url)
        await self._client.__aenter__()
        self._connected = True
        log.info("mcp_connected", url=self._url)

    async def disconnect(self) -> None:
        """Close transport (idempotent)."""
        if not self._connected or self._client is None:
            return
        await self._client.__aexit__(None, None, None)
        self._connected = False
        self._client = None
        log.info("mcp_disconnected")

    async def _ensure_connected(self) -> Client:
        if not self._connected or self._client is None:
            await self.connect()
        assert self._client is not None
        return self._client

    # ── Public API ────────────────────────────────────────────────────────

    # -- health ------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """Returns system status dict from nanorag_health."""
        return await self._call_tool("nanorag_health", {})

    # -- knowledge bases ---------------------------------------------------

    async def list_kbs(self) -> list[dict[str, Any]]:
        """List all knowledge bases."""
        return await self._call_tool("nanorag_list_kbs", {})

    # -- documents ---------------------------------------------------------

    async def list_documents(self, kb_id: str | None = None) -> list[dict[str, Any]]:
        """List documents in a knowledge base."""
        return await self._call_tool("nanorag_list_documents", {
            "kb_id": kb_id or self._kb_id,
        })

    async def upload_document(
        self,
        file_content: bytes,
        filename: str = "document",
        kb_id: str | None = None,
    ) -> dict[str, Any]:
        """Upload a document. Returns {document_id, chunk_count}."""
        return await self._call_tool("nanorag_upload_document", {
            "kb_id": kb_id or self._kb_id,
            "file_content": file_content,
            "filename": filename,
        })

    async def delete_document(
        self,
        document_id: str,
        kb_id: str | None = None,
    ) -> dict[str, Any]:
        """Delete a document. Returns {status: 'ok'}."""
        return await self._call_tool("nanorag_delete_document", {
            "kb_id": kb_id or self._kb_id,
            "document_id": document_id,
        })

    # -- graph -------------------------------------------------------------

    async def get_graph(
        self,
        kb_id: str | None = None,
        limit: int = 18,
        min_weight: int = 1,
    ) -> dict[str, Any]:
        """Snapshot of the knowledge graph."""
        return await self._call_tool("nanorag_get_graph", {
            "kb_id": kb_id or self._kb_id,
            "limit": limit,
            "min_weight": min_weight,
        })

    async def get_node_detail(
        self,
        entity_id: str,
        kb_id: str | None = None,
        evidence_limit: int = 12,
    ) -> dict[str, Any]:
        """Entity detail with relationships and supporting documents."""
        return await self._call_tool("nanorag_get_node_detail", {
            "kb_id": kb_id or self._kb_id,
            "entity_id": entity_id,
            "evidence_limit": evidence_limit,
        })

    # -- chat / search -----------------------------------------------------

    async def chat(
        self,
        message: str,
        kb_id: str | None = None,
        top_k: int = 6,
    ) -> dict[str, Any]:
        """Grounded chat. Returns {answer, sources, search_query}."""
        return await self._call_tool(
            "nanorag_chat",
            {
                "kb_id": kb_id or self._kb_id,
                "message": message,
                "top_k": top_k,
            },
            cache_key=f"chat:{message}:{top_k}",
        )

    async def search_documents(
        self,
        query: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Backward-compatible search via nanorag_chat.

        Calls nanorag_chat and extracts the ``sources`` list,
        returning results in the legacy format:
        [{source, title, excerpt, relevance_score, metadata}, …]
        """
        result = await self._call_tool(
            "nanorag_chat",
            {
                "kb_id": self._kb_id,
                "message": query,
                "top_k": limit,
            },
            cache_key=f"search:{query}:{limit}",
        )
        # nanorag_chat returns {answer, sources, search_query}
        raw_sources: list[dict[str, Any]] = result.get("sources", []) if isinstance(result, dict) else []

        # Normalise to legacy format
        return [
            {
                "source": s.get("document_id", s.get("source", "")),
                "title": s.get("title", s.get("document_id", "")),
                "excerpt": s.get("content", s.get("excerpt", ""))[:500],
                "relevance_score": s.get("score", s.get("relevance_score", 0.0)),
                "metadata": s.get("metadata", {}),
            }
            for s in raw_sources[:limit]
        ]

    # ── Internal helpers ──────────────────────────────────────────────────

    async def _call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        cache_key: str | None = None,
    ) -> Any:
        """Call an MCP tool with caching and logging."""
        if cache_key:
            if cached := self._get_cache(cache_key):
                log.debug("mcp_cache_hit", tool=tool_name, key=cache_key)
                return cached

        client = await self._ensure_connected()
        start = time.monotonic()

        try:
            result = await client.call_tool(tool_name, arguments)
        except Exception as exc:
            log.error("mcp_call_failed", tool=tool_name, error=str(exc))
            raise MCPError(f"Tool '{tool_name}' failed: {exc}") from exc

        duration_ms = int((time.monotonic() - start) * 1000)
        log.info("mcp_call_ok", tool=tool_name, duration_ms=duration_ms)

        # Extract content from CallToolResult
        data = self._extract_result(result)

        if cache_key:
            self._set_cache(cache_key, data)
        return data

    @staticmethod
    def _extract_result(result: Any) -> Any:
        """Extract the first text content from a CallToolResult."""
        # fastmcp CallToolResult has .content (list of content blocks)
        if hasattr(result, "content"):
            for block in result.content:
                if hasattr(block, "text"):
                    import json

                    text = block.text
                    try:
                        return json.loads(text)
                    except (json.JSONDecodeError, TypeError):
                        return text
        # Fallback: result might already be a plain value
        if isinstance(result, dict):
            return result
        return result

    def _get_cache(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry and (time.monotonic() - entry[1]) < self._cache_ttl:
            return entry[0]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = (value, time.monotonic())

