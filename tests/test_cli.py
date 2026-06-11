"""Tests pour le module CLI."""

import pytest

from mcp_agents.cli import build_parser


def test_build_parser():
    """Le parser argparse se construit sans erreur."""
    parser = build_parser()
    assert parser is not None
    assert parser.prog == "mcp-agents"


def test_parser_list_command():
    """La commande 'list' est reconnue."""
    parser = build_parser()
    args = parser.parse_args(["list"])
    assert args.command == "list"


def test_parser_run_command():
    """La commande 'run' accepte un objectif."""
    parser = build_parser()
    args = parser.parse_args(["run", "une app de fitness"])
    assert args.command == "run"
    assert args.objective == "une app de fitness"
    assert args.out is None
    assert args.quiet is False


def test_parser_run_with_options():
    """La commande 'run' accepte -o et -q."""
    parser = build_parser()
    args = parser.parse_args(["run", "test", "-o", "out.md", "-q"])
    assert args.out == "out.md"
    assert args.quiet is True


def test_parser_agent_command():
    """La commande 'agent' accepte un rôle et une tâche."""
    parser = build_parser()
    args = parser.parse_args(["agent", "product_owner", "Rédige des user stories"])
    assert args.command == "agent"
    assert args.role == "product_owner"
    assert args.task == "Rédige des user stories"


def test_parser_agent_invalid_role():
    """Un rôle invalide est rejeté."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["agent", "invalid_role", "task"])


def test_parser_no_command():
    """Sans commande, le parser lève une erreur."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])
