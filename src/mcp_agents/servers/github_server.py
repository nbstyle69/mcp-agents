"""Serveur MCP GitHub — LECTURE SEULE.

Permet aux agents d'explorer un dépôt GitHub : infos du repo, arborescence,
lecture de fichiers, recherche de code, issues et pull requests.

Sécurité : ce serveur n'effectue **que** des requêtes GET sur l'API GitHub. Il ne
peut donc ni écrire, ni committer, ni ouvrir/merger de PR. L'authentification se fait
via la variable d'environnement ``GITHUB_TOKEN`` (idéalement un fine-grained token
limité en lecture seule à un repo).

Variables d'environnement :
- ``GITHUB_TOKEN`` (requis) : token d'accès en lecture.
- ``GITHUB_DEFAULT_REPO`` (optionnel) : repo par défaut au format ``owner/name``.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("github")

API = "https://api.github.com"
MAX_FILE_CHARS = 20000


def _token() -> str | None:
    return os.environ.get("GITHUB_TOKEN")


def _resolve_repo(repo: str) -> str | None:
    repo = (repo or "").strip()
    if not repo:
        repo = (os.environ.get("GITHUB_DEFAULT_REPO") or "").strip()
    return repo or None


def _err(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False, indent=2)


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Requête GET authentifiée sur l'API GitHub. Lève une exception en cas d'échec."""

    token = _token()
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN absent. Fournis un token GitHub en lecture seule."
        )
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = path if path.startswith("http") else f"{API}{path}"
    resp = httpx.get(url, headers=headers, params=params, timeout=30.0)
    if resp.status_code == 404:
        raise RuntimeError("Ressource introuvable (404) — vérifie le repo/chemin/accès du token.")
    if resp.status_code in (401, 403):
        raise RuntimeError(
            f"Accès refusé ({resp.status_code}) — le token est invalide ou n'a pas la portée nécessaire."
        )
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def gh_repo_info(repo: str = "") -> str:
    """Renvoie les informations principales d'un dépôt GitHub (lecture seule).

    Args:
        repo: Dépôt au format "owner/name". Si vide, utilise GITHUB_DEFAULT_REPO.
    """

    target = _resolve_repo(repo)
    if not target:
        return _err("Aucun repo spécifié et GITHUB_DEFAULT_REPO non défini.")
    try:
        data = _get(f"/repos/{target}")
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))
    return json.dumps(
        {
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "default_branch": data.get("default_branch"),
            "language": data.get("language"),
            "stars": data.get("stargazers_count"),
            "open_issues": data.get("open_issues_count"),
            "topics": data.get("topics", []),
            "visibility": data.get("visibility"),
            "url": data.get("html_url"),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def gh_list_files(repo: str = "", path: str = "", ref: str = "") -> str:
    """Liste le contenu d'un dossier du dépôt (lecture seule).

    Args:
        repo: "owner/name" (sinon GITHUB_DEFAULT_REPO).
        path: Chemin du dossier (vide = racine).
        ref: Branche/commit (vide = branche par défaut).
    """

    target = _resolve_repo(repo)
    if not target:
        return _err("Aucun repo spécifié et GITHUB_DEFAULT_REPO non défini.")
    params = {"ref": ref} if ref else None
    try:
        data = _get(f"/repos/{target}/contents/{path.lstrip('/')}", params=params)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))
    if isinstance(data, dict):  # un fichier, pas un dossier
        return json.dumps(
            {"note": "Ce chemin est un fichier, pas un dossier.", "path": data.get("path")},
            ensure_ascii=False,
            indent=2,
        )
    entries = [
        {"name": e.get("name"), "type": e.get("type"), "size": e.get("size"), "path": e.get("path")}
        for e in data
    ]
    return json.dumps({"repo": target, "path": path or "/", "entries": entries}, ensure_ascii=False, indent=2)


@mcp.tool()
def gh_read_file(path: str, repo: str = "", ref: str = "") -> str:
    """Lit le contenu texte d'un fichier du dépôt (lecture seule).

    Args:
        path: Chemin du fichier (ex: "src/app.py").
        repo: "owner/name" (sinon GITHUB_DEFAULT_REPO).
        ref: Branche/commit (vide = branche par défaut).
    """

    target = _resolve_repo(repo)
    if not target:
        return _err("Aucun repo spécifié et GITHUB_DEFAULT_REPO non défini.")
    params = {"ref": ref} if ref else None
    try:
        data = _get(f"/repos/{target}/contents/{path.lstrip('/')}", params=params)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))
    if isinstance(data, list):
        return _err("Ce chemin est un dossier. Utilise gh_list_files.")
    if data.get("encoding") != "base64" or "content" not in data:
        return _err("Contenu binaire ou non lisible.")
    try:
        text = base64.b64decode(data["content"]).decode("utf-8")
    except UnicodeDecodeError:
        return _err("Fichier binaire — lecture texte impossible.")
    truncated = len(text) > MAX_FILE_CHARS
    return json.dumps(
        {
            "repo": target,
            "path": data.get("path"),
            "size": data.get("size"),
            "truncated": truncated,
            "content": text[:MAX_FILE_CHARS],
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def gh_search_code(query: str, repo: str = "", limit: int = 10) -> str:
    """Recherche du code dans le dépôt (lecture seule).

    Args:
        query: Termes à rechercher dans le code.
        repo: "owner/name" (sinon GITHUB_DEFAULT_REPO).
        limit: Nombre de résultats (1-30).
    """

    target = _resolve_repo(repo)
    if not target:
        return _err("Aucun repo spécifié et GITHUB_DEFAULT_REPO non défini.")
    limit = max(1, min(int(limit), 30))
    try:
        data = _get("/search/code", params={"q": f"{query} repo:{target}", "per_page": limit})
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))
    items = [
        {"path": it.get("path"), "url": it.get("html_url")}
        for it in data.get("items", [])
    ]
    return json.dumps({"repo": target, "query": query, "matches": items}, ensure_ascii=False, indent=2)


@mcp.tool()
def gh_list_issues(repo: str = "", state: str = "open", limit: int = 10) -> str:
    """Liste les issues du dépôt (lecture seule). Exclut les pull requests.

    Args:
        repo: "owner/name" (sinon GITHUB_DEFAULT_REPO).
        state: "open", "closed" ou "all".
        limit: Nombre d'issues (1-30).
    """

    target = _resolve_repo(repo)
    if not target:
        return _err("Aucun repo spécifié et GITHUB_DEFAULT_REPO non défini.")
    limit = max(1, min(int(limit), 30))
    try:
        data = _get(f"/repos/{target}/issues", params={"state": state, "per_page": limit})
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))
    issues = [
        {
            "number": it.get("number"),
            "title": it.get("title"),
            "state": it.get("state"),
            "labels": [lbl.get("name") for lbl in it.get("labels", [])],
            "url": it.get("html_url"),
        }
        for it in data
        if "pull_request" not in it  # l'API issues inclut les PR ; on les filtre
    ]
    return json.dumps({"repo": target, "state": state, "issues": issues}, ensure_ascii=False, indent=2)


@mcp.tool()
def gh_list_pull_requests(repo: str = "", state: str = "open", limit: int = 10) -> str:
    """Liste les pull requests du dépôt (lecture seule).

    Args:
        repo: "owner/name" (sinon GITHUB_DEFAULT_REPO).
        state: "open", "closed" ou "all".
        limit: Nombre de PR (1-30).
    """

    target = _resolve_repo(repo)
    if not target:
        return _err("Aucun repo spécifié et GITHUB_DEFAULT_REPO non défini.")
    limit = max(1, min(int(limit), 30))
    try:
        data = _get(f"/repos/{target}/pulls", params={"state": state, "per_page": limit})
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))
    prs = [
        {
            "number": it.get("number"),
            "title": it.get("title"),
            "state": it.get("state"),
            "draft": it.get("draft"),
            "url": it.get("html_url"),
        }
        for it in data
    ]
    return json.dumps({"repo": target, "state": state, "pull_requests": prs}, ensure_ascii=False, indent=2)


def run() -> None:
    """Point d'entrée : lance le serveur MCP via le transport stdio."""

    mcp.run()


if __name__ == "__main__":
    run()
