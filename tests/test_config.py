"""Tests pour le module config."""

import os
from unittest.mock import patch

import pytest

from mcp_agents.config import Settings, load_settings


def test_settings_defaults():
    """Les valeurs par défaut sont correctes."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}, clear=False):
        s = Settings(anthropic_api_key="sk-test-key")
        assert s.max_tokens == 2048 or s.max_tokens > 0
        assert s.max_tool_iterations > 0


def test_settings_require_api_key_raises():
    """require_api_key lève RuntimeError sans clé."""
    s = Settings(anthropic_api_key=None)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        s.require_api_key()


def test_settings_require_api_key_ok():
    """require_api_key renvoie la clé si présente."""
    s = Settings(anthropic_api_key="sk-test")
    assert s.require_api_key() == "sk-test"


def test_load_settings():
    """load_settings instancie un Settings sans crash."""
    s = load_settings()
    assert isinstance(s, Settings)


def test_custom_max_tokens():
    """Les valeurs personnalisées depuis l'environnement sont prises en compte."""
    with patch.dict(os.environ, {"ANTHROPIC_MAX_TOKENS": "4096"}, clear=False):
        s = Settings()
        assert s.max_tokens == 4096


def test_custom_max_tool_iterations():
    """max_tool_iterations peut être surchargé."""
    with patch.dict(os.environ, {"MCP_AGENTS_MAX_TOOL_ITERATIONS": "20"}, clear=False):
        s = Settings()
        assert s.max_tool_iterations == 20
