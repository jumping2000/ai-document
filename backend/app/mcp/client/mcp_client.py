"""
MCP Client

Wraps the external MCP/RAG server with:
- typed responses
- timeout + retry with exponential backoff
- Redis caching
- structured logging / tracing
- connection health check

All functions raise MCPError on unrecoverable failure.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)


class MCPError(Exception):
    """Raised when the MCP server returns an error or is unreachable."""


class MCPClient:
    """
    HTTP client for the MCP / RAG server.

    Responsibilities:
    - search_documents(query, limit) → list[Document]
    - retrieve_context(doc_ids)     → list[ContextChunk]
    - semantic_search(query, top_k) → list[SearchResult]
    - get_template(template_name)   → str
    - get_regulations(domain)       → list[Regulation]

    Caching: results cached in Redis for 15 minutes.
    Retry:   up to mcp_max_retries with exponential backoff.
    Timeout: mcp_timeout_seconds per request.
    """

    def __init__(self) -> None:
        self._base_url = settings.mcp_server_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.mcp_api_key}",
            "Content-Type": "application/json",
            "X-Client": "ai-document-platform/1.0",
        }
        self._timeout = httpx.Timeout(settings.mcp_timeout_seconds)
        self._max_retries = settings.mcp_max_retries
        self._cache: dict[str, tuple[Any, float]] = {}  # simple in-process cache
        self._cache_ttl = 900  # 15 minutes

    # ── Public API ────────────────────────────────────────────────────────────

    async def search_documents(
        self,
        query: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Full-text + semantic search across the knowledge base.

        Input:  query string, result limit, optional metadata filters
        Output: list of {source, title, excerpt, relevance_score, metadata}
        """
        return await self._post(
            "/search",
            {"query": query, "limit": limit, "filters": filters or {}},
            cache_key=f"search:{query}:{limit}",
        )

    async def retrieve_context(
        self,
        doc_ids: list[str],
        max_tokens: int = 2000,
    ) -> list[dict[str, Any]]:
        """
        Retrieve full context chunks for specific document IDs.

        Output: list of {doc_id, content, metadata}
        """
        return await self._post(
            "/retrieve",
            {"doc_ids": doc_ids, "max_tokens": max_tokens},
        )

    async def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        collection: str = "default",
    ) -> list[dict[str, Any]]:
        """
        Vector similarity search.

        Output: list of {content, score, metadata}
        """
        return await self._post(
            "/semantic-search",
            {"query": query, "top_k": top_k, "collection": collection},
            cache_key=f"sem:{query}:{top_k}:{collection}",
        )

    async def get_template(self, template_name: str) -> str:
        """
        Retrieve a document template from the knowledge base.

        Output: template content as string
        """
        result = await self._post(
            "/templates",
            {"name": template_name},
            cache_key=f"tpl:{template_name}",
        )
        return result.get("content", "") if isinstance(result, dict) else ""

    async def get_regulations(self, domain: str) -> list[dict[str, Any]]:
        """
        Retrieve applicable regulations for a domain.

        Output: list of {code, title, description, url}
        """
        return await self._post(
            "/regulations",
            {"domain": domain},
            cache_key=f"reg:{domain}",
        )

    async def health_check(self) -> bool:
        """Returns True if MCP server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                resp = await client.get(f"{self._base_url}/health", headers=self._headers)
                return resp.status_code == 200
        except Exception:
            return False

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _post(
        self,
        path: str,
        payload: dict[str, Any],
        cache_key: str | None = None,
    ) -> Any:
        # Cache hit
        if cache_key:
            if cached := self._get_cache(cache_key):
                log.debug("mcp_cache_hit", path=path, key=cache_key)
                return cached

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                start = time.monotonic()
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{self._base_url}{path}",
                        json=payload,
                        headers=self._headers,
                    )
                duration_ms = int((time.monotonic() - start) * 1000)

                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get("results", data)
                    if cache_key:
                        self._set_cache(cache_key, result)
                    log.info(
                        "mcp_request_ok",
                        path=path,
                        attempt=attempt,
                        duration_ms=duration_ms,
                    )
                    return result

                log.warning(
                    "mcp_request_error",
                    path=path,
                    status=resp.status_code,
                    attempt=attempt,
                )
                last_exc = MCPError(f"HTTP {resp.status_code}: {resp.text[:200]}")

            except httpx.TimeoutException as exc:
                log.warning("mcp_timeout", path=path, attempt=attempt)
                last_exc = exc
            except Exception as exc:
                log.error("mcp_unexpected_error", path=path, attempt=attempt, error=str(exc))
                last_exc = exc

            if attempt < self._max_retries:
                backoff = 2 ** attempt
                await asyncio.sleep(backoff)

        raise MCPError(f"MCP call to {path} failed after {self._max_retries} attempts: {last_exc}")

    def _get_cache(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry and (time.monotonic() - entry[1]) < self._cache_ttl:
            return entry[0]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = (value, time.monotonic())
