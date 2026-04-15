"""Resilient startup handler with comprehensive logging."""

import sys
import os
from pathlib import Path
import time


def setup_startup_logging():
    """Configure logging for startup diagnostics."""
    log_file = Path("/tmp/geb_startup.log")
    
    class DualWriter:
        """Write to both stdout and a log file."""
        def __init__(self, stdout, logfile):
            self.stdout = stdout
            self.logfile = logfile
        
        def write(self, msg):
            self.stdout.write(msg)
            try:
                with open(self.logfile, "a") as f:
                    f.write(msg)
            except:
                pass
        
        def flush(self):
            self.stdout.flush()
    
    sys.stdout = DualWriter(sys.stdout, log_file)
    sys.stderr = DualWriter(sys.stderr, log_file)
    
    print(f"\n{'='*60}")
    print(f"GEB Application Starting at {log_file}")
    print(f"Python: {sys.version}")
    print(f"Path: {os.getcwd()}")
    print(f"{'='*60}\n")


def run_startup_sequence():
    """Run the startup sequence with maximum resilience."""
    global_start = time.time()
    
    print("🚀 Initializing application components...\n")
    
    try:
        print(f"[{time.time()-global_start:.2f}s] Importing modules...")
        from . import state
        from .ingestion.loader import ingest_mock_feed, ingest_kaggle_dataset, ingest_yahoo_finance_articles
        from .clustering.engine import build_story_clusters
        print(f"[{time.time()-global_start:.2f}s] ✅ Modules imported\n")
    except Exception as e:
        print(f"[{time.time()-global_start:.2f}s] ❌ FATAL: Failed to import modules: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # Check if already initialized
    if state.startup_complete:
        print(f"[{time.time()-global_start:.2f}s] ✅ Startup already completed in previous run, resuming...\n")
        return
    
    # Phase 1: WebHose
    print(f"[{time.time()-global_start:.2f}s] 📥 [Phase 1/4] Loading WebHose articles...")
    phase1_start = time.time()
    try:
        count = ingest_mock_feed()
        phase1_time = time.time() - phase1_start
        print(f"[{time.time()-global_start:.2f}s] ✅ WebHose: {count} articles loaded ({phase1_time:.2f}s)\n")
    except Exception as e:
        phase1_time = time.time() - phase1_start
        print(f"[{time.time()-global_start:.2f}s] ❌ WebHose failed after {phase1_time:.2f}s (continuing): {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
    
    # Phase 2: Kaggle
    print(f"[{time.time()-global_start:.2f}s] 📥 [Phase 2/5] Loading Kaggle dataset...")
    phase2_start = time.time()
    try:
        count = ingest_kaggle_dataset()
        phase2_time = time.time() - phase2_start
        print(f"[{time.time()-global_start:.2f}s] ✅ Kaggle: {count} articles loaded ({phase2_time:.2f}s)")
        print(f"[{time.time()-global_start:.2f}s] 📊 Total articles: {len(state.articles)}\n")
    except Exception as e:
        phase2_time = time.time() - phase2_start
        print(f"[{time.time()-global_start:.2f}s] ❌ Kaggle failed after {phase2_time:.2f}s (continuing): {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
    
    # Phase 3: Yahoo Finance (async, requires special handling in event loop)
    print(f"[{time.time()-global_start:.2f}s] 📥 [Phase 3/5] Loading Yahoo Finance articles...")
    phase3_start = time.time()
    try:
        import asyncio
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop:
            # We're in an event loop, use create_task or run_until_complete approach
            # For startup, we'll just call it synchronously via a helper
            from ..services.news_service import NewsService
            import httpx
            
            # Create a simple sync wrapper for the async call
            news_service = NewsService()
            
            # Fetch directly using sync httpx for startup
            try:
                with httpx.Client(timeout=30) as client:
                    params = {
                        "region": "US",
                        "lang": "en",
                        "count": 50,
                    }
                    response = client.get(news_service.yahoo_finance_url, params=params)
                    
                    if response.status_code == 200:
                        # Process articles
                        data = response.json()
                        count = 0
                        category = "💰 Finance"
                        
                        if category not in state.available_categories:
                            state.available_categories.append(category)
                        if category not in state.articles_by_category:
                            state.articles_by_category[category] = []
                        
                        for idx, item in enumerate(data.get("finance", {}).get("result", [])[:50]):
                            try:
                                from .ingestion.loader import classify_topic, text_to_embedding, _parse_published
                                import uuid
                                
                                title = item.get("title", "").strip()
                                content = item.get("summary", "").strip()
                                url = item.get("link", f"https://example.local/{uuid.uuid4()}")
                                source_name = "Yahoo Finance"
                                published = item.get("pubDate", "")
                                image_url = item.get("thumbnail", {}).get("url", "") if item.get("thumbnail") else ""
                                
                                if not title or not content:
                                    continue
                                
                                combined_text = f"{title} {content}"
                                topic, confidence = classify_topic(combined_text)
                                embedding = text_to_embedding(combined_text)
                                
                                article_id = f"yahoo_finance_{count}_{idx}"
                                source_id = source_name.lower().replace(" ", "_")
                                
                                article = {
                                    "id": article_id,
                                    "title": title,
                                    "content": content,
                                    "url": url,
                                    "source_id": source_id,
                                    "source_name": source_name,
                                    "published_at": _parse_published(published),
                                    "topic": topic,
                                    "topic_confidence": confidence,
                                    "embedding": embedding,
                                    "logo_url": "",
                                    "main_image": image_url,
                                    "category": category,
                                }
                                
                                if article_id not in state.articles:
                                    state.articles[article_id] = article
                                    state.article_popularity.setdefault(article_id, 0)
                                    state.articles_by_category[category].append(article)
                                    count += 1
                            except Exception as e:
                                pass
                        
                        phase3_time = time.time() - phase3_start
                        if count > 0:
                            print(f"[{time.time()-global_start:.2f}s] ✅ Yahoo Finance: {count} articles loaded ({phase3_time:.2f}s)")
                            print(f"[{time.time()-global_start:.2f}s] 📊 Total articles: {len(state.articles)}\n")
                        else:
                            print(f"[{time.time()-global_start:.2f}s] ℹ️  Yahoo Finance: 0 articles loaded ({phase3_time:.2f}s)\n")
                    else:
                        phase3_time = time.time() - phase3_start
                        print(f"[{time.time()-global_start:.2f}s] ⚠️  Yahoo Finance API returned {response.status_code} ({phase3_time:.2f}s)\n")
            except Exception as e:
                phase3_time = time.time() - phase3_start
                print(f"[{time.time()-global_start:.2f}s] ⚠️  Yahoo Finance request failed ({phase3_time:.2f}s): {type(e).__name__}\n")
        else:
            # No event loop, use asyncio.run
            count = asyncio.run(ingest_yahoo_finance_articles())
            phase3_time = time.time() - phase3_start
            print(f"[{time.time()-global_start:.2f}s] ✅ Yahoo Finance: {count} articles loaded ({phase3_time:.2f}s)")
            print(f"[{time.time()-global_start:.2f}s] 📊 Total articles: {len(state.articles)}\n")
    
    except Exception as e:
        phase3_time = time.time() - phase3_start
        print(f"[{time.time()-global_start:.2f}s] ⚠️  Yahoo Finance failed after {phase3_time:.2f}s (non-critical): {type(e).__name__}: {str(e)[:80]}\n")
    
    # Mark startup complete
    print(f"[{time.time()-global_start:.2f}s] ✅ [Phase 4/5] Startup checkpoint saved")
    state.startup_complete = True
    print(f"[{time.time()-global_start:.2f}s] 💾 state.startup_complete = True\n")
    
    # Phase 5: Background clustering (non-blocking)
    print(f"[{time.time()-global_start:.2f}s] 🔄 [Phase 5/5] Starting background clustering...")
    try:
        import threading
        
        def cluster_worker():
            cluster_start = time.time()
            try:
                print(f"[{time.time()-global_start:.2f}s]    🔄 Clustering {len(state.articles)} articles...")
                count = build_story_clusters()
                cluster_time = time.time() - cluster_start
                print(f"[{time.time()-global_start:.2f}s]    ✅ Clustering complete: {count} clusters ({cluster_time:.2f}s)\n")
            except Exception as cluster_err:
                cluster_time = time.time() - cluster_start
                print(f"[{time.time()-global_start:.2f}s]    ⚠️  Clustering failed after {cluster_time:.2f}s (non-critical): {type(cluster_err).__name__}: {cluster_err}\n")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=cluster_worker, daemon=True, name="ClusterWorker")
        thread.start()
        print(f"[{time.time()-global_start:.2f}s] ✅ Background clustering thread started\n")
    except Exception as e:
        print(f"[{time.time()-global_start:.2f}s] ⚠️  Threading setup failed: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
    
    total_time = time.time() - global_start
    print("="*60)
    print("✅ APPLICATION STARTUP COMPLETE")
    print("="*60)
    print(f"Total startup time: {total_time:.2f}s")
    print(f"Articles: {len(state.articles)}")
    print(f"Categories: {len(state.available_categories)}")
    print(f"Clusters: {len(state.clusters)}")
    print(f"Server should be accepting requests now")
    print("="*60 + "\n")
