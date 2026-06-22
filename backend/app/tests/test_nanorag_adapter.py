"""Tests for NanoRAGAdapter.search_documents()."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.mcp.client.adapters.nanorag import NanoRAGAdapter


@pytest.fixture
def client() -> NanoRAGAdapter:
    """Return a NanoRAGAdapter with mocked lifecycle (skip real connect)."""
    c = NanoRAGAdapter.__new__(NanoRAGAdapter)
    c._connected = True
    c._client = AsyncMock()
    c._exit_stack = None
    c._cache = {}
    c._cache_ttl = 900
    return c


# ---------------------------------------------------------------------------
# 1. search tool found → returns list
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_documents_with_search_tool(client: NanoRAGAdapter) -> None:
    """list_tools returns a tool named 'search_docs' → call_tool result is returned."""
    tools = [{"name": "search_docs", "description": "Search documents", "input_schema": {}}]
    with (
        patch.object(client, "list_tools", new_callable=AsyncMock, return_value=tools),
        patch.object(
            client,
            "call_tool",
            new_callable=AsyncMock,
            return_value=[{"text": "hello", "source": "kb", "relevance_score": 0.9}],
        ),
    ):
        result = await client.search_documents("hello")
    assert isinstance(result, list)
    assert result[0]["text"] == "hello"


# ---------------------------------------------------------------------------
# 2. no search tool → returns [] and logs warning
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_documents_no_search_tool(client: NanoRAGAdapter) -> None:
    """When no tool matches search patterns, returns empty list."""
    tools = [{"name": "ping", "description": "Ping", "input_schema": {}}]
    with patch.object(client, "list_tools", new_callable=AsyncMock, return_value=tools):
        result = await client.search_documents("test query")
    assert result == []


# ---------------------------------------------------------------------------
# 3. parameter mapping from input_schema
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_documents_maps_params(client: NanoRAGAdapter) -> None:
    """Tool schema with query/limit/kb_id → call_tool receives mapped args."""
    tools = [
        {
            "name": "search_docs",
            "description": "Search",
            "input_schema": {
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                    "kb_id": {"type": "string"},
                }
            },
        }
    ]
    call_mock = AsyncMock(return_value=[])
    with (
        patch.object(client, "list_tools", new_callable=AsyncMock, return_value=tools),
        patch.object(client, "call_tool", call_mock),
    ):
        await client.search_documents("test", limit=10, kb_id="my-kb")

    call_mock.assert_called_once_with(
        "search_docs", {"query": "test", "limit": 10, "kb_id": "my-kb"}
    )


# ---------------------------------------------------------------------------
# 4. dict result with "sources" key → extracts sources
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_documents_dict_result(client: NanoRAGAdapter) -> None:
    """call_tool returns {"sources": [...]} → method returns the list."""
    tools = [{"name": "search_docs", "description": "Search", "input_schema": {}}]
    sources = [{"text": "a", "source": "x", "relevance_score": 0.8}]
    with (
        patch.object(client, "list_tools", new_callable=AsyncMock, return_value=tools),
        patch.object(
            client, "call_tool", new_callable=AsyncMock, return_value={"sources": sources}
        ),
    ):
        result = await client.search_documents("q")
    assert result == sources


# ---------------------------------------------------------------------------
# 5. plain string result → wraps in list
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_documents_fallback_result(client: NanoRAGAdapter) -> None:
    """call_tool returns a plain string → wrapped in [{...}]."""
    tools = [{"name": "search_docs", "description": "Search", "input_schema": {}}]
    with (
        patch.object(client, "list_tools", new_callable=AsyncMock, return_value=tools),
        patch.object(client, "call_tool", new_callable=AsyncMock, return_value="some text"),
    ):
        result = await client.search_documents("q")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["text"] == "some text"
    assert result[0]["source"] == "mcp"
    assert result[0]["relevance_score"] == 0.5
