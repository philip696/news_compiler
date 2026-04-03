import uuid
from datetime import timedelta

from .. import state
from ..core.config import settings


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors"""
    if not vec1 or not vec2:
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = sum(x * x for x in vec1) ** 0.5
    mag2 = sum(x * x for x in vec2) ** 0.5
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot_product / (mag1 * mag2)


def _connected_components(graph: dict[str, set[str]]) -> list[list[str]]:
    visited: set[str] = set()
    components: list[list[str]] = []
    for node in graph:
        if node in visited:
            continue
        stack = [node]
        component = []
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            component.append(cur)
            stack.extend(graph[cur] - visited)
        components.append(component)
    return components


def build_story_clusters() -> int:
    articles = list(state.articles.values())
    if not articles:
        state.clusters = {}
        return 0

    ids = [a["id"] for a in articles]
    vectors = [a["embedding"] for a in articles]
    
    # Compute pairwise similarity matrix
    sims = {}
    for i in range(len(vectors)):
        for j in range(len(vectors)):
            sims[(i, j)] = _cosine_similarity(vectors[i], vectors[j])

    graph = {article_id: set() for article_id in ids}
    for i, source_id in enumerate(ids):
        graph[source_id].add(source_id)
        for j in range(i + 1, len(ids)):
            target_id = ids[j]
            article_a = state.articles[source_id]
            article_b = state.articles[target_id]

            topic_match = article_a["topic"] == article_b["topic"]
            time_gap = abs(article_a["published_at"] - article_b["published_at"]) <= timedelta(hours=48)
            similar = sims[(i, j)] >= settings.similarity_threshold

            if topic_match and time_gap and similar:
                graph[source_id].add(target_id)
                graph[target_id].add(source_id)

    components = _connected_components(graph)

    new_clusters: dict[str, dict] = {}
    for comp in components:
        comp_articles = [state.articles[a_id] for a_id in comp]
        comp_articles.sort(key=lambda x: x["published_at"], reverse=True)
        headline = comp_articles[0]["title"]
        topic = comp_articles[0]["topic"]
        sources = sorted({article["source_name"] for article in comp_articles})
        summary = f"{len(comp_articles)} related articles across {len(sources)} sources"
        cluster_id = str(uuid.uuid4())

        new_clusters[cluster_id] = {
            "cluster_id": cluster_id,
            "topic": topic,
            "headline": headline,
            "summary": summary,
            "article_ids": [a["id"] for a in comp_articles],
            "sources": sources,
            "created_at": comp_articles[0]["published_at"],
        }

    state.clusters = new_clusters
    return len(new_clusters)
