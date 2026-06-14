"""Serveur MCP « mcp-team » — expose les agents comme outils pour Devin / tout client MCP.

Chaque agent de l'équipe produit est disponible sous forme d'outil MCP :
``ask_product_owner``, ``ask_ux_designer``, ``ask_ui_architect``,
``ask_fullstack_dev``, ``ask_qa_tester``, ``ask_social_researcher``.

Un outil supplémentaire ``run_team_pipeline`` lance le pipeline complet
(veille → PO → UX → UI → Dev → QA) et renvoie le rapport markdown.

Variables d'environnement attendues (transmises par le processus parent) :
- ``ANTHROPIC_API_KEY`` (requis)
- ``GITHUB_TOKEN`` / ``GITHUB_DEFAULT_REPO`` (optionnels, lecture seule)
- ``MCP_AGENTS_PROJECT_BRIEF`` (optionnel, brief projet par défaut)
"""

from __future__ import annotations

import asyncio
import os
from functools import lru_cache

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-team")


@lru_cache(maxsize=1)
def _orchestrator():
    """Singleton paresseux — créé une seule fois au premier appel d'outil."""
    from ..config import load_settings
    from ..orchestrator import Orchestrator

    return Orchestrator(load_settings())


def _brief(override: str) -> str | None:
    b = (override or "").strip()
    return b if b else os.environ.get("MCP_AGENTS_PROJECT_BRIEF") or None


def _log_lines() -> list[str]:
    lines: list[str] = []
    return lines


# ---------------------------------------------------------------------------
# Outils individuels (un par agent)
# ---------------------------------------------------------------------------

@mcp.tool()
async def ask_product_owner(question: str, project_brief: str = "") -> str:
    """Pose une question au Product Owner (vision produit, user stories, priorisation MoSCoW, MVP).

    Args:
        question: La question ou tâche à soumettre au Product Owner.
        project_brief: Contexte du projet (optionnel, sinon MCP_AGENTS_PROJECT_BRIEF).
    """
    step = await _orchestrator().run_single("product_owner", question, project_brief=_brief(project_brief))
    return step.output


@mcp.tool()
async def ask_ux_designer(question: str, project_brief: str = "") -> str:
    """Pose une question au UX Designer (parcours utilisateurs, wireframes, ergonomie).

    Args:
        question: La question ou tâche à soumettre au UX Designer.
        project_brief: Contexte du projet (optionnel, sinon MCP_AGENTS_PROJECT_BRIEF).
    """
    step = await _orchestrator().run_single("ux_designer", question, project_brief=_brief(project_brief))
    return step.output


@mcp.tool()
async def ask_ui_architect(question: str, project_brief: str = "") -> str:
    """Pose une question à l'Architecte d'interface (design system, composants, accessibilité WCAG).

    Args:
        question: La question ou tâche à soumettre à l'Architecte d'interface.
        project_brief: Contexte du projet (optionnel, sinon MCP_AGENTS_PROJECT_BRIEF).
    """
    step = await _orchestrator().run_single("ui_architect", question, project_brief=_brief(project_brief))
    return step.output


@mcp.tool()
async def ask_fullstack_dev(question: str, project_brief: str = "") -> str:
    """Pose une question au Développeur Full Stack (architecture technique, stack, API, modèle de données).

    Args:
        question: La question ou tâche à soumettre au Développeur Full Stack.
        project_brief: Contexte du projet (optionnel, sinon MCP_AGENTS_PROJECT_BRIEF).
    """
    step = await _orchestrator().run_single("fullstack_dev", question, project_brief=_brief(project_brief))
    return step.output


@mcp.tool()
async def ask_qa_tester(question: str, project_brief: str = "") -> str:
    """Pose une question au QA Tester (plan de test, cas de test, critères d'acceptation, risques).

    Args:
        question: La question ou tâche à soumettre au QA Tester.
        project_brief: Contexte du projet (optionnel, sinon MCP_AGENTS_PROJECT_BRIEF).
    """
    step = await _orchestrator().run_single("qa_tester", question, project_brief=_brief(project_brief))
    return step.output


@mcp.tool()
async def ask_social_researcher(question: str, project_brief: str = "") -> str:
    """Pose une question à l'analyste veille réseaux sociaux (tendances, sentiment, concurrents, insights).

    Args:
        question: La question ou tâche à soumettre à l'analyste veille.
        project_brief: Contexte du projet (optionnel, sinon MCP_AGENTS_PROJECT_BRIEF).
    """
    step = await _orchestrator().run_single("social_researcher", question, project_brief=_brief(project_brief))
    return step.output


# ---------------------------------------------------------------------------
# Pipeline complet
# ---------------------------------------------------------------------------

@mcp.tool()
async def run_team_pipeline(objective: str, project_brief: str = "") -> str:
    """Lance l'équipe complète (6 agents en pipeline) sur un objectif produit.

    Ordre : Veille → Product Owner → UX Designer → Architecte UI → Dev Full Stack → QA Tester.
    Renvoie le rapport complet en markdown.

    Args:
        objective: L'objectif produit en une phrase.
        project_brief: Contexte du projet (optionnel, sinon MCP_AGENTS_PROJECT_BRIEF).
    """
    result = await _orchestrator().run(objective, project_brief=_brief(project_brief))
    return result.to_markdown()


# ---------------------------------------------------------------------------
# Utilitaire
# ---------------------------------------------------------------------------

@mcp.tool()
def list_team() -> str:
    """Liste les agents disponibles dans l'équipe produit et leur rôle."""
    from ..agents import PERSONAS

    lines = ["Agents disponibles :\n"]
    for key, p in PERSONAS.items():
        lines.append(f"- **{p.name}** (`{key}`): {p.system_prompt.split(chr(10))[-1][:120]}…")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def run() -> None:
    """Lance le serveur MCP via le transport stdio."""
    mcp.run()


if __name__ == "__main__":
    run()
