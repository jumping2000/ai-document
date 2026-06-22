"""
NanoRAG adapter — MCPClient subclass for NanoRAG-specific search logic.

Separates NanoRAG result normalization from the generic MCP protocol client.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.mcp.client.mcp_client import MCPClient

log = structlog.get_logger(__name__)


class NanoRAGAdapter(MCPClient):
    """Adapter that adds NanoRAG-specific search_documents() on top of MCPClient."""

    async def search_documents(
        self, query: str, limit: int = 5, kb_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        High-level wrapper: discover a search tool, call it, return documents.

        Strategy: look for any tool whose name contains 'search', 'query',
        'retrieve', or 'ask'. Map known parameter names from the tool's
        input_schema. Normalize the result into a list of document dicts.

        Args:
            query: Search query string
            limit: Max results
            kb_id: Optional knowledge base identifier

        Returns:
            List of document dicts (may be empty if no search tool found)
        """
        tools = await self.list_tools()
        tool_names = [t["name"] for t in tools]

        # Find first tool matching a search pattern
        search_tool_name: str | None = None
        for pattern in ["search", "query", "retrieve", "ask", "chat"]:
            match = next((n for n in tool_names if pattern in n.lower()), None)
            if match:
                search_tool_name = match
                break

        if not search_tool_name:
            log.warning("mcp_no_search_tool", available=tool_names)
            return []

        # Build arguments from tool schema
        args: dict[str, Any] = {}
        tool_def = next((t for t in tools if t["name"] == search_tool_name), None)
        if tool_def and tool_def.get("input_schema"):
            props = tool_def["input_schema"].get("properties", {})
            for param_name in props:
                low = param_name.lower()
                if low in ("query", "message", "text", "question"):
                    args[param_name] = query
                elif low in ("limit", "top_k", "max_results", "count"):
                    args[param_name] = limit
                elif low in ("kb_id", "knowledge_base", "database", "collection"):
                    args[param_name] = kb_id or "default"

        if not args:
            args = {"query": query, "limit": limit}

        result = await self.call_tool(search_tool_name, args)

        # Normalize result
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            # NanoRAG format: {answer, sources}
            if "sources" in result and isinstance(result["sources"], list):
                sources = result["sources"]
                answer = result.get("answer", "")
                # Check if sources already have text/content (standard format)
                has_text = any(s.get("text") or s.get("content") for s in sources)
                if has_text and not answer:
                    # Standard format — return as-is
                    return sources
                # NanoRAG format — normalize sources
                normalized = []
                for src in sources:
                    doc = {
                        "source": src.get("filename", src.get("source", "")),
                        "text": src.get("text", src.get("content", "")),
                        "excerpt": src.get("text", src.get("content", src.get("excerpt", ""))),
                        "relevance_score": src.get("score", src.get("relevance_score", 0.5)),
                        "title": src.get("section", src.get("title", "")),
                        "page": src.get("page"),
                        "chunk_id": src.get("chunk_id"),
                        "document_id": src.get("document_id"),
                        "kb_id": src.get("kb_id"),
                    }
                    normalized.append(doc)
                # If no text in sources but answer exists, prepend as first doc
                if answer and not any(d["text"] for d in normalized):
                    normalized.insert(
                        0,
                        {
                            "source": "nanorag-chat",
                            "text": answer,
                            "excerpt": answer[:500],
                            "relevance_score": 1.0,
                            "title": "NanoRAG Chat Answer",
                        },
                    )
                return normalized
            if "documents" in result:
                return result["documents"]
            if "results" in result:
                return result["results"]
        return [{"text": str(result), "source": "mcp", "relevance_score": 0.5}]
