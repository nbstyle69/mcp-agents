"""Orchestrateur : fait collaborer les agents en pipeline sur un objectif produit."""

from __future__ import annotations

from dataclasses import dataclass, field

from .agent import LogFn
from .agents import build_all_agents
from .config import Settings
from .mcp_client import MCPClientManager, MCPServerConfig

# Ordre de collaboration : la veille alimente le PO, qui alimente la conception, etc.
PIPELINE: list[tuple[str, str]] = [
    (
        "social_researcher",
        "Sonde les réseaux sociaux pour cet objectif et synthétise les insights "
        "essentiels (attentes, tendances, sentiment, concurrents).",
    ),
    (
        "product_owner",
        "À partir des insights de veille, définis la vision, les personas, le MVP et "
        "3 à 6 user stories priorisées avec critères d'acceptation.",
    ),
    (
        "ux_designer",
        "À partir des user stories, propose les parcours utilisateurs clés et des "
        "wireframes décrits textuellement.",
    ),
    (
        "ui_architect",
        "À partir de l'UX, définis l'architecture d'interface et le design system "
        "(composants, tokens, accessibilité).",
    ),
    (
        "fullstack_dev",
        "À partir de tout ce qui précède, propose l'architecture technique, la stack, "
        "le modèle de données et les endpoints principaux.",
    ),
    (
        "qa_tester",
        "À partir de l'ensemble, rédige le plan de test et les critères d'acceptation "
        "vérifiables.",
    ),
]


@dataclass
class StepResult:
    role: str
    agent_name: str
    output: str


@dataclass
class OrchestrationResult:
    objective: str
    steps: list[StepResult] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [f"# Spécification produit générée\n\n**Objectif:** {self.objective}\n"]
        for step in self.steps:
            lines.append(f"\n## {step.agent_name}\n\n{step.output}\n")
        return "\n".join(lines)


def _with_brief(base: str | None, project_brief: str | None) -> str | None:
    """Préfixe un contexte avec le brief projet (connu de tous les agents)."""

    brief = (project_brief or "").strip()
    if not brief:
        return base
    header = f"Contexte du projet (à toujours prendre en compte):\n{brief}"
    return header if not base else f"{header}\n\n{base}"


def default_servers() -> list[MCPServerConfig]:
    """Serveur MCP par défaut : la veille réseaux sociaux (lancé en sous-processus)."""

    return [
        MCPServerConfig(
            name="social",
            command="python",
            args=["-m", "mcp_agents.servers.social_research_server"],
        )
    ]


class Orchestrator:
    def __init__(
        self,
        settings: Settings,
        servers: list[MCPServerConfig] | None = None,
    ):
        self.settings = settings
        self.servers = servers if servers is not None else default_servers()
        self.agents = build_all_agents(settings)

    async def run(
        self,
        objective: str,
        log: LogFn | None = None,
        project_brief: str | None = None,
    ) -> OrchestrationResult:
        result = OrchestrationResult(objective=objective)
        async with MCPClientManager(self.servers) as manager:
            if log:
                log(f"Outils MCP disponibles: {', '.join(manager.tool_names()) or 'aucun'}")
            context = _with_brief(f"Objectif produit: {objective}", project_brief)
            for role, instruction in PIPELINE:
                agent = self.agents[role]
                if log:
                    log(f"\n=== {agent.name} ===")
                output = await agent.run(
                    task=instruction, manager=manager, context=context, log=log
                )
                result.steps.append(
                    StepResult(role=role, agent_name=agent.name, output=output)
                )
                # On enrichit le contexte transmis aux agents suivants.
                context += f"\n\n[{agent.name}]\n{output}"
        return result

    async def run_single(
        self,
        role: str,
        task: str,
        log: LogFn | None = None,
        project_brief: str | None = None,
    ) -> StepResult:
        """Exécute un seul agent (utile pour tester une persona isolément)."""

        if role not in self.agents:
            raise KeyError(f"Rôle inconnu '{role}'. Disponibles: {', '.join(self.agents)}")
        agent = self.agents[role]
        context = _with_brief(None, project_brief)
        async with MCPClientManager(self.servers) as manager:
            output = await agent.run(
                task=task, manager=manager, context=context, log=log
            )
        return StepResult(role=role, agent_name=agent.name, output=output)
