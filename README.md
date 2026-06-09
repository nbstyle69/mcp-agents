# mcp-agents

Système **multi-agents IA** basé sur **MCP** (Model Context Protocol) et **Claude** (Anthropic).

Une équipe produit virtuelle collabore pour transformer un objectif en spécification complète. Chaque agent a une persona dédiée :

| Rôle | Agent | Ce qu'il produit |
|------|-------|------------------|
| `social_researcher` | Veille réseaux sociaux | Insights, tendances, sentiment, concurrents (via outils MCP) |
| `product_owner` | Product Owner | Vision, personas, MVP, user stories priorisées |
| `ux_designer` | UX Designer | Parcours utilisateurs, wireframes décrits |
| `ui_architect` | Architecte d'interface | Design system, composants, accessibilité |
| `fullstack_dev` | Développeur Full Stack | Stack, architecture technique, modèle de données, API |
| `qa_tester` | QA Tester | Plan de test, cas de test, critères d'acceptation |

## Architecture

```
                 ┌─────────────────────────────────────────┐
   Objectif ───► │              Orchestrator                │
                 │  (pipeline: veille → PO → UX → UI →      │
                 │   Dev → QA, contexte transmis à chaque   │
                 │   étape)                                  │
                 └───────────────┬─────────────────────────┘
                                 │ chaque agent = persona Claude
                                 ▼
                 ┌─────────────────────────────────────────┐
                 │   Agent (boucle d'appel d'outils Claude) │
                 └───────────────┬─────────────────────────┘
                                 │ tools au format Anthropic
                                 ▼
                 ┌─────────────────────────────────────────┐
                 │   MCPClientManager (stdio)               │
                 │   ↕ connecte les serveurs MCP            │
                 └───────────────┬─────────────────────────┘
                                 ▼
                 ┌─────────────────────────────────────────┐
                 │  Serveur MCP "social-research"           │
                 │  outils: search_mentions, trending_      │
                 │  topics, sentiment_summary,              │
                 │  competitor_scan                         │
                 └─────────────────────────────────────────┘
```

- **MCP** : les outils sont exposés par un serveur MCP (`social-research`) et consommés par les agents via le transport stdio. On peut ajouter d'autres serveurs MCP (ex. un serveur de fichiers, une base de données) sans toucher aux agents.
- **Agents** : chaque agent est une instance de Claude avec un prompt système (persona) et un sous-ensemble d'outils autorisés.
- **Orchestrateur** : enchaîne les agents et transmet le contexte accumulé.

> ⚠️ Le serveur de veille renvoie par défaut des **données simulées** (mock) déterministes, pour que le projet tourne sans clé d'API réseau social. Les emplacements à brancher sur de vraies API sont marqués `TODO` dans `social_research_server.py`.

## Installation

```bash
uv sync
cp .env.example .env   # puis renseigne ANTHROPIC_API_KEY
```

## Utilisation

Pipeline complet (génère une spécification produit) :

```bash
uv run mcp-agents run "une app mobile de fitness gamifiée pour débutants" -o spec.md
```

Un seul agent :

```bash
uv run mcp-agents agent product_owner "Rédige 3 user stories pour un onboarding rapide"
uv run mcp-agents agent social_researcher "Sonde les attentes autour des apps de méditation"
```

Lister les agents :

```bash
uv run mcp-agents list
```

Lancer le serveur MCP seul (debug / inspection avec un client MCP) :

```bash
uv run social-research-server
```

## Bot Telegram

Discute avec les agents directement depuis Telegram.

1. Crée un bot via [@BotFather](https://t.me/BotFather) (`/newbot`) et récupère le token.
2. Lance le bot :

```bash
TELEGRAM_BOT_TOKEN=123:AAE... ANTHROPIC_API_KEY=sk-ant-... uv run mcp-agents-telegram
```

Commandes dans Telegram :

- `/project <description>` — définir le **contexte du projet** (nom, but, cible…), injecté dans **tous** les agents et **persistant** (survit au redémarrage)
- `/agents` — choisir l'agent à qui parler (boutons)
- (texte libre) — discuter avec l'agent actif (conversation avec mémoire courte)
- `/run <objectif>` — lancer toute l'équipe ; renvoie le rapport en fichier `.md`
- `/reset` — réinitialiser la conversation
- `/start`, `/help` — aide

## Accès GitHub (lecture seule)

Les agents peuvent **explorer un dépôt GitHub en lecture seule** (lister/lire des fichiers, rechercher du code, voir issues et PR) — ils ne peuvent **rien modifier**. Activé uniquement si `GITHUB_TOKEN` est défini.

1. Crée un **fine-grained token** sur https://github.com/settings/personal-access-tokens/new, limité au(x) repo(s) voulu(s), avec **Contents: Read-only** et **Metadata: Read-only** (Issues/Pull requests en Read-only si souhaité).
2. Lance avec le token (et un repo par défaut optionnel) :

```bash
GITHUB_TOKEN=github_pat_... GITHUB_DEFAULT_REPO=owner/repo \
ANTHROPIC_API_KEY=sk-ant-... uv run mcp-agents-telegram
```

Outils exposés (serveur MCP `github`) : `gh_repo_info`, `gh_list_files`, `gh_read_file`, `gh_search_code`, `gh_list_issues`, `gh_list_pull_requests`. Agents autorisés : Product Owner, Développeur Full Stack, QA Tester.

> 🔒 Le serveur n'effectue que des requêtes **GET** — aucune écriture, aucun commit, aucun merge possible.

## Configuration

Variables d'environnement (voir `.env.example`) : `ANTHROPIC_API_KEY` (requis), `ANTHROPIC_MODEL`, `ANTHROPIC_MAX_TOKENS`, `MCP_AGENTS_MAX_TOOL_ITERATIONS`, `TELEGRAM_BOT_TOKEN` (pour le bot), `GITHUB_TOKEN` + `GITHUB_DEFAULT_REPO` (pour l'accès GitHub en lecture seule).

## Structure

```
src/mcp_agents/
├── config.py          # paramètres (env)
├── mcp_client.py      # gestion des sessions MCP + adaptation des outils
├── agent.py           # agent de base (boucle outils Claude)
├── agents.py          # personas (rôles)
├── orchestrator.py    # pipeline de collaboration
├── cli.py             # CLI
├── telegram_bot.py    # bot Telegram (discuter avec les agents)
└── servers/
    ├── social_research_server.py   # serveur MCP de veille réseaux sociaux
    └── github_server.py            # serveur MCP GitHub (lecture seule)
```

## Étendre

- **Ajouter un agent** : ajoute une `Persona` dans `agents.py`.
- **Ajouter un outil MCP** : ajoute une fonction `@mcp.tool()` dans un serveur, ou crée un nouveau serveur et référence-le dans `orchestrator.default_servers()`.
- **Brancher de vraies données** : remplace les mocks marqués `TODO` par des appels d'API réels.
