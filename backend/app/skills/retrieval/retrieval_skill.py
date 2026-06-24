"""
Retrieval Skill

Orchestrates MCP calls to build rich context for ProcurementAgent.

Responsibilities:
- Build targeted search queries from template.yaml (retrieval_queries section)
- Resolve {placeholder} syntax from requirement fields
- Deduplicate and rank retrieved documents
- Format context for injection into agent prompts
- Handle MCP unavailability gracefully (fallback to empty context)

Input:  requirements dict
Output: formatted context string + source metadata list
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.app_config import app_cfg
from app.core.template_config import load_template_config
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
        max_docs: int | None = None,
        kb_id: str | None = None,
    ) -> RetrievedContext:
        """
        Build KB context from requirements.

        Input:  requirements dict + document type
        Output: RetrievedContext with formatted context_text
        """
        if max_docs is None:
            max_docs = app_cfg("retrieval.max_docs", 8)
        queries = self._build_queries(requirements, document_type)
        log.info("retrieval_queries", count=len(queries), doc_type=document_type)

        # Run queries with limited concurrency (NanoRAG processes LLM calls sequentially)
        sem = asyncio.Semaphore(app_cfg("retrieval.max_concurrency", 2))

        async def _limited(query: str) -> list[dict[str, Any]]:
            async with sem:
                return await self._safe_search(
                    query, limit=app_cfg("retrieval.max_results_per_query", 3), kb_id=kb_id
                )

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
        """Generate targeted search queries from template.yaml retrieval_queries.

        Loads query templates from the template config, resolves {placeholder}
        tokens from the requirements dict using dot-notation, and returns only
        the queries where ALL placeholders resolved to non-empty values.
        """
        config = load_template_config(document_type)
        templates = config.get("retrieval_queries", [])
        if not templates:
            log.warning("no_retrieval_queries_in_template", doc_type=document_type)
            return []

        queries: list[str] = []
        placeholder_re = re.compile(r"\{([^}]+)\}")

        for tpl in templates:
            # Find all placeholders in this template
            placeholders = placeholder_re.findall(tpl)
            if not placeholders:
                # No placeholders — use template as-is
                queries.append(tpl)
                continue

            resolved = tpl
            skip = False
            for ph in placeholders:
                value = self._resolve_placeholder(requirements, ph)
                if value is None or value == "":
                    skip = True
                    break
                # For lists, take the first element as readable string
                if isinstance(value, list):
                    if not value:
                        skip = True
                        break
                    first = value[0]
                    if isinstance(first, dict):
                        # Try common descriptive fields
                        value = (
                            first.get("description")
                            or first.get("title")
                            or first.get("system")
                            or first.get("name")
                            or first.get("id", str(first))
                        )
                    else:
                        value = str(first)
                resolved = resolved.replace(f"{{{ph}}}", str(value))

            if not skip:
                queries.append(resolved)

        return list(dict.fromkeys(queries))  # preserve order, remove dups

    @staticmethod
    def _resolve_placeholder(requirements: dict[str, Any], dotpath: str) -> Any:
        """Traverse nested dict with dot-notation path, like _get_nested in validation."""
        parts = dotpath.split(".")
        current: Any = requirements
        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

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
            excerpt = doc.get("excerpt", "").strip()[: app_cfg("retrieval.max_excerpt_length", 500)]

            lines.append(f"### [{i}] {title}")
            lines.append(f"*Source: {source} | Relevance: {score:.2f}*")
            if excerpt:
                lines.append(f"\n{excerpt}\n")
            lines.append("")

        return "\n".join(lines)
