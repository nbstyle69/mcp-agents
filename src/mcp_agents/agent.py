"""Agent de base : une persona LLM (Claude) capable d'utiliser les outils MCP."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from anthropic import AsyncAnthropic

from .config import Settings
from .mcp_client import MCPClientManager

# Callback de log optionnel (ex. pour afficher la progression dans la CLI).
LogFn = Callable[[str], None]


@dataclass
class Agent:
    """Un agent = un rôle (persona) + un prompt système + accès aux outils MCP."""

    name: str
    role: str
    system_prompt: str
    settings: Settings
    # Sous-ensemble d'outils autorisés (noms qualifiés). None => tous les outils.
    allowed_tools: list[str] | None = None
    _client: AsyncAnthropic = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = AsyncAnthropic(api_key=self.settings.require_api_key())

    def _filtered_tools(self, manager: MCPClientManager | None) -> list[dict[str, Any]]:
        if manager is None:
            return []
        tools = manager.anthropic_tools()
        if self.allowed_tools is None:
            return tools
        allowed = set(self.allowed_tools)
        return [t for t in tools if t["name"] in allowed]

    async def run(
        self,
        task: str,
        manager: MCPClientManager | None = None,
        context: str | None = None,
        log: LogFn | None = None,
    ) -> str:
        """Exécute une tâche, en bouclant sur les appels d'outils si nécessaire.

        Renvoie la réponse texte finale de l'agent.
        """

        tools = self._filtered_tools(manager)
        user_content = task if not context else f"{context}\n\n---\n\nTâche: {task}"
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]

        for _ in range(self.settings.max_tool_iterations):
            response = await self._client.messages.create(
                model=self.settings.model,
                max_tokens=self.settings.max_tokens,
                system=self.system_prompt,
                messages=messages,
                tools=tools or [],
            )

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                return _join_text(response.content)

            # On rejoue le tour de l'assistant puis on renvoie les résultats d'outils.
            messages.append({"role": "assistant", "content": response.content})
            tool_results: list[dict[str, Any]] = []
            for use in tool_uses:
                if log:
                    log(f"[{self.name}] → outil {use.name}({_short(use.input)})")
                assert manager is not None  # un tool_use implique des outils dispo
                output = await manager.call_tool(use.name, dict(use.input))
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": use.id,
                        "content": output,
                    }
                )
            messages.append({"role": "user", "content": tool_results})

        return (
            "(L'agent a atteint la limite d'itérations d'outils sans réponse finale. "
            "Augmente MCP_AGENTS_MAX_TOOL_ITERATIONS si besoin.)"
        )


def _join_text(content_blocks: list[Any]) -> str:
    parts = [b.text for b in content_blocks if getattr(b, "type", None) == "text"]
    return "\n".join(parts).strip()


def _short(value: Any, limit: int = 80) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"
