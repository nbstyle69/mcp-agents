"""Tests pour le module orchestrator."""

from mcp_agents.orchestrator import (
    PIPELINE,
    OrchestrationResult,
    StepResult,
    default_servers,
)


def test_pipeline_order():
    """Le pipeline contient les rôles dans l'ordre attendu."""
    roles = [role for role, _ in PIPELINE]
    assert roles == [
        "social_researcher",
        "product_owner",
        "ux_designer",
        "ui_architect",
        "fullstack_dev",
        "qa_tester",
    ]


def test_pipeline_has_instructions():
    """Chaque étape du pipeline a une instruction non-vide."""
    for role, instruction in PIPELINE:
        assert len(instruction) > 20, f"{role}: instruction trop courte"


def test_step_result():
    """StepResult stocke les données correctement."""
    step = StepResult(role="qa_tester", agent_name="QA Tester", output="Tests OK")
    assert step.role == "qa_tester"
    assert step.agent_name == "QA Tester"
    assert step.output == "Tests OK"


def test_orchestration_result_to_markdown():
    """to_markdown génère un rapport structuré."""
    result = OrchestrationResult(
        objective="app fitness",
        steps=[
            StepResult(role="product_owner", agent_name="PO", output="Vision claire"),
            StepResult(role="qa_tester", agent_name="QA", output="Plan de test"),
        ],
    )
    md = result.to_markdown()
    assert "app fitness" in md
    assert "## PO" in md
    assert "## QA" in md
    assert "Vision claire" in md
    assert "Plan de test" in md


def test_default_servers_without_github_token(monkeypatch):
    """Sans GITHUB_TOKEN, seul le serveur social est configuré."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    servers = default_servers()
    assert len(servers) == 1
    assert servers[0].name == "social"


def test_default_servers_with_github_token(monkeypatch):
    """Avec GITHUB_TOKEN, le serveur github est ajouté."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
    servers = default_servers()
    assert len(servers) == 2
    names = [s.name for s in servers]
    assert "social" in names
    assert "github" in names
