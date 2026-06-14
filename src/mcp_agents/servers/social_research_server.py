"""Serveur MCP de veille réseaux sociaux.

Expose des outils permettant aux agents de "sonder" les réseaux sociaux pour en
extraire les informations essentielles à une application.

⚠️ IMPORTANT : par défaut ce serveur renvoie des données SIMULÉES (mock) afin que le
système soit immédiatement exécutable sans clé d'API réseau social. Les fonctions sont
structurées pour être facilement remplacées par de vrais appels d'API (X/Twitter,
Reddit, etc.) — voir les TODO dans le code.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("social-research")

PLATFORMS = ["x", "reddit", "linkedin", "tiktok", "instagram"]

_SENTIMENTS = ["positif", "neutre", "négatif"]


def _seeded_rng(*parts: Any) -> random.Random:
    """RNG déterministe basé sur les arguments (résultats stables pour une même requête)."""

    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _normalize_platforms(platform: str) -> list[str]:
    if platform == "all":
        return PLATFORMS
    return [platform] if platform in PLATFORMS else PLATFORMS


@mcp.tool()
def search_mentions(query: str, platform: str = "all", limit: int = 5) -> str:
    """Recherche des mentions/posts liés à une requête sur les réseaux sociaux.

    Args:
        query: Mot-clé ou sujet à rechercher (ex: "app de fitness gamifiée").
        platform: "all" ou l'une de: x, reddit, linkedin, tiktok, instagram.
        limit: Nombre de mentions à renvoyer (1-20).

    Returns:
        Un JSON listant les mentions simulées (auteur, plateforme, texte, engagement).
    """

    # TODO: brancher ici un vrai client d'API (ex: X API v2, Reddit API) à la place du mock.
    rng = _seeded_rng("mentions", query, platform)
    platforms = _normalize_platforms(platform)
    limit = max(1, min(int(limit), 20))

    templates = [
        "J'adorerais une app pour {q}, mais celles que j'ai testées sont trop compliquées.",
        "Quelqu'un connaît une bonne solution pour {q} ? Je galère vraiment.",
        "Le gros problème avec {q}, c'est le manque de personnalisation.",
        "Enfin une appli {q} qui marche, il manque juste le mode hors-ligne.",
        "Je paierais volontiers pour {q} si l'UX était plus fluide.",
        "Trop de pubs dans les apps de {q}, ça me décourage.",
    ]
    mentions = []
    for i in range(limit):
        p = rng.choice(platforms)
        text = rng.choice(templates).format(q=query)
        mentions.append(
            {
                "id": f"{p}-{i+1}",
                "platform": p,
                "author": f"user_{rng.randint(1000, 9999)}",
                "text": text,
                "likes": rng.randint(2, 4200),
                "shares": rng.randint(0, 800),
                "sentiment": rng.choice(_SENTIMENTS),
            }
        )
    return json.dumps({"query": query, "count": len(mentions), "mentions": mentions}, ensure_ascii=False, indent=2)


@mcp.tool()
def trending_topics(domain: str, limit: int = 6) -> str:
    """Renvoie les sujets/tendances émergents dans un domaine donné.

    Args:
        domain: Domaine ou secteur (ex: "fitness", "fintech", "éducation").
        limit: Nombre de tendances (1-15).
    """

    # TODO: remplacer par un vrai endpoint de tendances (X trends, Google Trends, etc.).
    rng = _seeded_rng("trends", domain)
    limit = max(1, min(int(limit), 15))
    seeds = [
        "IA générative", "gamification", "communauté", "abonnement", "mode hors-ligne",
        "confidentialité des données", "accessibilité", "personnalisation", "social proof",
        "micro-paiements", "notifications intelligentes", "onboarding rapide",
    ]
    rng.shuffle(seeds)
    topics = [
        {
            "topic": f"{t} dans {domain}",
            "growth_pct": rng.randint(5, 180),
            "volume": rng.randint(1200, 95000),
        }
        for t in seeds[:limit]
    ]
    return json.dumps({"domain": domain, "trends": topics}, ensure_ascii=False, indent=2)


@mcp.tool()
def sentiment_summary(query: str, platform: str = "all") -> str:
    """Résume le sentiment global (positif/neutre/négatif) autour d'une requête.

    Args:
        query: Sujet analysé.
        platform: "all" ou une plateforme spécifique.
    """

    # TODO: agréger un vrai corpus de posts et passer par un modèle d'analyse de sentiment.
    rng = _seeded_rng("sentiment", query, platform)
    pos = rng.randint(20, 70)
    neg = rng.randint(5, 100 - pos)
    neu = 100 - pos - neg
    themes_pos = ["gain de temps", "simplicité", "communauté active"]
    themes_neg = ["bugs", "prix élevé", "trop de publicités", "courbe d'apprentissage"]
    return json.dumps(
        {
            "query": query,
            "platform": platform,
            "distribution_pct": {"positif": pos, "neutre": neu, "négatif": neg},
            "themes_positifs": rng.sample(themes_pos, k=min(2, len(themes_pos))),
            "themes_negatifs": rng.sample(themes_neg, k=min(2, len(themes_neg))),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def competitor_scan(product_category: str, limit: int = 4) -> str:
    """Identifie des produits/concurrents existants et leurs forces/faiblesses perçues.

    Args:
        product_category: Catégorie de produit (ex: "app de méditation").
        limit: Nombre de concurrents (1-10).
    """

    # TODO: brancher une vraie source (app stores, Product Hunt, G2) au lieu du mock.
    rng = _seeded_rng("competitors", product_category)
    limit = max(1, min(int(limit), 10))
    strengths = ["UX soignée", "grande communauté", "prix attractif", "intégrations", "contenu riche"]
    weaknesses = ["pas de mode hors-ligne", "support lent", "trop de pubs", "peu personnalisable"]
    competitors = []
    for i in range(limit):
        competitors.append(
            {
                "name": f"{product_category.title().split()[0]}Rival{i+1}",
                "rating": round(rng.uniform(3.2, 4.8), 1),
                "strengths": rng.sample(strengths, k=2),
                "weaknesses": rng.sample(weaknesses, k=2),
            }
        )
    return json.dumps(
        {"category": product_category, "competitors": competitors},
        ensure_ascii=False,
        indent=2,
    )


def run() -> None:
    """Point d'entrée : lance le serveur MCP via le transport stdio."""

    mcp.run()


if __name__ == "__main__":
    run()
