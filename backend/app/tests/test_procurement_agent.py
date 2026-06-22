"""Tests for ProcurementAgent — Task 5 refactor to RetrievalSkill."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.procurement.agent import ProcurementAgent, ProcurementResult
from app.skills.retrieval.retrieval_skill import RetrievedContext

SAMPLE_REQUIREMENTS: dict = {
    "project": {
        "name": "Test Project",
        "organization": "Comune di Roma",
    },
    "security_compliance": {
        "standards": ["ISO 27001"],
    },
}


@pytest.fixture(autouse=True)
def _mock_agno():
    """Patch Agent and get_model_adapter to avoid agno import issues."""

    class _FakeAgent:
        def __init__(self, *args, **kwargs):
            self.arun = AsyncMock(return_value=SimpleNamespace(content="{}"))

    with (
        patch("app.agents.procurement.agent.Agent", _FakeAgent),
        patch(
            "app.agents.procurement.agent.get_model_adapter",
            return_value=None,
        ),
    ):
        yield


# ---------------------------------------------------------------------------
# 1. test_enrich_without_mcp — no mcp_url → no KB context, still produces output
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_enrich_without_mcp() -> None:
    """When mcp_url is None, enrich() skips KB retrieval and still returns a result."""
    agent = ProcurementAgent()

    # Mock the Agno agent to return a valid JSON response
    mock_response = MagicMock()
    mock_response.content = '{"enriched": {"project": {"name": "Test Project"}}, "standards_applied": ["ISO 27001"], "sources": []}'
    agent._agno.arun = AsyncMock(return_value=mock_response)

    result = await agent.enrich(
        requirements=SAMPLE_REQUIREMENTS,
        document_type="capitolato",
        mcp_url=None,
    )

    assert isinstance(result, ProcurementResult)
    assert result.enriched == {"project": {"name": "Test Project"}}
    assert result.standards_applied == ["ISO 27001"]
    assert result.sources == []


# ---------------------------------------------------------------------------
# 2. test_enrich_with_mcp — mcp_url provided → RetrievalSkill.build_context called
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_enrich_with_mcp() -> None:
    """When mcp_url is provided, RetrievalSkill.build_context is called and context injected."""
    agent = ProcurementAgent()

    # Mock RetrievalSkill.build_context
    mock_ctx = RetrievedContext(
        context_text="## Knowledge Base Context\nISO 27001 compliance info.",
        sources=[
            {"title": "ISO Guide", "source": "kb://iso"},
        ],
        query_count=2,
        total_docs=1,
    )

    with patch("app.agents.procurement.agent.RetrievalSkill") as MockSkill:
        mock_skill_instance = MockSkill.return_value
        mock_skill_instance.build_context = AsyncMock(return_value=mock_ctx)

        # Mock the Agno agent
        mock_response = MagicMock()
        mock_response.content = (
            '{"enriched": {"project": {"name": "Test"}}, '
            '"standards_applied": ["ISO 27001"], "sources": ["ISO Guide"]}'
        )
        agent._agno.arun = AsyncMock(return_value=mock_response)

        result = await agent.enrich(
            requirements=SAMPLE_REQUIREMENTS,
            document_type="capitolato",
            mcp_url="http://test:8001/mcp",
            mcp_api_key="sk-test",
            mcp_kb_id="kb-1",
        )

        # Verify RetrievalSkill was constructed with correct args
        MockSkill.assert_called_once_with(
            mcp_url="http://test:8001/mcp",
            mcp_api_key="sk-test",
        )

        # Verify build_context was called with correct args
        mock_skill_instance.build_context.assert_called_once()
        call_args = mock_skill_instance.build_context.call_args
        assert call_args[0][0] == SAMPLE_REQUIREMENTS
        assert call_args[0][1] == "capitolato"
        assert call_args[1].get("kb_id") == "kb-1"

        # Verify result merges sources
        assert isinstance(result, ProcurementResult)
        assert len(result.sources) >= 1


# ---------------------------------------------------------------------------
# 3. test_fetch_kb_context_removed — _fetch_kb_context does not exist
# ---------------------------------------------------------------------------
def test_fetch_kb_context_removed() -> None:
    """The legacy _fetch_kb_context method must not exist on ProcurementAgent."""
    agent = ProcurementAgent()
    assert not hasattr(agent, "_fetch_kb_context"), (
        "_fetch_kb_context should have been removed in favor of RetrievalSkill"
    )


# ---------------------------------------------------------------------------
# 4. test_procurement_result_dataclass — verify dataclass shape
# ---------------------------------------------------------------------------
def test_procurement_result_dataclass() -> None:
    """ProcurementResult has the expected fields."""
    result = ProcurementResult(
        enriched={"key": "val"},
        sources=["src1"],
        standards_applied=["ISO 27001"],
    )
    assert result.enriched == {"key": "val"}
    assert result.sources == ["src1"]
    assert result.standards_applied == ["ISO 27001"]
