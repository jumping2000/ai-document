"""
Procurement Agent — enriches requirements via MCP/RAG knowledge base.
Input  : requirements dict, document_type, optional mcp connection params
Output : ProcurementResult(enriched, sources)
"""

import json
from dataclasses import dataclass
from typing import Any

import structlog
from agno.agent import Agent

from app.core.agent_config import load_agent_config
from app.core.json_extract import extract_json
from app.core.llm import get_model_adapter
from app.skills.retrieval.retrieval_skill import RetrievalSkill

log = structlog.get_logger(__name__)


@dataclass
class ProcurementResult:
    enriched: dict[str, Any]
    sources: list[str]
    standards_applied: list[str]


class ProcurementAgent:
    def __init__(self) -> None:
        self._retrieval = RetrievalSkill()
        cfg = load_agent_config("procurement")
        system_prompt = cfg.get("system_prompt", "")
        if isinstance(system_prompt, list):
            instructions = [s.strip() for s in system_prompt if s.strip()]
        elif isinstance(system_prompt, str) and system_prompt.strip():
            instructions = [
                line.strip() for line in system_prompt.strip().split("\n") if line.strip()
            ]
        else:
            instructions = [
                "Apply ISO 27001, ISO 9001, and GDPR where relevant.",
                "Add SLA templates from the knowledge base.",
                "Include security requirements from OWASP and CIS benchmarks.",
                "Reference Italian public procurement code (D.Lgs. 36/2023) for capitolati.",
                "Return enriched requirements as structured JSON.",
            ]

        self._agno = Agent(
            name="procurement_specialist",
            role="IT Procurement Specialist",
            description="Enrich requirements with standards, regulations, and best practices",
            instructions=instructions,
            model=get_model_adapter(),
            markdown=False,
        )

    async def enrich(
        self,
        requirements: dict[str, Any],
        document_type: str,
        mcp_url: str | None = None,
        mcp_api_key: str | None = None,
        mcp_tools: list[dict[str, Any]] | None = None,
        mcp_kb_id: str | None = None,
    ) -> ProcurementResult:
        """
        Enrich requirements with standards and knowledge base context.

        Args:
            requirements: Structured requirements
            document_type: Type of document
            mcp_url: Optional MCP server URL (if not provided, skips MCP)
            mcp_api_key: Optional MCP API key
            mcp_tools: Optional pre-discovered tools list (unused, kept for API compat)
            mcp_kb_id: Optional knowledge base ID
        """
        log.info(
            "procurement.enrich.start",
            doc_type=document_type,
            has_mcp=bool(mcp_url),
        )

        kb_context = ""
        sources: list[str] = []

        if mcp_url:
            self._retrieval = RetrievalSkill(mcp_url=mcp_url, mcp_api_key=mcp_api_key)
            ctx = await self._retrieval.build_context(requirements, document_type, kb_id=mcp_kb_id)
            kb_context = ctx.context_text
            sources = [s.get("title", str(s)) for s in ctx.sources]

        prompt = (
            "Enrich these requirements with standards, regulations, and best practices.\n"
            f"Document type: {document_type}\n"
            f"Requirements: {json.dumps(requirements, ensure_ascii=False)}\n"
            f"Knowledge base context:\n{kb_context}\n\n"
            'Return JSON: {"enriched": {{...all fields...}}, '
            '"standards_applied": [str], "sources": [str]}'
        )
        response = await self._agno.arun(prompt)

        data = extract_json(response.content) or {
            "enriched": requirements,
            "standards_applied": [],
            "sources": [],
        }

        all_sources = list(set(data.get("sources", []) + sources))

        log.info("procurement.enrich.done", sources=len(all_sources))
        return ProcurementResult(
            enriched=data.get("enriched", requirements),
            sources=all_sources,
            standards_applied=data.get("standards_applied", []),
        )
