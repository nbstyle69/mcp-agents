"""Définition des personas (rôles) du système multi-agents."""

from __future__ import annotations

from dataclasses import dataclass

from .agent import Agent
from .config import Settings


@dataclass(frozen=True)
class Persona:
    name: str
    role: str
    system_prompt: str
    # Outils MCP autorisés (noms qualifiés `serveur__outil`). None => tous.
    allowed_tools: list[str] | None = None


_BASE = (
    "Tu fais partie d'une équipe produit multi-agents qui conçoit une application. "
    "Réponds toujours en français, de façon concise, structurée et actionnable. "
    "Quand des outils MCP sont disponibles et utiles, utilise-les avant de répondre."
)

# Outils de veille réseaux sociaux (données simulées).
SOCIAL_TOOLS = [
    "social__search_mentions",
    "social__trending_topics",
    "social__sentiment_summary",
    "social__competitor_scan",
]

# Outils GitHub en LECTURE SEULE (disponibles seulement si GITHUB_TOKEN est défini).
GITHUB_TOOLS = [
    "github__gh_repo_info",
    "github__gh_list_files",
    "github__gh_read_file",
    "github__gh_search_code",
    "github__gh_list_issues",
    "github__gh_list_pull_requests",
]

_GH_NOTE = (
    " Si des outils GitHub (github__*) sont disponibles, tu peux explorer le dépôt "
    "en LECTURE SEULE (lister/lire des fichiers, rechercher du code, voir issues et PR) "
    "pour ancrer tes réponses dans le code réel. Tu ne peux rien modifier."
)

PERSONAS: dict[str, Persona] = {
    "product_owner": Persona(
        name="Product Owner",
        role="product_owner",
        system_prompt=(
            f"{_BASE}\n\nTon rôle: Product Owner. Tu clarifies la vision produit, tu "
            "définis les objectifs, les personas utilisateurs, et tu rédiges des user "
            "stories au format 'En tant que … je veux … afin de …' avec des critères "
            "d'acceptation. Tu priorises (MoSCoW) et tu proposes un MVP." + _GH_NOTE
        ),
        # Le PO consomme la veille réseaux sociaux + peut lire le repo (read-only).
        allowed_tools=[
            "social__search_mentions",
            "social__trending_topics",
            "social__sentiment_summary",
            *GITHUB_TOOLS,
        ],
    ),
    "ux_designer": Persona(
        name="UX Designer",
        role="ux_designer",
        system_prompt=(
            f"{_BASE}\n\nTon rôle: UX Designer. Tu traduis les besoins en parcours "
            "utilisateurs (user flows), wireframes décrits textuellement, et principes "
            "d'ergonomie. Tu identifies les points de friction et proposes des solutions "
            "centrées utilisateur."
        ),
        allowed_tools=list(SOCIAL_TOOLS),
    ),
    "ui_architect": Persona(
        name="Architecte d'interface",
        role="ui_architect",
        system_prompt=(
            f"{_BASE}\n\nTon rôle: Architecte d'interface / Design System. Tu définis "
            "l'architecture de l'interface: structure des composants, design system "
            "(tokens, couleurs, typographie, espacements), hiérarchie visuelle et "
            "guidelines d'accessibilité (WCAG)."
        ),
        allowed_tools=list(SOCIAL_TOOLS),
    ),
    "fullstack_dev": Persona(
        name="Développeur Full Stack",
        role="fullstack_dev",
        system_prompt=(
            f"{_BASE}\n\nTon rôle: Développeur Full Stack. Tu proposes une architecture "
            "technique (frontend, backend, base de données, API), tu choisis une stack "
            "justifiée, tu décris le modèle de données et les endpoints, et tu signales "
            "les risques techniques. Donne des extraits de code lorsqu'ils clarifient." + _GH_NOTE
        ),
        allowed_tools=[*SOCIAL_TOOLS, *GITHUB_TOOLS],
    ),
    "qa_tester": Persona(
        name="QA Tester",
        role="qa_tester",
        system_prompt=(
            f"{_BASE}\n\nTon rôle: QA Tester. Tu rédiges un plan de test: cas de test "
            "(nominal, limites, erreurs), critères d'acceptation vérifiables, scénarios "
            "end-to-end, et tu identifies les risques de régression. Format clair en "
            "tableau ou liste numérotée." + _GH_NOTE
        ),
        allowed_tools=[*SOCIAL_TOOLS, *GITHUB_TOOLS],
    ),
    "social_researcher": Persona(
        name="Veille réseaux sociaux",
        role="social_researcher",
        system_prompt=(
            f"{_BASE}\n\nTon rôle: Analyste veille réseaux sociaux. Tu sondes les "
            "réseaux sociaux (via les outils MCP) pour extraire les informations "
            "essentielles à l'app: attentes des utilisateurs, tendances, sentiment, "
            "fonctionnalités demandées, concurrents. Synthétise des insights actionnables "
            "et cite les signaux observés."
        ),
        allowed_tools=[
            "social__search_mentions",
            "social__trending_topics",
            "social__sentiment_summary",
            "social__competitor_scan",
        ],
    ),
}


def build_agent(role: str, settings: Settings) -> Agent:
    if role not in PERSONAS:
        raise KeyError(f"Rôle inconnu '{role}'. Rôles disponibles: {', '.join(PERSONAS)}")
    persona = PERSONAS[role]
    return Agent(
        name=persona.name,
        role=persona.role,
        system_prompt=persona.system_prompt,
        settings=settings,
        allowed_tools=persona.allowed_tools,
    )


def build_all_agents(settings: Settings) -> dict[str, Agent]:
    return {role: build_agent(role, settings) for role in PERSONAS}
