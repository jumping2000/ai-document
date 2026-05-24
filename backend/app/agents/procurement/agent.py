"""
Procurement Agent — enriches requirements via MCP/RAG knowledge base.
Input  : requirements dict, document_type
Output : ProcurementResult(enriched, sources)
"""
import structlog
from dataclasses import dataclass
from typing import Any

from agno.agent import Agent
from app.core.llm import get_model_adapter

from app.core.config import settings
from app.mcp.client.mcp_client import MCPClient

log = structlog.get_logger(__name__)


@dataclass
class ProcurementResult:
    enriched: dict[str, Any]
    sources: list[str]
    standards_applied: list[str]


class ProcurementAgent:
    def __init__(self) -> None:
        self._mcp = MCPClient()
        self._agno = Agent(
            name="procurement_specialist",
            role="IT Procurement Specialist",
            description="Enrich requirements with standards, regulations, and best practices",
            instructions=[
                "Apply ISO 27001, ISO 9001, and GDPR where relevant.",
                "Add SLA templates from the knowledge base.",
                "Include security requirements from OWASP and CIS benchmarks.",
                "Reference Italian public procurement code (D.Lgs. 36/2023) for capitolati.",
                "Return enriched requirements as structured JSON.",
            ],
            model=get_model_adapter(),
            markdown=False,
        )

    async def enrich(
        self,
        requirements: dict[str, Any],
        document_type: str,
    ) -> ProcurementResult:
        log.info("procurement.enrich.start", doc_type=document_type)

        # Query MCP for relevant standards and templates
        kb_context = await self._fetch_kb_context(requirements, document_type)

        prompt = (
            f"Enrich these requirements with standards, regulations, and best practices.\n"
            f"Document type: {document_type}\n"
            f"Requirements: {requirements}\n"
            f"Knowledge base context:\n{kb_context}\n\n"
            "Return a JSON object: {\"enriched\": {{...all fields...}}, "
            "\"standards_applied\": [str], \"sources\": [str]}"
        )
        response = await self._agno.arun(prompt)

        import json, re
        match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            data = {"enriched": requirements, "standards_applied": [], "sources": []}

        log.info("procurement.enrich.done", sources=len(data.get("sources", [])))
        return ProcurementResult(
            enriched=data.get("enriched", requirements),
            sources=data.get("sources", []),
            standards_applied=data.get("standards_applied", []),
        )

    async def _fetch_kb_context(self, requirements: dict, document_type: str) -> str:
        try:
            results = await self._mcp.search_documents(
                query=f"{document_type} {requirements.get('project_scope', '')}",
                limit=5,
            )
            return "\n".join(r.get("content", "") for r in results)
        except Exception as exc:
            log.warning("procurement.mcp.unavailable", error=str(exc))
            return "MCP knowledge base unavailable — using base standards only."
