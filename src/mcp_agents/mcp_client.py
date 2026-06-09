"""Gestion des connexions aux serveurs MCP et exposition de leurs outils à Claude.

Un `MCPClientManager` ouvre une ou plusieurs sessions MCP (via stdio), agrège les
outils exposés par ces serveurs, les traduit au format d'outils Anthropic, et permet
de les appeler par leur nom qualifié `serveur__outil`.
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Séparateur entre le nom du serveur et le nom de l'outil dans un nom qualifié.
SEP = "__"


@dataclass(frozen=True)
class MCPServerConfig:
    """Comment lancer un serveur MCP en sous-processus (transport stdio)."""

    name: str
    command: str
    args: list[str]
    env: dict[str, str] | None = None


@dataclass
class _RegisteredTool:
    server: str
    tool_name: str
    description: str
    input_schema: dict[str, Any]
    session: ClientSession


def _content_to_text(content_blocks: list[Any]) -> str:
    """Aplati les blocs de contenu renvoyés par un outil MCP en texte simple."""

    parts: list[str] = []
    for block in content_blocks:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
            continue
        data = getattr(block, "data", None)
        if data is not None:
            mime = getattr(block, "mimeType", "données")
            parts.append(f"[contenu binaire: {mime}]")
            continue
        parts.append(str(block))
    return "\n".join(parts).strip()


class MCPClientManager:
    """Gère plusieurs sessions MCP et agrège leurs outils.

    À utiliser comme context manager asynchrone :

        async with MCPClientManager(configs) as manager:
            tools = manager.anthropic_tools()
            result = await manager.call_tool("social__search_mentions", {...})
    """

    def __init__(self, servers: list[MCPServerConfig]):
        self._servers = servers
        self._stack = AsyncExitStack()
        self._tools: dict[str, _RegisteredTool] = {}

    async def __aenter__(self) -> "MCPClientManager":
        await self._stack.__aenter__()
        for server in self._servers:
            await self._connect(server)
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._stack.aclose()

    async def _connect(self, server: MCPServerConfig) -> None:
        params = StdioServerParameters(
            command=server.command, args=server.args, env=server.env
        )
        read, write = await self._stack.enter_async_context(stdio_client(params))
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        listed = await session.list_tools()
        for tool in listed.tools:
            qualified = f"{server.name}{SEP}{tool.name}"
            self._tools[qualified] = _RegisteredTool(
                server=server.name,
                tool_name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema or {"type": "object", "properties": {}},
                session=session,
            )

    def anthropic_tools(self) -> list[dict[str, Any]]:
        """Renvoie la liste des outils au format attendu par l'API Anthropic."""

        return [
            {
                "name": qualified,
                "description": reg.description,
                "input_schema": reg.input_schema,
            }
            for qualified, reg in self._tools.items()
        ]

    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    async def call_tool(self, qualified_name: str, arguments: dict[str, Any]) -> str:
        reg = self._tools.get(qualified_name)
        if reg is None:
            return f"Erreur: outil inconnu '{qualified_name}'."
        try:
            result = await reg.session.call_tool(reg.tool_name, arguments=arguments)
        except Exception as exc:  # noqa: BLE001 - on remonte l'erreur au LLM proprement
            return f"Erreur lors de l'appel de '{qualified_name}': {exc}"
        text = _content_to_text(list(result.content))
        if getattr(result, "isError", False):
            return f"L'outil a renvoyé une erreur: {text}"
        return text or "(aucune sortie)"
