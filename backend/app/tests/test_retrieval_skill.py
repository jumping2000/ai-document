"""Tests for RetrievalSkill."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.mcp.client.adapters.nanorag import NanoRAGAdapter
from app.mcp.client.mcp_client import MCPError
from app.skills.retrieval.retrieval_skill import RetrievalSkill, RetrievedContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_mcp_client() -> NanoRAGAdapter:
    """Return a NanoRAGAdapter with mocked internals (skip real connect)."""
    c = NanoRAGAdapter.__new__(NanoRAGAdapter)
    c._connected = True
    c._client = AsyncMock()
    c._exit_stack = None
    c._cache = {}
    c._cache_ttl = 900
    return c


SAMPLE_REQUIREMENTS: dict = {
    "project": {
        "title": "Sistema ERP Cloud",
        "name": "Test Project",
        "organization": "Comune di Roma - Pubblica Amministrazione",
    },
    "scope": {
        "objectives": ["Digitalizzare i processi"],
    },
    "security_compliance": {
        "standards": ["ISO 27001", "GDPR"],
        "data_classification": "riservato",
    },
    "functional_requirements": [
        {"id": "FR-001", "title": "Login SSO"},
        {"id": "FR-002", "title": "Dashboard"},
    ],
    "technical_requirements": [
        {"id": "TR-001", "category": "Hosting", "description": "Cloud SaaS"},
    ],
    "integrations": [
        {"system": "SAP ERP"},
        {"system": "PagoPA"},
    ],
    "sla": {"K1": "99%", "K2": "1%", "K3": "0"},
}


# ---------------------------------------------------------------------------
# 1. Default constructor — no crash
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retrieval_skill_default_client() -> None:
    """No args → MCPClient created with defaults (verify no crash)."""
    skill = RetrievalSkill()
    assert isinstance(skill._mcp, NanoRAGAdapter)


# ---------------------------------------------------------------------------
# 2. Custom url / api_key injected into MCPClient
# ---------------------------------------------------------------------------
def test_retrieval_skill_custom_url() -> None:
    """mcp_url and mcp_api_key are forwarded to MCPClient constructor."""
    with patch("app.skills.retrieval.retrieval_skill.NanoRAGAdapter") as MockClient:
        skill = RetrievalSkill(
            mcp_url="http://custom:8001/mcp",
            mcp_api_key="sk-test",
        )
        MockClient.assert_called_once_with(
            url="http://custom:8001/mcp",
            api_key="sk-test",
        )


# ---------------------------------------------------------------------------
# 3. _build_queries loads from template.yaml and resolves placeholders
# ---------------------------------------------------------------------------
def test_build_queries_resolves_placeholders() -> None:
    """_build_queries loads retrieval_queries from template.yaml and resolves placeholders."""
    skill = RetrievalSkill()
    queries = skill._build_queries(SAMPLE_REQUIREMENTS, "capitolato")

    # Should have queries (loaded from template.yaml)
    assert len(queries) > 0

    # Placeholders should be resolved — no {xxx} patterns remaining
    for q in queries:
        assert "{" not in q, f"Unresolved placeholder in query: {q}"

    # Project title should appear in resolved queries
    assert any("Sistema ERP Cloud" in q for q in queries)

    # Technical requirements should appear
    assert any("Cloud SaaS" in q or "Hosting" in q for q in queries)

    # Integrations should appear (first element resolved)
    assert any("SAP ERP" in q for q in queries)


def test_build_queries_skips_empty_placeholders() -> None:
    """Queries with unresolvable placeholders are skipped."""
    skill = RetrievalSkill()
    # Minimal requirements — missing many fields
    minimal = {"project": {"title": "Test"}}
    queries = skill._build_queries(minimal, "capitolato")
    # All returned queries should have resolved placeholders
    for q in queries:
        assert "{" not in q, f"Unresolved placeholder in query: {q}"


def test_build_queries_empty_template_returns_empty() -> None:
    """If template has no retrieval_queries, returns empty list."""
    skill = RetrievalSkill()
    with patch("app.skills.retrieval.retrieval_skill.load_template_config", return_value={}):
        queries = skill._build_queries(SAMPLE_REQUIREMENTS, "capitolato")
    assert queries == []


# ---------------------------------------------------------------------------
# 4. MCP failure → empty context, no crash
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_build_context_handles_mcp_failure() -> None:
    """When MCP is unavailable, build_context returns empty RetrievedContext."""
    skill = RetrievalSkill()
    skill._mcp = AsyncMock()
    skill._mcp.search_documents = AsyncMock(side_effect=MCPError("connection refused"))

    result = await skill.build_context(SAMPLE_REQUIREMENTS, "capitolato")

    assert isinstance(result, RetrievedContext)
    assert result.context_text == ""
    assert result.total_docs == 0
    assert result.query_count > 0  # queries were built


# ---------------------------------------------------------------------------
# 5. _format_context with empty docs → ""
# ---------------------------------------------------------------------------
def test_format_context_empty() -> None:
    """No docs → empty string."""
    skill = RetrievalSkill()
    assert skill._format_context([]) == ""


# ---------------------------------------------------------------------------
# 6. _format_context with multiple docs → markdown
# ---------------------------------------------------------------------------
def test_format_context_multiple_docs() -> None:
    """3 docs → formatted markdown with titles, sources, scores."""
    docs = [
        {
            "title": "ISO Compliance Guide",
            "source": "kb://iso-guide",
            "relevance_score": 0.95,
            "excerpt": "This guide covers ISO 27001 requirements.",
        },
        {
            "title": "GDPR Data Protection",
            "source": "kb://gdpr-doc",
            "relevance_score": 0.88,
            "excerpt": "GDPR overview for Italian public sector.",
        },
        {
            "title": "Cloud SLA Template",
            "source": "kb://cloud-sla",
            "relevance_score": 0.72,
            "excerpt": "Standard SLA benchmarks for enterprise IT.",
        },
    ]

    skill = RetrievalSkill()
    result = skill._format_context(docs)

    assert "## Knowledge Base Context" in result
    assert "ISO Compliance Guide" in result
    assert "GDPR Data Protection" in result
    assert "Cloud SLA Template" in result
    assert "kb://iso-guide" in result
    assert "0.95" in result
    assert "This guide covers ISO 27001" in result
