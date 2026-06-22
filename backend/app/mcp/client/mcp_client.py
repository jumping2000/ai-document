"""
Generic MCP Client — works with ANY MCP server.

Implements the MCP protocol (tools, resources, prompts) without
server-specific knowledge. The client discovers capabilities
dynamically via the protocol itself.
"""

from __future__ import annotations

import time
from typing import Any
from datetime import timedelta

import structlog
from fastmcp import Client
from fastmcp.client.transports.sse import SSETransport
from fastmcp.client.transports.http import StreamableHttpTransport

from app.core.config import settings

log = structlog.get_logger(__name__)


class MCPError(Exception):
    """Raised when the MCP server returns an error or is unreachable."""


class MCPClient:
    """
    Generic FastMCP client that works with ANY MCP server.

    Discovers server capabilities (tools, resources, prompts) via
    the MCP protocol itself — no hardcoded tool names.

    Caching: results cached in-process for 15 minutes.
    """

    def __init__(self, url: str | None = None, api_key: str | None = None) -> None:
        self._url = (url or settings.mcp_server_url).rstrip("/")
        self._api_key = api_key or settings.mcp_api_key
        self._client: Client | None = None
        self._connected = False
        self._exit_stack = None

        # In-process TTL cache
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 900  # 15 minutes

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Open transport to MCP server (idempotent)."""
        if self._connected:
            return

        headers = {}
        if self._api_key:
            headers["X-API-Key"] = self._api_key

        # Create transport with headers
        if self._url.endswith("/sse"):
            transport = SSETransport(self._url, headers=headers if headers else None)
        else:
            transport = StreamableHttpTransport(self._url, headers=headers if headers else None)

        # Create client with longer timeout
        self._client = Client(
            transport,
            timeout=timedelta(seconds=60),
            init_timeout=timedelta(seconds=30),
            auto_initialize=True,
        )
        # Use the async context manager properly
        self._exit_stack = await self._client.__aenter__()
        self._connected = True
        log.info("mcp_connected", url=self._url)

    async def disconnect(self) -> None:
        """Close transport (idempotent)."""
        if not self._connected or self._client is None:
            return
        try:
            await self._client.__aexit__(None, None, None)
        except Exception:
            pass
        self._connected = False
        self._client = None
        self._exit_stack = None
        log.info("mcp_disconnected")

    async def _ensure_connected(self) -> Client:
        if not self._connected or self._client is None:
            await self.connect()
        assert self._client is not None
        return self._client

    # ── Tools ─────────────────────────────────────────────────────────────

    async def list_tools(self) -> list[dict[str, Any]]:
        """
        List all tools available on the MCP server.

        Returns:
            List of tool dicts with: name, description, inputSchema
        """
        client = await self._ensure_connected()
        result = await client.list_tools()

        tools = []
        for tool in result:
            tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
            })

        log.info("mcp_list_tools", count=len(tools))
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """
        Call any tool by name with arguments.

        Args:
            name: Tool name (discovered via list_tools)
            arguments: Tool arguments dict

        Returns:
            Tool result (parsed from response)
        """
        cache_key = f"tool:{name}:{hash(frozenset(arguments.items()))}"
        if cached := self._get_cache(cache_key):
            log.debug("mcp_cache_hit", tool=name)
            return cached

        client = await self._ensure_connected()
        start = time.monotonic()

        try:
            result = await client.call_tool(name, arguments)
        except Exception as exc:
            log.error("mcp_call_failed", tool=name, error=str(exc))
            raise MCPError(f"Tool '{name}' failed: {exc}") from exc

        duration_ms = int((time.monotonic() - start) * 1000)
        log.info("mcp_call_ok", tool=name, duration_ms=duration_ms)

        data = self._extract_result(result)
        self._set_cache(cache_key, data)
        return data

    # ── Resources ─────────────────────────────────────────────────────────

    async def list_resources(self) -> list[dict[str, Any]]:
        """
        List all resources available on the MCP server.

        Returns:
            List of resource dicts with: uri, name, description, mimeType
        """
        client = await self._ensure_connected()
        result = await client.list_resources()

        resources = []
        for resource in result:
            resources.append({
                "uri": str(resource.uri),
                "name": resource.name or "",
                "description": resource.description or "",
                "mime_type": resource.mimeType or "",
            })

        log.info("mcp_list_resources", count=len(resources))
        return resources

    async def read_resource(self, uri: str) -> Any:
        """
        Read a resource by URI.

        Args:
            uri: Resource URI (discovered via list_resources)

        Returns:
            Resource content
        """
        cache_key = f"resource:{uri}"
        if cached := self._get_cache(cache_key):
            log.debug("mcp_cache_hit", resource=uri)
            return cached

        client = await self._ensure_connected()
        start = time.monotonic()

        try:
            result = await client.read_resource(uri)
        except Exception as exc:
            log.error("mcp_read_failed", resource=uri, error=str(exc))
            raise MCPError(f"Resource '{uri}' failed: {exc}") from exc

        duration_ms = int((time.monotonic() - start) * 1000)
        log.info("mcp_read_ok", resource=uri, duration_ms=duration_ms)

        data = self._extract_resource_result(result)
        self._set_cache(cache_key, data)
        return data

    # ── Prompts ───────────────────────────────────────────────────────────

    async def list_prompts(self) -> list[dict[str, Any]]:
        """
        List all prompts available on the MCP server.

        Returns:
            List of prompt dicts with: name, description, arguments
        """
        client = await self._ensure_connected()
        result = await client.list_prompts()

        prompts = []
        for prompt in result:
            args = []
            if hasattr(prompt, "arguments") and prompt.arguments:
                for arg in prompt.arguments:
                    args.append({
                        "name": arg.name,
                        "description": arg.description or "",
                        "required": getattr(arg, "required", False),
                    })

            prompts.append({
                "name": prompt.name,
                "description": prompt.description or "",
                "arguments": args,
            })

        log.info("mcp_list_prompts", count=len(prompts))
        return prompts

    async def get_prompt(self, name: str, arguments: dict[str, str] | None = None) -> Any:
        """
        Get a prompt by name with arguments.

        Args:
            name: Prompt name (discovered via list_prompts)
            arguments: Prompt arguments dict

        Returns:
            Prompt result (messages list)
        """
        client = await self._ensure_connected()
        start = time.monotonic()

        try:
            result = await client.get_prompt(name, arguments or {})
        except Exception as exc:
            log.error("mcp_prompt_failed", prompt=name, error=str(exc))
            raise MCPError(f"Prompt '{name}' failed: {exc}") from exc

        duration_ms = int((time.monotonic() - start) * 1000)
        log.info("mcp_prompt_ok", prompt=name, duration_ms=duration_ms)

        return self._extract_prompt_result(result)

    # ── Discovery ─────────────────────────────────────────────────────────

    async def discover_all(self) -> dict[str, Any]:
        """
        Discover all server capabilities.

        Returns:
            dict with tools, resources, and prompts lists
        """
        tools = await self.list_tools()
        resources = await self.list_resources()
        prompts = await self.list_prompts()

        return {
            "tools": tools,
            "resources": resources,
            "prompts": prompts,
            "summary": {
                "tools_count": len(tools),
                "resources_count": len(resources),
                "prompts_count": len(prompts),
            },
        }

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _extract_result(result: Any) -> Any:
        """Extract content from a CallToolResult.
        
        Handles multiple content blocks by collecting all parsed items.
        If there's only one item, returns it directly.
        If there are multiple items, returns a list.
        """
        if hasattr(result, "content"):
            items = []
            for block in result.content:
                if hasattr(block, "text"):
                    import json
                    text = block.text
                    try:
                        parsed = json.loads(text)
                        items.append(parsed)
                    except (json.JSONDecodeError, TypeError):
                        items.append(text)
            
            if len(items) == 0:
                return None
            elif len(items) == 1:
                return items[0]
            else:
                return items
        
        if isinstance(result, dict):
            return result
        return result

    @staticmethod
    def _extract_resource_result(result: Any) -> Any:
        """Extract content from a ReadResourceResult."""
        if hasattr(result, "contents"):
            for content in result.contents:
                if hasattr(content, "text"):
                    import json

                    try:
                        return json.loads(content.text)
                    except (json.JSONDecodeError, TypeError):
                        return content.text
                elif hasattr(content, "blob"):
                    return content.blob
        return result

    @staticmethod
    def _extract_prompt_result(result: Any) -> Any:
        """Extract content from a GetPromptResult."""
        if hasattr(result, "messages"):
            messages = []
            for msg in result.messages:
                content = ""
                if hasattr(msg, "content"):
                    if hasattr(msg.content, "text"):
                        content = msg.content.text
                    else:
                        content = str(msg.content)
                messages.append({
                    "role": getattr(msg, "role", "unknown"),
                    "content": content,
                })
            return {"messages": messages}
        return result

    def _get_cache(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry and (time.monotonic() - entry[1]) < self._cache_ttl:
            return entry[0]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = (value, time.monotonic())
