"""Interface en ligne de commande pour le système multi-agents MCP."""

from __future__ import annotations

import argparse
import asyncio
import sys

from .agents import PERSONAS
from .config import load_settings
from .orchestrator import Orchestrator


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _cmd_list(_: argparse.Namespace) -> int:
    print("Agents disponibles:\n")
    for role, persona in PERSONAS.items():
        print(f"  - {role:18s} {persona.name}")
    return 0


async def _run_pipeline(objective: str, out: str | None, quiet: bool) -> int:
    settings = load_settings()
    orchestrator = Orchestrator(settings)
    result = await orchestrator.run(objective, log=None if quiet else _log)
    markdown = result.to_markdown()
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(markdown)
        _log(f"\nRapport écrit dans {out}")
    else:
        print("\n" + markdown)
    return 0


async def _run_agent(role: str, task: str, quiet: bool) -> int:
    settings = load_settings()
    orchestrator = Orchestrator(settings)
    step = await orchestrator.run_single(role, task, log=None if quiet else _log)
    print(f"\n## {step.agent_name}\n\n{step.output}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    return asyncio.run(_run_pipeline(args.objective, args.out, args.quiet))


def _cmd_agent(args: argparse.Namespace) -> int:
    return asyncio.run(_run_agent(args.role, args.task, args.quiet))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-agents",
        description="Système multi-agents IA (PO, QA, Dev, UX, Architecte UI, Veille) basé sur MCP.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Lance le pipeline complet sur un objectif produit.")
    p_run.add_argument("objective", help="Objectif produit, ex: 'app de fitness gamifiée'.")
    p_run.add_argument("-o", "--out", help="Fichier de sortie Markdown (sinon stdout).")
    p_run.add_argument("-q", "--quiet", action="store_true", help="Masque les logs de progression.")
    p_run.set_defaults(func=_cmd_run)

    p_agent = sub.add_parser("agent", help="Lance un seul agent.")
    p_agent.add_argument("role", choices=list(PERSONAS), help="Rôle de l'agent.")
    p_agent.add_argument("task", help="Tâche à confier à l'agent.")
    p_agent.add_argument("-q", "--quiet", action="store_true", help="Masque les logs.")
    p_agent.set_defaults(func=_cmd_agent)

    p_list = sub.add_parser("list", help="Liste les agents disponibles.")
    p_list.set_defaults(func=_cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
