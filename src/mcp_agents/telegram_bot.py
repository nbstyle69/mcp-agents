"""Bot Telegram pour discuter avec l'équipe multi-agents.

- Discute avec un agent précis (Product Owner, QA, Dev, UX, Architecte UI, Veille).
- `/run <objectif>` lance le pipeline complet et renvoie le rapport en fichier .md.

Lancement :
    TELEGRAM_BOT_TOKEN=... ANTHROPIC_API_KEY=... uv run mcp-agents-telegram
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .agents import PERSONAS
from .config import load_settings
from .orchestrator import Orchestrator

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("mcp_agents.telegram")

TELEGRAM_LIMIT = 4096
DEFAULT_AGENT = "product_owner"
# Nombre d'échanges (utilisateur+agent) conservés comme contexte de conversation.
HISTORY_TURNS = 6

# Fichier de persistance des briefs projet (par chat). Survit aux redémarrages.
PROJECTS_FILE = Path(
    os.environ.get(
        "MCP_AGENTS_PROJECTS_FILE", str(Path.home() / ".mcp_agents_projects.json")
    )
)


def _load_projects() -> dict[str, str]:
    try:
        return json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_projects(projects: dict[str, str]) -> None:
    PROJECTS_FILE.write_text(
        json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _project_brief(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> str | None:
    """Brief du chat, sinon brief global par défaut (env), sinon None."""

    projects: dict[str, str] = context.application.bot_data.setdefault("projects", {})
    return projects.get(str(chat_id)) or os.environ.get("MCP_AGENTS_PROJECT_BRIEF")


def _chunk(text: str, size: int = TELEGRAM_LIMIT) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _agent_keyboard() -> InlineKeyboardMarkup:
    rows, row = [], []
    for role, persona in PERSONAS.items():
        row.append(InlineKeyboardButton(persona.name, callback_data=f"agent:{role}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def _active_agent(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.chat_data.get("agent", DEFAULT_AGENT)


def _history(context: ContextTypes.DEFAULT_TYPE) -> list[tuple[str, str]]:
    return context.chat_data.setdefault("history", [])


def _context_string(history: list[tuple[str, str]]) -> str | None:
    if not history:
        return None
    recent = history[-HISTORY_TURNS * 2 :]
    lines = [f"{speaker}: {text}" for speaker, text in recent]
    return "Historique de la conversation:\n" + "\n".join(lines)


async def _send(update: Update, text: str) -> None:
    for part in _chunk(text):
        await update.effective_message.reply_text(part)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    agents = "\n".join(f"• {p.name}" for p in PERSONAS.values())
    await _send(
        update,
        "Bonjour ! Je suis ton équipe produit multi-agents.\n\n"
        f"Agents disponibles :\n{agents}\n\n"
        "Commandes :\n"
        "/project <description> — définir le contexte de ton projet (connu de tous les agents)\n"
        "/agents — choisir l'agent à qui parler\n"
        "/run <objectif> — lancer toute l'équipe sur un objectif (renvoie un rapport)\n"
        "/reset — repartir de zéro\n"
        "/help — aide\n\n"
        f"Par défaut tu parles au {PERSONAS[DEFAULT_AGENT].name}. Écris simplement ton message.",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        f"Agent actuel : {PERSONAS[_active_agent(context)].name}\nChoisis un agent :",
        reply_markup=_agent_keyboard(),
    )


async def on_agent_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    role = query.data.split(":", 1)[1]
    if role not in PERSONAS:
        await query.edit_message_text("Agent inconnu.")
        return
    context.chat_data["agent"] = role
    context.chat_data["history"] = []
    await query.edit_message_text(
        f"Tu parles maintenant au {PERSONAS[role].name}. Envoie ton message."
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data["history"] = []
    await update.effective_message.reply_text("Conversation réinitialisée.")


async def cmd_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    projects: dict[str, str] = context.application.bot_data.setdefault("projects", {})
    brief = " ".join(context.args).strip()
    if not brief:
        current = _project_brief(context, chat_id)
        if current:
            await _send(update, f"Contexte projet actuel :\n\n{current}")
        else:
            await update.effective_message.reply_text(
                "Aucun contexte projet défini. Ajoute-le avec :\n"
                "/project <décris ton app : nom, but, cible, fonctionnalités...>"
            )
        return
    projects[str(chat_id)] = brief
    _save_projects(projects)
    await update.effective_message.reply_text(
        "Contexte projet enregistré ✅ Tous les agents en tiendront compte désormais."
    )


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    objective = " ".join(context.args).strip()
    if not objective:
        await update.effective_message.reply_text(
            "Donne un objectif, ex : /run une app de fitness gamifiée pour débutants"
        )
        return
    orchestrator: Orchestrator = context.application.bot_data["orchestrator"]
    brief = _project_brief(context, update.effective_chat.id)
    await update.effective_message.reply_text(
        f"L'équipe travaille sur : « {objective} »\n"
        "Les 6 agents collaborent (veille → PO → UX → UI → Dev → QA), "
        "ça prend 1 à 3 min…"
    )
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        result = await orchestrator.run(objective, project_brief=brief)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Echec du pipeline")
        await update.effective_message.reply_text(f"Erreur durant le pipeline : {exc}")
        return

    markdown = result.to_markdown()
    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(markdown)
        path = fh.name
    with open(path, "rb") as doc:
        await context.bot.send_document(
            update.effective_chat.id,
            document=doc,
            filename="specification.md",
            caption=f"Spécification générée pour : {objective}",
        )
    os.unlink(path)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.effective_message.text or "").strip()
    if not text:
        return
    role = _active_agent(context)
    orchestrator: Orchestrator = context.application.bot_data["orchestrator"]
    history = _history(context)
    brief = _project_brief(context, update.effective_chat.id)
    task = text if not history else f"{_context_string(history)}\n\nMessage: {text}"
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        step = await orchestrator.run_single(role, task, project_brief=brief)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Echec de l'agent")
        await update.effective_message.reply_text(f"Erreur : {exc}")
        return
    history.append(("Utilisateur", text))
    history.append((PERSONAS[role].name, step.output))
    await _send(update, f"[{PERSONAS[role].name}]\n\n{step.output}")


def build_application(token: str) -> Application:
    settings = load_settings()
    settings.require_api_key()  # échoue tôt si ANTHROPIC_API_KEY manque
    application = ApplicationBuilder().token(token).build()
    application.bot_data["orchestrator"] = Orchestrator(settings)
    application.bot_data["projects"] = _load_projects()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("agents", cmd_agents))
    application.add_handler(CommandHandler("reset", cmd_reset))
    application.add_handler(CommandHandler("project", cmd_project))
    application.add_handler(CommandHandler("run", cmd_run))
    application.add_handler(CallbackQueryHandler(on_agent_choice, pattern=r"^agent:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    return application


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN manquant. Obtiens un token via @BotFather puis exporte-le."
        )
    application = build_application(token)
    logger.info("Bot Telegram démarré (long polling). Ctrl+C pour arrêter.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
