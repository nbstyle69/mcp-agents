"""Tests pour le module agents (définition des personas)."""

from mcp_agents.agents import PERSONAS, Persona, build_all_agents
from mcp_agents.config import Settings


def test_personas_all_defined():
    """Tous les rôles attendus sont définis."""
    expected_roles = {
        "product_owner",
        "ux_designer",
        "ui_architect",
        "fullstack_dev",
        "qa_tester",
        "social_researcher",
    }
    assert set(PERSONAS.keys()) == expected_roles


def test_persona_has_required_fields():
    """Chaque persona a un nom, rôle et prompt système."""
    for role, persona in PERSONAS.items():
        assert isinstance(persona, Persona)
        assert persona.name, f"{role}: nom manquant"
        assert persona.role == role, f"{role}: rôle incohérent"
        assert len(persona.system_prompt) > 50, f"{role}: prompt trop court"


def test_persona_allowed_tools_type():
    """Les outils autorisés sont une liste de strings ou None."""
    for role, persona in PERSONAS.items():
        if persona.allowed_tools is not None:
            assert isinstance(persona.allowed_tools, list)
            for tool in persona.allowed_tools:
                assert isinstance(tool, str), f"{role}: outil non-string"
                assert "__" in tool, f"{role}: outil sans préfixe serveur: {tool}"


def test_build_all_agents():
    """build_all_agents renvoie un dict avec un Agent par persona."""
    settings = Settings(anthropic_api_key="sk-test-fake")
    agents = build_all_agents(settings)
    assert set(agents.keys()) == set(PERSONAS.keys())
    for role, agent in agents.items():
        assert agent.name == PERSONAS[role].name
        assert agent.role == role
