"""
Procurement Agent — enriches requirements via MCP/RAG knowledge base.
Input  : requirements dict, document_type, optional mcp_connection_id
Output : ProcurementResult(enriched, sources)
"""
import structlog
from dataclasses import dataclass
from typing import Any

from agno.agent import Agent
from app.core.llm import get_model_adapter
from app.mcp.client.mcp_client import MCPClient, MCPError

log = structlog.get_logger(__name__)


@dataclass
class ProcurementResult:
    enriched: dict[str, Any]
    sources: list[str]
    standards_applied: list[str]


class ProcurementAgent:
    def __init__(self) -> None:
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
            mcp_tools: Optional pre-discovered tools list
        """
        log.info("procurement.enrich.start", doc_type=document_type, has_mcp=bool(mcp_url))

        # Fetch context from MCP if available
        kb_context = ""
        sources = []

        if mcp_url:
            kb_context, sources = await self._fetch_kb_context(
                requirements, document_type, mcp_url, mcp_api_key, mcp_tools, mcp_kb_id
            )

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

        # Merge MCP sources with LLM sources
        all_sources = list(set(data.get("sources", []) + sources))

        log.info("procurement.enrich.done", sources=len(all_sources))
        return ProcurementResult(
            enriched=data.get("enriched", requirements),
            sources=all_sources,
            standards_applied=data.get("standards_applied", []),
        )

    async def _fetch_kb_context(
        self,
        requirements: dict,
        document_type: str,
        mcp_url: str,
        mcp_api_key: str | None,
        mcp_tools: list[dict[str, Any]] | None = None,
        mcp_kb_id: str | None = None,
    ) -> tuple[str, list[str]]:
        """
        Fetch knowledge base context using generic MCP tools.

        Discovers available tools and uses the most appropriate one
        for searching/retrieving context.
        """
        client = MCPClient(url=mcp_url, api_key=mcp_api_key)
        sources = []

        try:
            await client.connect()

            # Use pre-discovered tools or discover now
            if not mcp_tools:
                mcp_tools = await client.list_tools()

            tool_names = [t["name"] for t in mcp_tools]

            # Discover available knowledge bases
            available_kb = mcp_kb_id  # Use provided KB ID first
            if not available_kb:
                list_kb_tool = next((t for t in tool_names if "list_kbs" in t.lower() or "list_kb" in t.lower()), None)
                if list_kb_tool:
                    try:
                        kb_result = await client.call_tool(list_kb_tool, {})
                        if isinstance(kb_result, list) and len(kb_result) > 0:
                            available_kb = kb_result[0].get("id", kb_result[0].get("name", "default"))
                            log.info("procurement.mcp.kb_found", kb_id=available_kb)
                    except Exception as exc:
                        log.warning("procurement.mcp.list_kbs_failed", error=str(exc))

            # Try common search/chat patterns
            search_tool = None
            search_args = {}

            # Look for search-like tools
            for pattern in ["search", "chat", "ask", "query", "retrieve"]:
                matches = [t for t in tool_names if pattern in t.lower()]
                if matches:
                    search_tool = matches[0]
                    break

            # If no search tool, try first available tool that accepts text input
            if not search_tool and tool_names:
                search_tool = tool_names[0]

            if search_tool:
                # Build generic arguments
                query = f"{document_type} {requirements.get('project_scope', '')}"

                # Try to match tool schema
                tool_def = next((t for t in mcp_tools if t["name"] == search_tool), None)
                if tool_def and tool_def.get("input_schema"):
                    schema = tool_def["input_schema"]
                    props = schema.get("properties", {})

                    # Map common parameter names
                    for param_name in props:
                        lower = param_name.lower()
                        if lower in ("query", "message", "text", "question", "search"):
                            search_args[param_name] = query
                        elif lower in ("kb_id", "knowledge_base", "database"):
                            search_args[param_name] = available_kb or "default"
                        elif lower in ("limit", "top_k", "max_results"):
                            search_args[param_name] = 5

                # If we couldn't map params, try common patterns
                if not search_args:
                    search_args = {"query": query, "limit": 5}

                result = await client.call_tool(search_tool, search_args)

                # Extract text content from result
                if isinstance(result, dict):
                    # Try to extract sources/answer
                    if "answer" in result:
                        context = result["answer"]
                        for src in result.get("sources", []):
                            if isinstance(src, dict):
                                sources.append(src.get("title", src.get("source", str(src))))
                            else:
                                sources.append(str(src))
                        return context, sources
                    elif "content" in result:
                        return str(result["content"]), sources
                    elif "text" in result:
                        return str(result["text"]), sources

                return str(result)[:2000], sources

            return "No search tools available on MCP server.", sources

        except MCPError as exc:
            log.warning("procurement.mcp.error", error=str(exc))
            return f"MCP error: {exc}", sources
        except Exception as exc:
            log.warning("procurement.mcp.unavailable", error=str(exc))
            return "MCP knowledge base unavailable — using base standards only.", sources
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
