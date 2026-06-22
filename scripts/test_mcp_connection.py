"""
Quick MCP connection test — discovers tools, resources, prompts from a live MCP server.

Usage:
    uv run scripts/test_mcp_connection.py
    uv run scripts/test_mcp_connection.py http://192.168.1.162:8000/mcp
"""

import asyncio
import sys
from datetime import timedelta

from fastmcp import Client
from fastmcp.client.transports.http import StreamableHttpTransport
from fastmcp.client.transports.sse import SSETransport


async def main(url: str) -> None:
    print(f"\n🔌 Connecting to MCP server: {url}\n")

    # Pick transport based on URL
    api_key = "YDmq1awGDoNY2hj"
    headers = {"X-API-Key": api_key}

    if url.rstrip("/").endswith("/sse"):
        transport = SSETransport(url, headers=headers)
        print("  Transport: SSE")
    else:
        transport = StreamableHttpTransport(url, headers=headers)
        print("  Transport: StreamableHTTP")

    client = Client(
        transport,
        timeout=timedelta(seconds=120),
        init_timeout=timedelta(seconds=30),
        auto_initialize=True,
    )

    try:
        async with client:
            print("✅ Connected!\n")

            # ── Tools ─────────────────────────────────────────────────────
            tools = await client.list_tools()
            print(f"📦 Tools ({len(tools)}):")
            for t in tools:
                desc = (t.description or "")[:80]
                print(f"  • {t.name} — {desc}")
                if t.inputSchema and t.inputSchema.get("properties"):
                    params = ", ".join(t.inputSchema["properties"].keys())
                    print(f"    params: ({params})")
            print()

            # ── Resources ─────────────────────────────────────────────────
            try:
                resources = await client.list_resources()
                print(f"📂 Resources ({len(resources)}):")
                for r in resources:
                    print(f"  • {r.uri} — {(r.description or '')[:60]}")
            except Exception as e:
                print(f"📂 Resources: not available ({e})")
            print()

            # ── Prompts ───────────────────────────────────────────────────
            try:
                prompts = await client.list_prompts()
                print(f"💬 Prompts ({len(prompts)}):")
                for p in prompts:
                    print(f"  • {p.name} — {(p.description or '')[:60]}")
            except Exception as e:
                print(f"💬 Prompts: not available ({e})")
            print()

            # ── Try calling the first tool (if any) ───────────────────────
            if tools:
                # Test: list knowledge bases
                print("🧪 Test: nanorag_list_kbs")
                try:
                    result = await client.call_tool("nanorag_list_kbs", {})
                    for item in (result.content or [])[:1]:
                        text = getattr(item, "text", str(item))
                        print(f"  → {text[:1000]}")
                except Exception as e:
                    print(f"  ❌ {e}")
                print()

                # Test: health check
                print("🧪 Test: nanorag_health")
                try:
                    result = await client.call_tool("nanorag_health", {})
                    for item in (result.content or [])[:1]:
                        text = getattr(item, "text", str(item))
                        print(f"  → {text[:500]}")
                except Exception as e:
                    print(f"  ❌ {e}")
                print()

                # Test: list documents in arch-new KB
                print("🧪 Test: nanorag_list_documents (kb_id=arch-new)")
                try:
                    result = await client.call_tool(
                        "nanorag_list_documents", {"kb_id": "arch-new"}
                    )
                    for item in (result.content or [])[:1]:
                        text = getattr(item, "text", str(item))
                        print(f"  → {text[:1500]}")
                except Exception as e:
                    print(f"  ❌ {e}")
                print()

                # Test: chat with a question
                print("🧪 Test: nanorag_chat")
                try:
                    result = await client.call_tool(
                        "nanorag_chat",
                        {
                            "kb_id": "arch-new",
                            "message": "Quali sono i principali componenti architetturali?",
                            "top_k": 3,
                        },
                    )
                    for item in (result.content or [])[:1]:
                        text = getattr(item, "text", str(item))
                        # Show full result to understand response format
                        print(f"  → {text[:3000]}")
                except Exception as e:
                    print(f"  ❌ {e}")
                print()

                # Test: get graph
                print("🧪 Test: nanorag_get_graph (kb_id=arch-new, limit=5)")
                try:
                    result = await client.call_tool(
                        "nanorag_get_graph",
                        {
                            "kb_id": "arch-new",
                            "limit": 5,
                        },
                    )
                    for item in (result.content or [])[:1]:
                        text = getattr(item, "text", str(item))
                        print(f"  → {text[:1500]}")
                except Exception as e:
                    print(f"  ❌ {e}")

    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}: {e}")
        print("\nTroubleshooting:")
        print(f"  1. Is the server running? curl {url}")
        print("  2. Check firewall / network")
        print("  3. Try /sse endpoint if StreamableHTTP fails")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.1.162:8000/mcp"
    asyncio.run(main(url))
