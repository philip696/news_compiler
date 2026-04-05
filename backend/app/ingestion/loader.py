"""Data ingestion loaders for the GEB application."""

import json
import uuid
import random
import sys
from pathlib import Path
from datetime import datetime, timezone
import hashlib

from .. import state

# WebHose category to GEB topic mapping
WEBHOSE_CATEGORY_TO_TOPIC = {
    "business": "finance",
    "sport": "sports",
    "tech": "technology",
    "health": "health",
    "politics": "politics",
    "science": "science",
    "entertainment": "politics",
    "world": "politics",
    "domestic": "politics",
}

# Kaggle category to GEB topic mapping  
KAGGLE_CATEGORY_TO_TOPIC = {
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
    """Parse published date from string, default to now if not found."""
    if not value:
        return state.now_utc()
    try:
        # Handle ISO format dates (YYYY-MM-DD or full ISO)
        if isinstance(value, str) and "T" not in value:
            dt = datetime.fromisoformat(value)
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except:
        return state.now_utc()


def text_to_embedding(text: str) -> list[float]:
    """Generate a lightweight embedding using hash-based approach."""
    text_words = text.lower().split()
    # Create 384-dimensional embedding
    embedding = [0.0] * 384
    
    for word in text_words:
        # Use hash to determine which positions to increment
        word_hash = int(hashlib.sha256(word.encode()).hexdigest(), 16)
        for i in range(3):  # Add to 3 positions per word
            pos = (word_hash + i) % len(embedding)
            embedding[pos] += 1.0
    
    # Normalize
    max_val = max(embedding) if max(embedding) > 0 else 1
    embedding = [x / max_val for x in embedding]
    return embedding


def classify_topic(text: str) -> tuple[str, float]:
    """Classify text into a topic based on keyword matching."""
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


def ingest_webhose_jsonl() -> int:
    """Load articles from webhose JSONL file into application state (max 25 for main feed)."""
    jsonl_path = Path(__file__).parent.parent.parent / "data" / "webhose_sample" / "news.jsonl"
    data_path = Path(__file__).parent.parent.parent / "data" / "webhose_sample"
    
    if not jsonl_path.exists():
        print(f"⚠️  WebHose JSONL file not found at {jsonl_path}")
        return 0
    
    try:
        inserted = 0
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                if line.strip():
                    # Load max 50 articles from webhose
                    if inserted >= 50:
                        break
                    
                    article_data = json.loads(line)
                    
                    # Extract fields
                    title = article_data.get("title", "")
                    text = article_data.get("text", "")
                    url = article_data.get("url", f"https://example.local/{uuid.uuid4()}")
                    source_name = article_data.get("thread", {}).get("site", "unknown")
                    source_id = source_name.lower().replace(" ", "_").replace("-", "_")
                    published = article_data.get("thread", {}).get("published", "")
                    raw_category = article_data.get("category", ["news"])[0] if article_data.get("category") else "news"
                    
                    # Map local image for this article (article 1-25 maps to article1.jpeg - article25.jpeg)
                    article_num = inserted + 1
                    image_path = f"/data/webhose_sample/article{article_num}.jpeg"
                    
                    # Topic and embedding
                    combined_text = f"{title} {text}".strip()
                    topic, confidence = classify_topic(combined_text)
                    embedding = text_to_embedding(combined_text)
                    
                    # Convert webhose category to uppercase to match Kaggle categories
                    # Replace hyphens with spaces to handle WORLD-NEWS -> WORLD NEWS
                    normalized_category = raw_category.upper().replace("-", " ")
                    
                    # Map webhose categories to Kaggle TOP_CATEGORIES for consistency
                    WEBHOSE_CATEGORY_MAP = {
                        "TECHNOLOGY": "TECH",
                        "FINANCE": "BUSINESS",
                        "NEWS": "POLITICS",
                        "CULTURE": "ENTERTAINMENT",
                    }
                    normalized_category = WEBHOSE_CATEGORY_MAP.get(normalized_category, normalized_category)
                    article_id = f"webhose_{article_num}"
                    article = {
                        "id": article_id,
                        "title": title or "Untitled",
                        "content": text or title or "",
                        "url": url,
                        "source_id": source_id,
                        "source_name": source_name,
                        "published_at": _parse_published(published),
                        "topic": topic,
                        "topic_confidence": confidence,
                        "embedding": embedding,
                        "logo_url": "",
                        "main_image": image_path,
                        "category": normalized_category,
                    }
                    
                    state.articles[article_id] = article
                    state.article_popularity.setdefault(article_id, 0)
                    
                    # Track categories - webhose articles mixed with same categories as Kaggle
                    if normalized_category not in state.available_categories:
                        state.available_categories.append(normalized_category)
                    if normalized_category not in state.articles_by_category:
                        state.articles_by_category[normalized_category] = []
                    state.articles_by_category[normalized_category].append(article)
                    
                    inserted += 1
        
        print(f"✅ Loaded {inserted} articles from WebHose JSONL (main feed)")
        return inserted
    except Exception as e:
        print(f"❌ Error loading WebHose JSONL: {e}")
        return 0


def ingest_kaggle_dataset() -> int:
    """Load articles from Kaggle dataset organized by category (100 random per category, top categories only)."""
    kaggle_path = Path(__file__).parent.parent.parent / "data" / "webhose_extended" / "News_Category_Dataset_v3.json"
    
    if not kaggle_path.exists():
        print(f"ℹ️  Kaggle dataset not found at {kaggle_path}")
        return 0
    
    # Top categories to include (most populated, most relevant)
    TOP_CATEGORIES = [
        "POLITICS", "ENTERTAINMENT", "WORLD NEWS", "BUSINESS", 
        "TECH", "SPORTS", "SCIENCE", "EDUCATION", "WELLNESS", "TRAVEL"
    ]
    
    try:
        # First pass: collect articles by category (only TOP_CATEGORIES)
        articles_by_category_temp = {}
        processed = 0
        matched = 0
        
        print(f"📊 Scanning Kaggle dataset for top categories...", flush=True)
        sys.stdout.flush()
        
        with open(kaggle_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f):
                if line.strip():
                    try:
                        article_data = json.loads(line)
                        processed += 1
                        
                        kaggle_category = article_data.get("category", "UNCATEGORIZED")
                        
                        # Only process top categories
                        if kaggle_category not in TOP_CATEGORIES:
                            continue
                        
                        matched += 1
                        
                        # Initialize category if not seen
                        if kaggle_category not in articles_by_category_temp:
                            articles_by_category_temp[kaggle_category] = []
                        
                        # Extract fields
                        title = article_data.get("headline", "").strip()
                        description = article_data.get("short_description", "").strip()
                        url = article_data.get("link", f"https://example.local/{uuid.uuid4()}")
                        authors = article_data.get("authors", "")
                        published = article_data.get("date", "")
                        
                        # Prepare text
                        combined_text = f"{title} {description}".strip()
                        if not combined_text:
                            continue
                        
                        # Generate embedding
                        embedding = text_to_embedding(combined_text)
                        
                        # Determine confidence
                        if title and description:
                            confidence = 0.85
                        elif title:
                            confidence = 0.70
                        else:
                            confidence = 0.50
                        
                        # Extract source from URL
                        try:
                            from urllib.parse import urlparse
                            parsed_url = urlparse(url)
                            source_domain = parsed_url.netloc or "huffpost.com"
                        except:
                            source_domain = "huffpost.com"
                        
                        source_id = source_domain.replace(".", "_").replace("-", "_")
                        source_name = source_domain.split(".")[0].upper() or "HuffPost"
                        
                        # Get topic from category
                        topic = KAGGLE_CATEGORY_TO_TOPIC.get(kaggle_category, "politics")
                        
                        # Generate unique ID
                        article_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
                        
                        # Store article data but don't add to state yet
                        article = {
                            "id": article_id,
                            "title": title or "Untitled",
                            "content": description or title or "",
                            "url": url,
                            "source_id": source_id,
                            "source_name": source_name,
                            "published_at": _parse_published(published),
                            "topic": topic,
                            "topic_confidence": confidence,
                            "embedding": embedding,
                            "logo_url": "",
                            "main_image": "",
                            "category": kaggle_category,
                            "authors": authors,
                        }
                        
                        articles_by_category_temp[kaggle_category].append(article)
                        
                        if (line_num + 1) % 50000 == 0:
                            print(f"  📈 Scanned {line_num + 1} articles from Kaggle... (matched: {matched})", flush=True)
                            sys.stdout.flush()
                    
                    except Exception as e:
                        pass  # Skip malformed lines
        
        print(f"✅ Scanned {processed} total Kaggle articles, matched {matched} in top categories, found {len(articles_by_category_temp)} categories", flush=True)
        sys.stdout.flush()
        
        # Second pass: select 100 random from each top category
        print(f"🎲 [Phase 2B] Selecting 100 random articles from {len(TOP_CATEGORIES)} top categories...", flush=True)
        sys.stdout.flush()
        inserted = 0
        
        for category in TOP_CATEGORIES:
            articles_list = articles_by_category_temp.get(category, [])
            if not articles_list:
                print(f"  ⚠ {category}: no articles found")
                continue
            
            # Randomly select up to 100 articles from this category
            num_to_select = min(100, len(articles_list))
            selected_articles = random.sample(articles_list, num_to_select)
            
            # Add to state
            if category not in state.available_categories:
                state.available_categories.append(category)
            if category not in state.articles_by_category:
                state.articles_by_category[category] = []
            
            for article in selected_articles:
                # Skip if article already exists (from webhose)
                if article["id"] not in state.articles:
                    state.articles[article["id"]] = article
                    state.article_popularity.setdefault(article["id"], 0)
                    state.articles_by_category[category].append(article)
                    inserted += 1
            
            print(f"  ✓ {category}: {num_to_select} articles selected", flush=True)
        
        print(f"✅ Loaded {inserted} total articles from Kaggle dataset", flush=True)
        sys.stdout.flush()
        return inserted
    except Exception as e:
        print(f"❌ Error loading Kaggle dataset: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return 0


def ingest_mock_feed() -> int:
    """Load mock articles for development/testing."""
    return ingest_webhose_jsonl()
