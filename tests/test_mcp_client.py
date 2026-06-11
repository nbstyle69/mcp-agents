"""Tests pour le module mcp_client."""

from mcp_agents.mcp_client import SEP, MCPClientManager, MCPServerConfig


def test_sep_constant():
    """Le séparateur est bien '__'."""
    assert SEP == "__"


def test_mcp_server_config_creation():
    """MCPServerConfig se crée correctement."""
    cfg = MCPServerConfig(name="test", command="python", args=["-m", "test_server"])
    assert cfg.name == "test"
    assert cfg.command == "python"
    assert cfg.args == ["-m", "test_server"]
    assert cfg.env is None


def test_mcp_server_config_with_env():
    """MCPServerConfig accepte un dictionnaire d'env."""
    cfg = MCPServerConfig(name="gh", command="python", args=[], env={"TOKEN": "abc"})
    assert cfg.env == {"TOKEN": "abc"}


def test_mcp_client_manager_init():
    """MCPClientManager s'initialise sans crash."""
    configs = [MCPServerConfig(name="s", command="echo", args=["hello"])]
    manager = MCPClientManager(configs)
    # Avant connexion, pas d'outils
    assert manager.anthropic_tools() == []
    assert manager.tool_names() == []
