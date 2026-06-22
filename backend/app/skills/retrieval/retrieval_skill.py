"""
Retrieval Skill

Orchestrates MCP calls to build rich context for ProcurementAgent.

Responsibilities:
- Build targeted search queries from requirement fields
- Deduplicate and rank retrieved documents
- Format context for injection into agent prompts
- Handle MCP unavailability gracefully (fallback to empty context)

Input:  requirements dict
Output: formatted context string + source metadata list
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.mcp.client.adapters.nanorag import NanoRAGAdapter
from app.mcp.client.mcp_client import MCPError

log = structlog.get_logger(__name__)


@dataclass
class RetrievedContext:
    context_text: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    query_count: int = 0
    total_docs: int = 0


class RetrievalSkill:
    """
    Builds knowledge-base context for document generation.

    Success:  returns RetrievedContext with populated context_text
    Failure:  returns RetrievedContext with empty context_text (agent proceeds without KB)
    """

    def __init__(
        self,
        mcp_url: str | None = None,
        mcp_api_key: str | None = None,
    ) -> None:
        self._mcp = NanoRAGAdapter(url=mcp_url, api_key=mcp_api_key)

    async def build_context(
        self,
        requirements: dict[str, Any],
        document_type: str = "capitolato",
        max_docs: int = 8,
        kb_id: str | None = None,
    ) -> RetrievedContext:
        """
        Build KB context from requirements.

        Input:  requirements dict + document type
        Output: RetrievedContext with formatted context_text
        """
        queries = self._build_queries(requirements, document_type)
        log.info("retrieval_queries", count=len(queries), doc_type=document_type)

        # Run queries with limited concurrency (NanoRAG processes LLM calls sequentially)
        sem = asyncio.Semaphore(2)

        async def _limited(query: str) -> list[dict[str, Any]]:
            async with sem:
                return await self._safe_search(query, limit=3, kb_id=kb_id)

        search_tasks = [_limited(q) for q in queries]
        results_per_query = await asyncio.gather(*search_tasks)

        # Flatten + deduplicate
        all_docs: list[dict[str, Any]] = []
        seen_sources: set[str] = set()
        for docs in results_per_query:
            for doc in docs:
                src = doc.get("source", "")
                if src not in seen_sources:
                    seen_sources.add(src)
                    all_docs.append(doc)

        # Sort by relevance score, take top N
        all_docs.sort(key=lambda d: d.get("relevance_score", 0), reverse=True)
        top_docs = all_docs[:max_docs]

        context_text = self._format_context(top_docs)

        log.info(
            "retrieval_done",
            queries=len(queries),
            total_docs=len(all_docs),
            selected=len(top_docs),
        )

        return RetrievedContext(
            context_text=context_text,
            sources=top_docs,
            query_count=len(queries),
            total_docs=len(all_docs),
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_queries(
        self,
        requirements: dict[str, Any],
        document_type: str,
    ) -> list[str]:
        """Generate targeted search queries from requirement fields."""
        queries: list[str] = []

        # Base document type query
        queries.append(f"template {document_type} IT procurement italiana")

        # Standards
        standards = requirements.get("security_compliance", {}).get("standards", [])
        for std in standards[:3]:
            queries.append(f"requisiti compliance {std} IT")

        # Integration systems
        integrations = requirements.get("integrations", [])
        for intg in integrations[:2]:
            sys_name = intg.get("system", "")
            if sys_name:
                queries.append(f"integrazione {sys_name} requisiti tecnici")

        # Sector-specific
        org = requirements.get("project", {}).get("organization", "")
        if "pubblica amministrazione" in org.lower() or "pa" in org.lower():
            queries.append("normativa appalti pubblici ICT AGID CAD")
            queries.append("D.Lgs 36/2023 codice contratti pubblici digitale")

        # Security
        data_class = requirements.get("security_compliance", {}).get("data_classification", "")
        if data_class:
            queries.append(f"GDPR {data_class} data protection requirements IT")

        # SLA benchmarks
        queries.append(f"SLA benchmark {document_type} enterprise IT")

        return list(dict.fromkeys(queries))  # preserve order, remove dups

    async def _safe_search(
        self,
        query: str,
        limit: int = 3,
        kb_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Wraps MCPClient.search_documents — returns [] on failure."""
        try:
            return await self._mcp.search_documents(query, limit=limit, kb_id=kb_id)
        except MCPError as exc:
            log.warning("retrieval_mcp_error", query=query, error=str(exc))
            return []
        except Exception as exc:
            log.error("retrieval_unexpected_error", query=query, error=str(exc))
            return []

    def _format_context(self, docs: list[dict[str, Any]]) -> str:
        """Format retrieved docs into a prompt-injectable context string."""
        if not docs:
            return ""

        lines = ["## Knowledge Base Context\n"]
        for i, doc in enumerate(docs, 1):
            title = doc.get("title", f"Document {i}")
            source = doc.get("source", "unknown")
            score = doc.get("relevance_score", 0.0)
            excerpt = doc.get("excerpt", "").strip()[:500]

            lines.append(f"### [{i}] {title}")
            lines.append(f"*Source: {source} | Relevance: {score:.2f}*")
            if excerpt:
                lines.append(f"\n{excerpt}\n")
            lines.append("")

        return "\n".join(lines)
