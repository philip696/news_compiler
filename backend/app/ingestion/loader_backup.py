import json
import uuid
import random
from pathlib import Path
from datetime import datetime, timezone
import hashlib

from .. import state
from ..core.config import settings


CATEGORY_TO_TOPIC = {
    "ARTS": "technology",
    "ARTS & CULTURE": "technology",
    "BLACK VOICES": "politics",
    "BUSINESS": "finance",
    "COLLEGE": "science",
    "COMEDY": "politics",
    "CRIME": "politics",
    "CULTURE & ARTS": "technology",
    "DIVORCE": "politics",
    "EDUCATION": "science",
    "ENTERTAINMENT": "politics",
    "ENVIRONMENT": "science",
    "FIFTY": "politics",
    "FOOD & DRINK": "politics",
    "GOOD NEWS": "politics",
    "GREEN": "science",
    "HEALTHY LIVING": "health",
    "HOME & LIVING": "politics",
    "IMPACT": "politics",
    "LATINO VOICES": "politics",
    "MEDIA": "politics",
    "MONEY": "finance",
    "PARENTING": "politics",
    "PARENTS": "politics",
    "POLITICS": "politics",
    "QUEER VOICES": "politics",
    "RELIGION": "politics",
    "SCIENCE": "science",
    "SPORTS": "sports",
    "STYLE": "politics",
    "STYLE & BEAUTY": "politics",
    "TASTE": "politics",
    "TECH": "technology",
    "THE WORLDPOST": "politics",
    "TRAVEL": "politics",
    "U.S. NEWS": "politics",
    "WEDDINGS": "politics",
    "WEIRD NEWS": "politics",
    "WELLNESS": "health",
    "WOMEN": "politics",
    "WORLD NEWS": "politics",
    "WORLDPOST": "politics",
}

TOPIC_KEYWORDS = {
    "technology": ["ai", "software", "cloud", "chip", "startup", "model", "tech"],
    "politics": ["election", "senate", "government", "policy", "president", "minister"],
    "finance": ["market", "stocks", "inflation", "bank", "economy", "rates", "investor"],
    "sports": ["match", "league", "goal", "coach", "tournament", "player"],
    "science": ["research", "study", "experiment", "nasa", "physics", "biology"],
    "health": ["hospital", "vaccine", "health", "doctor", "disease", "medical"],
}


def _parse_published(value: str | None) -> datetime:
    if not value:
        return state.now_utc()
    try:
        # Handle ISO format dates (YYYY-MM-DD)
        if isinstance(value, str) and "T" not in value:
            dt = datetime.fromisoformat(value)
        else:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except:
        return state.now_utc()


def _parse_text(value):
    if isinstance(value, str):
        return value[:10000]  # Limit text to 10K chars for memory
    return str(value)[:10000]






def classify_topic(text: str) -> tuple[str, float]:
    normalized = text.lower()
    best_topic = "technology"
    best_score = 0
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for k in keywords if k in normalized)
        if score > best_score:
            best_score = score
            best_topic = topic
    confidence = 0.55 + min(0.4, best_score * 0.05)
    return best_topic, confidence


def text_to_embedding(text: str) -> list[float]:
    """Generate a lightweight embedding using hash-based approach"""
    text = text.lower().split()
    # Create 384-dimensional embedding using hash-based approach
    embedding = [0.0] * 384
    
    for word in text:
        # Use hash to determine which positions to increment
        word_hash = int(hashlib.sha256(word.encode()).hexdigest(), 16)
        for i in range(3):  # Add to 3 random positions per word
            pos = (word_hash + i) % len(embedding)
            embedding[pos] += 1.0
    
    # Normalize
    max_val = max(embedding) if max(embedding) > 0 else 1
    embedding = [x / max_val for x in embedding]
    return embedding


def normalize_record(record: dict, category: str = "") -> dict:
    """Normalize a record from News_Category_Dataset_v3.json"""
    try:
        headline = (record.get("headline") or "").strip()
        description = (record.get("short_description") or "").strip()
        url = (record.get("link") or f"https://example.local/{uuid.uuid4()}").strip()
        authors = (record.get("authors") or "").strip()
        date_str = (record.get("date") or "").strip()
        
        # Extract source from URL
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            source_domain = parsed_url.netloc or "huffpost.com"
        except:
            source_domain = "huffpost.com"
        
        source_id = source_domain.replace(".", "_").replace("-", "_")
        if source_id in state.SOURCES:
            source_name = state.SOURCES[source_id]["name"]
            logo_url = state.SOURCES[source_id].get("logo_url", "")
        else:
            source_name = source_domain.split(".")[0].upper() or "HuffPost"
            logo_url = "/images/logos/default.png"
            state.SOURCES[source_id] = {
                "id": source_id,
                "name": source_name,
                "domain": source_domain,
                "logo_url": logo_url
            }
        
        # Get topic from category
        mapped_category = record.get("category", category)
        topic = CATEGORY_TO_TOPIC.get(mapped_category, "politics")
        
        text = f"{headline} {description}".strip()
        text_to_classify = text.lower()
        
        # Classify confidence based on available data
        if headline and description:
            confidence = 0.85
        elif headline:
            confidence = 0.70
        else:
            confidence = 0.50
        
        embedding = text_to_embedding(text)
        
        # Generate a unique ID based on headline and URL
        article_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
        
        article = {
            "id": article_id,
            "title": headline or "Untitled",
            "content": description or headline or "",
            "url": url,
            "source_id": source_id,
            "source_name": source_name,
            "published_at": _parse_published(date_str),
            "topic": topic,
            "topic_confidence": confidence,
            "embedding": embedding,
            "logo_url": logo_url,
            "main_image": "",  # Will be fetched from webpage if needed
            "category": mapped_category,
            "authors": authors,
        }
        return article
    except Exception as e:
        return None


def ingest_webhose_jsonl(file_path: str | None = None) -> int:
    """
    Load 100 random articles from News_Category_Dataset_v3.json.
    Store category information for later category-based filtering.
    """
    print("🚀 Starting data ingestion from News_Category_Dataset_v3.json...")
    
    dataset_path = Path("/Users/philipdewanto/Downloads/Code/GEB/webhose_extended/News_Category_Dataset_v3.json")
    
    all_articles_by_category = {}
    categories_found = set()
    total_articles = 0
    
    # First pass: scan the dataset and collect articles by category
    print("📊 Scanning dataset for categories...")
    
    try:
        with open(dataset_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                    total_articles += 1
                    
                    category = record.get("category", "UNCATEGORIZED")
                    categories_found.add(category)
                    
                    if category not in all_articles_by_category:
                        all_articles_by_category[category] = []
                    
                    article = normalize_record(record, category=category)
                    if article:
                        all_articles_by_category[category].append(article)
                    
                    # Progress indicator
                    if (line_num + 1) % 50000 == 0:
                        print(f"  📈 Scanned {line_num + 1} articles...")
                
                except Exception as e:
                    pass  # Skip malformed lines
    
    except Exception as e:
        print(f"❌ Error reading dataset: {e}")
        return 0
    
    print(f"✓ Dataset scan complete:")
    print(f"  - Total articles in dataset: {total_articles}")
    print(f"  - Categories found: {len(categories_found)}")
    
    # Store categories in state
    state.available_categories = sorted(list(categories_found))
    state.articles_by_category = all_articles_by_category
    
    print(f"\n📚 Categories ({len(state.available_categories)}):")
    for i, cat in enumerate(state.available_categories, 1):
        count = len(all_articles_by_category.get(cat, []))
        print(f"  {i}. {cat}: {count} articles")
    
    # Second pass: select 100 random articles
    print(f"\n🎲 Selecting 100 random articles from all categories...")
    
    all_available = []
    for category, articles in all_articles_by_category.items():
        all_available.extend(articles)
    
    print(f"  Total available articles: {len(all_available)}")
    
    # Shuffle and take 100
    random.shuffle(all_available)
    selected_articles = all_available[:100]
    
    inserted = 0
    for article in selected_articles:
        if article["id"] not in state.articles:
            state.articles[article["id"]] = article
            state.article_popularity.setdefault(article["id"], 0)
            inserted += 1
    
    print(f"\n✅ Ingestion complete:")
    print(f"  - Loaded 100 random articles into memory")
    print(f"  - Categories available for browsing: {len(state.available_categories)}")
    print(f"  - Total articles in memory: {len(state.articles)}")
    
    return inserted
