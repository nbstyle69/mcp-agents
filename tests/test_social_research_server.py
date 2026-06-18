"""Tests pour le serveur MCP de veille réseaux sociaux."""

import json

from mcp_agents.servers.social_research_server import (
    competitor_scan,
    search_mentions,
    sentiment_summary,
    trending_topics,
)


def test_search_mentions_returns_valid_json():
    """search_mentions renvoie du JSON valide."""
    result = search_mentions("fitness", platform="all", limit=3)
    data = json.loads(result)
    assert data["query"] == "fitness"
    assert data["count"] == 3
    assert len(data["mentions"]) == 3


def test_search_mentions_deterministic():
    """Les résultats sont déterministes pour les mêmes paramètres."""
    r1 = search_mentions("yoga", platform="reddit", limit=2)
    r2 = search_mentions("yoga", platform="reddit", limit=2)
    assert r1 == r2


def test_search_mentions_limit_clamped():
    """Le limit est borné entre 1 et 20."""
    result = json.loads(search_mentions("test", limit=50))
    assert result["count"] <= 20

    result = json.loads(search_mentions("test", limit=0))
    assert result["count"] >= 1


def test_trending_topics_returns_valid_json():
    """trending_topics renvoie du JSON structuré."""
    result = trending_topics("fitness", limit=4)
    data = json.loads(result)
    assert data["domain"] == "fitness"
    assert len(data["trends"]) == 4
    for trend in data["trends"]:
        assert "topic" in trend
        assert "growth_pct" in trend
        assert "volume" in trend


def test_sentiment_summary_returns_percentages():
    """sentiment_summary renvoie des pourcentages cohérents."""
    result = sentiment_summary("meditation", platform="all")
    data = json.loads(result)
    dist = data["distribution_pct"]
    total = dist["positif"] + dist["neutre"] + dist["négatif"]
    assert total == 100


def test_competitor_scan_returns_competitors():
    """competitor_scan renvoie une liste de concurrents."""
    result = competitor_scan("fitness app", limit=3)
    data = json.loads(result)
    assert data["category"] == "fitness app"
    assert len(data["competitors"]) == 3
    for comp in data["competitors"]:
        assert "name" in comp
        assert "strengths" in comp
        assert "weaknesses" in comp
