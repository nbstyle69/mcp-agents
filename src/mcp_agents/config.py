"""Configuration centrale du système multi-agents."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

# Modèle Claude par défaut. Surchargeable via la variable d'environnement ANTHROPIC_MODEL.
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


@dataclass(frozen=True)
class Settings:
    """Paramètres runtime, lus depuis l'environnement."""

    anthropic_api_key: str | None = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY")
    )
    model: str = field(default_factory=lambda: DEFAULT_MODEL)
    max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("ANTHROPIC_MAX_TOKENS", "2048"))
    )
    # Nombre maximum d'allers-retours (tour LLM <-> outils) par agent.
    max_tool_iterations: int = field(
        default_factory=lambda: int(os.environ.get("MCP_AGENTS_MAX_TOOL_ITERATIONS", "6"))
    )

    def require_api_key(self) -> str:
        if not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY introuvable. Crée un fichier .env (voir .env.example) "
                "ou exporte la variable d'environnement."
            )
        return self.anthropic_api_key


def load_settings() -> Settings:
    return Settings()
