"""
End-to-end test: MCPClient + RetrievalSkill against live NanoRAG MCP.

Usage:
    uv run scripts/test_nanorag_e2e.py
"""

import asyncio

from app.mcp.client.adapters.nanorag import NanoRAGAdapter
from app.skills.retrieval.retrieval_skill import RetrievalSkill

NANORAG_URL = "http://192.168.1.162:8000/mcp"
NANORAG_KEY = "YDmq1awGDoNY2hj"
KB_ID = "arch-new"


async def test_mcp_client() -> None:
    """Test MCPClient directly."""
    print("=" * 60)
    print("1. MCPClient — direct test")
    print("=" * 60)

    client = NanoRAGAdapter(url=NANORAG_URL, api_key=NANORAG_KEY)
    try:
        await client.connect()
        print("✅ Connected\n")

        # List tools
        tools = await client.list_tools()
        print(f"📦 Tools: {len(tools)}")
        for t in tools:
            print(f"  • {t['name']}")
        print()

        # search_documents (should find nanorag_chat)
        print("🔍 search_documents('architettura componenti')")
        docs = await client.search_documents(
            "architettura componenti", limit=3, kb_id=KB_ID
        )
        print(f"  Found {len(docs)} docs:")
        for d in docs[:3]:
            src = d.get("source", "?")
            score = d.get("relevance_score", 0)
            text = (d.get("text") or d.get("excerpt") or "")[:100]
            print(f"  • [{score:.2f}] {src}")
            if text:
                print(f"    {text}...")
        print()

    finally:
        await client.disconnect()


async def test_retrieval_skill() -> None:
    """Test RetrievalSkill with NanoRAG."""
    print("=" * 60)
    print("2. RetrievalSkill — build_context test")
    print("=" * 60)

    skill = RetrievalSkill(mcp_url=NANORAG_URL, mcp_api_key=NANORAG_KEY)

    requirements = {
        "project": {
            "name": "Migrazione Architettura Applicativa",
            "organization": "Consorzio Operativo Gruppo MPS",
        },
        "security_compliance": {
            "standards": ["ISO 27001"],
            "data_classification": "confidential",
        },
        "integrations": [
            {"system": "GGS"},
        ],
    }

    print("📋 Building context from requirements...")
    ctx = await skill.build_context(
        requirements=requirements,
        document_type="capitolato",
        max_docs=5,
        kb_id=KB_ID,
    )

    print(f"  Queries executed: {ctx.query_count}")
    print(f"  Total docs found: {ctx.total_docs}")
    print(f"  Selected docs: {len(ctx.sources)}")
    print(f"  Context length: {len(ctx.context_text)} chars")
    print()

    if ctx.context_text:
        print("📄 Context preview (first 1000 chars):")
        print("-" * 40)
        print(ctx.context_text[:1000])
        print("-" * 40)
    else:
        print("⚠️  Empty context — check logs for errors")
    print()


async def main() -> None:
    print("\n🧪 NanoRAG MCP End-to-End Test\n")
    await test_mcp_client()
    await test_retrieval_skill()
    print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
