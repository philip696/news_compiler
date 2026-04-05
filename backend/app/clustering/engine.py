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
    """Build story clusters: group similar articles by topic with memory-efficient approach."""
    try:
        articles = list(state.articles.values())
        if not articles:
            state.clusters = {}
            return 0

        new_clusters: dict[str, dict] = {}
        
        # Cluster by topic first to reduce O(n²) comparisons
        articles_by_topic = {}
        for article in articles:
            topic = article["topic"]
            if topic not in articles_by_topic:
                articles_by_topic[topic] = []
            articles_by_topic[topic].append(article)
        
        print(f"📊 Clustering {len(articles)} articles across {len(articles_by_topic)} topics...")
        
        # Process each topic independently
        for topic, topic_articles in articles_by_topic.items():
            if not topic_articles:
                continue
            
            # Within-topic clustering: compare only articles in same topic
            ids = [a["id"] for a in topic_articles]
            vectors = [a["embedding"] for a in topic_articles]
            
            # Compute pairwise similarity matrix (only within topic)
            sims = {}
            for i in range(len(vectors)):
                for j in range(i + 1, len(vectors)):
                    sims[(i, j)] = _cosine_similarity(vectors[i], vectors[j])
            
            # Build connectivity graph
            graph = {article_id: set() for article_id in ids}
            for i, source_id in enumerate(ids):
                graph[source_id].add(source_id)
                for j in range(i + 1, len(ids)):
                    target_id = ids[j]
                    article_a = state.articles[source_id]
                    article_b = state.articles[target_id]
                    
                    time_gap = abs(article_a["published_at"] - article_b["published_at"]) <= timedelta(hours=48)
                    similar = sims.get((i, j), 0) >= settings.similarity_threshold
                    
                    if time_gap and similar:
                        graph[source_id].add(target_id)
                        graph[target_id].add(source_id)
            
            # Extract connected components
            components = _connected_components(graph)
            
            # Create clusters from components
            for comp in components:
                comp_articles = [state.articles[a_id] for a_id in comp]
                comp_articles.sort(key=lambda x: x["published_at"], reverse=True)
                headline = comp_articles[0]["title"]
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
        print(f"✅ Clustering complete: created {len(new_clusters)} clusters")
        return len(new_clusters)
    
    except Exception as e:
        print(f"❌ Clustering failed: {e}")
        import traceback
        traceback.print_exc()
        state.clusters = {}
        return 0
