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

PERSONAS: dict[str, Persona] = {
    "product_owner": Persona(
        name="Product Owner",
        role="product_owner",
        system_prompt=(
            f"{_BASE}\n\nTon rôle: Product Owner. Tu clarifies la vision produit, tu "
            "définis les objectifs, les personas utilisateurs, et tu rédiges des user "
            "stories au format 'En tant que … je veux … afin de …' avec des critères "
            "d'acceptation. Tu priorises (MoSCoW) et tu proposes un MVP."
        ),
        # Le PO consomme la veille réseaux sociaux pour orienter le produit.
        allowed_tools=[
            "social__search_mentions",
            "social__trending_topics",
            "social__sentiment_summary",
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
    ),
    "fullstack_dev": Persona(
        name="Développeur Full Stack",
        role="fullstack_dev",
        system_prompt=(
            f"{_BASE}\n\nTon rôle: Développeur Full Stack. Tu proposes une architecture "
            "technique (frontend, backend, base de données, API), tu choisis une stack "
            "justifiée, tu décris le modèle de données et les endpoints, et tu signales "
            "les risques techniques. Donne des extraits de code lorsqu'ils clarifient."
        ),
    ),
    "qa_tester": Persona(
        name="QA Tester",
        role="qa_tester",
        system_prompt=(
            f"{_BASE}\n\nTon rôle: QA Tester. Tu rédiges un plan de test: cas de test "
            "(nominal, limites, erreurs), critères d'acceptation vérifiables, scénarios "
            "end-to-end, et tu identifies les risques de régression. Format clair en "
            "tableau ou liste numérotée."
        ),
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
        raise KeyError(
            f"Rôle inconnu '{role}'. Rôles disponibles: {', '.join(PERSONAS)}"
        )
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
